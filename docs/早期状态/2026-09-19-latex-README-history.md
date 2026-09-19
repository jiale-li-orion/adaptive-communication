# 论文目录 README 历史快照（2026-09-19 归档）

来源：`e8ff1c420070840439f7133b30748a36d33ba8b4` 的 `docs/s8-report/latex/README.md`。保留历史正文、决策编号和当时表述；仅重定位 Markdown 相对链接，根 README 的决策表另加稳定锚点。文中的「当前／最新／下一步」只代表当时状态，部分结论已被后续审查取代。

当前状态见[根 README](../../README.md)；证据修订见[doc51](../s7-method/v1.2/51-independent-review-paper-v06-2026-09-19.md)，收敛判断见[doc52](../s7-method/v1.2/52-runtime-convergence-assessment-2026-09-19.md)。

---

# Execution-Grounded Mission Feasibility — LaTeX working draft

Working draft v0.1 (2026-09-18) of the single agentic-communication paper whose route was
locked in method docs doc42/doc43 (see `docs/s7-method/v1.2/42-*.md`, `43-*.md`), following
the doc33 synthesis and the doc38 review (three arms A0 / A0-structured / A1; three statement
classes; symmetric upper bounds; no premature NO-GO).

- `main.tex` — manuscript (10 pages, `article` class).
- `refs.bib` — bibliography. Entries contain only facts verified in the repository source
  ledger; authors not verified from the primary record are omitted (misc-type with
  title/venue/year/URL) rather than guessed.
- `main.pdf` — built artifact.

## Build

Toolchain present in WSL: `pdflatex` + `bibtex` (TeX Live; no `latexmk`/`tectonic`).

```
pdflatex -interaction=nonstopmode main
bibtex main
pdflatex -interaction=nonstopmode main
pdflatex -interaction=nonstopmode main
```

Clean build: no errors, no undefined citations/references.

## Section → evidence map (all numbers from repository scripts, none invented)

- §4 feasibility frontier: r30c wall decomposition (Table 1), doc41 night feed-forward/MPC
  negative result, r34 outage-window symmetric upper bound (Table 2), r31 segment attribution.
- §5 certificates: r33 compile-time structural S_time certificate (602 certs; 588 true;
  100% recall; 0 false positive; median 7.2 h lead), r32 arrival-time attribution
  (2136/2136 = 100%).
- §6.3 cost: r35 (219/480 = 45.6% backup records arrive expired).
- §6.4 agent: r36 within-subject deepseek-flash A0 vs A1 at three decision points
  (`results/agent_traces/E3_cert_A0A1.json`); existence proof, n=3, one model.
- Standards grounding: DZ/T 0460-2023 §5.3.3/§5.3.6/§5.3.7/§8.4.1/§8.4.2, DZ/T 0450-2023,
  BDS-OS-PS-3.0 Table 7-1.

## Honest limitations carried into §8

- Throughput negative result at one main operating point with symmetric relaxations and
  omniscient/MPC baselines; S_time certificate is geometric/seed-invariant, capacity and
  night-energy forecasts are not claimed deterministic.
- Agent study is n=3 within-subject; effect size needs 3–5 full trajectories and an
  A0-structured arm.
- Absorbing brownout (restart sensitivity not swept); standards retrieval-channel grade;
  no author-code replication; one field-study endpoint rate-limited and cited without numbers.

This is a complete, compilable first draft, not a submission-ready manuscript: figures are
currently tables/text (a chain/frontier figure and an outage timeline are the natural next
additions), and related-work bibliographic author fields should be completed from primary
records before submission.
