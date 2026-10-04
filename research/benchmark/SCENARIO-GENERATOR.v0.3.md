# Layer-1 Scenario Generator v0.3 — process-generated multi-evidence pilot

状态：method-development pilot / not benchmark release

## 1. 目标

v0.3 不再手工生成 QUERY_REQUIRED / QUERY_HARMFUL / PASSIVE_BETTER 三类标签。

生成顺序：

    source-shaped obligations
    + actual Connecta opportunity phase
    + hidden current service mode
    + finite terrestrial rescue process
    + owner-evidence projections
    + evidence catalog
    -> alias bundle
    -> exact observation-matched solver
    -> information-structure label

标签是 solver 结果，不是 generator 输入。

## 2. 冻结 primitives

- DB44 grade-3 orange 2 h reporting cadence lower boundary；
- tracked Sihui Connecta geometry trace；
- three consecutive periodic obligations；
- one normalized satellite budget；
- one actual satellite opportunity per obligation interval；
- current service mode determines which obligation lacks terrestrial rescue；
- legal gateway evidence proposition types：
  - communication.gateway.primary_health
  - communication.gateway.receipt_summary
  - resource-specific communication.gateway.node_report

Current-mode -> future finite-service pattern is CONTROLLED_STRESS.
The generator does not claim this mapping is a Guangdong field distribution.

## 3. Evidence process

primary_health and receipt_summary expose different coarse projections of the current hidden mode.
Resource-specific node_report entries remain catalog noise / irrelevant evidence options.

Query issue is asynchronous：
- issuing a query does not consume the current send opportunity；
- response arrival occurs after declared delay；
- normal sends / ACKs remain available while queries are in flight。

Multi-query latency is accounted by critical path, not by summing independent asynchronous delays.

## 4. Process distribution pilot

Default pilot：
- 8 actual trace phases；
- 4 alias-mode sets；
- 4 evidence-projection profiles；
- 5-query catalog；

total：128 bundles

Exact labels：

    NO_PAID_QUERY          32
    SINGLE_QUERY           32
    MULTI_QUERY             8
    INFORMATION_INFEASIBLE 56

The generator therefore preserves simple, information-positive and information-infeasible regimes instead of filtering everything toward one desired behavior.

## 5. Computation-gap pilot

For the three-world complementary-evidence structure, catalog size is expanded only with additional resource-specific node_report queries.

Conflict-guided selection performs：
1. constant/dominated evidence pruning；
2. one exact first-action signature pass；
3. conflict-aware subset ordering；
4. exact subset verification。

All preprocessing exact solves are included in reported cost.

Mean results over 6 actual Connecta phases：

| catalog | exhaustive subset solves | guided subset solves | guided preprocessing solves | guided/exhaustive memo-node ratio |
| ---: | ---: | ---: | ---: | ---: |
| 3 | 6 | 3 | 6 | 0.682 |
| 5 | 15 | 3 | 6 | 0.264 |
| 7 | 28 | 3 | 6 | 0.143 |
| 9 | 45 | 3 | 6 | 0.090 |

The selector preserves the same exact minimum-cardinality evidence set as exhaustive search.

## 6. Claim boundary

This pilot supports only：
- process-generated mixed information regimes；
- exact non-anticipative evidence-selection reference；
- conditional evidence can avoid irrelevant catalog entries；
- structural pruning can reduce exact search work on the generated pilot。

It does not yet support：
- real deployment query-frequency claims；
- general asymptotic complexity claims；
- learned-policy superiority；
- Agent-vs-traditional-control superiority；
- final benchmark admission。

Next scaling must vary：
- world count；
- obligation count；
- number of genuinely informative and partially redundant evidence sources；
- multiple resource conflicts；
- asynchronous overlapping evidence arrivals。

## 7. Structural scaling pilot

A second pilot varies alias-world count and obligation count together while
keeping the same 2 h source cadence and using only actual Connecta opportunity
phases.

Mean over 4 valid trace phases：

| worlds / obligations | selected evidence | exact policy memo nodes | exhaustive subset solves | guided subset solves | guided preprocessing solves | guided / exhaustive memo ratio |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 / 2 | 1 | 906 | 3 | 1 | 4 | 1.182 |
| 3 / 3 | 2 | 5,241 | 10 | 3 | 6 | 0.502 |
| 4 / 4 | 2 | 6,503 | 10 | 3 | 8 | 0.684 |

Interpretation：

- conflict preprocessing is not free；
- for the 2-world structure it costs more exact memo work than direct subset enumeration；
- at 3/4 worlds the reduced evidence-subset search begins to repay preprocessing cost；
- therefore the method should use a cheap-size / conflict threshold rather than force structural analysis on every case。

This crossover is a retained negative/positive result, not filtered out for presentation.
