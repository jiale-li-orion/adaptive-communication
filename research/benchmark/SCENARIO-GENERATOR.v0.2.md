# Layer-1 Scenario Generator v0.2 — alias-bundle mechanism prototype

状态：MECHANISM VALIDATED / BENCHMARK ADMISSION FAILED

v0.2 首次把生成单位从独立 full-state world 改成 alias bundle / finite scenario tree。

## 已实现

- finite non-nested terrestrial service windows；
- shared public satellite geometry；
- shared satellite budget；
- identical initial public observation across hidden worlds；
- current gateway-owner evidence query；
- query delay advances physical time；
- passive evidence and transmission ACK can also split alias worlds；
- exact non-anticipative policy solver；
- hindsight / observation-matched / no-paid-query feasibility separation。

主 H2 witness 使用 DB44 grade-3 orange 的 2 h source cadence boundary：

- report_0: current 2 h obligation；
- report_1: next periodic 2 h obligation；
- one early real Connecta satellite opportunity；
- one later real Connecta satellite opportunity；
- one normalized satellite transmission budget；
- hidden terrestrial service mode is either early-window or late-window。

Early world:
- report_0 can use early terrestrial；
- report_1 needs later satellite。

Late world:
- report_0 needs early satellite；
- report_1 can use late terrestrial。

At the early satellite commitment, the two worlds require opposite resource decisions.

A paid gateway-health query returns a current owner-local mode observation before the commitment. It does not return future truth directly.

## Exact result

Current prototype produces 72 bundles:

- QUERY_REQUIRED: 24
- QUERY_HARMFUL control: 24
- PASSIVE_BETTER control: 24

For QUERY_REQUIRED:
- all worlds hindsight-solvable: 24/24；
- observation-matched with query: 24/24；
- exact no-paid-query policy: 0/24。

Therefore the active-evidence mechanism itself is real: information can change whether a common successful policy exists.

## Shortcut audit

A deliberately simple depth-2 timing rule:

1. if free passive evidence arrives before the first satellite opportunity, wait；
2. else if paid query returns before that opportunity, query；
3. else use no-query continuation。

solves:

    72 / 72

Therefore v0.2 still fails benchmark-hardness admission.

The failure is narrower than v0.1:
- v0.1 collapsed to a local deadline/recovery rule before any genuine EvidenceNeed existed；
- v0.2 establishes genuine EvidenceNeed, but query utility is too directly exposed by public timing structure。

## Consequence

Keep:
- scenario-tree oracle；
- non-anticipativity contract；
- alias-bundle representation；
- query/passive/ACK evidence transitions；
- H2 positive regression cases。

Do not release:
- current bundle distribution；
- current query timing axes as benchmark hardness；
- any Agent-vs-baseline result。

The next generator must make evidence selection depend on multiple interacting current facts/capabilities rather than a one-step timing predicate, while preserving legal evidence ownership and explicit query cost.
