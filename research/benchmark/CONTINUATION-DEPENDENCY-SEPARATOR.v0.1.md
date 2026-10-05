# Continuation dependency separator v0.1

Status: bounded correctness and compute diagnostic, 2026-10-05.

This increment follows the `cache06.md` condition-frontier line.  It asks
whether a continuation certificate can survive changes to execution history
that provably cannot affect any future transition.  It does not change Layer 1
task semantics and does not claim that graph/separator terminology is itself a
method contribution.

## v0.1 separator

The full continuation boundary retains time, compatible worlds, delivered
obligations, all window-usage history, pending operations, evidence history and
resource state.  v0.1 removes only transition-kernel-dead history:

- terrestrial/satellite usage entries for windows whose `end <= current time`;
- `last_direct_signature` when direct-current-state observation is disabled;
- passive receipt bookkeeping bits when no passive receipt/ACK surface exists.

It does **not** remove `last_query_signature`, pending-operation timing,
future/current window capacity, compatible-world support or obligation state.
Remaining satellite budget stays outside `z` as the explicit monotone resource
coordinate already used by continuation-resource domains.

Cross-full-boundary failure reuse is disabled.  A success certificate may cross
the separator only after the stored causal policy is replayed against the target
state.  A failed replay falls back to ordinary full-boundary search.

## Natural-state collision audit

The audit instruments the real continuation AND/OR search over the twelve frozen
source-corrected retry-review bundles.  No state pairs are manufactured.  It
looks for two naturally reached full histories with equal separator and equal
resource coordinates.

All 12 bundles contain such collisions.  The frozen audit retains six pairs per
bundle, 72 pairs total:

- 72 / 72 independently re-solved pairs have the same exact feasibility outcome;
- every successful certificate cross-replays on the paired full state;
- 60 / 72 sampled pairs are failure-state collisions and therefore receive no
  cross-boundary reuse credit in v0.1;
- 12 success pairs admit safe certificate reuse; their sampled fresh-search work
  sums to 114 expansions.

This establishes a real state-compression opportunity, not a deployment-frequency
estimate or a speedup claim.

## Replay-gated cache comparison

The fair compute comparison uses the same twelve bundles and the same bounded
resource rectangles as `CONTINUATION-RESOURCE-DOMAINS.v0.1.md`.  Both sides use
the same `witness_domain` planner.  The treatment adds only separator-indexed
success lookup plus deterministic target-state replay.

| traversal | full-boundary expansions | separator expansions | expansion change | full wall | separator wall |
|---|---:|---:|---:|---:|---:|
| rich → poor | 202,303 | 200,212 | -2,091 (-1.03%) | 16.15 s | 20.70 s |
| poor → rich | 200,907 | 199,785 | -1,122 (-0.56%) | 16.34 s | 20.31 s |

The separator produces 108 / 75 cross-boundary hits respectively, with zero
replay failures.  Replay itself costs only about 0.125 s / 0.056 s in aggregate;
the net slowdown comes from maintaining and comparing the compressed separator
index for a small amount of additional reuse.

Therefore v0.1 passes the correctness gate but **fails the net-compute gate** on
this workload.  Dead-history compression is a valid context representation
primitive; at current scale it is not a useful main algorithmic advantage over
ordinary persistent memoization + resource monotonicity.

## Research consequence

The result narrows the next method object.  Further work should not keep adding
cache equivalence rules merely to shave search nodes.  The more informative
context is the **conditional feasibility/resource frontier** itself:

```text
which future continuations are certified;
which resource conditions keep them valid;
whether paid evidence is required for feasibility;
if not required, how much scarce fallback/capacity evidence can release;
which execution/evidence event invalidates that comparison.
```

This is where evidence can change the attainable future-choice set, rather than
merely allow two histories to share a memo entry.  Ordinary memoization,
resource antichains and replay-gated separator caching remain mandatory compute
baselines for any later conditional-frontier method.

Artifacts:

- `code/evaluation/benchmark/continuation_dependency_separator_v0_1.py`
- `code/evaluation/benchmark/audit_continuation_dependency_separator_v0_1.py`
- `code/evaluation/benchmark/audit_continuation_separator_cache_v0_1.py`
- `results/benchmark/layer2-continuation-dependency-separator-v0.1.json`
- `results/benchmark/layer2-continuation-separator-cache-v0.1.json`
