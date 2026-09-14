"""**条件计划**：把"未来证据 → 目标值"的映射编译成可下发给网关的产物。

对应 [Task Contract v1.1](../../../docs/s7-method/task-contract-v1.1.md) §10 允许的分布式控制比较，
与 [`31-communication-method-candidates-2026-09-14.md`](../../../docs/s7-method/instance-v1/31-communication-method-candidates-2026-09-14.md)
§三第 43、45 行。**它是"位置对照"（判别 A）之后才需要的东西**：

> §31 第 43 行：「shadow 保存当前目标值，**条件计划保存未来证据到目标值的映射**。」
> §31 第 45 行：「计划包含：**适用节点与已有字段、合法观察量及其采集时间、条件分支、
> 允许的配置集合、资源限制、计划版本与有效范围**。**编译/准入阶段检查某个分支的证据是否在
> 执行位置可得**：网关能读取自己收到的节点状态，但不能把中心实际收到的最新样本或不可见的任务更新
> 当成本地知识。**依赖中心信息的分支保留为等待或请求更新**。」

**三条纪律写在代码里。**

1. **计划是数据，不是代码。** 它是 frozen dataclass，可序列化、带 `version` 与有效范围——
   因为它的用途就是**被下发给网关**（§31 第 55 行要求"计划安装、更新、撤销的字节和开销记账"）。
2. **准入检查是编译期的事，不是运行期的事。** 一个分支要用的证据若只在中心可得，
   **必须在编译时就把它留下**（`wait`/`request_update`），**不许**在网关侧"猜"或"当成本地知识"。
   这条是本文件存在的主要理由。
3. **没有证据时不动手。** 运行时缺证据 ⇒ 该分支**不产生动作**（等下一份证据），
   而不是退回一个"保守猜测"——猜测会把未知伪装成已知（§31 第 89 行同一精神）。

**它不是新动作面**：计划能产生的目标值必须落在**允许的配置集合**内，
而那个集合就是节点已有的两个设置字段的取值范围。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from center import (OP_SET_REPORT_PERIOD, OP_SET_SAMPLING_INTERVAL, CenterPolicy,
                    CenterView)

# ---------------------------------------------------------------- 观察量及其"可得位置"

#: **合法观察量登记表**：名字 → 它在**哪些执行位置可得**。
#:
#: **这里有一个必须写清的不对称性**（§31 第 45 行的要害）：
#:
#: * **网关原生的证据**（网关自己收到的节点状态）**在中心也可得**——只是要**经回传**，
#:   因此中心读到的是**同一个量的更旧版本**。这正是判别 A 的对照对象
#:   （`node.newest_sample_taken_at` 是网关侧的，`center.newest_sample_taken_at` 是中心侧迟到的）。
#: * **中心独有的证据**（任务更新、中心自己的意图历史）在网关**根本不可得**——
#:   网关不在那条路径上，**没有任何延迟版本可读**。
#:
#: ⇒ 所以"可下沉"的判据是：**该分支用到的每一个观察量，在网关位置的可得集合里**。
#: 依赖 `center.*` 的分支**必须**留在中心侧（wait / request_update）。
EVIDENCE_AVAILABLE: dict[str, frozenset] = {
    # —— 网关原生：两处都可得（中心那份是经回传的旧版本）
    "node.soc_wh": frozenset({"gateway", "center"}),
    "node.sample_interval_s": frozenset({"gateway", "center"}),
    "node.report_period_s": frozenset({"gateway", "center"}),
    "node.newest_sample_taken_at": frozenset({"gateway", "center"}),
    "node.cache_level": frozenset({"gateway", "center"}),
    "gateway.in_flight": frozenset({"gateway", "center"}),
    "gateway.now_s": frozenset({"gateway", "center"}),
    # —— 只有中心可得：网关**没有**任何延迟版本
    "center.newest_sample_taken_at": frozenset({"center"}),
    "center.report_received_at": frozenset({"center"}),
    "center.task_update": frozenset({"center"}),
    "center.intent_history": frozenset({"center"}),
}
#: 兼容旧名（登记表本身是"可得位置集合"，不再是单一位置）。
EVIDENCE_LOCATION: dict[str, str] = {
    k: ("gateway" if len(v) > 1 else "center") for k, v in EVIDENCE_AVAILABLE.items()}

#: 合法执行位置。`center` ＝现状（判别 A 的 `placement="center"`）；
#: `gateway` ＝现场（判别 A 的 `placement="gateway"`）。
POSITIONS = ("center", "gateway")


class PlanAdmissionError(ValueError):
    """计划在**准入期**被拒。**响亮地失败**，不许静默下沉一个依赖中心证据的分支。"""


# ---------------------------------------------------------------- 计划结构（七要素）

@dataclass(frozen=True)
class PlanBranch:
    """一条条件分支：`证据条件 → 目标值`。

    - `applies_to`：**适用节点**（节点 id 元组，或 `("*",)` 表示全部已有节点）；
    - `evidence`：本分支条件**用到的观察量**（必须在 `EVIDENCE_LOCATION` 里登记）——
      准入检查就是拿它去查"这些量在执行位置是否可得"；
    - `when`：条件的名字（由解释器实现，**计划本身只是数据**）；
    - `target`：目标值（一个或两个字段），必须落在计划的 `allowed_configs` 内；
    - `on_missing`：**证据缺失时怎么办**——`"wait"`（等下一份）或 `"request_update"`
      （请中心补一份）。**不允许**第三种"按保守值猜"。
    """

    branch_id: str
    applies_to: tuple[str, ...]
    evidence: tuple[str, ...]
    when: str
    target: dict
    on_missing: str = "wait"
    priority: int = 0

    def __post_init__(self) -> None:
        if self.on_missing not in ("wait", "request_update"):
            raise PlanAdmissionError(
                f"分支 {self.branch_id!r} 的 on_missing={self.on_missing!r} 不合法："
                f"只允许 wait / request_update——**不许按保守值猜**")
        unknown = [e for e in self.evidence if e not in EVIDENCE_AVAILABLE]
        if unknown:
            raise PlanAdmissionError(
                f"分支 {self.branch_id!r} 引用了**未登记**的观察量 {unknown}。"
                f"未登记就无法判断它在执行位置是否可得，因此不允许下沉。")


@dataclass(frozen=True)
class ConditionalPlan:
    """一份可下发的条件计划。**七要素逐项对应 §31 第 45 行**：

    ==========================  ==========================================
    §31 第 45 行                本结构
    ==========================  ==========================================
    适用节点与已有字段            `PlanBranch.applies_to` + `PlanBranch.target` 的字段名
    合法观察量及其采集时间        `PlanBranch.evidence`（在 `EVIDENCE_LOCATION` 登记）
    条件分支                      `branches`
    允许的配置集合                `allowed_configs`
    资源限制                      `resource_limits`
    计划版本                      `version`
    有效范围                      `valid_from_s` / `valid_to_s`
    ==========================  ==========================================
    """

    plan_id: str
    version: int
    branches: tuple[PlanBranch, ...]
    allowed_configs: frozenset          # 元素是 ((字段, 值), ...) 的 frozenset，见 `config_key`
    resource_limits: dict = field(default_factory=dict)
    valid_from_s: int = 0
    valid_to_s: int = 1 << 62

    def active_at(self, t_s: int) -> bool:
        """**有效范围**：过期只阻止**后续执行**，不撤销节点上已经生效的配置（§31 第 49 行）。"""
        return self.valid_from_s <= t_s < self.valid_to_s


#: **命令载荷的字段名**（`_apply_field` 读的就是这两个名字）与**节点状态字段名**的对照。
#: 计划的目标值用**命令字段名**——因为它要产生的是下发报文；比对"是否已生效"时才映射到状态名。
#: 这两组名字不同是一个真实存在的坑：写错名字命令**不会生效**，而且不会报错。
CMD_FIELD = {"interval_s": "sample_interval_s", "period_s": "report_period_s"}


def config_key(pair: dict) -> frozenset:
    """把一组目标字段值变成一个可比较的键。"""
    return frozenset(pair.items())


# ---------------------------------------------------------------- 准入检查（本文件的核心）

@dataclass(frozen=True)
class AdmissionReport:
    """准入结果：**可执行的分支**与**被留下的分支**，以及每个留下的原因。"""

    position: str
    executable: tuple[PlanBranch, ...]
    held: tuple[PlanBranch, ...]
    held_reasons: dict           # branch_id -> 原因（人可读）


def admit(plan: ConditionalPlan, position: str,
          raise_on_held: bool = False) -> AdmissionReport:
    """**编译/准入阶段**：逐分支检查"它要的证据在执行位置是否可得"。

    这是 §31 第 45 行那句要求的实现：
    「网关能读取自己收到的节点状态，**但不能把中心实际收到的最新样本或不可见的任务更新
    当成本地知识**。依赖中心信息的分支保留为等待或请求更新。」

    ⇒ 依赖 center-only 证据的分支**不进 `executable`**，而是进 `held` 并带原因；
    它们由中心侧继续负责（`wait` / `request_update`）。
    """
    if position not in POSITIONS:
        raise PlanAdmissionError(f"未知执行位置 {position!r}；合法值 {POSITIONS}")
    exe, held, why = [], [], {}
    for b in sorted(plan.branches, key=lambda x: x.priority):
        foreign = [e for e in b.evidence if position not in EVIDENCE_AVAILABLE[e]]
        if foreign:
            held.append(b)
            why[b.branch_id] = (
                f"证据 {foreign} 在位置 {position!r} **不可得**"
                f"（它们的可得位置是 {sorted({tuple(sorted(EVIDENCE_AVAILABLE[e])) for e in foreign})}）"
                f"⇒ 保留为 {b.on_missing}，不下沉")
            continue
        exe.append(b)
    if raise_on_held and held:
        raise PlanAdmissionError(
            f"计划 {plan.plan_id!r} 有 {len(held)} 条分支不可下沉到 {position!r}："
            + "；".join(f"{k}: {v}" for k, v in why.items()))
    return AdmissionReport(position=position, executable=tuple(exe), held=tuple(held),
                           held_reasons=why)


# ---------------------------------------------------------------- 确定性解释器

def _condition(name: str, ctx: dict) -> bool | None:
    """条件的确定性求值。**返回 None 表示证据缺失**（调用方必须按 `on_missing` 处理）。

    条件名封闭在这一处：计划是数据，只有这里知道每个名字怎么算。
    """
    if name == "aoi_missing_or_gt_stale":
        aoi = ctx.get("aoi_s")
        if aoi is None and not ctx.get("aoi_known", False):
            return True                      # 从没听到过 ⇒ 走"先加密看能不能收到"那一支
        return aoi is not None and aoi > ctx["stale_s"]
    if name == "always":
        return True
    if name == "soc_lt_threshold":
        soc = ctx.get("soc_wh")
        return None if soc is None else soc < ctx["threshold_wh"]
    if name == "soc_ge_threshold":
        soc = ctx.get("soc_wh")
        return None if soc is None else soc >= ctx["threshold_wh"]
    if name == "center_newest_sample_stale":
        # **故意保留的 center-only 条件**：用来演示准入检查会把它拦下来。
        age = ctx.get("center_newest_sample_age_s")
        return None if age is None else age > ctx["stale_s"]
    raise PlanAdmissionError(f"未知条件名 {name!r}（计划的 `when` 必须落在解释器支持集合内）")


class PlanGatewayPolicy(CenterPolicy):
    """**在网关侧执行一份条件计划**（位置 = `gateway`）。

    **它与"把同一个策略对象放到网关"（判别 A 的做法）是两件不同的事**：
    判别 A 让策略读写它自己看得见的东西；这里让策略读**一份被下发的数据**，
    并且**只有通过准入检查的分支才会被执行**。

    `gating` 是计划自己的执行纪律（驻留时间、已确认即不重发）——**它们对两处都相同**，
    因此不是位置带来的差异。
    """

    def __init__(self, plan: ConditionalPlan, dwell_s: int = 600,
                 threshold_wh: float = 0.010, stale_s: int = 3600) -> None:
        super().__init__()
        rep = admit(plan, "gateway")
        # **不能叫 `self.plan`**：那会**覆盖 `CenterPolicy.plan` 方法**（本类必须实现它）。
        # 第一版就是这么写的，运行时报 `'ConditionalPlan' object is not callable`。
        self.document = plan
        self.report = rep
        self.dwell_s = dwell_s
        self.threshold_wh = threshold_wh
        self.stale_s = stale_s
        self._last: dict[str, int] = {}
        self.held_ticks = 0
        self.wait_ticks = 0
        self.name = f"plan:{plan.plan_id}"

    def _branch_for(self, nid: str, view: CenterView) -> tuple[PlanBranch | None, dict]:
        """按 `priority` 取**第一条**适用且条件成立的分支。缺证据 ⇒ 返回 (None, ctx)。"""
        for b in self.report.executable:
            if "*" not in b.applies_to and nid not in b.applies_to:
                continue
            ctx = self._context(view, nid, b)
            verdict = _condition(b.when, ctx)
            if verdict is None:
                self.wait_ticks += 1
                return None, ctx          # **缺证据 ⇒ 不动手**（不是猜一个保守值）
            if verdict:
                return b, ctx
        return None, {}

    def _context(self, view: CenterView, nid: str, branch: PlanBranch) -> dict:
        snap = view.reports.get(nid) or {}
        ctx: dict = {"stale_s": self.stale_s, "threshold_wh": self.threshold_wh}
        if "node.newest_sample_taken_at" in branch.evidence:
            ctx["aoi_s"] = view.aoi_s(nid)
            ctx["aoi_known"] = view.aoi_s(nid) is not None
        if "node.soc_wh" in branch.evidence:
            ctx["soc_wh"] = view.soc_of(nid)
        if "node.report_period_s" in branch.evidence:
            ctx["known_report_period"] = snap.get("report_period_s")
        if "center.newest_sample_taken_at" in branch.evidence:
            # 网关**读不到**这个量：这里只是把"它会缺"如实表达出来，
            # 而准入检查本来就已经把这类分支留在中心侧了。
            ctx["center_newest_sample_age_s"] = None
        return ctx

    def plan(self, view: CenterView) -> list[tuple[str, dict]]:
        if not self.document.active_at(view.t_s):
            # 过期只阻止后续执行，**不撤销已经生效的配置**（§31 第 49 行）。
            return []
        out = []
        for nid in view.node_ids:
            if nid in view.in_flight:
                self._skip("in_flight", nid)
                continue
            last = self._last.get(nid)
            if last is not None and view.t_s - last < self.dwell_s:
                self._skip("dwell", nid)
                continue
            branch, _ctx = self._branch_for(nid, view)
            if branch is None:
                self._skip("no_branch_or_missing_evidence", nid)
                continue
            target = dict(branch.target)
            if config_key(target) not in self.document.allowed_configs:
                # **计划只能产生允许的配置集合内的目标值**——越界即准入出错。
                raise PlanAdmissionError(
                    f"分支 {branch.branch_id!r} 的目标 {target} 不在允许的配置集合内")
            snap = view.reports.get(nid) or {}
            # 命令字段名 → 节点状态字段名，再比"是否已生效"（回执里是状态名）。
            if all(snap.get(CMD_FIELD[k]) == v for k, v in target.items()):
                self._skip("already_confirmed", nid)
                continue
            self._last[nid] = view.t_s
            payloads = [{"op": OP_SET_SAMPLING_INTERVAL if k == "interval_s"
                         else OP_SET_REPORT_PERIOD, k: v} for k, v in target.items()]
            if len(payloads) == 1:
                out.append((nid, self.stamp(nid, **payloads[0])))
            else:
                a, b = self.stamp_pair(nid, payloads[0], payloads[1])
                out.append((nid, a))
                out.append((nid, b))
        return out


# ---------------------------------------------------------------- 从既有规则编译出计划

def compile_aoi_plan(stale_s: int = 3600, fast_s: int = 300, slow_s: int = 900,
                     dwell_s: int = 600, version: int = 1,
                     valid_to_s: int = 1 << 62) -> ConditionalPlan:
    """把既有 `AoiPolicy` 的规则**编译成一份条件计划**（用于等价性验证）。

    **两个分支**：太旧/从未听到 ⇒ 加密；否则 ⇒ 放宽。两者都只用**网关本地可得**的证据
    （`node.newest_sample_taken_at` = 网关自己听到的最新样本；`node.report_period_s` = 快照里的回执）。
    **dwell 与"已确认即不重发"不写进分支**——它们是执行纪律，由解释器统一施加。
    """
    b_fast = PlanBranch(
        branch_id="aoi_stale_to_fast", applies_to=("*",),
        evidence=("node.newest_sample_taken_at", "node.report_period_s"),
        when="aoi_missing_or_gt_stale", target={"period_s": fast_s},
        priority=0)
    b_slow = PlanBranch(
        branch_id="aoi_fresh_to_slow", applies_to=("*",),
        evidence=("node.newest_sample_taken_at", "node.report_period_s"),
        when="always", target={"period_s": slow_s}, priority=1)
    allowed = frozenset({config_key({"period_s": fast_s}),
                         config_key({"period_s": slow_s})})
    return ConditionalPlan(plan_id="aoi_compiled", version=version,
                           branches=(b_fast, b_slow), allowed_configs=allowed,
                           resource_limits={"dwell_s": dwell_s, "max_commands_per_node": None},
                           valid_to_s=valid_to_s)


# ---------------------------------------------------------------- 计划的开销记账（§31 第 55 行）

def plan_bytes(plan: ConditionalPlan) -> int:
    """**计划的安装/更新报文大小（字节，JSON 编码）**。

    §31 第 55 行要求「**计划安装、更新、撤销的字节和开销记账**；不能只拿逐 tick 调用 LLM 的
    人为高开销作对手」。本函数给的是**尺寸**这一半。

    **另一半必须如实声明：本轮没有任何一次运行把安装/更新/撤销的字节计入任何臂的成本。**
    理由是这条能力按声明是**全基线共享、预装**的（§31 第 49 行：网关可编程执行是 A 层能力，
    所有相关基线共享）；因此把安装费只记给某一条臂就是能力不对等。
    **把安装/更新费真正计进成本模型，是本轮未完成的一项。**
    """
    import json as _json

    def _b(br: PlanBranch) -> dict:
        return {"id": br.branch_id, "nodes": list(br.applies_to),
                "evidence": list(br.evidence), "when": br.when,
                "target": br.target, "on_missing": br.on_missing, "p": br.priority}

    body = {"plan_id": plan.plan_id, "version": plan.version,
            "branches": [_b(x) for x in plan.branches],
            "allowed": [sorted(x) for x in plan.allowed_configs],
            "limits": plan.resource_limits,
            "valid": [plan.valid_from_s, plan.valid_to_s]}
    return len(_json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8"))
