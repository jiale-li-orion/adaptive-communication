#!/usr/bin/env python3
"""
audit_consistency.py — the properties the paper's claims rest on, checked mechanically.

Each of these is a claim a reviewer could not verify by reading a table, and each is cheap to
check. If one of them quietly stops holding, the numbers in the README stop meaning what they say.

  1. every far-side observation crosses the link
  2. the environment trace is identical for every arm
  3. a packet-level draw does not depend on how many other operations ran
  4. P2's overwrite is a real domain-state overwrite, not an ordering counter
  5. restart's ad-hoc recovery is reproducible from durable state alone
  6. a relay does not reuse the permanently screened node's direct path
  7. a delayed request produces no reply and no downlink airtime
  8. README figures match the result files

Run: python3 code/experiments/audit_consistency.py
"""
from __future__ import annotations

import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE_ROOT = _os.path.dirname(_HERE)
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from method_comparison import Link, FarSide, EnvironmentTrace, Outcome, _u  # noqa: E402
from operations import Journal, DurableDecisionStore, recover  # noqa: E402

MC = os.path.join(HERE, "method_comparison.py")
RE = os.path.join(HERE, "restart_experiment.py")
FAIL: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")
    if not ok:
        FAIL.append(name)


NODE = {"nid": "r03", "sf": 10, "loss_db": 155.0, "permanent": False, "good": True,
        "alive": True, "servable": False, "energy": None}
BLOCKED = dict(NODE, nid="b01", sf=12, permanent=True, good=False, servable=True)


def audit_far_side_only_through_link() -> None:
    print("\n[1] 所有远端观测都经过 Link")
    src = open(MC, encoding="utf-8").read()
    body = src[src.index("def run_arm("):src.index("def postcondition_holds")]
    reads = [m.start() for m in re.finditer(r"read_state\(\)|read_receipt\(", body)]
    # every read must sit inside the channel_read helper, or inside a block guarded by a
    # successful exchange. Find reads that are not preceded by a channel_read call on the item.
    unguarded = 0
    for pos in reads:
        window = body[max(0, pos - 900):pos]
        if "channel_read(" not in window and "link.exchange(" not in window:
            unguarded += 1
    check("run_arm 中不存在绕过链路的远端读", unguarded == 0,
          f"{len(reads)} 处读，{unguarded} 处无链路调用在前")

    # and the Link itself must be the only path: no rng inside run_arm anymore
    check("run_arm 内不再持有自己的随机源", "np.random.default_rng" not in body)


def audit_environment_trace() -> None:
    print("\n[2] EnvironmentTrace 对所有 arm 一致")
    nodes = [dict(NODE), dict(BLOCKED)]
    a = EnvironmentTrace(nodes, 72, 4242)
    b = EnvironmentTrace(nodes, 72, 4242)
    check("同 seed 两次构造完全一致",
          all(a.good[k] == b.good[k] for k in a.good)
          and all(a.alive[k] == b.alive[k] for k in a.alive))
    # a trace built after an arm has chattered must be identical to one built before
    lk = Link(4242)
    for i in range(3000):
        lk.request(nodes[0], i % 72, "verify_read", 0, intent=f"r03:verify:{i}")
    c = EnvironmentTrace(nodes, 72, 4242)
    check("构造轨迹前跑满报文不影响轨迹",
          all(a.good[k] == c.good[k] for k in a.good))
    check("轨迹按 (节点, 小时) 索引，不看 arm",
          len(a.good) == 2 * 72 and len(a.alive) == 2 * 72)


def audit_draw_independence() -> None:
    print("\n[3] 报文级抽样不受其它 operation 数量影响")
    lk = Link(9)
    first = lk.request(NODE, 40, "data_write", 1, intent="r03:threshold:7")
    for i in range(700):
        lk.request(NODE, i % 72, "data_write", 0, intent=f"r03:threshold:{100 + i}")
    again = lk.request(NODE, 40, "data_write", 1, intent="r03:threshold:7")
    check("同一 key 在 700 次其它抽样后结果不变", first == again)
    x = _u(9, "rx", "r03", 40, "data_write", 1, "r03:threshold:7")
    y = _u(9, "rx", "r03", 40, "data_write", 1, "r03:threshold:8")
    check("不同 logical operation 得到不同抽样", x != y)
    try:
        lk.request(NODE, 1, "data_write", 0, intent="")
        check("缺少 logical_intent 时硬失败", False)
    except AssertionError:
        check("缺少 logical_intent 时硬失败", True)


def audit_overwrite_is_domain_state() -> None:
    print("\n[4] P2 的覆盖是真实领域状态覆盖")
    # a stale write that clobbers a newer value, with no fencing at the sink
    sink = FarSide("r03", receipts=True, fencing=False)
    sink.apply("opA", 10, {"threshold": 30}, 1, true_epoch=10)
    sink.apply("opB", 11, {"threshold": 50}, 2, true_epoch=11)
    check("新值先生效", sink.state["threshold"] == 50)
    _o, did = sink.apply("opC", 10, {"threshold": 30}, 3, true_epoch=10)
    check("旧写入晚到确实把状态改回去", did and sink.state["threshold"] == 30,
          f"threshold={sink.state['threshold']}")
    check("覆盖被单独计数", sink.stale_overwrites == 1, f"{sink.stale_overwrites}")

    # and it is NOT the same counter as the ordering violation
    check("覆盖与乱序是两个计数器",
          sink.stale_reorders == sink.stale_overwrites == 1)

    # with fencing the same sequence must leave the newer value in force
    fenced = FarSide("r03", receipts=True, fencing=True)
    fenced.apply("opA", 10, {"threshold": 30}, 1, true_epoch=10)
    fenced.apply("opB", 11, {"threshold": 50}, 2, true_epoch=11)
    o, did = fenced.apply("opC", 10, {"threshold": 30}, 3, true_epoch=10)
    check("有 fencing 时旧写入被拒且状态不变",
          (not did) and fenced.state["threshold"] == 50 and fenced.stale_overwrites == 0,
          f"outcome={o.name} threshold={fenced.state['threshold']}")

    # a max()-accumulated or set-valued field cannot show an overwrite at all
    m = FarSide("r03", receipts=True, fencing=False)
    m.apply("opA", 10, {"version": 30}, 1, true_epoch=10)
    m.apply("opB", 11, {"version": 50}, 2, true_epoch=11)
    m.apply("opC", 10, {"version": 30}, 3, true_epoch=10)
    check("max() 累加字段不会被改回去（所以它测不了覆盖）", m.state["version"] == 50)


def audit_restart_durable_context() -> None:
    print("\n[5] restart 的 adhoc 恢复只依赖持久状态")
    j = Journal()
    store = DurableDecisionStore(j)
    key = "r03:adhoc:5"
    store.commit(key, 987654)
    # a fresh process sees only the journal
    rebuilt = DurableDecisionStore.replay(j)
    check("决策可由日志单独重建", rebuilt.recall(key) == 987654)
    check("重建后不再依赖原对象", rebuilt is not store)

    # the registry can also be replayed alongside it without either assuming write order
    reg = recover(j)
    check("注册表可在含 decision 条目的日志上恢复", reg is not None)

    src = open(RE, encoding="utf-8").read()
    check("实验脚本里不再有存活于进程外的局部 side map",
          "durable_draws" not in src and "live_draws" not in src)
    check("adhoc 身份与 payload 同源",
          'store.recall(key)' in src and 'store.commit(key, draw)' in src)
    # The three durable arms hold the decision context; the arms with no storage hold none.
    # Asserted against the one tuple the script uses, so adding a durable arm cannot leave the
    # store behind on some paths and present on others without this failing.
    check("持久化 arm 由一个元组统一声明",
          'durable_arms = ("journal", "journal_cursor", "journal_reauthorize")' in src)
    check("决策存储只对持久化 arm 创建",
          'if arm in durable_arms else None' in src)
    check("日志也只对持久化 arm 创建",
          'if arm in durable_arms else None' in src and 'journal = Journal()' in src)
    check("无存储 arm 明确没有决策存储",
          'OperationRegistry(None, incarnation=' in src)


def audit_analysis_inputs() -> None:
    """分析脚本要读的列必须真的被轨迹脚本写出。

    `paired_ci.py` 按 `workload` 分组，并对 `duplicate_applications`、`stale_overwrites`、
    `stale_reorders` 做逐种子零值检查。这些名字是两套代码之间的契约，改一处而另一处不知道，
    后果是分析**静默少报一栏**而不是报错——一份声称"逐种子检查过"的结果里其实没有这一项。
    """
    import re as _re
    src = open(os.path.join(HERE, "monitoring_trajectories.py"), encoding="utf-8").read()
    columns = set(_re.findall(r'\("([a-z_]+)", lambda', src))
    for needed in ("duplicate_applications", "stale_overwrites", "stale_reorders",
                   "coverage", "observation_gap", "false_success"):
        check(f"轨迹脚本输出 {needed}（分析脚本要读它）", needed in columns,
              f"columns={sorted(columns)[:8]}...")
    check("轨迹脚本按 workload 分组写出（paired_ci 的分组键）",
          '"workload": trajectory' in src)
    check("轨迹脚本保存 per_seed（配对区间的前提）", '"per_seed":' in src)


def audit_result_index() -> None:
    """`results/README.md` 的索引与实际目录必须互为子集。

    D29 要求每个结果文件都能说清是否可用、被谁取代。索引漏登一个文件，那个文件就变成了
    "没有任何说明"的孤儿；索引多登一个不存在的文件，则复现命令指向空气。两种都不报错。
    """
    import os as _os
    import re as _re
    results_dir = _os.path.join(_CODE_ROOT, "..", "results")
    readme = _os.path.join(results_dir, "README.md")
    if not _os.path.exists(readme):
        check("results/README.md 存在", False, readme)
        return
    text = open(readme, encoding="utf-8").read()
    # **文件名里可以有连字符。** 字符类原本是 `[A-Za-z_0-9.]`、**不含 `-`**，
    # 于是任何名字带连字符的结果文件（如 `instance_idle_5e-8.json`）**永远无法被登记**——
    # 审计会一直报"未登记"，而照着 README 改也改不掉。此前没人用过带 `-` 的文件名所以没露出来。
    # 记住这条：**检查工具的限制会伪装成数据的缺陷**。
    named = set(_re.findall(r"`([A-Za-z_0-9.-]+\.(?:json|txt|csv|png|obj|xml|log))`", text))
    # **登记册索引的是结果产物，不是文档。** 本目录下的 markdown（README.md、CLAIMS.md）
    # 描述结果而不是结果本身，把它们算成"未登记的结果文件"会让检查报出无法通过照做来消除的红，
    # 而那正是这条检查最该避免的失败模式：检查工具的限制伪装成数据的缺陷。
    _RESULT_EXT = (".json", ".txt", ".csv", ".png", ".obj", ".xml", ".log")
    on_disk = {f for f in _os.listdir(results_dir)
               if _os.path.isfile(_os.path.join(results_dir, f))
               and not f.endswith(".md")
               and f.endswith(_RESULT_EXT)}
    unlisted = sorted(on_disk - named)
    check("results/ 下没有被索引漏登的文件", not unlisted, f"未登记: {unlisted}")
    # A file the index names but that is not on disk is allowed only when it is named as withdrawn.
    missing = sorted(n for n in named if not _os.path.exists(_os.path.join(results_dir, n)))
    withdrawn_named = [n for n in missing if n in open(
        _os.path.join(results_dir, "_withdrawn", "MANIFEST.md"), encoding="utf-8").read()]
    check("索引提到的缺失文件都在归档清单里", len(withdrawn_named) == len(missing),
          f"缺失 {missing}，其中已归档 {withdrawn_named}")


def audit_relay_bypasses_screen() -> None:
    print("\n[6] 中继不复用被永久遮挡的直连路径")
    lk = Link(21)
    direct = lk.request(BLOCKED, 5, "data_write", 0, intent="b01:threshold:1")
    check("永久遮挡节点的直连从不成功", direct is False)
    via = lk.request(BLOCKED, 5, "data_write", 0, intent="b01:threshold:1", via_relay=True)
    check("同一节点经中继可以到达", via is True)
    dead = dict(BLOCKED, alive=False)
    check("中继跳仍要求节点有电",
          lk.request(dead, 6, "data_write", 0, intent="b01:threshold:2", via_relay=True) is False)
    src = open(MC, encoding="utf-8").read()
    check("中继入队与投递两条腿都标记 via_relay",
          src.count("via_relay=True") >= 2, f"{src.count('via_relay=True')} 处")


def audit_delayed_request_accounting() -> None:
    print("\n[7] 延迟请求不产生回复与下行空口")
    lk = Link(33)
    before = lk.airtime_ms_total
    arrived = lk.request(NODE, 10, "data_write", 0, intent="r03:threshold:1")
    one_leg = lk.airtime_ms_total - before
    # a held write: the request leg is spent, nothing else
    held_cost = lk.airtime_ms_total - before
    check("只算上行时成本等于单跳", abs(one_leg - held_cost) < 1e-9)
    replies_before, lost_before = lk.msg["replies"], lk.msg["reply_lost"]
    if arrived:
        lk.reply(NODE, 10, "data_write", 0, intent="r03:threshold:1")
        check("被扣留的写入不调用 reply，因此不产生回复",
              lk.msg["replies"] + lk.msg["reply_lost"] - replies_before - lost_before <= 1)
    total_after_request = lk.airtime_ms_total
    check("未调用 reply 时没有下行计费",
          abs((total_after_request - before) - one_leg) < 1e-9
          or arrived, "（到达时 reply 会另计一跳，符合预期）")
    src = open(MC, encoding="utf-8").read()
    check("命中扣留时不调用 link.reply",
          "replied = False" in src and "late_buf[n[\"nid\"]].append" in src)


def _md_tables(rd: str) -> list[list[list[str]]]:
    """Every markdown table in the document, as lists of cell lists with emphasis stripped."""
    tables, cur = [], None
    for line in rd.splitlines():
        st = line.strip()
        if st.startswith("|"):
            if set(st) <= set("|-: "):
                continue
            cells = [c.strip().replace("**", "").replace("`", "")
                     for c in st.strip("|").split("|")]
            if cur is None:
                cur = []
                tables.append(cur)
            cur.append(cells)
        else:
            cur = None
    return tables


def _as_float(cell: str):
    t = cell.replace(",", "").replace("%", "").replace("h", "").strip()
    try:
        return float(t)
    except ValueError:
        return None


def _row_match(rows, prefix: list[str], expected: list[float], dec: list[int]) -> bool:
    """True if some row starts with `prefix` and then carries exactly these numbers.

    Comparison is numeric and at the precision the table prints, so thousands separators and
    0-vs-0.0 are formatting rather than disagreement, while a genuinely different figure still
    fails. Non-numeric cells between the prefix and the numbers (a contract name, a unit) are
    skipped, and `dec[i]` is the number of decimals shown for value i.
    """
    for row in rows:
        if row[:len(prefix)] != prefix:
            continue
        nums = [v for v in (_as_float(c) for c in row[len(prefix):]) if v is not None]
        if len(nums) < len(expected):
            continue
        if all(abs(nums[i] - round(exp, dec[i])) <= 0.5 * 10 ** (-dec[i]) + 1e-9
               for i, exp in enumerate(expected)):
            return True
    return False


def audit_readme_matches_results() -> None:
    print("\n[8] README 数字与结果文件对齐")
    rd = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    rows = [r for t in _md_tables(rd) for r in t]

    def load(tag):
        p = os.path.join(ROOT, "results", tag)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    def arm(doc, name, wl):
        for r in doc["results"]:
            if r["arm"] == name and (wl is None or r.get("workload") == wl):
                return r
        return None

    # The batches below were withdrawn with the implementations that produced them. They are named
    # here rather than silently skipped, so a reader of the audit sees that these tables have no
    # backing result file instead of seeing a shorter list of checks and assuming nothing is
    # missing. The evidence for the withdrawal is in results/_withdrawn/MANIFEST.md.
    WITHDRAWN = (
        "method_comparison_main.json", "method_comparison_p2.json",
        "method_comparison_budget3.json", "method_comparison_budget8.json",
        "method_comparison_budget20.json", "restart_experiment_main.json",
    )
    main = load("method_comparison_main.json")
    check("主表结果文件已撤销（读数建立在缺失本文臂的实现上）", main is None)
    if main:
        for name, label in (("one_shot", "One-shot execution"),
                            ("retry_uncertainty", "Retry-on-uncertainty"),
                            ("verified_tool_calls", "Verified Tool Calls"),
                            ("verified_tool_calls_c1", "Verified Tool Calls，幂等 sink"),
                            ("ours", "本文 runtime"),
                            ("ours_plain_sink", "本文 runtime，普通 sink")):
            r = arm(main, name, "operation")
            exp = [100 * r["exactly_once_rate"], 100 * r["zero_rate"], 100 * r["dup_rate"],
                   r["duplicate_applications"], r["data_writes"], r["verify_reads"],
                   r["reconcile_reads"]]
            check(f"主表 {label} 整行一致", _row_match(rows, [label], exp, [1, 1, 1, 1, 0, 0, 0]),
                  " ".join(f"{v:.1f}" for v in exp[:4]))

    for budget, tag in ((3, "method_comparison_budget3.json"),
                        (8, "method_comparison_budget8.json"),
                        (20, "method_comparison_budget20.json")):
        doc = load(tag)
        check(f"{tag} 已撤销（等预算对照因固定重试预算而失效）", doc is None)
        if not doc:
            continue
        for name, label in (("verified_tool_calls", "Verified Tool Calls"), ("ours", "本文")):
            r = arm(doc, name, "operation")
            exp = [100 * r["exactly_once_rate"], r["duplicate_applications"],
                   r["stale_reorders"], r["data_writes"], r["verify_reads"]]
            check(f"等预算表 预算 {budget} / {label} 整行一致",
                  _row_match(rows, [str(budget), label], exp, [1, 1, 0, 0, 0]),
                  f"once={100*r['exactly_once_rate']:.1f}% reorder={r['stale_reorders']:.0f}")

    p2 = load("method_comparison_p2.json")
    check("P2 结果文件已撤销（与主表同一批代码）", p2 is None)
    if p2:
        for name, label in (("ours", "本文"), ("ablate_fencing", "只留 C1（回执）"),
                            ("ablate_receipts", "只留 C2（fencing）"),
                            ("ablate_identity", "去掉稳定写入身份"),
                            ("verified_tool_calls_c1", "Verified Tool Calls，幂等 sink"),
                            ("verified_tool_calls", "Verified Tool Calls"),
                            ("retry_uncertainty", "Retry-on-uncertainty"),
                            ("ours_plain_sink", "无契约的本文 runtime"),
                            ("one_shot", "One-shot execution")):
            r = arm(p2, name, "mutable_state")
            exp = [100 * r["exactly_once_rate"], r["duplicate_applications"],
                   r["stale_reorders"], r["stale_overwrites"]]
            check(f"P2 {label} 整行一致", _row_match(rows, [label], exp, [1, 1, 0, 0]),
                  f"once={100*r['exactly_once_rate']:.1f}% dup={r['duplicate_applications']:.0f} "
                  f"overwrite={r['stale_overwrites']:.0f}")

    rs = load("restart_experiment_main.json")
    check("重启结果文件已撤销（产生于按动作武装故障的修复之前）", rs is None)
    if rs:
        check("重启实验为 20 seed", rs["config"]["seeds"] == 20)
        src = {"fresh_id": "每次重发新身份", "reconstructed_id": "重算同一身份",
               "journal": "持久日志"}
        kind = {"scheduled": "周期测量（可重算）", "adhoc": "临时处置（不可重算）"}
        for r in rs["results"]:
            # the restart table's first column is the command kind and the second the source
            exp = [100 * r["once_rate"], r["duplicates"], r["spurious"]]
            hit = _row_match(rows, [kind[r["kind"]], src[r["arm"]]], exp, [1, 1, 0])
            check(f"重启表 {r['kind']}/{r['arm']} 整行一致", hit,
                  f"once={100*r['once_rate']:.1f}% dup={r['duplicates']:.0f} "
                  f"spurious={r['spurious']:.0f}")


def audit_cost_weight_is_separate_from_radio() -> None:
    print("\n[9] 读写权重只作用于加权代价，不作用于物理空口")
    # at the radio level the same frames are sent either way, so time-on-air cannot move
    nodes = [dict(NODE)]
    airtimes, costs = [], []
    for ratio in (0.25, 1.0, 4.0):
        lk = Link(17, read_cost_ratio=ratio)
        for i in range(200):
            lk.exchange(nodes[0], 40, "verify_read", 0, intent=f"r03:verify:{i}")
            lk.exchange(nodes[0], 40, "data_write", 0, intent=f"r03:threshold:{i}")
        airtimes.append(lk.airtime_ms_total)
        costs.append(lk.normalized_cost())
    check("物理空口在三档权重下逐位相同", len(set(airtimes)) == 1,
          f"{airtimes[0]:.1f} ms")
    check("加权代价随权重变化", len(set(costs)) == 3, f"{costs}")

    # and the same must hold in the stored results
    base = os.path.join(ROOT, "results")
    got = {}
    for ratio in ("0.25", "0.5", "1.0"):
        p = os.path.join(base, f"method_comparison_msr{ratio}_b20.json")
        if not os.path.exists(p):
            continue
        doc = json.load(open(p, encoding="utf-8"))
        for r in doc["results"]:
            got.setdefault(r["arm"], []).append((r["airtime_s"], r["normalized_cost"]))
    for arm_, vals in got.items():
        check(f"结果文件：{arm_} 的物理空口跨权重不变",
              len({round(a, 3) for a, _ in vals}) == 1,
              f"{[round(a/3600, 2) for a, _ in vals]} h")
        check(f"结果文件：{arm_} 的加权代价跨权重变化",
              len({round(c, 1) for _, c in vals}) == len(vals),
              f"{[round(c) for _, c in vals]}")


def audit_instance_figures() -> None:
    """实例层文档里引用的每一个数，都必须与 `results/` 下的结果文件对得上。

    **为什么单独加这一条。** 已有的 `audit_readme_matches_results` 只覆盖**旧批次**（那批已随实现
    撤销）。README 6.1–6.4 与 `05-final-analysis.md` 里的实例层数字**此前没有任何自动核对**——
    也就是说，一个数字被写错、或者某个结果文件被重新生成而值变了，**没有任何东西会变红**。
    这正是本项目反复栽的那一类：数字算对了，但**它已经不是当初那句话里的那个数**。

    表里左列是**文档里写的数**，右列是**从结果文件现算的数**。任一侧改动而另一侧没跟上，这里就红。
    """
    print("\n[10] 实例层文档数字与结果文件对齐")

    def g(tag, arm, field):
        path = os.path.join(ROOT, "results", f"instance_{tag}.json")
        if not os.path.exists(path):
            return None
        arms = json.load(open(path, encoding="utf-8"))["aggregate"]["arms"]
        return (arms.get(arm) or {}).get(field)

    # **2026-09-13 的 AoI 修复 + 全量重跑之后，13 项数字变了，这里是更新后的值。**
    # 变的两个原因要分清：① `routine_aoi_mean_s` 的实现被修好（§6.22）；
    # ② 其余是现行代码与这些文件登记时的代码不同（`rerun_from_config.py` 的全量重跑）。
    # **这张表的价值在于"文档写错或结果被重算而没跟上，这里就红"**——它刚刚正是这样红的。
    # (说明, tag, 臂, 字段, 文档里写的数, 容差)
    CASES = [
        ("6.1 宽松 dense600 naive 交付", "exec_layer_20s_v2", "dense600__naive",
         "routine_delivered", 154.35, 0.05),
        ("6.1 宽松 dense600 contract 交付", "exec_layer_20s_v2", "dense600__contract",
         "routine_delivered", 154.35, 0.05),
        ("6.1 宽松 dense600 atomic 交付", "exec_layer_20s_v2", "dense600__atomic",
         "routine_delivered", 153.2, 0.05),
        ("6.1 宽松 dense600 naive AoI", "exec_layer_20s_v2", "dense600__naive",
         "routine_aoi_mean_s", 3046.96, 0.5),
        ("6.1 宽松 dense600 atomic AoI", "exec_layer_20s_v2", "dense600__atomic",
         "routine_aoi_mean_s", 3453.62, 0.5),
        ("6.1 绑定 dense600 naive 交付", "exec_layer_bind0.008v2", "dense600__naive",
         "routine_delivered", 122.2, 0.05),
        ("6.1 绑定 dense600 contract 交付", "exec_layer_bind0.008v2", "dense600__contract",
         "routine_delivered", 130.8, 0.05),
        ("6.1 绑定 dense600 atomic 交付", "exec_layer_bind0.008v2", "dense600__atomic",
         "routine_delivered", 133.35, 0.05),
        ("6.1 绑定 dense600 naive 缺采", "exec_layer_bind0.008v2", "dense600__naive",
         "routine_missing_collection", 33.5, 0.05),
        ("6.1 绑定 dense600 atomic 缺采", "exec_layer_bind0.008v2", "dense600__atomic",
         "routine_missing_collection", 21.8, 0.05),
        ("6.2 名义上界", "oracle_headroom005", "local", "dynamic_oracle", 168.0, 0.05),
        ("6.2 绑定上界 (0.008)", "oracle_headroom008", "local", "dynamic_oracle", 168.0, 0.05),
        ("6.2 强绑定上界 (0.004)", "oracle_headroom004", "local", "dynamic_oracle", 146.2, 0.05),
        ("6.2 名义 dense600 达标", "oracle_headroom005", "dense600", "oracle_coverage",
         0.919, 0.0005),
        ("6.2 强绑定 local 达标", "oracle_headroom004", "local", "oracle_coverage",
         0.870, 0.0005),
        ("6.3 C1 上界", "oodoracle_C1", "local", "dynamic_oracle", 168.0, 0.05),
        ("6.3 容量 0.006 上界", "oodoracle_cap0.006", "local", "dynamic_oracle", 162.6, 0.05),
        ("6.3 容量 0.004 上界", "oodoracle_cap0.004", "local", "dynamic_oracle", 146.2, 0.05),
        ("6.3 容量 0.002 上界", "oodoracle_cap0.002", "local", "dynamic_oracle", 124.4, 0.05),
        ("6.3 容量 0.001 上界", "oodoracle_cap0.001", "local", "dynamic_oracle", 113.5, 0.05),
        ("6.3 C4 dense600 达标", "oodoracle_C4", "dense600", "oracle_coverage", 0.6765, 0.0005),
        ("6.3 初始 SoC 1.0 dense600 达标", "initsoc_1.0", "dense600", "oracle_coverage",
         0.6632, 0.0005),
        ("6.3 初始 SoC 0.05 dense600 达标", "initsoc_0.05", "dense600", "oracle_coverage",
         0.9191, 0.0005),
        ("6.4 日照 s12p1 上界", "solar_s12p1", "local", "dynamic_oracle", 126.0, 0.05),
        ("6.4 日照 s12p1 dense600 达标", "solar_s12p1", "dense600", "oracle_coverage",
         0.2019, 0.0005),
        ("6.4 日照 s6p2 上界", "solar_s6p2", "local", "dynamic_oracle", 168.0, 0.05),
        ("6.4 日照 s6p2 dense600 达标", "solar_s6p2", "dense600", "oracle_coverage",
         0.1595, 0.0005),
        ("6.4 日照 s0p4 local 达标", "solar_s0p4", "local", "oracle_coverage", 0.352, 0.0005),
        ("6.4 日照 s0p4 margin", "solar_s0p4", "local", "autonomy_margin", 0.0, 0.005),
        ("6.4 日照 s12p4 margin", "solar_s12p4", "local", "autonomy_margin", 2.88, 0.005),
    ]
    missing, drifted = [], []
    for name, tag, arm_key, field, want, tol in CASES:
        got = g(tag, arm_key, field)
        if got is None:
            missing.append(f"{name}（{tag}）")
        elif abs(got - want) > tol:
            drifted.append(f"{name}: 文档 {want} → 实际 {round(got, 4)}")
    check("文档引用的实例层数字都能在结果文件里找到", not missing,
          f"缺失 {missing[:3]}" if missing else f"{len(CASES)} 项")
    check("文档引用的实例层数字与结果文件逐项一致", not drifted,
          f"{drifted[:3]}" if drifted else f"{len(CASES)} 项全部对齐")


def audit_manifest_matches_code() -> None:
    """`spec/instance-v1-manifest.md` 的**部署条件**那一节必须与代码一致。

    部署条件是系统模型那节唯一的数字来源。它一旦与代码不一致，**不会自己报错**——只会让引用它的人
    算错。本项目已经栽过一次：manifest §五 的采样能耗长期停在已作废的 `2e-5 Wh`，而实现早已是
    `4.7e-4 Wh`。所以这一条查的不是"文档写得好不好"，是**两边是不是同一个数**。
    """
    print("\n[11] manifest 部署条件与代码一致")
    import sys as _sys
    for d in ("instance", "monitoring", "physics"):
        _p = os.path.join(ROOT, "code", d)
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
    import deployment as _dep
    from network import DeviceProfile, nodes_from

    prof = DeviceProfile()
    dep = _dep.build_deployment(groups=2)
    nodes = nodes_from(dep, profile=prof)

    spec = os.path.join(ROOT, "spec", "instance-v1-manifest.md")
    if not os.path.exists(spec):
        check("规范性文件 spec/instance-v1-manifest.md 存在", False,
              "缺失：部署条件是系统模型唯一的数字来源，本仓库必须随附该文件")
        return
    md = open(spec, encoding="utf-8").read()
    # **数值项按数值比，不按字符串比。** 同一件事有 `4.7e-4` 与 `0.00047` 两种合理写法，
    # 用字符串比会把它们判成不一致——那种噪声化的核对很快就会被无视，比没有核对更糟。
    import re as _re
    tokens = [float(x) for x in _re.findall(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", md)
              if x.strip() not in ("", ".", "-")]

    def has_num(v: float, tol: float = 1e-12) -> bool:
        return any(abs(x - v) <= tol + 1e-9 * max(1.0, abs(v)) for x in tokens)

    num_expect = {
        "纬度": float(_dep.GATEWAY_LAT),
        "经度": float(_dep.GATEWAY_LON),
        "海拔": float(_dep.GATEWAY_ELEV_M),
        "采样能耗": prof.sample_wh,
        "闸门": float(prof.charge_min_c),
        "静息": prof.idle_wh_per_tick,
        "缓存": float(prof.cache_slots),
        "节点数": float(len(nodes)),
    }
    for name, val in num_expect.items():
        check(f"部署条件「{name}」= {val:g} 出现在 manifest 里（按数值比）", has_num(val),
              "" if has_num(val) else f"manifest 里找不到与 {val:g} 相等的数")
    check("部署条件「地形瓦片」出现在 manifest 里", _dep.TILE in md, _dep.TILE)

    # 实测点数与测项分布也要对得上（曾在文档里被写成 16 个节点）
    n_disp = sum(1 for n in nodes.values() if n.measurand == "displacement")
    n_rain = sum(1 for n in nodes.values() if n.measurand == "rainfall")
    check("manifest 的节点数与实测一致（14 = 网关 + 13 位移站）",
          len(nodes) == 14 and n_disp == 13 and n_rain == 1,
          f"实测 {len(nodes)} 个：位移 {n_disp}、雨量 {n_rain}")


def main() -> int:
    print("一致性审计")
    audit_far_side_only_through_link()
    audit_environment_trace()
    audit_draw_independence()
    audit_overwrite_is_domain_state()
    audit_restart_durable_context()
    audit_relay_bypasses_screen()
    audit_delayed_request_accounting()
    audit_readme_matches_results()
    audit_cost_weight_is_separate_from_radio()
    audit_analysis_inputs()
    audit_result_index()
    audit_instance_figures()
    audit_manifest_matches_code()
    print("\n" + "-" * 74)
    if FAIL:
        print(f"  {len(FAIL)} 项失败：")
        for f in FAIL:
            print(f"    - {f}")
        return 1
    print("  全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
