# Information Timing Validation Implementation Plan

> **For Codex:** Execute this plan in order. Preserve the original exploratory files and label every result by evidence level.

**Goal:** Determine whether current path information can be obtained early enough to change delivery under the repository's multipath extension, using realizable feedback arms before considering any new agent method.

**Architecture:** Keep the existing batch simulator as an immutable exploratory snapshot. Add a small sequential-timing simulator that reuses its frozen trace and workload but gives every arm the same queue, path, quota, energy, deadline, and packet-outcome rules. The arms differ only in when path evidence becomes available: prior history only, ACK after an ordinary data attempt, paid probe before data, or infeasible current truth. Save per-seed metrics and action/evidence ledgers.

**Tech Stack:** Python standard library, NumPy already used by the probe, JSON result artifacts, repository shell checks.

---

## Task 1: Preserve and reconcile the existing evidence

**Files:**
- Add: `multipath_probe/` current exploratory snapshot
- Add: `docs/s7-method/instance-v1/55-review-fair-pacing-and-multipath-probe-2026-09-14.md`
- Modify: `multipath_probe/README.md`
- Modify: `multipath_probe/STAGE2_FINDINGS.md`

1. Commit the untouched exploratory snapshot and independent review so later fixes cannot silently rewrite provenance.
2. Add a prominent status block to the probe documents: current-state greedy reference, approximate belief controller, old probe timing defect, and A-layer extension scope.
3. Retain the fair-pacing service/cost finding while withdrawing the unsupported claim that all saved uplinks were deadline-redundant.

## Task 2: Specify and test the timing semantics

**Files:**
- Create: `multipath_probe/information_timing.py`
- Create: `multipath_probe/test_information_timing.py`

1. Write failing tests for this exact order: arrivals and expiration; optional paid probe; observation return; ordinary data attempt; ACK return; subsequent same-tick choice; deadline accounting.
2. Test that zero attempts create no evidence, probe and data observations in one tick are both retained, same-tick ACK can alter a later action, and all arms share the same exogenous trace and packet-outcome keys.
3. Implement the smallest sequential environment and common controller needed to pass those tests. A probe consumes energy and quota where applicable but delivers no sample. A data attempt consumes the same resources and can both deliver a sample and return an ACK.
4. Keep the current state fixed within the one-hour scheduling epoch. Mark same-epoch feedback as an A-level interface assumption, since the repository does not establish a production modem API with that latency.

## Task 3: Run the representative information-access comparison

**Files:**
- Create: `multipath_probe/run_information_timing.py`
- Create: `multipath_probe/results/information_timing.json`

1. Run 20 paired seeds at `K=3`, `chirpbox`, energy budget 1950, plus the loose-budget boundary.
2. Compare four arms with one shared allocation heuristic: history-only batch commitment, ordinary data ACK with sequential reallocation, paid probe then sequential data, and current-truth reference.
3. Save per-seed event/routine delivery, attempts, probe attempts, energy, money, satellite quota, bad-path waste, and evidence/action timing counts.
4. Compute paired mean differences, 95% intervals, and win/tie/loss directly from per-seed rows.

## Task 4: Decide the method gate and integrate the result

**Files:**
- Create: `docs/s7-method/instance-v1/56-information-timing-result-2026-09-14.md`
- Create: `docs/s7-method/instance-v1/57-scenario-interface-bridge-2026-09-14.md`
- Modify: `README.md`
- Modify: `results/README.md`

1. Record whether ordinary ACK already captures the available gain, whether paid probe adds value after its cost, and how far both remain from the infeasible truth reference.
2. If ordinary feedback closes the gap, promote it to the strong baseline and close the new-method gate. If a paid probe has incremental value under equal accounting, state the narrow mechanism and its interface precondition. If neither helps, close the probe direction because information arrives too late or is not predictive.
3. Bridge every new object to the core task: source obligation, controlled interface, observation location, return time, resource cost, and evidence level. Keep satellite/UAV settings in the A-level extension column.
4. Do not add an LLM or claim an agent advantage.

## Task 5: Verify, commit, and push

1. Run `python3 multipath_probe/test_information_timing.py`.
2. Run `python3 multipath_probe/test_probe.py` to guard the preserved simulator.
3. Run `python3 code/run_checks.py` for the repository-wide 18 checks.
4. Verify every result file referenced in docs is registered and the working tree has no unintended files.
5. Commit the implementation/results separately from the preserved snapshot, then push `master` to `origin`.
