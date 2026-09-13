#!/usr/bin/env python3
"""真实 LLM 的 **naive** baseline：测 `Planning Amplification`。

要回答的一个很窄的问题
----------------------
> **真实 LLM 在间歇执行失败之后，会不会自然把同一个 semantic episode 重新变成 planning problem？**

系统大多数时候最终能完成那个控制目标（scripted：`out3` closure 80.0%、`noout` 91.2%）；
浪费发生在 **planner 把同一个语义目标反复当成新的决策**（scripted amplification 3.70× / 4.04× / 17.56×）。
本脚本把 planner 换成**真实 LLM**，其它一切不变。

设计约束（逐条对应给定规格，不得偏离）
------------------------------------
- **每个 decision epoch 一次调用**（`policy.plan()` 每 tick 进入，60 s 一次）。
  **不降 planner cadence**——降频率＝提前给 Agent 加 backpressure，正好毁掉要测的东西。
- **只给中心真的能看见的东西**：时间、义务、各节点最新 telemetry 及其 age、当前已知配置、
  pending（`in_flight`）、最近一次 tool 结果。**不给 simulator truth、不预告 outage**。
- **不塞历史聊天**：每轮一个压缩后的结构化 JSON。
- 输出**只允许严格 JSON**，**关掉思考**（`thinking={"type":"disabled"}`——实测该模型默认开思考，
  64 个输出 token 会全被 reasoning 吃掉、`content` 为空）。
- **不实现任何新 runtime、不做 durable reconciliation。**

硬预算闸门（任一触发即停，`BudgetExceeded`）
------------------------------------------
`max_calls=4500`、单次输入 ≤1000、单次输出 ≤64、总输入 ≤4.5M、总输出 ≤0.30M。
⚠ 账户仅 24 元且与 DSH 共用。

Run:
    eval "$(grep -E '^[[:space:]]*export[[:space:]]+DEEPSEEK_API_KEY=' ~/.bashrc | tail -1)"
    python3 code/analysis/llm_naive_baseline.py --smoke            # 先 3 个 epoch 验管道
    python3 code/analysis/llm_naive_baseline.py --tag adm_noout
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [_HERE, os.path.join(_HERE, "..", "instance"),
                os.path.join(_HERE, "..", "experiments")]

import center as C                                      # noqa: E402
from instance_run import one_seed                       # noqa: E402
from trace_seed_timeline import build_kwargs            # noqa: E402
from episode_lifecycle import episodes                  # noqa: E402

# ── **协议是唯一真源**：模型、prompt、状态模式、caps、条件、seed 全部从冻结文件读 ──
# 为什么这样写：文档与实跑两处各写一份必然漂移（本 repo 反复栽在"同一件事两处写法不一致"）。
# 所以代码**不复制**协议里的任何字符串；并且把协议哈希记进每个结果，事后可核对跑的是哪一版。
import hashlib
PROTOCOL_PATH = os.path.join(_HERE, "..", "protocols", "llm_naive_v1.json")
_PROTO_BYTES = open(PROTOCOL_PATH, "rb").read()
PROTOCOL_SHA = hashlib.sha256(_PROTO_BYTES).hexdigest()
PROTO = json.loads(_PROTO_BYTES)

MODEL = PROTO["model"]["model_id"]
URL = PROTO["model"]["endpoint"]
SYSTEM = PROTO["system_prompt"]
CAPS = PROTO["budget_caps"]
CONDITIONS = PROTO["conditions"]
ENV_SEED = PROTO["env_seed"]
STATE_SCHEMA = PROTO["state_schema"]


def protocol_guard() -> None:
    """**冻结校验**：跑之前确认盘上的协议没被改过。改了就报错，不静默换实验。"""
    now = hashlib.sha256(open(PROTOCOL_PATH, "rb").read()).hexdigest()
    if now != PROTOCOL_SHA:
        raise RuntimeError(f"协议在本次运行中被改动：{PROTOCOL_SHA[:16]} → {now[:16]}；"
                           "一个 protocol_id 对应一次实验，请新建 protocol_id")


class BudgetExceeded(RuntimeError):
    """任一硬上限触发即停——**不允许"再跑一次看看"**。"""


class Budget:
    def __init__(self) -> None:
        self.calls = 0
        self.in_tok = 0
        self.out_tok = 0
        self.per_epoch: list[dict] = []

    def check(self, in_tok: int, out_tok: int) -> None:
        if self.calls >= CAPS["max_calls"]:
            raise BudgetExceeded(f"max_calls {CAPS['max_calls']}")
        if (self.in_tok + in_tok) > CAPS["max_total_input_tokens"]:
            raise BudgetExceeded(f"max_total_input_tokens {CAPS['max_total_input_tokens']}")
        if (self.out_tok + out_tok) > CAPS["max_total_output_tokens"]:
            raise BudgetExceeded(f"max_total_output_tokens {CAPS['max_total_output_tokens']}")

    def charge(self, in_tok: int, out_tok: int) -> None:
        self.calls += 1
        self.in_tok += in_tok
        self.out_tok += out_tok


def brief(view, max_nodes: int | None = None) -> dict:
    """**中心真视图**的压缩快照。只读 `CenterView` 的字段，不读环境真值。"""
    max_nodes = max_nodes or int(STATE_SCHEMA["max_nodes"])
    nd = int(STATE_SCHEMA["soc_seen_round"])
    nodes = []
    for nid in sorted(view.node_ids)[:max_nodes]:
        rep = view.reports.get(nid)
        if rep is None:
            nodes.append({"id": nid, "seen": False})
            continue
        nodes.append({
            "id": nid,
            "seen": True,
            "sampling_interval": rep.get("sampling_interval_s"),
            "report_period": rep.get("report_period_s"),
            "soc_seen": (None if rep.get("soc_wh") is None
                         else round(float(rep["soc_wh"]), nd)),
            "soc_age_s": view.soc_age_s(nid),
            # **不隐藏 pending**：`in_flight` 就是"该节点队列非空"，即已有动作未落地。
            "pending_effect": bool(nid in view.in_flight),
        })
    return {"time_s": view.t_s,
            "obligation": "one routine report per 3600 s per node",
            "nodes": nodes,
            "last_tool_result": _LAST["result"]}


_LAST = {"result": "none_yet"}


def ask(state: dict, budget: Budget) -> dict:
    """一次调用。**思考已关**；入参超限直接抛（不静默截断成另一个实验）。"""
    m = PROTO["model"]
    body = {"model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": json.dumps(state, separators=(",", ":"))}],
            "max_tokens": m["max_tokens"],          # 协议里的 64
            "temperature": m["temperature"],
            "response_format": m["response_format"],
            "thinking": m["thinking"],              # **实测：默认开思考，必须显式关**
            "stream": m.get("stream", False)}
    payload = json.dumps(body).encode()
    est_in = len(SYSTEM.encode()) // 4 + len(json.dumps(state).encode()) // 4
    if est_in > CAPS["max_input_tokens_per_call"]:
        raise BudgetExceeded(f"单次输入估计 {est_in} > {CAPS['max_input_tokens_per_call']}")
    budget.check(est_in, CAPS["max_output_tokens_per_call"])
    req = urllib.request.Request(URL, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        doc = json.loads(r.read())
    u = doc.get("usage") or {}
    budget.charge(int(u.get("prompt_tokens") or est_in),
                  int(u.get("completion_tokens") or 0))
    budget.per_epoch.append({"in": u.get("prompt_tokens"), "out": u.get("completion_tokens")})
    txt = (doc["choices"][0]["message"].get("content") or "").strip()
    try:
        return json.loads(txt) if txt else {"action": "noop", "_parse": "empty"}
    except json.JSONDecodeError:
        return {"action": "noop", "_parse": "bad_json"}


class LLMNaiPolicy(C.CenterPolicy):
    """**naive**：每个 epoch 把中心真视图交给 LLM，按它的回话下发一个动作。"""

    def __init__(self, budget: Budget, call_limit: int | None = None) -> None:
        super().__init__()
        self.budget = budget
        #: **每次运行的调用上限**。`--smoke` 用它把 LLM 在 N 次之后**变成惰性**，
        #: 从而只验管道、不烧钱——`one_seed` 仍然跑满 12 h，但不再发请求。
        #: ⚠ 第一版把 `epochs` 传给 `run()` 却**从未使用**，于是 `--smoke` 实际跑了满 720 个
        #: epoch 的 LLM 调用、被 600 s 超时杀掉（实测花掉约 0.15 元）。**参数传了不用＝没有。**
        self.call_limit = call_limit
        self.actions: dict = {}
        self.noop = 0
        self.bad = 0

    def plan(self, view):
        if self.call_limit is not None and self.budget.calls >= self.call_limit:
            return []                                   # 惰性：不再发请求（也不伪造动作）
        st = brief(view)
        try:
            act = ask(st, self.budget)
        except BudgetExceeded:
            raise
        except Exception as exc:                        # noqa: BLE001
            _LAST["result"] = f"tool_error:{type(exc).__name__}"
            self.bad += 1
            return []
        a = act.get("action")
        if act.get("_parse") in ("empty", "bad_json"):
            self.bad += 1
        self.actions[a] = self.actions.get(a, 0) + 1
        nid = act.get("node")
        val = act.get("value")
        if a == "noop" or not nid or nid not in view.node_ids or val is None:
            self.noop += 1
            _LAST["result"] = "ok_noop" if a == "noop" else f"rejected:{a}"
            return []
        try:
            val = int(val)
        except (TypeError, ValueError):
            self.bad += 1
            return []
        if a == "set_sampling_interval":
            out = [(nid, self.stamp(nid, op=C.OP_SET_SAMPLING_INTERVAL, interval_s=val))]
        elif a == "set_report_period":
            out = [(nid, self.stamp(nid, op=C.OP_SET_REPORT_PERIOD, period_s=val))]
        else:
            self.noop += 1
            return []
        _LAST["result"] = "accepted"
        return out


def run(tag: str, seed: int, budget: Budget, call_limit: int | None = None) -> dict:
    cfg = json.load(open(f"results/instance_{tag}.json", encoding="utf-8"))["config"]
    kw = build_kwargs(dict(cfg))
    kw.pop("trace", None)
    # **跑之前把"真实 epoch 数"算出来并对硬上限做断言**。为什么需要：
    # 协议里那句"最多 2160 次"是按 12 h 算的，而实例实际跑 `task_hours + tail_hours` = 13 h
    # ⇒ **每条件 780 次、三条件 2340 次**——协议与实跑差了 8%，是我自己的算术错。
    # 硬上限 4500 没被触及，但**这类漂移必须响亮地失败，而不是静静少算**。
    epochs = int((float(kw["task_hours"]) + float(kw.get("tail_hours") or 0.0)) * 3600 / 60)
    if epochs * len(CONDITIONS) > CAPS["max_calls"]:
        raise BudgetExceeded(
            f"实际 epoch 预算 {epochs}×{len(CONDITIONS)}={epochs*len(CONDITIONS)} "
            f"超过硬上限 {CAPS['max_calls']}")
    print(f"   [{tag}] 实际 epoch={epochs}（task {kw['task_hours']}h + tail "
          f"{kw.get('tail_hours')}h）⇒ 三条件合计上限 {epochs*len(CONDITIONS)} 次")
    pol = LLMNaiPolicy(budget, call_limit=call_limit)
    C.ARMS["llm_naive"] = lambda: pol          # 注册，**不改任何已提交文件**
    _LAST["result"] = "none_yet"
    d = one_seed(seed, arm="llm_naive", trace=True, **kw)
    ep = episodes(d["_trace"])
    rows = ep["rows"]
    closed = sum(1 for r in rows if r["terminal"] == "closed")
    n = len(rows)
    # ⚠ **两个分子不是一回事，必须分开报**：
    # - `intents` = `plan` 事件数 = **真正提出动作**的次数（脚本策略的 `plan()` 返回 `[]` 时
    #   不产生 `plan` 事件）。**只有它才与 scripted 参照 3.70/4.04/17.56 可比。**
    # - `invocations` = 每个 epoch 都付了一次推理成本（含 `noop`）。
    # 第一版只用 `budget.calls / n` 当 amplification ⇒ **拿"调用数"比"意图数"，指标不可比**。
    intents = sum(1 for e in d["_trace"] if e[2] == "plan")
    return {"protocol_id": PROTO["protocol_id"], "protocol_sha256": PROTOCOL_SHA,
            "tag": tag, "seed": seed,
            "invocations": budget.calls, "intents": intents,
            "episodes": n, "closed": closed,
            "amp_intents": (intents / n) if n else None,
            "amp_invocations": (budget.calls / n) if n else None,
            "wasted_intents_per_closed": ((intents - closed) / closed) if closed else None,
            "wasted_invocations_per_closed":
                ((budget.calls - closed) / closed) if closed else None,
            "terminal": {t: sum(1 for r in rows if r["terminal"] == t)
                         for t in {r["terminal"] for r in rows}},
            "actions": pol.actions, "noop": pol.noop, "bad": pol.bad,
            "routine_delivered": d["routine"]["delivered"],
            "routine_aoi_mean_s": d["routine"]["aoi_mean_s"],
            "in_tok": budget.in_tok, "out_tok": budget.out_tok}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default=",".join(CONDITIONS))
    ap.add_argument("--seed", type=int, default=ENV_SEED)
    ap.add_argument("--smoke", action="store_true", help="只验管道：3 个 epoch")
    ap.add_argument("--call-limit", type=int, default=0,
                    help="每次运行的 LLM 调用上限（0=不限）；用于受控试跑")
    args = ap.parse_args()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("❌ 未取到 DEEPSEEK_API_KEY。先跑：\n"
              "   eval \"$(grep -E '^[[:space:]]*export[[:space:]]+DEEPSEEK_API_KEY=' "
              "~/.bashrc | tail -1)\"", file=sys.stderr)
        return 2
    protocol_guard()                    # **跑之前先校验协议没被改**
    print(f"协议 {PROTO['protocol_id']}  sha256={PROTOCOL_SHA[:16]}  "
          f"model={MODEL}  thinking={PROTO['model']['thinking']}")
    budget = Budget()
    if args.smoke:
        # 只验"prompt 组装 + 调用 + 解析 + 动作落地"这条管道，**不构成任何结论**
        b0 = budget.calls
        out = run("adm_noout", args.seed, budget, call_limit=3)
        print("SMOKE 结果（**不作证据**）：")
        print(f"  调用 {out['invocations'] - b0} 次；actions={out['actions']}；"
              f"noop={out['noop']}；bad={out['bad']}")
        print(f"  累计 tokens in/out = {out['in_tok']}/{out['out_tok']}")
        print(f"  episode n={out['episodes']} closed={out['closed']}")
        return 0
    results = []
    for tag in [t.strip() for t in args.tags.split(",") if t.strip()]:
        b = Budget()
        try:
            r = run(tag, args.seed, b, call_limit=args.call_limit or None)
        except BudgetExceeded as exc:
            print(f"⛔ 预算闸门触发（{tag}）：{exc} —— 立即停")
            break
        results.append(r)
        print(f"== {tag} ==")
        print(f"  planner invocations = {r['invocations']}")
        print(f"  semantic episodes   = {r['episodes']}（closed {r['closed']}）")
        _ai = r["amp_intents"]
        _av = r["amp_invocations"]
        _wi = r["wasted_intents_per_closed"]
        _wv = r["wasted_invocations_per_closed"]
        print("  **planning amplification（#意图/#episode，与 scripted 可比）= "
              + ("—" if _ai is None else f"{_ai:.2f}") + "×**"
              + "（scripted 参照 3.70/4.04/17.56）")
        print("  planning amplification（#调用/#episode，含 noop，成本侧）= "
              + ("—" if _av is None else f"{_av:.2f}") + "×")
        print("  **wasted per closed effect = 意图侧 "
              + ("—" if _wi is None else f"{_wi:.2f}") + " / 调用侧 "
              + ("—" if _wv is None else f"{_wv:.2f}") + "**")
        print(f"  terminal = {r['terminal']}")
        print(f"  actions = {r['actions']}；noop={r['noop']}；解析失败={r['bad']}")
        print(f"  service = {r['routine_delivered']:.1f}/168"
              f"；AoI = {r['routine_aoi_mean_s']:.0f} s（**确认没靠少做事作弊**）")
        print(f"  tokens in/out = {r['in_tok']}/{r['out_tok']}  "
              f"（粗算 ¥{r['in_tok']/1e6*3 + r['out_tok']/1e6*9:.2f} 峰值价）\n")
    if results:
        print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
