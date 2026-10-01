"""Append-only runtime trace for R0/R1/R2/R3 replay and audit."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from .contracts import RuntimeTraceEvent


def json_payload(value) -> dict:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"unsupported trace payload {type(value)!r}")


class RuntimeTrace:
    def __init__(self) -> None:
        self.events: list[RuntimeTraceEvent] = []

    def append(self, event_type: str, t_s: int, payload=None, *, task_run_id: str | None = None):
        body = {} if payload is None else json_payload(payload)
        evt = RuntimeTraceEvent(
            seq=len(self.events) + 1,
            t_s=int(t_s),
            event_type=event_type,
            task_run_id=task_run_id,
            payload=body,
        )
        self.events.append(evt)
        return evt

    def count(self, event_type: str) -> int:
        return sum(e.event_type == event_type for e in self.events)

    def write_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for event in self.events:
                fh.write(event.model_dump_json() + "\n")

    def to_json(self) -> list[dict]:
        return [e.model_dump(mode="json") for e in self.events]
