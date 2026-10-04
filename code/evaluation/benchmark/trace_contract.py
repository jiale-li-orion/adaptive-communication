#!/usr/bin/env python3
"""Semantic guards for empirical/model-derived benchmark traces."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any


class TraceContractError(ValueError):
    pass


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_trace_profile(profile: Mapping[str, Any], *, root: Path) -> None:
    klass = profile.get("provenance_class")
    if klass not in {"EMPIRICAL_TRACE", "MODEL_DERIVED_TRACE"}:
        raise TraceContractError(f"invalid trace provenance {klass!r}")

    inputs = profile.get("input_snapshots")
    if not isinstance(inputs, list) or not inputs:
        raise TraceContractError("trace profile requires input snapshots")
    for row in inputs:
        if not isinstance(row, Mapping):
            raise TraceContractError("input snapshot must be an object")
        ref = row.get("ref")
        expected = row.get("sha256")
        if not isinstance(ref, str) or not isinstance(expected, str):
            raise TraceContractError("input snapshot requires ref and sha256")
        path = root / ref
        if not path.exists():
            raise TraceContractError(f"input snapshot missing: {ref}")
        got = _sha256(path)
        if got != expected:
            raise TraceContractError(
                f"input snapshot hash mismatch for {ref}: {got} != {expected}"
            )

    trace_ref = profile.get("trace_ref")
    expected_trace = profile.get("trace_sha256")
    if not isinstance(trace_ref, str) or not isinstance(expected_trace, str):
        raise TraceContractError("trace_ref and trace_sha256 are required")
    trace_path = root / trace_ref
    if not trace_path.exists():
        raise TraceContractError(f"trace artifact missing: {trace_ref}")
    got_trace = _sha256(trace_path)
    if got_trace != expected_trace:
        raise TraceContractError(
            f"trace artifact hash mismatch: {got_trace} != {expected_trace}"
        )

    variables = profile.get("variables")
    if not isinstance(variables, Mapping):
        raise TraceContractError("variables must be an object")
    for name, spec in variables.items():
        if not isinstance(spec, Mapping):
            raise TraceContractError(f"trace variable {name!r} must be an object")
        vklass = spec.get("provenance_class")
        if vklass == "CONTROLLED_STRESS" and not spec.get("stress_rationale"):
            raise TraceContractError(
                f"controlled-stress trace variable {name!r} needs rationale"
            )
        if vklass == "MODEL_DERIVED_TRACE" and not spec.get("trace_ref"):
            raise TraceContractError(
                f"model-derived trace variable {name!r} needs trace_ref"
            )


def validate_trace_registry(
    profiles: Sequence[Mapping[str, Any]], *, root: Path
) -> None:
    seen: set[str] = set()
    for profile in profiles:
        validate_trace_profile(profile, root=root)
        pid = profile.get("trace_profile_id")
        if not isinstance(pid, str) or not pid:
            raise TraceContractError("trace_profile_id required")
        if pid in seen:
            raise TraceContractError(f"duplicate trace_profile_id {pid!r}")
        seen.add(pid)
