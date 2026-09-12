#!/usr/bin/env python3
"""
task_generator.py — the exogenous demand sequence, P0.4 of the pre-disaster contract.

WHAT THIS FILE IS. The primary metric of the study is timely valid monitoring coverage,

    TimelyCoverage = sum_d w_d * I(valid sample in d.window AND received by d.deadline)
                     / sum_d w_d,

and the denominator D is exogenous (README D4, contract §8): it is produced here, before any
method runs, and every arm is scored against the same D. A method that communicates more, or
samples more, therefore cannot enlarge its own denominator. That is why this module is a pure
function of (deployment, hours, seed): it never reads channel state, energy state, buffer state,
agent beliefs or any simulator object.

WHAT THIS FILE IS NOT. It models demands only. Sampling, scheduling, uplink, retransmission,
buffering and delivery belong to the simulator and to the methods that are compared. The scorer
compares the demands below against what actually arrived; it does not ask this module whether
anything arrived.

EVIDENCE LAYER. Every coordinate, elevation, offset, interval, deadline and critical-set
membership in this file is **A: a research reference assumption** (README D16). None of it is a
surveyed site, a customer SLA, an acceptance figure from a monitoring contract, or a geohazard
safety standard. The 72 h / 5 min / 10 min / 90 min figures are diagnostic parameters chosen so
that the chain demand -> sampling -> delivery -> scoring can be exercised end to end; their
sensitivity is part of the plan (contract §5, D16).

DEV / TEST ISOLATION. Seeds are split into two disjoint ranges (contract §5, README §8):
development seeds 0-999, test seeds 10000 and above. The seed fixes a bounded, documented shift of
the normal demand cadence (see `_seed_offset_s`), so seeds of one split give different normal demand
sets while the two splits stay genuinely disjoint; the risk windows are never shifted. Tune a method
on the development split only; the test split is for the frozen protocol. See `demand_seed_split`.

Deps: standard library only (numpy is not needed to produce demands).
"""
from __future__ import annotations

# --- module resolution -------------------------------------------------------
# Scripts live in code/{physics,runtime,experiments,analysis,monitoring}; any of them may import
# from another group, so the code root and every group directory go on the path.
import os as _os, sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_CODE = _os.path.dirname(_HERE)
for _p in (_HERE, *(_os.path.join(_CODE, d) for d in ("physics", "runtime",
                                                     "experiments", "analysis", "monitoring"))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# -----------------------------------------------------------------------------

import hashlib
import json
from dataclasses import dataclass

# =============================================================== reference workload
# Contract §5, "首个可实现的 72 小时参考负载". Every value below is **A: a diagnostic parameter
# of this study, not a geohazard safety standard and not a customer SLA.** The frequency pattern
# has case background (Wang et al. 2022 switch cadence between normal and abnormal stages), but
# the combination, the deadlines and the event instants are research assumptions.

DEFAULT_HOURS = 72                              # A: reference run length, hours
RISK_WINDOWS_H = ((12.0, 18.0), (48.0, 54.0))   # A: risk windows, hours since run start.
                                                #    The reference load stops before any disaster.
NORMAL_INTERVAL_S = 60 * 60                     # A: one normal demand window per 60 min
RISK_INTERVAL_S = 5 * 60                        # A: one risk demand window per 5 min
DEADLINE_S = {"normal": 90 * 60, "risk": 10 * 60}   # A: valid sample within 90 min / 10 min
                                                    #    of the window start
NODE_DT_S = 60                                  # A: the run clock is a 1 min grid; every interval
                                                #    here is a whole number of minutes

NODE_COUNT = 16                                 # A: fixed by architecture A (README D2, §3)
GROUP_COUNT = 2                                 # A: two slope groups (README D2, contract §3)

# The monitoring profiles the demand refers to. `policy_generation` names one of these; it does
# not describe a concrete device and this module does not schedule anything.
PROFILE_NORMAL = "normal"
PROFILE_RISK = "risk"
PROFILE_LOW_POWER = "low_power"          # A: never demanded by the 72 h load; it exists for the
                                         #    recovery phase of W3 (contract §4)

MONITORING_PROFILES = {
    PROFILE_NORMAL:    {"sample_s": 5 * 60,  "upload_s": 60 * 60},     # A
    PROFILE_RISK:      {"sample_s": 1 * 60,  "upload_s": 5 * 60},      # A
    PROFILE_LOW_POWER: {"sample_s": 15 * 60, "upload_s": 60 * 60},     # A; a demanded profile
                                                                       #    never lowers a local
                                                                       #    watchdog
}

PRIORITY_NORMAL = 0        # A: ordinal, not a calibrated weight. Risk-window demands rank above
PRIORITY_RISK = 1          #    normal demands; the metric weights w_d are a separate, pre-fixed
                           #    choice (contract §8).

# =============================================================== dev / test isolation
DEV_SEED_MIN, DEV_SEED_MAX = 0, 999        # development: tuning, debugging, sensitivity scans
TEST_SEED_MIN = 10_000                     # test: frozen protocol only, never tune on these
SEED_RANGE_DEV = (DEV_SEED_MIN, DEV_SEED_MAX)
SEED_RANGE_TEST = (TEST_SEED_MIN, None)    # open-ended upper bound

# A: how far the per-seed shift of the normal demand cadence may go, in seconds. Bounded at one
# risk-window step (5 min) so that a normal window can never creep into a risk window and so that
# nobody can mistake the shift for a modelling parameter. The reference reading of the contract
# table is the zero-shift cadence; this exists only to make a seed mean something.
SEED_OFFSET_MAX_S = RISK_INTERVAL_S

# A: the shift values each split may use, in seconds, as multiples of the run clock. The pools are
# disjoint, so no development seed can reproduce a test cadence. Zero is in the development pool so
# that at least one development seed reproduces the contract table's cadence literally: normal
# windows exactly on the hour. A shift of 60-240 s is what makes two seeds of the same split differ.
SEED_OFFSETS_DEV = (0, 60, 120, 180)
SEED_OFFSETS_TEST = (240, SEED_OFFSET_MAX_S)
assert not (set(SEED_OFFSETS_DEV) & set(SEED_OFFSETS_TEST))
assert all(0 <= o <= SEED_OFFSET_MAX_S and o % NODE_DT_S == 0
           for o in SEED_OFFSETS_DEV + SEED_OFFSETS_TEST)
assert 0 in SEED_OFFSETS_DEV, "no seed reproduces the table's cadence literally"


def demand_seed_range(split: str) -> tuple[int, int | None]:
    """Seed range for a split name. The two ranges are disjoint by construction."""
    if split == "dev":
        return SEED_RANGE_DEV
    if split == "test":
        return SEED_RANGE_TEST
    raise ValueError(f"unknown split {split!r}; expected 'dev' or 'test'")


def demand_seed_split(seed: int) -> str:
    """Which split a seed belongs to. Seeds in no split are rejected."""
    if DEV_SEED_MIN <= seed <= DEV_SEED_MAX:
        return "dev"
    if seed >= TEST_SEED_MIN:
        return "test"
    raise ValueError(
        f"seed {seed} is in no split: dev is [{DEV_SEED_MIN}, {DEV_SEED_MAX}], "
        f"test starts at {TEST_SEED_MIN}")

# =============================================================== deployment (A-layer)
# Architecture A (README D2, contract §3): one gateway in the valley, LoRaWAN Class A nodes on two
# slopes, intermittent cellular backhaul. The gateway is the fixed gateway of the existing study
# (README §四): 30.330 N, 94.780 E, 2317 m, in the valley, with ridges above 3300 m around it.
#
# A-LAYER NOTICE. The node coordinates and elevations below are **research assumptions**. They are
# not surveyed monuments and must never be described as real monitoring sites. What the study
# needs is two separated slope groups with distinct aspect and slope; the exact numbers are a
# design choice. The gateway line itself carries over from the existing physics group and its
# 2317 m reproduces the value recorded in README §四.
#
# HOW THE OFFSETS WERE CHOSEN. Local offsets are multiples of the spacing of the study grid in
# results/coverage_grid.csv (121 x 121 points, 0.00183 deg, about 204 m in latitude and about
# 176 m in longitude; README §四). Using that grid keeps every node exactly one grid step from its
# neighbours and keeps the deployment inside the region the physics group already models.
# Elevations were sampled from the same real SRTM1 tile the physics group uses
# (data/dem/hgt/N30E094.hgt) and rounded to whole metres: an A-layer convenience so the energy
# model has a defensible starting altitude, not a survey result.
GATEWAY_LAT = 30.3300            # A/mixed: the fixed gateway of the existing study (README §四)
GATEWAY_LON = 94.7800            # A/mixed: as above
GATEWAY_ELEV_M = 2317.0          # A/mixed: as above
GRID_STEP_DEG = 0.00183          # A: spacing of the study grid, about 204 m in latitude

# Node rows as (lat_step, lon_step) multiples of GRID_STEP_DEG relative to the gateway. Each group
# is a three-row fan of 8 points: 5 on the row nearest the gateway, 2 in the middle row, 1 on the
# farthest row. Both fans drop one far corner, so neither group contains the gateway grid cell
# itself (the gateway has no sensor) and the two groups occupy disjoint cells.
#
# What makes the groups two slopes rather than two clouds: group 0 is north of the valley and rises
# away from it, group 1 is south and its high side is a west spur whose east side drops to the
# valley. The near rows sit on the valley floor within about 270 m of the gateway, so the split into
# a near row (0-13 m above the gateway) and an upslope part (39-200 m above it) is common to both,
# while the aspect and the slope profile differ. The numbers are A-layer; the separation is the
# point.
_GROUP_OFFSETS = {
    # group 0, looking north. Near row local 0-2, middle row local 3-4, far row local 5-7.
    0: ((1, -1), (1, 0), (1, 1), (2, -1), (2, 1), (3, -1), (3, 0), (3, 1)),
    # group 1, looking south. Near row local 5-7, middle row local 3-4, far row local 0-2.
    1: ((-3, -1), (-3, 0), (-3, 1), (-2, -1), (-2, 1), (-1, -1), (-1, 0), (-1, 1)),
}

# Whole-metre elevations in the order of _GROUP_OFFSETS above, sampled from SRTM1 N30E094 at those
# coordinates. The gateway (2317 m) sits in a hollow: its nearest node in either group is already
# 3-13 m higher.
# group 0: near row 2317, 2325, 2330 m; middle row 2356, 2361 m; far row 2454, 2470, 2491 m.
#          The far row is the top of this slope, about 175 m above the near row.
# group 1: near row 2307, 2311, 2312 m; middle row 2307, 2389 m; far row 2507, 2517, 2539 m.
#          The west side of the group is the spur and the east side stays near 2307 m, so the group
#          is asymmetric: a steep 129-187 m step between the middle row and the far row on the
#          west, and an almost flat shoulder on the east.
_GROUP_ELEV_M = {
    0: (2325.0, 2317.0, 2330.0, 2361.0, 2356.0, 2470.0, 2454.0, 2491.0),
    1: (2539.0, 2517.0, 2507.0, 2389.0, 2307.0, 2318.0, 2311.0, 2312.0),
}

# A: role split. Displacement monitoring needs stable, well-founded stations; a rain gauge is an
# areal instrument, so one gauge per slope group is the documented choice. Both gauges sit on the
# middle row, which reads as the shoulder of each slope above the valley floor.
_ROLE_BY_LOCAL_INDEX = ("deformation", "rainfall", "deformation", "deformation",
                        "deformation", "deformation", "deformation", "deformation")

# A: the risk-window critical set. Contract §3 has the risk-window critical set given by the task,
# and the demand generator must not redraw it per task, so it is a property of the deployment. The
# documented rule: the whole far row of each group plus the highest displacement station of the
# middle row plus that group's rain gauge. Displacement at the top of a slope is what threatens the
# valley and the gateway, and the gauge on the slope is what sees the rain that feeds it; the
# near-row stations sit on the valley floor a few metres above the gateway, so they are not in the
# critical set. Result: 8 of the 16 nodes are critical, 4 per group, 6 of the 10 displacement
# stations and both gauges. Local indices per group -> group 0: 1 (gauge, n01), 5 (n05), 6 (n06),
# 7 (n07); group 1: 0 (n08), 2 (n10), 3 (n11), 1 (gauge, n09).
_CRITICAL_LOCAL_INDEX = {0: (1, 5, 6, 7), 1: (0, 1, 2, 3)}


@dataclass(frozen=True)
class Gateway:
    """The single field gateway."""
    gid: str
    lat: float
    lon: float
    elev_m: float
    is_gateway: bool = True


@dataclass(frozen=True)
class Node:
    """One monitoring station. All geometry is A-layer (see the notice above)."""
    nid: str
    lat: float
    lon: float
    elev_m: float
    role: str                 # "deformation" | "rainfall"
    slope_group: int          # 0 | 1
    critical: bool            # member of the risk-window critical set


@dataclass(frozen=True)
class Deployment:
    """16 nodes in 2 slope groups plus one gateway. Fixed across seeds by construction.

    Every derived view is returned in canonical node-id order. That is not cosmetic: the demand
    task ids embed the node-set order, so a generator that trusted an incidental container order
    would let the deployment's storage order leak into D. Ordering here keeps D a function of the
    deployment's contents.
    """
    gateway: Gateway
    nodes: tuple[Node, ...]

    @property
    def nids(self) -> tuple[str, ...]:
        return tuple(sorted(n.nid for n in self.nodes))

    @property
    def critical_nids(self) -> tuple[str, ...]:
        return tuple(sorted(n.nid for n in self.nodes if n.critical))

    def nodes_with_role(self, role: str) -> tuple[str, ...]:
        return tuple(sorted(n.nid for n in self.nodes if n.role == role))


@dataclass(frozen=True)
class Task:
    """The contract §4 task representation. A demand only: no sampling, no delivery.

    id                 stable identity of the demand, deterministic and arm-independent
    node_set           nodes the demand applies to
    measurement_type   "displacement" or "rainfall"
    release_time       seconds since run start; the demand exists from here on
    sample_window      (start_s, end_s); a sample taken in this interval can satisfy the demand
    delivery_deadline  seconds since run start by which a valid sample must have arrived
    priority           ordinal rank; risk-window demands rank above normal demands
    policy_generation  which monitoring profile the demand calls for (MONITORING_PROFILES)
    """
    id: str
    node_set: tuple[str, ...]
    measurement_type: str
    release_time: int
    sample_window: tuple[int, int]
    delivery_deadline: int
    priority: int
    policy_generation: int

    @property
    def window_s(self) -> int:
        return self.sample_window[1] - self.sample_window[0]

    @property
    def slack_s(self) -> int:
        """How long after the window closes a sample may still arrive: deadline - window end."""
        return self.delivery_deadline - self.sample_window[1]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "node_set": list(self.node_set),
            "measurement_type": self.measurement_type,
            "release_time": self.release_time,
            "sample_window": list(self.sample_window),
            "delivery_deadline": self.delivery_deadline,
            "priority": self.priority,
            "policy_generation": self.policy_generation,
        }

    def signature(self) -> str:
        """Canonical one-line form used for byte-identity and disjointness checks."""
        return (f"{self.id}|{','.join(self.node_set)}|{self.measurement_type}|"
                f"{self.release_time}|{self.sample_window[0]}-{self.sample_window[1]}|"
                f"{self.delivery_deadline}|{self.priority}|{self.policy_generation}")


# =============================================================== helpers

def risk_window_hours() -> tuple[tuple[float, float], ...]:
    """The risk windows as (start_hour, end_hour) pairs, fixed by the contract §5 table."""
    return RISK_WINDOWS_H


def profile_for_hour(hour: float, risk_windows: tuple[tuple[float, float], ...] = RISK_WINDOWS_H
                     ) -> str:
    """Which monitoring profile is demanded at `hour`.

    Hours 12-18 and 48-54 demand the dense risk profile; every other hour demands the normal
    profile. The intervals are half-open, [start, end), so hour 18.0 and hour 54.0 are already
    back to normal. The low-power profile is never demanded by the 72 h reference load: the
    contract lists it for the recovery phase of W3 (contract §4).
    """
    for start, end in risk_windows:
        if start <= hour < end:
            return PROFILE_RISK
    return PROFILE_NORMAL


def window_len_s(profile: str) -> int:
    """Length of one demand window under a profile, from the reference load table.

    The risk window is one 5 min demand window, so each critical-node demand must be met by a
    sample taken inside that same 5 min; the normal window is one 60 min demand window. The
    decision that is left open by the table: the sample that satisfies a demand is taken INSIDE
    the demand window. The alternative reading, where a 10 min risk deadline lets a demand be
    satisfied by a sample taken up to 10 min after its window starts, would make neighbouring
    risk windows share samples, and would give the risk profile a 1 min sampler five chances to
    satisfy one demand instead of one. The stricter reading is used here and the choice is
    recorded in the module notes.
    """
    if profile == PROFILE_RISK:
        return RISK_INTERVAL_S
    if profile == PROFILE_NORMAL:
        return NORMAL_INTERVAL_S
    raise ValueError(f"no demand window is defined for profile {profile!r}")


def normal_nodes(deployment: Deployment) -> tuple[str, ...]:
    """Nodes the normal demand applies to: all 16 (contract §5)."""
    return deployment.nids


def critical_nodes(deployment: Deployment) -> tuple[str, ...]:
    """Nodes the risk-window demand applies to: the fixed critical subset of the deployment."""
    return deployment.critical_nids


def _seed_offset_s(seed: int) -> int:
    """Deterministic per-seed offset of the normal demand cadence, in seconds.

    A-layer research assumption. The offset is drawn from a hash of the seed, so it is fully
    reproducible, it does not consume any random stream, and it cannot be influenced by a method.
    It makes the seed a real input: distinct seeds give distinct normal demand sets, which is what
    lets the development and test splits stay disjoint.

    The offset is drawn only from that split's own pool (see SEED_OFFSETS_DEV and
    SEED_OFFSETS_TEST); the pools are disjoint, so a development seed and a test seed can never
    produce the same normal cadence, and one development seed keeps the table's exact zero-shift
    cadence. Risk-window demand instants are NOT offset, so the risk windows stay exactly where the
    contract puts them, and the shift is bounded by one risk step, so a normal window can never
    leave its own hour and can never land inside a risk window.
    """
    split = demand_seed_split(seed)
    pool = SEED_OFFSETS_DEV if split == "dev" else SEED_OFFSETS_TEST
    digest = hashlib.sha256(f"p0.4-normal-offset|{split}|{seed}".encode()).digest()
    return pool[int.from_bytes(digest[:4], "big") % len(pool)]


def _release_grid(total_s: int, seed: int = 0) -> list[int]:
    """Demand-window start instants for the whole run, on the 60 s run clock.

    Normal windows sit on the 60 min grid and five of them fall inside each 6 h risk window. Those
    five are dropped: hours 12-18 and 48-54 are demanded at the risk cadence, so the normal cadence
    does not also apply inside them. Without that exclusion the reference load would demand 30 %
    more windows than its own table implies.

    A window is kept when it STARTS inside the run, because every start instant the table specifies
    is a demand the generator is supposed to produce. The last normal window therefore closes after
    the nominal 72 h, and its deadline reaches past it too; both overruns are bounded by one window
    and one deadline respectively, and the run-level rule that nothing is demanded after the run
    ends still holds. Dropping that window instead would silently remove a demand from the last
    hour of the reference load.

    Normal windows are then shifted by one documented per-seed offset (see `_seed_offset_s`). The
    shift is common to all of them, so their spacing stays exactly one hour and they cannot
    collide. Risk instants are never shifted. The shift is bounded by one risk step, so a normal
    window can never leave its own hour and can never land inside a risk window.
    """
    normal = [t for t in range(0, total_s, NORMAL_INTERVAL_S)]
    risk = [t for t in range(0, total_s, RISK_INTERVAL_S)
            if profile_for_hour(t / 3600.0) == PROFILE_RISK]
    in_risk = {t for t in normal if profile_for_hour(t / 3600.0) == PROFILE_RISK}
    kept_normal = set(normal) - in_risk
    offset = _seed_offset_s(seed)
    shifted_normal = {t + offset for t in kept_normal}
    grid = sorted(shifted_normal | set(risk))

    assert len(grid) == len(shifted_normal) + len(risk), "a start instant was lost or duplicated"
    assert not (shifted_normal & set(risk)), "a normal window collides with a risk window"
    assert all(t % RISK_INTERVAL_S == 0 for t in risk), "risk instants leave the 5 min grid"
    assert all(t < total_s for t in grid), "a window starts after the end of the run"
    assert 0 <= offset <= SEED_OFFSET_MAX_S
    assert offset % NODE_DT_S == 0, "the shift is not on the run clock"
    assert {t - offset for t in shifted_normal} == kept_normal, "the shift changed the cadence"
    return grid


def _demands_for_instant(deployment: Deployment, in_risk: bool
                         ) -> tuple[tuple[tuple[str, ...], str], ...]:
    """The (node_set, measurement_type) pairs demanded at one start instant.

    A task carries a single measurement_type, so one demand window yields one task per measured
    quantity: displacement and rainfall. Both pairs at an instant share the same release time,
    window and deadline; they differ only in what is measured and on which stations.

      normal instant: all 16 nodes, split by role -> 10 displacement stations, 6 gauges
      risk instant:   the critical set, split by role -> 6 displacement stations, 2 gauges

    Only the deployment's contents are read, each through the deployment's own canonical views, so
    the result does not depend on the order in which the deployment stores its nodes.
    """
    scope = set(deployment.critical_nids if in_risk else deployment.nids)
    if not scope:
        raise ValueError("no node is in scope at this instant")
    plans: list[tuple[tuple[str, ...], str]] = []
    for role, measurement_type in (("deformation", "displacement"), ("rainfall", "rainfall")):
        subset = tuple(sorted(nid for nid in deployment.nodes_with_role(role) if nid in scope))
        if subset:
            plans.append((subset, measurement_type))
    if not plans:
        raise ValueError("no measured quantity is demanded at this instant")
    return tuple(plans)


# =============================================================== deployment

def build_deployment(seed: int = 0) -> Deployment:
    """The reference deployment: 16 nodes in 2 slope groups of 8, plus the fixed gateway.

    The deployment does NOT depend on the seed. The argument is accepted so that call sites read
    uniformly with the rest of the P0 generators; if a later revision randomises anything here it
    may randomise only A-layer geometry. Nothing about a method may reach this function.
    """
    del seed  # deliberately unused: the deployment is fixed, see _GROUP_OFFSETS
    for group in range(GROUP_COUNT):
        assert len(_GROUP_OFFSETS[group]) == NODE_COUNT // GROUP_COUNT
        assert len(_GROUP_ELEV_M[group]) == NODE_COUNT // GROUP_COUNT
        assert set(_CRITICAL_LOCAL_INDEX[group]) <= set(range(len(_GROUP_OFFSETS[group]))), \
            f"group {group} has a critical index outside its own rows"
    gateway = Gateway("gw0", GATEWAY_LAT, GATEWAY_LON, GATEWAY_ELEV_M)
    nodes: list[Node] = []
    for group in range(GROUP_COUNT):
        for idx, (lat_step, lon_step) in enumerate(_GROUP_OFFSETS[group]):
            nodes.append(Node(
                nid=f"n{group * 8 + idx:02d}",
                lat=round(GATEWAY_LAT + lat_step * GRID_STEP_DEG, 5),
                lon=round(GATEWAY_LON + lon_step * GRID_STEP_DEG, 5),
                elev_m=_GROUP_ELEV_M[group][idx],
                role=_ROLE_BY_LOCAL_INDEX[idx],
                slope_group=group,
                critical=idx in _CRITICAL_LOCAL_INDEX[group],
            ))
    assert len(nodes) == NODE_COUNT
    nodes.sort(key=lambda n: n.nid)
    return Deployment(gateway=gateway, nodes=tuple(nodes))


# =============================================================== demand generator

def _check_reference_load() -> None:
    """The reference load must be internally consistent and land where the table says."""
    for start, end in RISK_WINDOWS_H:
        assert start % (NORMAL_INTERVAL_S / 3600.0) == 0, "risk window does not start on the hour"
        assert end % (NORMAL_INTERVAL_S / 3600.0) == 0, "risk window does not end on the hour"
        assert start < end
    assert profile_for_hour(RISK_WINDOWS_H[0][0]) == PROFILE_RISK
    assert profile_for_hour(RISK_WINDOWS_H[0][1]) == PROFILE_NORMAL
    for name, p in MONITORING_PROFILES.items():
        for key in ("sample_s", "upload_s"):
            assert p[key] % NODE_DT_S == 0, f"{name}.{key} is not on the {NODE_DT_S} s clock"
    for value in (NORMAL_INTERVAL_S, RISK_INTERVAL_S, *DEADLINE_S.values()):
        assert value % NODE_DT_S == 0


def build_demand(deployment: Deployment, hours: int = DEFAULT_HOURS, seed: int = 0) -> list[Task]:
    """The reference demand sequence D for one run. Pure in (deployment, hours, seed).

    One demand window yields one task per measured quantity, because the contract's task carries a
    single measurement_type. Counts for the 72 h reference load: 60 normal windows (one per hour
    outside the two 6 h risk windows) times two quantities, and 72 risk windows (one per 5 min
    inside them) times two quantities.

    `seed` is validated against the dev/test split and it fixes the per-seed shift of the normal
    cadence (see `_seed_offset_s`). D is pure in (deployment, hours, seed): the same three inputs
    always give byte-identical D, no random stream is consumed, no module state is kept, and no
    argument of this function can be reached by a method. That is what README D4 asks for, and the
    permutation check in test_task_generator.py enforces it.

    Args:
        deployment: the fixed 16-node / 2-group / 1-gateway deployment.
        hours: run length in hours; defaults to the 72 h reference workload.
        seed: selects the dev or test split and the normal-cadence shift.

    Returns:
        Tasks ordered by (release_time, measurement_type).
    """
    _check_reference_load()
    if hours <= 0:
        raise ValueError(f"hours must be positive, got {hours}")
    demand_seed_split(seed)

    total_s = int(round(hours * 3600.0))
    critical = set(deployment.critical_nids)
    if not critical:
        raise ValueError("the deployment must define a risk-window critical set")
    normal_set = tuple(deployment.nids)
    assert normal_set, "the deployment must have nodes"

    tasks: list[Task] = []
    generation = 0
    previous_profile: str | None = None

    for index, release in enumerate(_release_grid(total_s, seed)):
        hour = release / 3600.0
        profile = profile_for_hour(hour)
        in_risk = profile == PROFILE_RISK
        if profile != previous_profile:
            # policy_generation advances when the demanded monitoring profile changes. It is a
            # property of the demand timeline, not of any arm's configuration events, so a method
            # cannot make it advance.
            generation += 1
            previous_profile = profile

        window = (release, release + window_len_s(profile))
        deadline = release + DEADLINE_S["risk" if in_risk else "normal"]
        for node_set, measurement_type in _demands_for_instant(deployment, in_risk):
            if in_risk:
                assert set(node_set) <= critical
            tasks.append(Task(
                id=f"{'risk' if in_risk else 'norm'}-{measurement_type[:4]}-"
                   f"{index:04d}-t{release}",
                node_set=node_set,
                measurement_type=measurement_type,
                release_time=release,
                sample_window=window,
                delivery_deadline=deadline,
                priority=PRIORITY_RISK if in_risk else PRIORITY_NORMAL,
                policy_generation=generation,
            ))

    tasks.sort(key=lambda t: (t.release_time, t.measurement_type))
    _assert_reference_counts(tasks, hours)
    return tasks


def expected_instants(hours: int = DEFAULT_HOURS) -> tuple[int, int]:
    """(normal start instants, risk start instants) the contract §5 table implies for `hours`.

    Derived from the table and the risk windows, not from the generator's own output, so a test can
    compare the two independently. A start instant counts when it lies inside the run, matching the
    generator's rule; for the 72 h reference load this gives 60 normal instants (one per hour
    outside the two 6 h risk windows) and 144 risk instants (one per 5 min, so 12/h inside the
    12 h covered by risk windows). One instant carries one task per measured quantity, so the task
    count is twice these numbers.
    """
    total_s = int(round(hours * 3600.0))
    risk = [t for t in range(0, total_s, RISK_INTERVAL_S)
            if profile_for_hour(t / 3600.0) == PROFILE_RISK]
    normal = [t for t in range(0, total_s, NORMAL_INTERVAL_S)
              if profile_for_hour(t / 3600.0) == PROFILE_NORMAL]
    return len(normal), len(risk)


def _assert_reference_counts(tasks: list[Task], hours: int) -> None:
    """The realised load must equal what the contract §5 table implies."""
    want_normal, want_risk = expected_instants(hours)
    quantities = 2                                     # displacement and rainfall
    got_normal = sum(1 for t in tasks if t.priority == PRIORITY_NORMAL)
    got_risk = sum(1 for t in tasks if t.priority == PRIORITY_RISK)
    assert got_normal == want_normal * quantities, (
        f"normal demands {got_normal}, the table implies {want_normal * quantities}")
    assert got_risk == want_risk * quantities, (
        f"risk demands {got_risk}, the table implies {want_risk * quantities}")


def canonical_demand_bytes(tasks: list[Task]) -> bytes:
    """Canonical serialisation of D, for byte-identity checks between arms and across runs."""
    payload = [t.as_dict() for t in tasks]
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def demand_digest(tasks: list[Task]) -> str:
    """SHA-256 of `canonical_demand_bytes`, for logging which D a run was scored against."""
    return hashlib.sha256(canonical_demand_bytes(tasks)).hexdigest()


def dev_demand(hours: int = DEFAULT_HOURS, seed: int = 0) -> list[Task]:
    """Demand set for the development split (seeds 0-999). Tuning is allowed here."""
    demand_seed_split(seed)
    if demand_seed_split(seed) != "dev":
        raise ValueError(f"dev_demand needs a dev seed in [{DEV_SEED_MIN}, {DEV_SEED_MAX}]")
    return build_demand(build_deployment(seed), hours=hours, seed=seed)


def test_demand(hours: int = DEFAULT_HOURS, seed: int = TEST_SEED_MIN) -> list[Task]:
    """Demand set for the test split (seeds >= 10000). Frozen protocol only, never tune on it."""
    if demand_seed_split(seed) != "test":
        raise ValueError(f"test_demand needs a test seed >= {TEST_SEED_MIN}")
    return build_demand(build_deployment(seed), hours=hours, seed=seed)


# =============================================================== command line

def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Exogenous demand generator (P0.4, contract §5). Prints the reference load's "
                    "size and its digest, and can dump the whole task list.")
    ap.add_argument("--hours", type=int, default=DEFAULT_HOURS, help="run length in hours")
    ap.add_argument("--seed", type=int, default=0,
                    help="dev seeds 0-999, test seeds 10000 and above")
    ap.add_argument("--split", choices=("dev", "test"), default=None,
                    help="assert that --seed belongs to this split")
    ap.add_argument("--list-tasks", action="store_true", help="print every task")
    args = ap.parse_args(argv)

    if args.split is not None and demand_seed_split(args.seed) != args.split:
        raise SystemExit(
            f"seed {args.seed} is in the {demand_seed_split(args.seed)} split, not {args.split}")

    deployment = build_deployment(args.seed)
    tasks = build_demand(deployment, hours=args.hours, seed=args.seed)

    print(f"split {demand_seed_split(args.seed)}  seed {args.seed}  hours {args.hours}")
    print(f"gateway {deployment.gateway.gid} at {deployment.gateway.lat:.4f}, "
          f"{deployment.gateway.lon:.4f}, {deployment.gateway.elev_m:.0f} m")
    print(f"nodes {len(deployment.nodes)}  critical {len(deployment.critical_nids)} "
          f"({', '.join(deployment.critical_nids)})")
    print(f"profiles {sorted(MONITORING_PROFILES)}")
    print(f"risk windows (h) {risk_window_hours()}")
    normal = [t for t in tasks if t.priority == PRIORITY_NORMAL]
    risk = [t for t in tasks if t.priority == PRIORITY_RISK]
    print(f"tasks {len(tasks)}  normal {len(normal)}  risk {len(risk)}")
    print(f"demand digest sha256 {demand_digest(tasks)}")
    if args.list_tasks:
        for t in tasks:
            print(f"  {t.signature()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(_sys.argv[1:]))
