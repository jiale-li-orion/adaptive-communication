#!/usr/bin/env python3
"""
trace_to_episode.py — PoC: real IODA outage trace -> disruption-tolerance benchmark episode.

Purpose: prove that a *real* disaster connectivity trace can be turned into the episode format
the paper needs (nodes + capability lifecycle + intervention/recovery events), with no NS-3 and
no synthetic fault injection.

Pipeline:
  1. resolve region entities by name (IODA NetAcuity codes)
  2. pull 5-minute raw signals per region (IODA /v2/signals/raw)
  3. build a robust baseline + hysteresis/dwell-time state machine
       -> capability availability: up | degraded | severe | outage
  4. emit episode JSON: per-tick node availability + discrete lifecycle events
  5. print observed failure-mode statistics that the benchmark must reproduce

Usage:
  python3 trace_to_episode.py --start 2024-09-24 --end 2024-10-05 \
     --regions Florida Georgia "North Carolina" --datasource merit-nt --out episode_helene.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import urllib.parse
import urllib.request

API = "https://api.ioda.inetintel.cc.gatech.edu/v2"
UA = {"User-Agent": "disruption-bench-poc/0.1 (research)"}


def get(path: str, **params) -> dict:
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def resolve_region(name: str, prefer_cc: str = "US") -> tuple[str, str]:
    """Return (code, fqid) for a region name.

    Region names are NOT unique across countries (e.g. 'Florida' exists in both the US and
    Uruguay), so an exact-name match alone silently picks the wrong node. Prefer the requested
    country code.
    """
    d = get("entities/query", entityType="region", search=name, limit=50)
    cands = [e for e in d.get("data", []) if e["name"].lower() == name.lower()]
    if not cands:
        raise SystemExit(f"region not found: {name}")
    same = [e for e in cands if e["attrs"].get("fqid", "").split(".")[3:4] == [prefer_cc]]
    if len(cands) > 1 and not same:
        print(f"  WARN ambiguous region name {name!r}: "
              f"{[e['attrs']['fqid'] for e in cands]} — using first")
    e = (same or cands)[0]
    return str(e["code"]), e["attrs"]["fqid"]


def raw_signal(code: str, start: int, end: int, datasource: str) -> list[tuple[int, float | None]]:
    d = get(f"signals/raw/region/{code}", from_=None) if False else get(
        f"signals/raw/region/{code}", **{"from": start, "until": end, "datasource": datasource}
    )
    if d.get("error"):
        raise SystemExit(f"signal error for region {code}: {d['error']}")
    e = d["data"][0][0]
    step, t0, vals = e["step"], e["from"], e["values"]
    return [(t0 + i * step, v) for i, v in enumerate(vals)]


class Lifecycle:
    """Threshold + hysteresis + minimum dwell-time state machine.

    Naive thresholding on a 5-minute series flaps hundreds of times per event; the dwell timer
    is what makes the derived capability lifecycle usable and reproducible.
    """

    def __init__(self, baseline: float, dwell_s: int = 1800):
        self.baseline = baseline
        self.dwell = dwell_s
        self.state = "up"
        self._cand: str | None = None
        self._cand_since: int | None = None

    def raw_state(self, v: float | None) -> str:
        if v is None:
            return "unavailable"
        r = v / self.baseline if self.baseline else 0.0
        if r >= 0.80:
            return "up"
        if r >= 0.40:
            return "degraded"
        if r > 0.05:
            return "severe"
        return "outage"

    def update(self, t: int, v: float | None) -> str:
        want = self.raw_state(v)
        if want == self.state:
            self._cand, self._cand_since = None, None
            return self.state
        if want != self._cand:
            self._cand, self._cand_since = want, t
        if self._cand_since is not None and t - self._cand_since >= self.dwell:
            self.state, self._cand, self._cand_since = want, None, None
        return self.state


def build(regions: list[str], start: int, end: int, datasource: str, dwell: int, warm: int) -> dict:
    nodes, ticks = [], None
    for name in regions:
        code, fqid = resolve_region(name)
        pts = raw_signal(code, start, end, datasource)
        # baseline = median over the pre-event warm-up window
        warmup = [v for t, v in pts if t < start + warm and v is not None]
        base = statistics.median(warmup) if warmup else statistics.median(
            [v for _, v in pts if v is not None]
        )
        lc = Lifecycle(base, dwell)
        series = [{"t": t, "value": v, "state": lc.update(t, v)} for t, v in pts]
        nodes.append({"id": f"region/{code}", "name": name, "fqid": fqid, "baseline": base,
                      "series": series})
        print(f"  node {name:<16} region/{code:<6} baseline={base:8.3f}  points={len(pts)}")

    # align on the shared tick grid
    grid = sorted({p["t"] for n in nodes for p in n["series"]})
    ticks = grid
    by_node = {n["id"]: {p["t"]: p["state"] for p in n["series"]} for n in nodes}

    # discrete lifecycle events
    events = []
    prev = {n["id"]: None for n in nodes}
    for t in ticks:
        for n in nodes:
            s = by_node[n["id"]].get(t)
            if s is None:
                continue
            if prev[n["id"]] is not None and s != prev[n["id"]]:
                kind = ("disconnect" if s in ("outage", "unavailable")
                        else "recover" if s == "up" and prev[n["id"]] in ("outage", "unavailable", "severe")
                        else "degrade" if s in ("degraded", "severe")
                        else "change")
                events.append({"t": t, "iso": dt.datetime.fromtimestamp(t, dt.UTC).isoformat(),
                               "node": n["id"], "from": prev[n["id"]], "to": s, "kind": kind})
            prev[n["id"]] = s

    span = (ticks[-1] - ticks[0]) if ticks else 0
    episode = {
        "meta": {
            "generated": dt.datetime.now(dt.UTC).isoformat(),
            "source": "IODA (Georgia Tech) /v2/signals/raw",
            "datasource": datasource,
            "window": {"from": start, "until": end,
                       "iso": [dt.datetime.fromtimestamp(start, dt.UTC).isoformat(),
                               dt.datetime.fromtimestamp(end, dt.UTC).isoformat()]},
            "tick_seconds": 300,
            "dwell_seconds": dwell,
            "n_ticks": len(ticks),
            "n_nodes": len(nodes),
            "n_events": len(events),
        },
        "nodes": [{k: v for k, v in n.items() if k != "series"} for n in nodes],
        "availability": {n["id"]: [by_node[n["id"]].get(t, "unavailable") for t in ticks] for n in nodes},
        "events": events,
    }
    return episode


def report(ep: dict) -> None:
    m = ep["meta"]
    print(f"\n=== episode summary ===")
    print(f" window  : {m['window']['iso'][0]} -> {m['window']['iso'][1]}")
    print(f" ticks   : {m['n_ticks']} x {m['tick_seconds']}s   nodes: {m['n_nodes']}   events: {m['n_events']}")
    counts: dict[str, int] = {}
    order = ["up", "degraded", "severe", "outage", "unavailable"]
    for nid, seq in ep["availability"].items():
        c: dict[str, int] = {}
        for s in seq:
            c[s] = c.get(s, 0) + 1
        counts[nid] = c
        worst = max(seq, key=lambda s: order.index(s))
        mins = {k: round(v * 300 / 60) for k, v in c.items()}
        print(f"   {nid:<16} worst={worst:<12} minutes={mins}")
    kinds: dict[str, int] = {}
    for e in ep["events"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f" event kinds: {kinds}")
    for nid in ep["availability"]:
        ev = [e for e in ep["events"] if e["node"] == nid]
        print(f"   {nid:<16} lifecycle transitions={len(ev)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD (UTC 00:00)")
    p.add_argument("--end", required=True, help="YYYY-MM-DD (UTC 00:00)")
    p.add_argument("--regions", nargs="+", required=True)
    p.add_argument("--datasource", default="merit-nt")
    p.add_argument("--dwell", type=int, default=1800, help="min dwell seconds before state commits")
    p.add_argument("--warm", type=int, default=86400, help="baseline warm-up seconds from start")
    p.add_argument("--out", default="episode.json")
    a = p.parse_args()

    s = int(dt.datetime.strptime(a.start, "%Y-%m-%d").replace(tzinfo=dt.UTC).timestamp())
    e = int(dt.datetime.strptime(a.end, "%Y-%m-%d").replace(tzinfo=dt.UTC).timestamp())
    print(f"building episode {a.start} -> {a.end}  datasource={a.datasource} dwell={a.dwell}s")
    ep = build(a.regions, s, e, a.datasource, a.dwell, a.warm)
    with open(a.out, "w") as f:
        json.dump(ep, f)
    report(ep)
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
