# Generator v0.1 Degeneracy Audit

状态：FAILED CANDIDATE GENERATOR / do not release as benchmark

## Result

Generator v0.1 produced 13,637 rows that passed its initial oracle filters:

- solvable；
- multiple legal first actions；
- satellite budget binding；
- forced-send / wait outcome separation；
- naive immediate satellite fallback fails。

That filter was insufficient.

A stronger ordinary deterministic baseline was added:

    deadline-aware reserve + EDF

Rule:

- when terrestrial is available, serve released reports by earliest deadline；
- before terrestrial recovery, spend satellite only on released reports whose deadline is earlier than terrestrial recovery；
- otherwise reserve satellite budget。

This baseline uses no learning, no LLM, no search over future action sequences, and no benchmark-specific reward.

Result:

    13,637 / 13,637 = 100%

Therefore Generator v0.1 is decision-degenerate under a reasonable ordinary baseline.

## Interpretation

The generator did create intertemporal resource coupling, but the coupling is exposed too directly by the state:

    deadline < known terrestrial recovery
    => satellite required

    deadline >= known terrestrial recovery
    => reserve satellite

The resulting policy collapses to a local deterministic rule.

Consequently:

- previous HARD_CANDIDATE is revoked；
- these rows become NEGATIVE_VALIDITY_CASES；
- no split / leaderboard / model evaluation should be built on v0.1；
- v0.1 remains useful as a benchmark-construction failure case and regression test。

## Requirement for v0.2

v0.2 must break the above local sufficient statistic without manufacturing difficulty.

Candidate sources of non-degeneracy must be reviewed adversarially before implementation:

- partial / stale evidence about recovery or path opportunity；
- multiple future obligations whose arrival/state is not fully known；
- evidence acquisition with cost and action relevance；
- coupled capacity/energy/cache state where a local deadline rule is insufficient；
- heterogeneous actions with genuine future feasibility trade-offs。

The new structure must still satisfy:

- source-backed operational semantics；
- preregistered controlled stress；
- exact oracle；
- strong ordinary baselines before model evaluation；
- no model-score-driven hard-case mining。
