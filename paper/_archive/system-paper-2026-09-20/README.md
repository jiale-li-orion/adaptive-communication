# System-paper snapshot before the Agentic Communication pivot

superseded_by: `paper/agentic/en/main.tex`

reason: The active research object moved from the standalone communication-systems manuscript to Evidence-Grounded Closed-Loop Agentic Communication. The system-paper mechanisms, claim corrections and negative results remain part of the physical/evaluation substrate, but this snapshot is no longer the active submission draft.

source_commit: `dd4f31ada5910d23b2973b119a3d036a4f4cd219`

This directory is an immutable source snapshot of the last commit before the 2026-10 Agentic manuscript pivot that modified both historical system-paper manuscripts.

- `main.en.tex`: exact `paper/en/main.tex` from `source_commit`.
- `main.zh.tex`: exact `paper/zh/main.tex` from `source_commit`.
- Current corrected compatibility copies remain at `paper/en/main.tex` and `paper/zh/main.tex`; they may receive claim-correction propagation so that old `C*` claims still build against current frozen result semantics.
- The active manuscript is `paper/agentic/en/main.tex`.
- Claim state is never inferred from this archive. `results/CLAIMS.md` is the sole current claim-state authority.
- Historical result corrections and withdrawn readings live under `results/_withdrawn/`.

To inspect the exact original tree without relying on this copied snapshot:

```bash
git show dd4f31a:paper/en/main.tex
git show dd4f31a:paper/zh/main.tex
```
