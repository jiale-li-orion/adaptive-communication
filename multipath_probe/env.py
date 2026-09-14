"""env.py — 多路径、隐状态回传选择环境（multipath_probe）。

设计原则（对齐主 repo 的公平化纪律）：
* 外生轨迹（链路好/坏、随机丢包、事件突发、UAV 窗口取消）只由 (seed, K, burst) 决定，
  在控制器运行**之前**就确定，控制器的任何动作都不能改变它 —— 跨臂严格配对的前提。
* 控制器**看不到**链路真实状态，只能看到自己历次尝试的成败（观测=控制同通道，且观测要花真实发送）。
* 控制器只决定"每条路径这一拍尝试发几条"；发哪些样本由环境按统一 EDF/event 优先规则出队，
  所有臂相同 —— 本探针只隔离"路径状态推断与分配"这一个能力，不把样本排序差异混进来。
* oracle 只多看到"当前真实状态"，不预知未来转移，也不预知本次随机丢包结果。

时间离散，1 拍 = 1 小时。纯 numpy + 标准库，自包含，不 import 主 repo。
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

TICK_HOURS = 1
ROUTINE = "routine"
EVENT = "event"

# ---- 路径静态规格（A 级假设见 README §2；cellular 的突发参数是 E 级 ChirpBox 拟合）----
# good_frac=边际好率；mean_bad_hours=平均连续坏态长度（仅 markov 档使用）。
PATH_SPECS = {
    "cellular":  dict(good_frac=0.688, cap=6,  energy=1.0, money=0.0, kind="markov"),
    "satellite": dict(good_frac=0.962, cap=2,  energy=3.0, money=1.0, kind="markov",
                      daily_quota=24),
    "uav":       dict(good_frac=0.90,  cap=20, energy=0.5, money=0.0, kind="contact"),
}
PATH_ORDER = ["cellular", "satellite", "uav"]
# 各突发档下每条 markov 路径的"平均坏突发长度（小时）"。iid=逐拍独立（无记忆）。
# cellular chirpbox=6.38h 来自 results/loss_model.json；heavy≈20h 为 LoRa-on-Ice 级（A）。
BAD_BURST_HOURS = {
    "iid":      dict(cellular=1.0 / (1 - PATH_SPECS["cellular"]["good_frac"]),
                     satellite=1.0 / (1 - PATH_SPECS["satellite"]["good_frac"])),
    "chirpbox": dict(cellular=6.38, satellite=4.57),
    "heavy":    dict(cellular=20.0, satellite=12.0),
}
GOOD_TX_SUCCESS = 0.95   # 好态单次发送成功率（A）
BAD_TX_SUCCESS = 0.02    # 坏态单次发送成功率（A）
UAV_WINDOWS = ((2, 3), (14, 15))   # 每天计划接触窗口（公开时刻表），半开区间 [a,b)
UAV_CANCEL_P = 0.10
SAT_DAILY_QUOTA = PATH_SPECS["satellite"]["daily_quota"]

ROUTINE_PER_H = 4
ROUTINE_DEADLINE_H = 12
ROUTINE_VALUE = 1
EVENT_BURSTS = 6
EVENT_DURATION_H = 2
EVENT_PER_H = 12
EVENT_DEADLINE_H = 2
EVENT_VALUE = 5
QUEUE_CAP = 200


def ge_params(good_frac: float, mean_bad_hours: float) -> tuple[float, float]:
    """从边际好率与平均坏突发长度反解两态链转移概率 (p_good->bad, p_bad->good)。"""
    p_bg = 1.0 / max(mean_bad_hours, 1e-9)
    p_gb = p_bg * (1.0 - good_frac) / max(good_frac, 1e-9)
    return p_gb, p_bg


@dataclass
class Sample:
    sid: str
    arrive_t: int
    kind: str
    deadline_t: int
    value: int


@dataclass
class Trace:
    """与控制器无关的外生轨迹，三臂共享同一份。"""
    seed: int
    K: int
    burst: str
    T: int
    paths: list[str]
    link_good: dict            # path -> bool[T] 真实好/坏
    event_hours: set           # 哪些拍产生 event 样本
    uav_canceled: set          # 被取消的 UAV 窗口起点（绝对小时）

    def uav_scheduled(self, t: int) -> bool:
        hod = t % 24
        return any(a <= hod < b for a, b in UAV_WINDOWS)

    def uav_window_start(self, t: int) -> int:
        hod = t % 24
        for a, b in UAV_WINDOWS:
            if a <= hod < b:
                return t - (hod - a)
        return -1


def generate_trace(seed: int, K: int, burst: str, T: int = 336) -> Trace:
    """预生成整条外生轨迹。只依赖 (seed,K,burst,T)，与控制器无关。"""
    rng = np.random.RandomState(seed)
    paths = PATH_ORDER[:K]
    link_good: dict[str, np.ndarray] = {}
    uav_canceled: set[int] = set()
    for p in paths:
        spec = PATH_SPECS[p]
        if spec["kind"] == "contact":
            # UAV：窗口外恒坏；窗口内默认好，整窗按取消率抽一次（外生）。
            state = np.zeros(T, dtype=bool)
            for day in range(T // 24 + 1):
                for a, b in UAV_WINDOWS:
                    ws = day * 24 + a
                    we = day * 24 + b
                    if ws >= T:
                        continue
                    if rng.rand() < UAV_CANCEL_P:
                        uav_canceled.add(ws)
                        continue
                    state[ws:min(we, T)] = True
            link_good[p] = state
        else:
            g = spec["good_frac"]
            if burst == "iid":
                link_good[p] = rng.rand(T) < g
            else:
                p_gb, p_bg = ge_params(g, BAD_BURST_HOURS[burst][p])
                state = np.zeros(T, dtype=bool)
                state[0] = rng.rand() < g
                for t in range(1, T):
                    r = rng.rand()
                    state[t] = (r < p_bg) if not state[t - 1] else (r >= p_gb)
                link_good[p] = state
    # 事件突发：在 [24, T-24] 内抽 EVENT_BURSTS 个不相邻起点。
    event_hours: set[int] = set()
    cand = list(range(24, max(25, T - 24)))
    rng.shuffle(cand)
    for start in cand:
        if len(event_hours) >= EVENT_BURSTS * EVENT_DURATION_H:
            break
        # 与已选事件小时保持 >2 倍窗长，保证不重叠、不相邻。
        if all(abs(start - e) > 2 * EVENT_DURATION_H for e in event_hours):
            event_hours |= set(range(start, start + EVENT_DURATION_H))
    return Trace(seed=seed, K=K, burst=burst, T=T, paths=paths,
                 link_good=link_good, event_hours=event_hours,
                 uav_canceled=uav_canceled)


@dataclass
class View:
    """给控制器的合法观测（不含真实链路状态、不含未来）。"""
    t: int
    paths: list[str]
    backlog: int
    backlog_event: int
    backlog_routine: int
    earliest_deadline: int | None
    sat_quota_left: int
    energy_left: float | None       # 本网关剩余发射能量（本地可见，合法观测）
    energy_budget: float | None     # 总能量预算（公开），None=不约束
    hours_total: int
    history: dict           # path -> list[(t, attempted, succeeded)]
    spec: dict              # 静态规格副本
    ge: dict                # path -> (p_gb,p_bg) 真实转移参数（偏惠 rule_mpc）


@dataclass
class StepResult:
    attempted: dict = field(default_factory=dict)
    succeeded: dict = field(default_factory=dict)
    wasted: dict = field(default_factory=dict)       # 在真实坏态上的尝试数
    delivered_event: int = 0
    delivered_routine: int = 0
    missed_event: int = 0
    missed_routine: int = 0
    overflow: int = 0
    energy: float = 0.0
    money: float = 0.0
    sat_quota_used: int = 0
    sat_quota_wasted: int = 0
    probe_count: int = 0          # 本拍主动探测次数（消融用，默认无探测）


class MultipathEnv:
    def __init__(self, trace: Trace, energy_budget_wh: float | None = None,
                 sat_daily_quota: int = SAT_DAILY_QUOTA, probe_energy: float | None = None):
        self.tr = trace
        self.energy_budget = energy_budget_wh
        self.energy_left = energy_budget_wh
        self.sat_daily_quota = sat_daily_quota
        # 探测一次的能量成本；None=不允许探测。0=免费带外探测（理想化上界），1.0≈与数据包同价（同通道真实情形）。
        self.probe_energy = probe_energy
        self.t = 0
        self.queue: list[Sample] = []
        self._seq = 0
        self.history: dict[str, list] = {p: [] for p in trace.paths}
        self.sat_quota_left = self.sat_daily_quota
        # 总账
        self.tot = StepResult()
        self.tot.attempted = {p: 0 for p in trace.paths}
        self.tot.succeeded = {p: 0 for p in trace.paths}
        self.tot.wasted = {p: 0 for p in trace.paths}
        self.total_event = 0
        self.total_routine = 0
        self._ge = {p: self._ge_of(p) for p in trace.paths}

    def _ge_of(self, p):
        spec = PATH_SPECS[p]
        if spec["kind"] != "markov":
            return (0.0, 0.0)
        if self.tr.burst == "iid":
            return (0.0, 0.0)
        return ge_params(spec["good_frac"], BAD_BURST_HOURS[self.tr.burst][p])

    # ---------- 控制器可见 ----------
    def view(self) -> View:
        be = sum(1 for s in self.queue if s.kind == EVENT)
        br = len(self.queue) - be
        ed = min((s.deadline_t for s in self.queue), default=None)
        return View(t=self.t, paths=list(self.tr.paths), backlog=len(self.queue),
                    backlog_event=be, backlog_routine=br, earliest_deadline=ed,
                    sat_quota_left=self.sat_quota_left,
                    energy_left=self.energy_left, energy_budget=self.energy_budget,
                    hours_total=self.tr.T, history=self.history,
                    spec={p: PATH_SPECS[p] for p in self.tr.paths}, ge=dict(self._ge))

    def true_good(self) -> dict[str, bool]:
        """仅 oracle 使用：当前真实好/坏。"""
        return {p: bool(self.tr.link_good[p][self.t]) for p in self.tr.paths}

    # ---------- 内部 ----------
    def _arrive(self):
        t = self.t
        for _ in range(ROUTINE_PER_H):
            self._add(Sample(f"s{t}_{self._seq}", t, ROUTINE, t + ROUTINE_DEADLINE_H, ROUTINE_VALUE))
            self._seq += 1
            self.total_routine += 1
        if t in self.tr.event_hours:
            for _ in range(EVENT_PER_H):
                self._add(Sample(f"e{t}_{self._seq}", t, EVENT, t + EVENT_DEADLINE_H, EVENT_VALUE))
                self._seq += 1
                self.total_event += 1

    def _add(self, s: Sample):
        if len(self.queue) >= QUEUE_CAP:
            # 溢出：先丢最旧 routine，event 优先保留。
            for i, x in enumerate(self.queue):
                if x.kind == ROUTINE:
                    self.queue.pop(i)
                    self.tot.overflow += 1
                    break
            else:
                self.tot.overflow += 1
                return
        self.queue.append(s)

    def _expire(self):
        keep = []
        for s in self.queue:
            if s.deadline_t < self.t:
                if s.kind == EVENT:
                    self.tot.missed_event += 1
                else:
                    self.tot.missed_routine += 1
            else:
                keep.append(s)
        self.queue = keep

    def _edf_order(self, n: int) -> list[Sample]:
        # event 优先、其次截止期早者先出（所有臂统一，控制器不碰样本选择）。
        order = sorted(range(len(self.queue)),
                       key=lambda i: (0 if self.queue[i].kind == EVENT else 1,
                                      self.queue[i].deadline_t))
        return [self.queue[i] for i in order[:n]]

    def _attempt_rng(self, p: str, k: int) -> np.random.RandomState:
        # 第 k 次尝试的随机丢包只由 (seed,path,t,k) 决定，与控制器、尝试总数无关 → 严格配对。
        pidx = PATH_ORDER.index(p)
        return np.random.RandomState(self.tr.seed * 1_000_003 + self.t * 1009 + pidx * 37 + k)

    def step(self, allocation: dict[str, int], probes: dict[str, int] | None = None) -> StepResult:
        """allocation: path -> 本拍数据尝试条数；probes: path -> 本拍探测条数（消融）。"""
        r = StepResult(attempted={}, succeeded={}, wasted={})
        # 0) 日配额在每天第 0 拍重置。
        if self.t % 24 == 0:
            self.sat_quota_left = self.sat_daily_quota
        # 1) 到达 → 2) 过期 → 3) 探测（结果写入历史，下一拍起被控制器信念吸收）→ 4) 数据发送。
        self._arrive()
        self._expire()
        if self.probe_energy is not None:
            for p in self.tr.paths:
                npr = int(max(0, (probes or {}).get(p, 0)))
                if npr <= 0:
                    continue
                if p == "uav" and not self.tr.uav_scheduled(self.t):
                    continue
                really_good = bool(self.tr.link_good[p][self.t])
                for k in range(npr):
                    if self.energy_left is not None and self.energy_left < self.probe_energy - 1e-9:
                        break
                    if self.energy_left is not None:
                        self.energy_left -= self.probe_energy
                    r.energy += self.probe_energy
                    self.tot.energy += self.probe_energy
                    r.probe_count += 1
                    ps = GOOD_TX_SUCCESS if really_good else BAD_TX_SUCCESS
                    obs = self._attempt_rng(p, 900000 + k).rand() < ps
                    # 探测=一次只产生观测、不交付样本的尝试，写入历史供下拍信念更新。
                    self.history[p].append((self.t, 1, 1 if obs else 0))
                    self.tot.attempted[p] += 1
        # 路径按（货币,能量）成本升序处理，与三控制器的优先级一致；能量是网关全局共享预算，
        # 先花在便宜路径上对所有臂都公平。
        ordered = sorted(self.tr.paths,
                         key=lambda x: (PATH_SPECS[x]["money"], PATH_SPECS[x]["energy"]))
        for p in ordered:
            req = int(max(0, allocation.get(p, 0)))
            spec = PATH_SPECS[p]
            cap = spec["cap"]
            if p == "satellite":
                cap = min(cap, self.sat_quota_left)
            if p == "uav" and not self.tr.uav_scheduled(self.t):
                cap = 0
            cap = min(cap, len(self.queue))
            really_good = bool(self.tr.link_good[p][self.t])
            succ = 0
            wasted = 0
            actual = 0
            for k in range(req):
                if actual >= cap:
                    break
                # 能量硬门：剩余能量不足以支付本次尝试 → 该路径停止（全局能量，后续路径同样受限）。
                if self.energy_left is not None and self.energy_left < spec["energy"] - 1e-9:
                    break
                psuccess = GOOD_TX_SUCCESS if really_good else BAD_TX_SUCCESS
                ok = self._attempt_rng(p, k).rand() < psuccess
                # 尝试即支付能量与空口；卫星尝试即扣配额与货币（失败也扣）。
                if self.energy_left is not None:
                    self.energy_left -= spec["energy"]
                r.energy += spec["energy"]
                self.tot.energy += spec["energy"]
                actual += 1
                if p == "satellite":
                    self.sat_quota_left -= 1
                    r.sat_quota_used += 1
                    r.money += spec["money"]
                    self.tot.money += spec["money"]
                    if not really_good:
                        r.sat_quota_wasted += 1
                if ok and self.queue:
                    s = self._edf_order(1)[0]
                    self.queue.remove(s)
                    succ += 1
                    if s.kind == EVENT:
                        r.delivered_event += 1
                    else:
                        r.delivered_routine += 1
                if not really_good:
                    wasted += 1
            r.attempted[p] = actual
            r.succeeded[p] = succ
            r.wasted[p] = wasted
            self.history[p].append((self.t, actual, succ))
            self.tot.attempted[p] += actual
            self.tot.succeeded[p] += succ
            self.tot.wasted[p] += wasted
        self.tot.delivered_event += r.delivered_event
        self.tot.delivered_routine += r.delivered_routine
        self.tot.missed_event += r.missed_event
        self.tot.missed_routine += r.missed_routine
        self.tot.sat_quota_used += r.sat_quota_used
        self.tot.sat_quota_wasted += r.sat_quota_wasted
        self.t += 1
        return r

    def finalize(self) -> dict:
        """任务结束：把仍在队列、已过最后交付机会的计为 missed。"""
        for s in self.queue:
            if s.kind == EVENT:
                self.tot.missed_event += 1
            else:
                self.tot.missed_routine += 1
        self.queue = []
        return self.metrics()

    def metrics(self) -> dict:
        te, tr = self.total_event, self.total_routine
        de, dr = self.tot.delivered_event, self.tot.delivered_routine
        return {
            "event_total": te, "routine_total": tr,
            "event_delivered": de, "routine_delivered": dr,
            "event_rate": de / te if te else float("nan"),
            "routine_rate": dr / tr if tr else float("nan"),
            "missed_event": self.tot.missed_event, "missed_routine": self.tot.missed_routine,
            "attempts": sum(self.tot.attempted.values()),
            "success": sum(self.tot.succeeded.values()),
            "wasted_bad_path": sum(self.tot.wasted.values()),
            "sat_quota_used": self.tot.sat_quota_used,
            "sat_quota_wasted": self.tot.sat_quota_wasted,
            "overflow": self.tot.overflow,
            "energy": round(self.tot.energy, 3), "money": round(self.tot.money, 3),
            "energy_left": (round(self.energy_left, 3) if self.energy_left is not None else None),
        }
