"""
code/monitoring — the exogenous demand side of the pre-disaster monitoring study.

This package holds what is GIVEN to every method rather than what a method decides. So far it
contains one module:

  task_generator   the reference deployment (16 nodes, 2 slope groups, 1 gateway) and the 72 h
                   reference demand sequence built on top of it.

The demand sequence is the denominator of the primary metric (README D4, contract §8). It is a
pure function of (deployment, hours, seed) and it must be identical for every arm, so nothing in
this package may read simulator state, channel state, energy state or agent beliefs.
"""
from __future__ import annotations

from .task_generator import (
    DEFAULT_HOURS,
    DEADLINE_S,
    DEV_SEED_MAX,
    DEV_SEED_MIN,
    GATEWAY_ELEV_M,
    GATEWAY_LAT,
    GATEWAY_LON,
    MONITORING_PROFILES,
    NODE_COUNT,
    NODE_DT_S,
    NORMAL_INTERVAL_S,
    PROFILE_LOW_POWER,
    PROFILE_NORMAL,
    PROFILE_RISK,
    RISK_INTERVAL_S,
    RISK_WINDOWS_H,
    SEED_RANGE_DEV,
    SEED_RANGE_TEST,
    TEST_SEED_MIN,
    Deployment,
    Gateway,
    Node,
    Task,
    build_demand,
    build_deployment,
    canonical_demand_bytes,
    critical_nodes,
    demand_seed_range,
    dev_demand,
    normal_nodes,
    profile_for_hour,
    risk_window_hours,
    test_demand,
)

__all__ = [
    "DEFAULT_HOURS",
    "DEADLINE_S",
    "DEV_SEED_MAX",
    "DEV_SEED_MIN",
    "GATEWAY_ELEV_M",
    "GATEWAY_LAT",
    "GATEWAY_LON",
    "MONITORING_PROFILES",
    "NODE_COUNT",
    "NODE_DT_S",
    "NORMAL_INTERVAL_S",
    "PROFILE_LOW_POWER",
    "PROFILE_NORMAL",
    "PROFILE_RISK",
    "RISK_INTERVAL_S",
    "RISK_WINDOWS_H",
    "SEED_RANGE_DEV",
    "SEED_RANGE_TEST",
    "TEST_SEED_MIN",
    "Deployment",
    "Gateway",
    "Node",
    "Task",
    "build_demand",
    "build_deployment",
    "canonical_demand_bytes",
    "critical_nodes",
    "demand_seed_range",
    "dev_demand",
    "normal_nodes",
    "profile_for_hour",
    "risk_window_hours",
    "test_demand",
]
