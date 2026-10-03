# Results Ownership

results/ stores machine-readable evidence and frozen comparisons. Claim state is owned only by CLAIMS.md.

- agentic/: Layer-2 / policy evaluation runs, including A7–A11 live-model evidence and supporting Agentic experiments.
- communication-substrate/claims/: current C1–C11 communication-substrate evidence referenced by CLAIMS.md.
- communication-substrate/calibration/: source-derived link/outage/energy calibration artifacts.
- communication-substrate/physics/: terrain, coverage, ITM/LoRa and physical-substrate outputs used by the shared simulator.
- reference/: frozen comparison snapshots used by reproduction audits; this remains a separate immutable comparison plane.
- legacy-communication/: historical instance sweeps, joint-control searches, old Agent traces and method probes that no longer define current claims.
- history/withdrawn/: explicitly withdrawn or superseded result material.
- history/registries/: historical result registries whose narrative/paths were valid for an earlier repository layout.

A file under legacy-communication/ is provenance, not a current claim. A current claim must appear in CLAIMS.md and point to an existing result.
