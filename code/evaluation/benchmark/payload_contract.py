#!/usr/bin/env python3
"""Guards for source-derived Layer-1 payload profiles."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class PayloadContractError(ValueError):
    pass


def validate_payload_profile(profile: Mapping[str, Any]) -> None:
    if profile.get("schema_version") != "0.1":
        raise PayloadContractError("unsupported payload profile schema")
    encoded = profile.get("encoded_bytes")
    if not isinstance(encoded, int) or encoded <= 0:
        raise PayloadContractError("encoded_bytes must be a positive integer")
    refs = profile.get("source_refs")
    if not isinstance(refs, list) or not refs:
        raise PayloadContractError("payload profile requires source refs")
    derivation = profile.get("derivation")
    if not isinstance(derivation, Mapping):
        raise PayloadContractError("payload profile requires derivation")

    # The current source-example profile is intentionally exact and auditable.
    if profile.get("payload_profile_id") == "DZT0450_TYPE1_SINGLE_SENSOR_EXAMPLE":
        raw = derivation.get("example_ascii")
        if not isinstance(raw, str):
            raise PayloadContractError("example_ascii required")
        header = derivation.get("header_bytes")
        if not isinstance(header, int):
            raise PayloadContractError("header_bytes required")
        if len(raw.encode("ascii")) != derivation.get("example_ascii_bytes"):
            raise PayloadContractError("example_ascii_bytes mismatch")
        if header + len(raw.encode("ascii")) != encoded:
            raise PayloadContractError("encoded_bytes derivation mismatch")


def validate_payload_registry(profiles: Sequence[Mapping[str, Any]]) -> None:
    seen: set[str] = set()
    for profile in profiles:
        validate_payload_profile(profile)
        pid = profile.get("payload_profile_id")
        if not isinstance(pid, str) or not pid:
            raise PayloadContractError("payload_profile_id required")
        if pid in seen:
            raise PayloadContractError(f"duplicate payload_profile_id {pid!r}")
        seen.add(pid)
