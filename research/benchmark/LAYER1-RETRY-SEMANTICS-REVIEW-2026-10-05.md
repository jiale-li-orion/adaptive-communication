# Layer 1 retry semantics review — 2026-10-05

Status: **exact/V8 action-mask repair implemented on an isolated branch; full corrected-source regeneration still required**.

This review follows the DB44 landslide/Table 11 correction. It does not replace
DSH's source correction, take ownership of its running regeneration, or sign Q11.
The older receipt-race fixture remains a mechanism regression, not the current
source-derived benchmark.

## 1. Decision

Continue the compositional Layer 1 line. Before public-test freezing, repair the
over-conservative delivery action mask and distinguish two receiver contracts:

1. **Existing no-duplicate-completion contract:** keep it unchanged in this fix,
   but permit retries that cannot produce a second successful completion.
2. **Idempotent receiver sensitivity:** duplicate attempts still consume physical
   resources; duplicate arrivals do not invalidate timely report delivery. This
   is a separate operational contract, not silently enabled by the repair.

Do not claim paid evidence necessity from the current labels until (1) has been
regenerated. Do not generalize that necessity to ordinary deduplicating telemetry
without evaluating (2). Neither finding is a reason to close the whole scenario.

## 2. A false negative under the existing contract

One report is released at 0, deadline 200. There is no satellite resource and no
passive ACK. Two compatible worlds have terrestrial windows:

| World | Window | Capacity |
|---|---|---:|
| A | [0, 90) | 2 |
| B | [100, 190) | 2 |

A single common open-loop policy attempts transmission at **0 and 100**:

- A accepts only the first attempt, completing at 30.
- B accepts only the second, completing at 130.
- Each world has exactly one successful reception. There is no duplication,
  no query, no hidden-world-dependent action, and no extra resource.

The old solver reports `with-query=True, no-query=False`. Its
`_active_common_obligations` excludes a report whenever **any** compatible world
has delivered it. Thus A's hidden completion removes the t=100 attempt needed
by B, even though A would reject that attempt.

This is an over-restrictive action mask, not proof of oracle information leakage.
The solver is solving a narrower action space than the no-duplicate execution
criterion requires. The independent existing execution evaluator accepts the
per-world successful traces of the common policy.

## 3. Bounded corrected-source result

Before examining ablation outcomes, selected the first six distinct
`PAID_EVIDENCE_REQUIRED` solver signatures in generator order for each of
`FINITE_CROSSING_WINDOWS` and `MULTI_WINDOW_DYNAMIC`. All twelve use the corrected
source profile and `GATEWAY_SUMMARY_QUERY`. Inputs are frozen, including profile
hash, original label digest and the corrected label summary.

| No-query reference | Solvable / 12 |
|---|---:|
| Explicit historical action mask | 0 |
| Repaired mask, duplicate completion still forbidden | **2** |
| Receiver deduplication, repeated accepted sends still charged | **12** |

All runs returned EXACT. Every positive witness was independently replayed
against all its worlds. Repaired-mask witnesses additionally pass the original
execution evaluator, with zero duplicate completions. The two actual corrected
source signatures that flip under the unchanged receiver contract are:

```text
a8e1080b374d02fd31c59c5ef3726dbc02db734d5df5236d1441e8e94f3ef8d1
da9cb6a63a1c9e4748f5cd0ce9b0d695a67652b6159730a27eea3ba2f11d1411
```

Both use one satellite delivery followed by two common, separated terrestrial
attempts for the other report. This is not merely a synthetic witness.

**Limits:** this is a diagnostic sample, not a random estimate of all 357 paid
signatures or all 2,496 corresponding recipes. No aggregate corrected count is
inferred. The dedup intervention retains the existing one-in-flight rule and
event lattice; it proves existence of successful policies, not completeness of
a new general deduplicating-protocol oracle.

## 4. What the full corrected manifest already says

Before this action-mask repair, the corrected-source manifest has 58,752 recipes
and 8,064 solver signatures. Its paid-evidence rows are exclusively:

| Process / evidence regime | Paid recipes |
|---|---:|
| FINITE_CROSSING_WINDOWS / GATEWAY_SUMMARY_QUERY | 534 |
| MULTI_WINDOW_DYNAMIC / GATEWAY_SUMMARY_QUERY | 1,962 |

`PASSIVE_ACK_ONLY` and `MIXED_PASSIVE_QUERY_PROBE` have no paid-required recipes
in that manifest. This is an information-value boundary, not evidence that
ordinary algorithms solve every case. Exact no-query feasibility and ordinary
baseline performance are different questions.

The observation contract must therefore justify where the controller resides,
why passive completion evidence is unavailable there, and what retry/receiver
semantics apply. Hiding a field in a benchmark is not itself that justification.
Source cadence alone does not supply an at-most-once reception requirement.

## 5. Implemented repair and its boundary

`_active_common_obligations` now retains reports delivered in only part of the
compatible support, while preserving the existing pending-attempt restriction.
The new shared `_delivery_retry_allowed` checks the chosen path:

- terrestrial: reject only if an already-completed compatible world could accept
  another transmission at the current instant;
- satellite: reject if any compatible world already completed that report,
  since a legal satellite action is accepted throughout the support.

Exact search and the V8 policy ladder use the same helper. No policy receives the
realized world. Resource charging, observations, deadlines and the evaluator are
unchanged. Receiver deduplication exists only in the diagnostic intervention.

`SOLVER_VERSION` changes to `T1-exact-reference-oracle-v0.2-retry-legality`, so old
exact signatures cannot be reused as corrected labels during resume/projection.
This patch does **not** establish global completeness of the event lattice or
the one-in-flight assumption; those retain their existing declared scope.

## 6. Handoff to the running regeneration

Do not overwrite or mix the running DSH artifacts. Preserve their source-corrected,
pre-retry-repair identity. Integrate this repair after a checkpoint, then:

1. Run the focused retry review and existing exact/V8 regression checks.
2. Generate exact labels into a **new output directory** under the bumped solver
   signature. Do not overwrite the just-produced corrected-source labels.
3. Reproject V0–V7 and rerun V8/V9 on that lineage. Rebuild structural splits and
   public freeze only after those results are available.
4. Retain the deduplicating-receiver variant as an explicit sensitivity baseline.
   Resolve its operational authority before changing the main task contract.
5. Require the release manifest to identify source-profile hash, solver version,
   receiver contract and observation regime. Q11 source review remains human.

No LLM batch is warranted before those labels and the test freeze stabilize.

## 7. Research implication and the next algorithm question

The promising question remains **which evidence changes the best feasible
continuation**, not whether a report's hidden status can be perfectly diagnosed.
But continuation candidates must include ordinary resource-charged retries and
normal-send-as-probe. Otherwise a feasibility conflict can be manufactured by
removing its information-free resolution.

After regeneration, separate three possible findings:

- Some cases retain genuine no-query infeasibility with realistic receiver and
  feedback semantics: they support an information-value result.
- No-query policies complete tasks, but spend more scarce backup/capacity than
  evidence-guided policies: compare a service/evidence/transmission Pareto front,
  without inventing an arbitrary weighted reward.
- Ordinary policies match both quality and resource cost: keep those as controls;
  computational claims still require comparison against generic memoized search,
  and the scenario as a whole is not declared impossible.

This is a better basis for the context-construction method: demonstrate that a
selected observation improves attainable action/resource outcomes, rather than
equating uncertainty with the necessity of querying.

## 8. Reproduce

```bash
python3 code/evaluation/benchmark/audit_retry_action_mask_v0_1.py
```

The default output is `/tmp/layer1-retry-review.json`, so reproduction cannot
silently overwrite registered evidence. The diagnostic freezes the historical
mask explicitly rather than delegating it to the modified production function.
It includes one minimal counterexample plus twelve existing-source cases; no API
calls, expanded generator or new hardware/task assumptions are required.

Artifacts:

- `results/benchmark/layer1-retry-review-inputs.json`
- `results/benchmark/layer1-retry-review.json`
- `code/evaluation/benchmark/audit_retry_action_mask_v0_1.py`

The main README, machine state, source registry, existing generated results and
Q11 artifacts are deliberately left to the current regeneration owner.
