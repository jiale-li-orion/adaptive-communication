# Continuation resource domains v0.1

Status: implemented bounded method diagnostic, 2026-10-05. Extends the approved
cache06 line; does not redesign Layer 1 or change source-derived task semantics.

## Purpose and prior implementation boundary

`dynamic_feasibility_frontier_v0_5.py` gives optimistic resource requirements.
`resource_continuation_frontier_v0_5.py` defines an expensive exact cost reference
on the old receipt fixture. Neither implements reusable causal success domains
for the new source-profiled compositional process.

This increment builds that object. It is **not** claimed as a new algorithm on
the strength of antichains, memoization or Pareto terminology. Those are ordinary
techniques and must be explicit comparators.

## Object and semantics

For a fixed normalized information-state boundary z, define F(z,Q,B): whether
there exists a causal policy completing all obligations in every compatible
world with at most Q additional paid queries and B additional satellite sends
on **each** execution branch. Q is an analysis/selection bound, not a source SLA.
The physical model still charges queries against terrestrial capacity, and all
normal send/ACK/passive feedback remain available.

A successful policy witness pi gives resource requirements:

    r(pi) = (max_world queries(pi), max_world satellite_sends(pi)).

The maxima can occur in different worlds. No prior or weighted reward is used.
Sequential actions add costs; mutually exclusive observation branches take a
componentwise maximum. A certificate is valid for Q >= r_q and B >= r_s while z
is unchanged. A fully exhausted failure at (Q,B) certifies failure for smaller
budgets. Search limits are unresolved, never negative certificates.

The boundary retains time, compatible support, delivered IDs, physical window
use, pending sends/queries and their timing, and query-history state. It excludes
only the two resource limits. The immutable session binds the whole process and
task contract. No reuse across altered opportunities, new evidence, changed
capacity or a different pending outcome is allowed in v0.1.

Direct-full-state regimes expose budget in observation strings; they are excluded
from this initial transfer theorem. All compatible states must have the same
remaining satellite budget, as expected under a shared action history.

## Why transfer is sound in this declared submodel

Satellite budget and the query bound restrict legal actions; they do not change
the outcome, arrival time or payload of an already chosen action in the partial
observation regimes. Follow the witness while ignoring unused extra budget.
Induction over actions and observation branches preserves the same physical
history, and the bound prevents resource exhaustion. This justifies an upward
success domain. Action-set inclusion justifies downward failure domains.

This argument does NOT apply automatically to terrestrial capacities: changing
capacity can change acceptance, receipt and future evidence. It also does not
justify merging different windows merely because a scalar deficit is equal.

## Three implementations, one search

1. `exact_memo`: persistent cache keyed by full boundary and exact Q/B.
2. `monotone_memo`: ordinary success/failure antichains; success starts at the
   resource point requested from the solver, failure extends downward.
3. `witness_domain`: success starts at the actual policy requirement, potentially
   below the requested resource point. Same negative certificates as (2).

All use the existing exact/V8 normalize/legal-action/transition semantics and
the same action ordering. No irrelevant catalog is added. Return the actual
policy and a resource-bound context; never call a necessary flow bound success.

An observed antichain is initially only a certified inner frontier. It becomes
complete over a specified integer budget rectangle only after all its cells are
resolved. A query-free certificate means acquisition can stop for feasibility;
it does not prove that more evidence cannot reduce transmission cost.

## Implementation plan

Executed in the isolated `research/layer1-retry-review` worktree.

- [x] Add `test_continuation_resource_domains_v0_1.py`: a reusable witness
  transfers to smaller sufficient budgets; resource exhaustion fails; a changed
  pending/physical boundary is not a hit; incomplete search is unresolved.
- [x] Add `continuation_resource_domains_v0_1.py`: shared AND/OR continuation
  search, witness costs, domain tables, metrics and explicit context projection.
- [x] Add `audit_continuation_resource_domains_v0_1.py`: compare the three modes
  on bounded, already-frozen corrected-source inputs; ascending and descending
  budget orders; verify every returned witness and compare all cell outcomes.
- [x] Record results, including search/lookup time, node expansions,
  exact and domain hits, and no-gain regimes. Keep task and method claims separate.
- [ ] Commit/push independently of DSH's main-tree source regeneration.

## Bounded result

Input is the twelve source-corrected bundles frozen before the retry-legality
ablation: six `FINITE_CROSSING_WINDOWS` and six `MULTI_WINDOW_DYNAMIC`, all in
`GATEWAY_SUMMARY_QUERY`.  For each bundle the audit evaluates the full integer
rectangle `Q=0..obligation_count`, `B=0..generated satellite budget`, giving
172 resource cells.  Each mode uses the same legal actions and action ordering.

All modes and both visitation orders agree on every cell outcome.  Every
positive returned witness replays successfully under the target resource cell.

| order | exact memo expansions | monotone memo | witness domain | witness vs monotone |
|---|---:|---:|---:|---:|
| rich → poor | 306,750 | 203,367 | 202,303 | -1,064 (-0.52%) |
| poor → rich | 306,750 | 200,907 | 200,907 | 0 |

Ordinary resource monotonicity already explains almost all reuse.  Under
rich-to-poor traversal, witness tightening creates 119 domain-reuse cells versus
109 for ordinary monotone memo and 71 versus 61 zero-expansion cells.  The ten
extra reuse cells arise when the first successful policy does not consume the
entire requested query or satellite budget.  They do not demonstrate reuse
across a changed evidence/execution boundary.

This is a useful negative/limiting result: **resource-validity domains are a
sound context primitive but are not, by themselves, the method advantage.**
The next method increment must attack the boundary state `z`, not keep polishing
the resource antichain.

## Acceptance and next research boundary

Required now: causal witness replay, exact agreement across all resolved cells,
no false reuse after a non-resource change, and measured comparison with the
ordinary monotone cache. This small study does not measure deployment success,
online trajectory speedup, held-out generalization or LLM benefit.

The next method step is to reduce `z` using communication dependency separators,
allowing safe reuse across local events rather than budget changes alone.  The
first admissible projection removes only transition-kernel-dead history (for
example, capacity use in windows that have already ended) and collapses evidence
history only when future query semantics cannot distinguish the old values.
Cross-boundary **success** reuse must replay its causal witness before acceptance;
failure certificates remain keyed by the full boundary until a stronger
equivalence proof exists.  This is an explicit safety gate against pretending
that equal scalar deficits imply equal continuation problems.
