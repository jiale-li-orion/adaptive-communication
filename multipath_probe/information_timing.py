"""同一调度周期内的信息返回时序微环境。

它复用 ``env.py`` 冻结的外生轨迹、业务到达和路径规格，但不复用旧的
``step(allocation, probes)``。旧接口在一拍开始前一次性提交所有动作，无法表达
“先发一包、收到 ACK、再选下一条路径”。本文件把一小时定义为一个信道状态不变的
调度 epoch，并显式暴露逐次尝试及其返回顺序。

同拍 ACK 是 A 层接口假设；它是否能映射到现场蜂窝/卫星设备需另行确认。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np

from env import (
    BAD_TX_SUCCESS,
    EVENT,
    EVENT_DEADLINE_H,
    EVENT_PER_H,
    GOOD_TX_SUCCESS,
    PATH_ORDER,
    PATH_SPECS,
    QUEUE_CAP,
    ROUTINE,
    ROUTINE_DEADLINE_H,
    ROUTINE_PER_H,
    SAT_DAILY_QUOTA,
    Sample,
    Trace,
)


@dataclass(frozen=True)
class Evidence:
    t: int
    path: str
    kind: str
    success: bool
    draw_key: str
    action_index: int
    returned_before_action_index: int


@dataclass(frozen=True)
class AttemptOutcome:
    success: bool
    delivered_kind: str | None
    draw_key: str
    evidence: Evidence


class TimingEnv:
    """逐尝试环境；probe 与 data 分开取随机键，避免探测改变配对数据结果。"""

    def __init__(self, trace: Trace, energy_budget: float | None = None,
                 probe_cost_multiplier: float = 1.0,
                 sat_daily_quota: int = SAT_DAILY_QUOTA):
        self.tr = trace
        self.energy_budget = energy_budget
        self.energy_left = energy_budget
        self.probe_cost_multiplier = probe_cost_multiplier
        self.sat_daily_quota = sat_daily_quota
        self.sat_quota_left = sat_daily_quota
        self.t = 0
        self.queue: list[Sample] = []
        self._seq = 0
        self._open = False
        self._cap_left: dict[str, int] = {}
        self._kind_attempt_index: dict[tuple[str, str], int] = {}
        self._action_index = 0
        self._epoch_energy_start = energy_budget
        self.evidence: list[Evidence] = []
        self.action_ledger: list[dict] = []
        self.total_event = 0
        self.total_routine = 0
        self.delivered_event = 0
        self.delivered_routine = 0
        self.missed_event = 0
        self.missed_routine = 0
        self.overflow = 0
        self.attempts = 0
        self.probes = 0
        self.successes = 0
        self.wasted_bad_path = 0
        self.energy = 0.0
        self.money = 0.0
        self.sat_quota_used = 0

    def _add(self, sample: Sample) -> None:
        if len(self.queue) >= QUEUE_CAP:
            for i, queued in enumerate(self.queue):
                if queued.kind == ROUTINE:
                    self.queue.pop(i)
                    self.overflow += 1
                    break
            else:
                self.overflow += 1
                return
        self.queue.append(sample)

    def _arrive(self) -> None:
        for _ in range(ROUTINE_PER_H):
            self._add(Sample(f"s{self.t}_{self._seq}", self.t, ROUTINE,
                             self.t + ROUTINE_DEADLINE_H, 1))
            self._seq += 1
            self.total_routine += 1
        if self.t in self.tr.event_hours:
            for _ in range(EVENT_PER_H):
                self._add(Sample(f"e{self.t}_{self._seq}", self.t, EVENT,
                                 self.t + EVENT_DEADLINE_H, 5))
                self._seq += 1
                self.total_event += 1

    def _expire(self) -> None:
        keep = []
        for sample in self.queue:
            if sample.deadline_t < self.t:
                if sample.kind == EVENT:
                    self.missed_event += 1
                else:
                    self.missed_routine += 1
            else:
                keep.append(sample)
        self.queue = keep

    def ge_for(self, path: str) -> tuple[float, float]:
        from env import BAD_BURST_HOURS, ge_params

        spec = PATH_SPECS[path]
        if spec["kind"] != "markov" or self.tr.burst == "iid":
            return 0.0, 0.0
        return ge_params(spec["good_frac"], BAD_BURST_HOURS[self.tr.burst][path])

    def begin_epoch(self) -> None:
        if self._open or self.t >= self.tr.T:
            raise RuntimeError("epoch state is invalid")
        if self.t % 24 == 0:
            self.sat_quota_left = self.sat_daily_quota
        self._arrive()
        self._expire()
        self._cap_left = {p: int(PATH_SPECS[p]["cap"]) for p in self.tr.paths}
        if "uav" in self._cap_left and not self.tr.uav_scheduled(self.t):
            self._cap_left["uav"] = 0
        self._kind_attempt_index = {(p, k): 0 for p in self.tr.paths for k in ("data", "probe")}
        self._epoch_energy_start = self.energy_left
        self._open = True

    @property
    def backlog_event(self) -> int:
        return sum(sample.kind == EVENT for sample in self.queue)

    @property
    def epoch_energy_spent(self) -> float:
        if self.energy_left is None or self._epoch_energy_start is None:
            return 0.0
        return self._epoch_energy_start - self.energy_left

    def eligible_paths(self, kind: str) -> list[str]:
        if not self._open or (kind == "data" and not self.queue):
            return []
        eligible = []
        for path in self.tr.paths:
            if self._cap_left.get(path, 0) <= 0:
                continue
            if path == "satellite" and self.sat_quota_left <= 0:
                continue
            cost = PATH_SPECS[path]["energy"] * (
                self.probe_cost_multiplier if kind == "probe" else 1.0)
            if self.energy_left is not None and self.energy_left < cost - 1e-9:
                continue
            eligible.append(path)
        return eligible

    def _draw(self, path: str, kind: str, index: int) -> tuple[bool, str]:
        path_index = PATH_ORDER.index(path)
        namespace = 700_001 if kind == "probe" else 0
        integer_key = self.tr.seed * 1_000_003 + self.t * 1009 + path_index * 37 + namespace + index
        really_good = bool(self.tr.link_good[path][self.t])
        probability = GOOD_TX_SUCCESS if really_good else BAD_TX_SUCCESS
        success = bool(np.random.RandomState(integer_key).rand() < probability)
        return success, f"{self.tr.seed}:{self.t}:{path}:{kind}:{index}"

    def _next_sample(self) -> Sample:
        return min(self.queue, key=lambda s: (0 if s.kind == EVENT else 1, s.deadline_t, s.sid))

    def attempt(self, path: str, kind: str) -> AttemptOutcome | None:
        if kind not in ("data", "probe"):
            raise ValueError(f"unknown attempt kind: {kind}")
        if path not in self.eligible_paths(kind):
            return None
        spec = PATH_SPECS[path]
        multiplier = self.probe_cost_multiplier if kind == "probe" else 1.0
        energy_cost = spec["energy"] * multiplier
        if self.energy_left is not None:
            self.energy_left -= energy_cost
        self.energy += energy_cost
        self.money += spec["money"]
        self._cap_left[path] -= 1
        if path == "satellite":
            self.sat_quota_left -= 1
            self.sat_quota_used += 1

        index = self._kind_attempt_index[(path, kind)]
        self._kind_attempt_index[(path, kind)] += 1
        success, draw_key = self._draw(path, kind, index)
        really_good = bool(self.tr.link_good[path][self.t])
        delivered_kind = None
        if kind == "data" and success and self.queue:
            sample = self._next_sample()
            self.queue.remove(sample)
            delivered_kind = sample.kind
            if sample.kind == EVENT:
                self.delivered_event += 1
            else:
                self.delivered_routine += 1
        self.attempts += 1
        self.probes += int(kind == "probe")
        self.successes += int(success)
        self.wasted_bad_path += int(not really_good)
        evidence = Evidence(
            t=self.t,
            path=path,
            kind=kind,
            success=success,
            draw_key=draw_key,
            action_index=self._action_index,
            returned_before_action_index=self._action_index + 1,
        )
        self.evidence.append(evidence)
        self.action_ledger.append({
            **asdict(evidence),
            "delivered_kind": delivered_kind,
            "true_good": really_good,
            "energy_cost": energy_cost,
        })
        self._action_index += 1
        return AttemptOutcome(success, delivered_kind, draw_key, evidence)

    def end_epoch(self) -> None:
        if not self._open:
            raise RuntimeError("no open epoch")
        self._open = False
        self.t += 1

    def finalize(self) -> dict:
        if self._open:
            raise RuntimeError("close the epoch before finalize")
        for sample in self.queue:
            if sample.kind == EVENT:
                self.missed_event += 1
            else:
                self.missed_routine += 1
        self.queue = []
        return {
            "event_total": self.total_event,
            "routine_total": self.total_routine,
            "event_delivered": self.delivered_event,
            "routine_delivered": self.delivered_routine,
            "event_rate": self.delivered_event / self.total_event if self.total_event else math.nan,
            "routine_rate": self.delivered_routine / self.total_routine if self.total_routine else math.nan,
            "missed_event": self.missed_event,
            "missed_routine": self.missed_routine,
            "attempts": self.attempts,
            "probe_attempts": self.probes,
            "successes": self.successes,
            "wasted_bad_path": self.wasted_bad_path,
            "energy": round(self.energy, 6),
            "energy_left": None if self.energy_left is None else round(self.energy_left, 6),
            "money": round(self.money, 6),
            "sat_quota_used": self.sat_quota_used,
            "overflow": self.overflow,
            "evidence_count": len(self.evidence),
            "same_epoch_evidence_count": sum(
                item.returned_before_action_index <= len(self.action_ledger) for item in self.evidence
            ),
            "action_ledger": list(self.action_ledger),
            "evidence_ledger": [asdict(item) for item in self.evidence],
        }


class InformationPolicy:
    """四臂共用的在线信念与逐包效率规则；仅信息返回时刻不同。"""

    def __init__(self, arm: str, event_energy_multiplier: float = 3.0,
                 feedback_batch_size: int = 1):
        if arm not in ("history_only", "data_ack", "paid_probe", "current_truth"):
            raise ValueError(f"unknown arm: {arm}")
        self.arm = arm
        self.event_energy_multiplier = event_energy_multiplier
        if feedback_batch_size < 1:
            raise ValueError("feedback_batch_size must be positive")
        self.feedback_batch_size = feedback_batch_size
        self.belief: dict[str, float] = {}

    def start_epoch(self, env: TimingEnv) -> None:
        for path in env.tr.paths:
            spec = PATH_SPECS[path]
            if path not in self.belief or env.t == 0:
                self.belief[path] = spec["good_frac"]
            elif spec["kind"] == "markov":
                if env.tr.burst == "iid":
                    self.belief[path] = spec["good_frac"]
                else:
                    p_gb, p_bg = env.ge_for(path)
                    b = self.belief[path]
                    self.belief[path] = b * (1 - p_gb) + (1 - b) * p_bg
            elif path == "uav":
                self.belief[path] = spec["good_frac"] if env.tr.uav_scheduled(env.t) else 0.0

    def update(self, evidence: Evidence) -> None:
        prior = min(1 - 1e-12, max(1e-12, self.belief[evidence.path]))
        like_good = GOOD_TX_SUCCESS if evidence.success else 1 - GOOD_TX_SUCCESS
        like_bad = BAD_TX_SUCCESS if evidence.success else 1 - BAD_TX_SUCCESS
        denominator = prior * like_good + (1 - prior) * like_bad
        self.belief[evidence.path] = prior * like_good / denominator

    def _q(self, env: TimingEnv, path: str) -> float:
        if self.arm == "current_truth":
            good = bool(env.tr.link_good[path][env.t])
            return GOOD_TX_SUCCESS if good else BAD_TX_SUCCESS
        belief = self.belief[path]
        return belief * GOOD_TX_SUCCESS + (1 - belief) * BAD_TX_SUCCESS

    def select_path(self, env: TimingEnv, kind: str, cap_left: dict[str, int] | None = None) -> str | None:
        eligible = env.eligible_paths(kind)
        if cap_left is not None:
            eligible = [path for path in eligible if cap_left.get(path, 0) > 0]
        scored = []
        for path in eligible:
            q = self._q(env, path)
            if q <= 0.05:
                continue
            energy = PATH_SPECS[path]["energy"] * (
                env.probe_cost_multiplier if kind == "probe" else 1.0)
            scored.append((q / energy, -PATH_SPECS[path]["money"], -PATH_ORDER.index(path), path))
        return max(scored)[-1] if scored else None

    def energy_allowance(self, env: TimingEnv) -> float:
        if env.energy_left is None:
            return math.inf
        hours_left = max(1, env.tr.T - env.t)
        multiplier = self.event_energy_multiplier if env.backlog_event else 0.75
        return min(env.energy_left, env.energy_left / hours_left * multiplier)

    def _run_batch(self, env: TimingEnv, allowance: float) -> None:
        cap_left = dict(env._cap_left)
        energy_left = allowance
        expected_backlog = float(len(env.queue))
        plan: list[str] = []
        while expected_backlog > 0.5:
            path = self.select_path(env, "data", cap_left)
            if path is None:
                break
            cost = PATH_SPECS[path]["energy"]
            if energy_left < cost - 1e-9:
                break
            plan.append(path)
            cap_left[path] -= 1
            energy_left -= cost
            expected_backlog -= self._q(env, path)
        observations = []
        for path in plan:
            outcome = env.attempt(path, "data")
            if outcome is not None:
                observations.append(outcome.evidence)
        for evidence in observations:
            self.update(evidence)

    def _run_sequential(self, env: TimingEnv, allowance: float) -> None:
        pending: dict[str, list[Evidence]] = {path: [] for path in env.tr.paths}
        while env.queue and env.epoch_energy_spent < allowance - 1e-9:
            path = self.select_path(env, "data")
            if path is None:
                break
            cost = PATH_SPECS[path]["energy"]
            if env.epoch_energy_spent + cost > allowance + 1e-9:
                break
            outcome = env.attempt(path, "data")
            if outcome is None:
                break
            if self.arm != "current_truth":
                pending[path].append(outcome.evidence)
                if len(pending[path]) >= self.feedback_batch_size:
                    for evidence in pending[path]:
                        self.update(evidence)
                    pending[path] = []
        if self.arm != "current_truth":
            for observations in pending.values():
                for evidence in observations:
                    self.update(evidence)

    def run_epoch(self, env: TimingEnv) -> None:
        allowance = self.energy_allowance(env)
        if self.arm == "paid_probe" and env.backlog_event:
            candidates = env.eligible_paths("probe")
            if candidates:
                path = max(candidates, key=lambda p: self.belief[p] * (1 - self.belief[p]))
                probe_cost = PATH_SPECS[path]["energy"] * env.probe_cost_multiplier
                if probe_cost <= allowance + 1e-9:
                    outcome = env.attempt(path, "probe")
                    if outcome is not None:
                        self.update(outcome.evidence)
        if self.arm == "history_only":
            self._run_batch(env, allowance)
        else:
            self._run_sequential(env, allowance)


def run_arm(trace: Trace, arm: str, energy_budget: float | None,
            probe_cost_multiplier: float = 1.0,
            event_energy_multiplier: float = 3.0,
            feedback_batch_size: int = 1) -> dict:
    env = TimingEnv(trace, energy_budget=energy_budget,
                    probe_cost_multiplier=probe_cost_multiplier)
    policy = InformationPolicy(
        arm,
        event_energy_multiplier=event_energy_multiplier,
        feedback_batch_size=feedback_batch_size,
    )
    for _ in range(trace.T):
        env.begin_epoch()
        policy.start_epoch(env)
        policy.run_epoch(env)
        env.end_epoch()
    return env.finalize()
