# Literature Reconnaissance: Agent Runtime Execution Semantics & Failure

> ⚠️ **定位说明（2026-09-12 追加）**：本文写作时的论文标题是
> *"Disruption-Tolerant Runtime for Tool-Using Agents in Emergency Communication Networks"*，
> **该定位已被取代**。当前定位见 [`../../README.md`](../../README.md)：
> **agent runtime 位于通信实体之上，在它们动态上线 / 掉线 / 退化 / 恢复时维持任务执行**。
> 本文的**调研内容与引用仍然有效**；只有"论文标题/中心"这一层需要按新定位重读。


**For:** *Disruption-Tolerant Runtime for Tool-Using Agents in Emergency Communication Networks*
**Scope:** what already exists, for each mechanism the context doc proposes, plus where a defensible gap remains.
**Date of reconnaissance:** environment date ≈ September 2026.

---

## How to read this document

**Verification legend.** Every citation below is something actually retrieved during this reconnaissance. Nothing is invented.

- `[V-CR]` = DOI **verified via the Crossref API** (title, container, year, authors confirmed programmatically). Strongest form.
- `[V-URL]` = URL **verified live** (HTTP 200). Venue/year taken from the page.
- `[V-REV]` = peer-reviewed venue confirmed from a proceedings/program page.
- `[P]` = **preprint only, venue and year UNVERIFIED.** Cite as arXiv/preprint.
- `[IND]` = **industry docs / blog / repository — not peer-reviewed.** Cite as practice, never as evidence.
- `[FLAG]` = **known uncertainty; read the source before citing.**

**One methodological warning that applies to the whole document.** Absence of a hit is *not* proof of absence. Search coverage of mid/late-2026 preprints is incomplete, many items were paywall- or snippet-only, and my queries may not use the authors' vocabulary. Every "gap" below is phrased as **"no positive hit found,"** never as "nobody has done this." Do not let the paper's related-work section overclaim.

**The single most important empirical correction in this report:** several agent fault-injection benchmarks *do* exist and *do* inject timeouts, latency, rate limits, and stale context — but at the **tool-API / HTTP semantic layer**, not the **transport layer**, and their faults are predominantly **visible errors** rather than **outcome-ambiguous** ones. That distinction is the load-bearing distinction for the paper's novelty claim, and it is narrower than the context doc currently assumes.

---

# Section A — Classic distributed-systems / workflow sources

These are the canonical sources that make most of the context doc's §10 mechanisms *not novel*. The paper must cite these, not re-invent them.

## A.1 RPC semantics, partial failure, and the origin of "outcome unknown"

**Birrell & Nelson — "Implementing Remote Procedure Calls"**
*ACM Transactions on Computer Systems 2(1), 1984.* `[V-CR]`
The founding RPC paper. Introduces the semantics distinction the whole paper rests on: an RPC that times out leaves the caller unable to tell whether the callee executed — hence at-most-once vs. at-least-once RPC, orphan detection, and the impossibility of a clean "exactly-once" RPC without server-side state.
**Why it matters:** This is the *canonical* citation for "timeout with unknown outcome." Any claim that agents surface a *new* unknown-outcome problem is false; agents merely inherit it. Cite as the origin, then argue agents make it worse (side-effecting, non-idempotent, LLM-arbitrated tools).
https://doi.org/10.1145/2080.357392

**Waldo, Wyant, Wollrath & Kendall — "A Note on Distributed Computing"**
*LNCS 1997 (Sun Microsystems TR, 1994).* `[V-CR]`
The classic argument that local and distributed computing differ *in kind* — the core difference being **partial failure**, latency, and memory access, none of which can be papered over by a nicer interface. Explicitly warns that trying to make remote calls look local is a design error.
**Why it matters (high value):** This is the **single best framing citation for the entire paper.** The paper's thesis — that agent runtimes inherit a local-call mental model while operating in a partial-failure regime — is precisely Waldo et al.'s argument applied to LLM tool calls. It also pre-empts the reviewer objection "isn't this just retry engineering?"
https://doi.org/10.1007/3-540-62852-5_6

**Gray — "Notes on Data Base Operating Systems"**
*LNCS 60, 1978.* `[V-CR]`
The origin of the **two-generals problem** (the paper's own §9 "ACK loss" and "action executed but ACK lost" cases), plus early treatment of commit protocols and intent logging.
**Why it matters:** Cite for the impossibility of confirmed delivery over an unreliable channel. This bounds what the paper can *ever* promise: no mechanism can give certain knowledge that a lost-ACK action did not execute — only reconcile/verify can.
https://doi.org/10.1007/3-540-08755-9_9

**Gray & Lamport — "Consensus on Transaction Commit"**
*ACM TODS 31(1), 2006.* `[V-CR]`
Shows distributed transaction commit (2PC) is a consensus problem, and gives the Paxos Commit construction — i.e. how to make commit non-blocking and fault-tolerant rather than blocking on a coordinator that may have died.
**Why it matters:** Directly relevant to the paper's §9 failure "long-running workflow 中 agent process 或 coordinator 重启." Cite when the runtime's commit point is itself distributed.
https://doi.org/10.1145/1132863.1132867

**Fischer, Lynch & Paterson — "Impossibility of Distributed Consensus with One Faulty Process"**
*Journal of the ACM 32(2), 1985.* `[V-CR]`
FLP: deterministic consensus is impossible in an asynchronous system with even one crash failure.
**Why it matters:** The theoretical floor. Use to justify why the paper proposes *bounded, best-effort, semantically-safe* recovery rather than guaranteed agreement — and to argue that a runtime should prefer `outcome_unknown` as an explicit, first-class state over pretending to know.
https://doi.org/10.1145/3149.214121

**Chandra & Toueg — "Unreliable Failure Detectors for Reliable Distributed Systems"**
*Journal of the ACM 43(2), 1996.* `[V-CR]`
Introduces failure detectors as first-class abstractions with completeness/accuracy properties, and shows which classes are sufficient for consensus.
**Why it matters:** This is the theory behind the paper's §10 **lease / lifecycle-aware capability registry** and its §3 `heartbeat/lease`. A heartbeat that declares a node "unavailable" can be *wrong*; the honest object is a *suspicion with a suspicion level*, not a boolean. Directly informs the `unavailable` vs `recovering` vs `timeout` distinctions in §9.
https://doi.org/10.1145/226643.226647

**Hayashibara, Défago, Yared & Katayama — "The φ Accrual Failure Detector"**
*SRDS 2004.* `[V-CR]`
Makes the above practical: instead of a binary heartbeat verdict, output a continuous suspicion value φ derived from arrival-time distribution.
**Why it matters:** The right technical answer to "capability 掉线后 … network 恶化" — degraded links should produce *graded suspicion*, and the context doc's `CapabilityDescriptor.availability` field is exactly where this belongs. Good citation for upgrading a boolean availability flag.
https://doi.org/10.1109/reldis.2004.1353004

## A.2 Idempotency, exactly-once, and duplicate side effects

**Helland — "Idempotence Is Not a Medical Condition"**
*ACM Queue 10(4), 2012.* `[V-CR]`
The canonical industry-theory treatment of idempotence, deduplication windows, and why "exactly-once" is really "effectively-once via dedup at a receiver that keeps state."
**Why it matters:** The **cite-as** source for the paper's §10 **idempotency-aware retry** and for `idempotency_key` in §3. Also supplies the key limitation to acknowledge: dedup requires a window and persistent receiver state — which in a disruption scenario is exactly what is missing.
https://doi.org/10.1145/2181796.2187821

**Apache Kafka — KIP-98, "Exactly Once Delivery and Transactional Messaging"**
*Apache Software Foundation design proposal.* `[IND]`
Specifies idempotent producers (producer ID + sequence number) plus transactions to obtain exactly-once across a pipeline.
**Why it matters:** The canonical *engineering* demonstration that exactly-once = idempotent producer + dedup + transactional boundary. Cite for the paper's baseline design, and note that Kafka's guarantees hold only while the broker and its ID allocation are reachable.
https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging

**Akidau et al. — "MillWheel: Fault-Tolerant Stream Processing at Internet Scale"**
*PVLDB 6(11), 2013.* `[V-CR]`
Low-watermark-based exactly-once stream processing with per-key persistent state and dedup, engineered to tolerate out-of-order and late data.
**Why it matters:** The canonical academic exactly-once system. Its "low watermark" is the direct ancestor of the paper's §10 **bounded replay** and its freshness/bounded-lateness reasoning. Cite when explaining why replay must be *bounded* rather than unbounded.
https://doi.org/10.14778/2536222.2536229

## A.3 Durable execution and workflow engines

**Zhang et al. — "Fault-tolerant and Transactional Stateful Serverless Workflows" (Beldi)**
*OSDI 2020.* `[V-URL]`
The key academic durable-execution paper: logs workflow state and journaled operations to cloud storage, adding **conditional writes** and transactional guarantees to serverless workflows so that retries and replays are safe.
**Why it matters:** This — not Temporal's marketing — is the citable academic prior art for "durable execution with transactional guarantees." The paper's §3 "canonical session / context / event history 用于恢复与审计" is Beldi's design, transplanted.
https://www.usenix.org/conference/osdi20/presentation/zhang-haoran · extended version: https://ar5iv.labs.arxiv.org/html/2010.06706

**Chandy & Lamport — "Distributed Snapshots: Determining Global States of Distributed Systems"**
*ACM TOCS 3(1), 1985.* `[V-CR]`
The consistent-global-snapshot algorithm — how to capture a distributed state that is *consistent* without stopping the system.
**Why it matters:** The foundation of the paper's §9 "network partition 后 state divergence" and of recovery-barrier design. Also the honest caveat: snapshot consistency requires in-band markers, so a partition during snapshotting yields a snapshot that may not correspond to any real moment.
https://doi.org/10.1145/214451.214456

**Elnozahy, Alvisi, Wang & Johnson — "A Survey of Rollback-Recovery Protocols in Message-Passing Systems"**
*ACM Computing Surveys 34(3), 2002.* `[V-CR]`
The definitive survey of checkpoint/rollback recovery, including the **domino effect**, orphan processes, and output commit — i.e. the impossibility of undoing an externally observable effect.
**Why it matters (high value):** The **cite-as** source for the paper's §10 **bounded replay** and §9 "恢复后 replay 顺序错误." "Output commit" is the precise classical name for the paper's central problem: once a side effect escapes, rollback cannot undo it — only compensation can. This single concept lets the paper state its core distinction with 40 years of authority behind it.
https://doi.org/10.1145/568522.568525

**Candea & Fox — "Crash-Only Software"**
*HotOS IX, 2003.* `[V-URL]`
Argues systems should be designed so that crash-and-restart is the *only* recovery path, eliminating complex in-place recovery code.
**Why it matters:** Directly relevant to the context doc's §9 "agent process 或 coordinator 重启." Cite to argue the runtime should make restart cheap and safe (via durable canonical state) rather than writing bespoke resume logic for each failure. Also a caution: crash-only works only when external effects are already committed and reconcilable.
https://static.usenix.org/events/hotos03/tech/full_papers/candea/candea_html/

**Garcia-Molina & Salem — "Sagas"**
*SIGMOD 1987.* `[V-CR]`
Replaces long-lived-transaction atomicity with a sequence of local transactions plus **compensating transactions** for semantic undo.
**Why it matters:** The **cite-as** source for the paper's §9 `compensating` state and for any rollback claim. Critical nuance the paper must state: sagas assume a *definable* compensation for every step, and assume you know the step ran. Under outcome-unknown, you may not know whether to compensate. That is where saga theory runs out — and it is the paper's genuine opening.
https://doi.org/10.1145/38714.38742 (SIGMOD Record) · https://doi.org/10.1145/38713.38742 (SIGMOD proceedings)

**Azure Architecture Center — "Saga distributed transactions pattern"** `[IND]` `[V-URL]`
**AWS Prescriptive Guidance — "Transactional outbox pattern"** `[IND]` `[V-URL]`
Industry specifications of the two compensation/atomicity patterns the paper's runtime will need. Cite as practice anchors (the reviewer will recognise them).
https://learn.microsoft.com/en-us/azure/architecture/patterns/saga · https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html

**Temporal — Workflow Execution / durable execution docs** `[IND]` `[V-URL]`
**Restate — Key Concepts / durable execution docs** `[IND]` `[V-URL]`
The two reference implementations of the deterministic-replay model of durability.
**Why they matter:** The paper's §10 mechanism set is *literally these products' feature list*. Cite them as the "mature mechanisms" the paper imports — and note the assumption they all share: **the event history is a faithful and complete record of nondeterministic effects.** Losing an ACK threatens exactly that assumption.
https://docs.temporal.io/workflow-execution · https://docs.restate.dev/foundations/key-concepts

## A.4 Consistency, staleness, and freshness

**Terry, Demers, Petersen, Spreitzer, Theimer & Welch — "Session Guarantees for Weakly Consistent Replicated Data"**
*PDIS 1994.* `[V-CR]`
Defines the four session guarantees — **read-your-writes, monotonic reads, monotonic writes, writes-follow-reads** — as the practical contract for mobile/disconnected clients.
**Why it matters (high value):** The **cite-as** source for the paper's §10 **stale-state / freshness guard** and for "掉线重连后不盲目重放." These guarantees were invented *precisely* for intermittently connected clients — the paper's exact setting — which both strengthens the work and removes any novelty claim for "freshness guards" as such.
https://doi.org/10.1109/pdis.1994.331722

**Herlihy & Wing — "Linearizability: A Correctness Condition for Concurrent Objects"**
*ACM TOPLAS 12(3), 1990.* `[V-CR]`
Defines linearizability — the standard strong-consistency correctness condition.
**Why it matters:** Gives the paper a precise vocabulary for what its canonical state does and does not guarantee. Useful for stating the correctness target of the runtime without hand-waving.
https://doi.org/10.1145/78969.78972

**Bailis, Davidson, Fekete, Ghodsi, Hellerstein & Stoica — "Highly Available Transactions: Virtues and Limitations"**
*PVLDB 7(3), 2013/2014.* `[V-CR]`
Maps which isolation levels are achievable without coordination, and proves which are not.
**Why it matters:** The rigorous backbone for the paper's consistency claims under partition. Lets the authors claim a specific, *achievable* consistency class instead of overclaiming.
https://doi.org/10.14778/2732232.2732237

**Kaul, Yates & Gruteser — "Real-time status: How often should one update?"**
*IEEE INFOCOM 2012.* `[V-CR]`
Founding **Age of Information** paper: quantifies staleness as a first-class metric and derives optimal update rates.
**Why it matters (high value):** The context doc's §12 metric "data freshness / AoI" already names this. AoI is the *canonical, communication-native* formalization of stale observations — and it is a genuine bridge between the wireless community and the agent-runtime community. Using AoI properly (rather than an ad-hoc "freshness" flag) is a real strength the paper should lean on.
https://doi.org/10.1109/infcom.2012.6195689

## A.5 Retry policy, overload, and metastability

**Google SRE Book — "Handling Overload"** `[IND]` `[V-URL]`
**Google SRE Book — "Addressing Cascading Failures"** `[IND]` `[V-URL]`
Origin of **client-side adaptive throttling** and **retry budgets**: cap retries as a *system-level* budget so a retrying fleet cannot amplify load into an outage.
**Why it matters:** The **cite-as** source for the paper's §10 retry budget and its §9 "一个持续失败 operation 耗尽 retry budget." Note that the doc's "retry budget" is currently framed *per-operation*; the canonical framing is *per-fleet*, which is the version that prevents metastable collapse.
https://sre.google/sre-book/handling-overload/ · https://sre.google/sre-book/addressing-cascading-failures/

**AWS Builders' Library — "Timeouts, retries, and backoff with jitter"** `[IND]` `[V-URL]`
Canonical guidance on bounding retries with exponential backoff plus jitter.
**Why it matters:** The paper's §11 baseline list includes "exponential backoff" — this is the citation for that baseline. Cite to define the baseline precisely, then show that backoff alone does not fix *side-effect duplication* (which is a semantics problem, not a timing one).
https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/

**Bronson, Aghayev, Charapko & Zhu — "Metastable Failures in Distributed Systems"**
*HotOS 2021.* `[V-CR]`
Names and models metastable failure: a system pushed into a self-sustaining bad equilibrium by a trigger plus a sustaining feedback loop (often retry amplification), where removing the trigger does not restore health.
**Why it matters (high value):** The theoretical frame for the paper's claim that communication degradation causes **persistent**, not transient, agent failure. A disruption that fires a retry storm can leave the system stuck even after the link recovers — which is a much stronger failure claim than "tasks fail during outages."
https://doi.org/10.1145/3458336.3465286

**Huang et al. — "Metastable Failures in the Wild"**
*OSDI 2022.* `[V-URL]`
Empirical study of metastable failures in production; catalogs triggers, sustaining effects, and mitigations.
**Why it matters:** Supplies real-world evidence that retry loops are a leading sustaining effect. Strengthens the paper's motivation from theory into observed practice.
https://www.usenix.org/conference/osdi22/presentation/huang-lexiang

**"Retry Amplification in Distributed Systems: A Systematic Analysis of Retry Policies and Their Role in Cascading Failures"** `[P]`
*arXiv 2608.25403, Aug 2026.* Abstract read directly.
Introduces a **retry amplification factor (RAF)**; audits 200 open-source microservice projects (backoff missing in 60.9% of detected configs; only 1 of 113 production configs randomizes delay); in simulation, under correlated failures a naive retry policy *reduces* success from 55.4% → 41.5% versus no retries at all; proposes **Adaptive Retry Budgeting (ARB)**.
**Why it matters:** Very recent, directly on-point, and empirically damning about naive retry. **Cite it** — but note it occupies the "retry budgets under correlated failure" space, so the paper should not claim that as novel. It also validates the paper's baseline choice (naive retry) as one that measurably *hurts*.
https://arxiv.org/abs/2608.25403

## A.6 Scheduling, head-of-line blocking, and liveness

**Demers, Keshav & Shenker — "Analysis and Simulation of a Fair Queueing Algorithm"**
*SIGCOMM 1989.* `[V-CR]`
The founding fair-queueing paper: per-flow queues with round-robin service to defeat **head-of-line blocking** and provide fairness/isolation between flows.
**Why it matters (high value):** The **cite-as** source for two of the context doc's §10/§12 items at once — **bounded + fair replay** and "FIFO replay 导致 critical task starvation / head-of-line blocking." Fair queueing *is* the answer to a stalled node blocking a critical task, and the paper should say so explicitly rather than inventing a scheduling scheme.
https://doi.org/10.1145/75246.75248

**Dean & Barroso — "The Tail at Scale"**
*Communications of the ACM 56(2), 2013.* `[V-CR]`
Diagnoses latency tail amplification in large fan-out services; introduces **hedged requests** and tied requests.
**Why it matters:** Explains *why* one degraded node poisons an agent's end-to-end latency, and gives the standard mitigation. Also a caution: hedging duplicates requests, so it is only safe on idempotent operations — a nice concrete link between the retry and idempotency mechanisms.
https://doi.org/10.1145/2408776.2408794

## A.7 Freshness/transport for the disaster-communications domain

**Fall — "A Delay-Tolerant Network Architecture for Challenged Internets"**
*SIGCOMM 2003.* `[V-CR]`
The DTN architecture: store-and-forward **bundle** layer, custody transfer, and the recognition that in challenged networks, connectivity is intermittent by nature and end-to-end paths may never exist.
**Why it matters (high value):** The canonical domain citation. It legitimizes the paper's premise — that intermittent connectivity is the *normal operating condition*, not a fault — and it supplies the correct vocabulary (custody transfer, store-and-forward) for the paper's durability/replay discussion. Cite it *and* draw the boundary: DTN delivers **bundles**, not **agent tool-call semantics**. Nobody has joined these two.
https://doi.org/10.1145/863955.863960

---

# Section B — LLM agent reliability literature (2023–2026)

## B.0 The headline finding

**Almost no widely used tool-use agent benchmark injects any fault at all.** τ-bench, τ²-bench, ToolSandbox, AgentBench, WebArena, WorkBench, MINT, BFCL and API-Bank are **capability** benchmarks over a correct, cooperative environment. Their failure signal is *task* failure, not *environment* failure.

**The dedicated fault-injection work is real — but it injects application/HTTP-layer tool faults, not transport faults.** Across every verified fault-injecting item (ToolMaze, ReliabilityBench, ChaosLLM, AgentChaos, ToolMisuseBench, AgentDisruptBench, Retry/Switch/Abstain, Atomix), the documented classes are latency spikes, partial failures, rate limits (429), malformed output, schema drift, and stale context.

**No verified instance was found that injects TCP reset, packet loss, ACK loss, node disconnect, or throughput degradation at the network layer.** And **unknown-outcome and duplicate-delivery are not verified as *injected fault classes* anywhere** — they appear only as *semantic concerns* in transactional/recovery systems.

## B.1 Failure taxonomies

**Cemri et al. — "Why Do Multi-Agent LLM Systems Fail?" (MAST)** — *NeurIPS 2025, Datasets & Benchmarks* `[V-REV]`; arXiv 2503.13657.
MAST-Data: 1600+ annotated traces across 7 MAS frameworks; MAST taxonomy of **14 failure modes** in 3 categories, built from 150 traces with κ = 0.88.
**Why it matters:** The reference taxonomy any new failure-mode claim will be compared against. Its modes are overwhelmingly about *inter-agent coordination*, not the transport layer underneath — the gap the paper occupies. It is also trace-based, i.e. it presupposes a durable execution record exists.
https://proceedings.neurips.cc//paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html · https://arxiv.org/abs/2503.13657

**"Demystifying the Lifecycle of Failures in Platform-Orchestrated Agentic Workflows" (AgentFail)** `[P]` — arXiv 2509.23735 (v2 Feb 2026). Abstract read directly. `[FLAG]`
AgentFail dataset: **307 real-world failure cases** from two agentic workflow platforms, analyzed by failure manifestation, root cause, and repair difficulty. Confirms failures propagate across heterogeneous nodes via natural language, tool invocations, and dynamic control logic.
**Why it matters:** The best empirical evidence that agent failures are *lifecycle* phenomena spanning nodes — supporting the paper's framing. Note: `[FLAG]` the subagent could not establish whether "AgentFail" is a paper, dataset, or benchmark; the arXiv title is the confirmed one. **Cite the arXiv title, not "AgentFail" alone.**
https://huggingface.co/papers/2509.23735

**"When Errors Become Narratives: A Longitudinal Taxonomy of Silent Failures in a Production LLM Agent Runtime"** `[P]` — arXiv 2606.14589.
Longitudinal taxonomy of **silent failures** in a production runtime: errors swallowed and re-narrated by the model as plausible progress, so the trace reads as success.
**Why it matters:** Extremely close to a "runtime semantics of failure" framing, and production-grounded. This is the class of failure (successful-looking execution) that motivates outcome-unknown semantics and durable logs. Must be cited and differentiated.
https://ar5iv.labs.arxiv.org/html/2606.14589v1

**"Model or Harness? An Interaction-Centric Taxonomy for Localizing Agent Failures"** `[P]` — arXiv 2607.28802.
Taxonomy explicitly designed to localize a failure to **model vs. harness** (the surrounding runtime/scaffold).
**Why it matters:** Formalizes "the harness is a first-class failure locus" — direct support for the paper's claim that execution semantics (not model quality) drive reliability. Arguably the most on-topic taxonomy found.
https://huggingface.co/papers/2607.28802

**"From Confident Closing to Silent Failure: Characterizing False Success in LLM Agents"** — ICML 2026 `[V-REV]` (`[FLAG]` abstract scope only partially verified).
Characterizes agents confidently reporting completion when the task is not complete.
**Why it matters:** False success is the **observable symptom of lost-ACK execution semantics**. Strong supporting citation for stating the problem.
https://icml.cc/virtual/2026/77904

**"Exploring Autonomous Agents: A Closer Look at Why They Fail When Completing Tasks"** — ASE 2025, NIER track `[V-REV]`.
Empirical study of agent task-completion failure published in a *software-engineering* venue.
**Why it matters:** Evidence that the failure-taxonomy conversation is being claimed by SE/dependability venues — the lineage a systems paper should cite.
https://conf.researchr.org/details/ase-2025/ase-2025-nier-track/15/Exploring-Autonomous-Agents-A-Closer-Look-at-Why-They-Fail-When-Completing-Tasks

**"A Survey on Failure Analysis and Fault Injection in AI Systems"** `[P]`/`[FLAG]` — arXiv 2407.00125; ACM DOI 10.1145/3732777 surfaced (year unverified).
Surveys failure analysis and fault injection for AI systems — the dependability-engineering bridge.
**Why it matters:** Lets the paper claim *lineage* from classical fault injection rather than novelty-by-isolation.
https://www.semanticscholar.org/paper/A-Survey-on-Failure-Analysis-and-Fault-Injection-in-Yu-Tan/dde772ac48962179e5bb20bb6cd1bc2cb46ba272

> **Negative result — do not miscite.** The lead "**AgentTaxo**" is **not a failure taxonomy**. The actual title is *"AgentTaxo: Dissecting and Benchmarking **Token Distribution** of LLM Multi-Agent Systems"* (ICML 2025). https://openreview.net/pdf?id=0LbiYYIpC

## B.2 Capability benchmarks (no fault injection)

| Benchmark | Venue | What it measures | Faults injected |
|---|---|---|---|
| **τ-bench** (arXiv 2406.12045) | `[P]` | LLM-simulated user + domain APIs; introduces **pass^k** | **None** |
| **τ²-bench** (arXiv 2506.07982) | `[P]` | Extends to **dual control** (user and agent mutate shared state) | **None** |
| **ToolSandbox** (arXiv 2408.04682) | `[P]` | **Stateful** tool exec, implicit state deps, **milestone DAG** eval | **None** |
| **AgentBench** (arXiv 2308.03688) | **ICLR 2024** `[V-REV]` | 8 interactive environments | **None** |
| **WebArena** (arXiv 2307.13854) | **ICLR 2024** `[V-REV]` | 812 long-horizon web tasks, programmatic eval | **None — deliberately removed** |
| **WorkBench** (arXiv 2405.00823) | `[P]` | Workplace tasks; scores **side effects** on environment | **None** |
| **MINT** (arXiv 2309.10691) | **ICLR 2024** `[V-REV]` | Multi-turn tool use + **language feedback** | **None** |
| **BFCL** | **ICML 2025** `[V-REV]` | Function-call correctness, incl. executable eval | **None** |
| **API-Bank** | **EMNLP 2023** `[V-REV]` | 3-level tool-augmented eval with API simulator | **None** |

**Why the table matters — three specific hooks:**

1. **τ-bench's `pass^k`** is the field's existing admission that agent behaviour is stochastic across repeated runs. The paper's hook: `pass^k` measures variance but treats the environment as *reliable*, so the variance contributed by *environment* faults is unmeasured. https://github.com/sierra-research/tau-bench
2. **ToolSandbox's milestone-DAG** is the best existing precedent for scoring *partial progress through a plan* — exactly what a runtime needs to decide retry vs. resume vs. roll back. It is the natural eval substrate to plug a fault-injection harness into. https://machinelearning.apple.com/research/toolsandbox-stateful-conversational-llm-benchmark
3. **WebArena is the sharpest rhetorical foil.** The community *deliberately eliminated* environment nondeterminism to make agent differences attributable to the agent. The paper can argue that this design choice removed the very phenomenon production exposes. https://openreview.net//pdf/384c500abb2b5adc4f3c40956a267477925c4b94.pdf

> **Title correction.** API-Bank's ACL Anthology title is **"A Comprehensive Benchmark for Tool-Augmented LLMs"** (EMNLP 2023), not "A Benchmark for Tool-Augmented LLMs." Use the anthology title. https://aclanthology.org/2023.emnlp-main.187/

## B.3 Fault-injecting agent benchmarks — the critical section

**"When Tools Fail: Benchmarking Dynamic Replanning and Anomaly Recovery in LLM Agents" (ToolMaze)** `[P]` — arXiv 2606.05806. Abstract read directly.
Benchmark for **dynamic path discovery and error recovery**. Two-dimensional design: DAG topological complexity × a **2×2 taxonomy of tool perturbations (explicit/implicit × transient/permanent)**. Finds perturbations degrade nearly all models, sharpest under **implicit semantic failures** (agents systemically over-trust corrupted outputs; Perturbation Recovery Rate drops ~37%); complex topologies trap agents in futile trial-and-error loops. Key result: **agentic fault-tolerance improves with model scale 3.66× slower than basic task execution** — replanning is a distinct bottleneck not fixed by scale or prompting.
**Why it matters:** This is the **strongest existing "tools fail, measure recovery" precedent**, and its scale-vs-recovery result is *directly reusable* as evidence for the context doc's §4 claim #2 ("these failures don't disappear as LLMs get stronger"). **Caveat:** its faults are tool anomalies with an *alternative path* available — i.e. the failure is **visible enough to replan**. The paper's differentiator is that network faults are **outcome-ambiguous**: you may not know the call ran, so you cannot even decide whether to replan.
https://arxiv.org/abs/2606.05806 · https://github.com/Zhudongsheng75/ToolMaze

**"ReliabilityBench: Evaluating LLM Agent Reliability Under Production-Like Stress Conditions"** `[P]` — arXiv 2601.06112. Abstract read directly.
Reliability across three dimensions: consistency under repeated execution (**pass^k**), robustness to semantically equivalent task perturbation (intensity ε), and **fault tolerance under controlled tool/API failures (intensity λ)**. Contributes the unified reliability surface **R(k, ε, λ)**, **action metamorphic relations** (correctness via end-state equivalence, not text similarity), and a chaos-engineering-style injector with faults: **timeouts, rate limits, partial responses, schema drift**. 1,280 episodes, 4 domains. Perturbations drop success 96.9% → 88.1%; **rate limiting is the most damaging fault**; ReAct more robust than Reflexion.
**Why it matters (high value):** The **closest existing benchmark to the paper's evaluation design**, and the R(k, ε, λ) surface is a strong methodological idea to adopt or differentiate from. **Crucially, its fault list is explicitly application-layer, not network-layer**, and it does not inject unknown-outcome or duplicate delivery. Its "action metamorphic relations" (end-state equivalence) is *exactly* the right correctness criterion for side-effect checking — the paper should adopt this rather than text similarity.
https://arxiv.org/abs/2601.06112

**"AgentChaos: Chaos Engineering for Agent Systems via Programmatic Fault Injection"** `[P]` — arXiv 2608.06790. Abstract read directly.
Injects faults at the **shared HTTP interface to LLM APIs** without source modification. Defines **crash, omission, and value faults** on content and tool-call fields; verifies each fault triggered (to avoid underestimating impact). 65 fault configurations: pass@1 drops up to **50 percentage points**; ranking consistent across models (robustness depends on *system implementation*, not model capability); existing fault diagnosis achieves <53% accuracy on fault type, <56% on fault step.
**Why it matters (very high value):** Two results are directly usable: (a) **robustness depends on implementation, not model** — strong support for the paper's §4 claim #2; (b) the fact that AgentChaos injects at the **HTTP layer** is precisely the boundary argument the paper needs — the *transport* layer beneath HTTP is untested. Also: "crash/omission/value" is a *content-corruption* taxonomy, not a *delivery* taxonomy; there is no unknown-outcome class.
https://arxiv.org/abs/2608.06790 · https://zenodo.org/records/21823973
> `[FLAG]` **Name collision.** This is **not** the same as the toolkit `reaatech/agent-chaos` (https://github.com/reaatech/agent-chaos), whose README lists "latency spikes, partial failures, 429s, malformed tool outputs, stale context." Do not conflate them in citations.

**ReliabilityBench/AgentChaos peers (existence verified, fault catalogues `[FLAG]` unverified):**
- **ToolMisuseBench** `[P]` arXiv 2604.01508 — an **offline deterministic** benchmark for tool *misuse* and recovery. The word "deterministic" is a strong foil: this line *removes* environment nondeterminism, the mirror image of the paper. https://huggingface.co/datasets/sigdelakshey/ToolMisuseBench
- **AgentDisruptBench** `[IND]`/no paper — HuggingFace dataset. **I read its datasheet directly:** a **20-type disruption taxonomy** (timing: timeout, latency; HTTP status: 429/401/403/500/502/503; response content: malformed_json, truncated, null, missing_fields, type_mismatch, schema_drift, wrong_data; behavioral: **intermittent, flapping**, quota_exhausted, auth_expiry, cascading), 9 severity profiles, and the same **R(k, ε, λ)** metric. **All fault classes are tool-call-level; none is a radio/channel model.** "Flapping" and "intermittent" are the closest any artifact comes to the context doc's §9 "gateway / relay flapping" — **cite this as the nearest neighbor and differentiate explicitly.** https://huggingface.co/datasets/kavirubc/AgentDisruptBench/blob/main/README.md
- **ChaosLLM: A Dependability Testing Approach for Tool-Calling Agents** — IEEE doc 11262344 `[FLAG]` venue/year unverified; fault classes unverified. Cite the *dependability-testing framing* only. https://www.semanticscholar.org/paper/ChaosLLM%3A-A-Dependability-Testing-Approach-for-Iannillo/691ba26ffad37c253d0c1a951e7600e052566db6
- **"Retry, Switch, or Abstain? Learning Strategy-Aware Tool-Use Policies via Controlled Error Injection"** `[P]` arXiv 2608.11977 — learns a policy over retry / switch-tool / abstain under controlled error injection. **The closest prior art to "retry policy under a specified fault model."** Differentiate: it *learns the policy*; the paper's runtime *provides the semantics* the policy depends on. https://www.alphaxiv.org/abs/2608.11977v1
- **"More Vulnerable than You Think: On the Stability of Tool-Integrated LLM Agents"** `[P]` arXiv 2506.21967 — stability under perturbation. https://papers.cool/arxiv/2506.21967
- **WAREX: Web Agent Reliability Evaluation** `[P]` arXiv 2510.03285 — **no faults injected**; "reliability" = repeat-run consistency. **Terminology hazard: define your terms, because "reliability" in this literature often means repeat-run stability, not fault tolerance.** https://ar5iv.labs.arxiv.org/html/2510.03285
- **AgentCheck** `[P]` arXiv 2607.11098 — reproduce→intervene→mitigate workbench **over MCP**. The natural experimental platform for a 2026 fault-injection claim. https://huggingface.co/papers/2607.11098

**"Towards a Science of AI Agent Reliability"** `[P]`/`[FLAG]` — arXiv 2602.16666.
Proposes **12 metrics across four dimensions: consistency, robustness, predictability, safety**.
**Why it matters:** The best available scaffold for *defining* reliability dimensions in the paper's evaluation, and it gives a defensible argument that current benchmarks cover only a subset of dimensions.
https://huggingface.co/papers/2602.16666

## B.4 Retry, self-correction, nondeterminism

**Shinn et al. — "Reflexion: Language Agents with Verbal Reinforcement Learning"** — *NeurIPS 2023* `[V-REV]`; arXiv 2303.11366. Read directly from arXiv.
Verbal self-reflection stored in episodic memory, retried on the next attempt.
**Why it matters:** Reflexion is the canonical "just retry with reflection" strategy — and it **silently assumes the action is repeatable and that retrying is safe**. That assumption is exactly what at-most-once/at-least-once semantics break. Crisp, citable gap: the reflection literature never asks whether the failed action had a side effect.
https://mlanthology.org/neurips/2023/shinn2023neurips-reflexion/

**Huang et al. — "Large Language Models Cannot Self-Correct Reasoning Yet"** — *ICLR 2024* `[V-REV]`.
Intrinsic self-correction (no external ground truth) often *degrades* performance; gains require external feedback.
**Why it matters (high value):** The key negative result the paper must respect — it kills "the agent will fix itself." It motivates **external, runtime-provided** signals (delivery confirmation, idempotency tokens, authoritative outcome queries) as the only sound basis for recovery. One of the strongest citations available for the thesis.
https://mlanthology.org/iclr/2024/huang2024iclr-large/

**Gou et al. — "CRITIC: LLMs Can Self-Correct with Tool-Interactive Critiquing"** — *ICLR 2024* `[V-REV]`.
Self-correction driven by external tools used to verify the model's own output.
**Why it matters:** CRITIC is the correct-sounding answer to Huang et al. — and its unexamined assumption is that **the verifier itself never fails**. Under network faults, the verifier call is itself subject to timeout/unknown-outcome/duplicate delivery. **That is the paper's opening.**
https://mlanthology.org/iclr/2024/gou2024iclr-critic/

**Madaan et al. — "Self-Refine: Iterative Refinement with Self-Feedback"** — *NeurIPS 2023* `[V-REV]`.
Cite alongside Self-Refine (generation gains) and Huang (reasoning losses) to state precisely when self-correction works. Neither covers retry-after-ambiguous-side-effect.
https://mlanthology.org/neurips/2023/madaan2023neurips-selfrefine/

**"On Randomness in Agentic Evals"** `[P]`/`[FLAG]` — arXiv 2602.07150.
Systematic catalog of nondeterminism sources in agentic evaluation beyond sampling temperature — environment, harness, evaluation loop.
**Why it matters (high value):** The strongest citation for "agent results are not reproducible," and it itemises *where* nondeterminism comes from. Methodological warning the paper must heed: any reliability claim needs repeated runs.
https://ar5iv.labs.arxiv.org/html/2602.07150

**"How Consistent Are LLM Agents? Measuring Behavioral Reproducibility in Multi-Step Tool-Calling Pipelines"** `[P]` `[FLAG]`.
Measures behavioural reproducibility in multi-step tool-calling pipelines. Directly supports the "stateful, non-reproducible tool-using agent" premise.
https://www.semanticscholar.org/paper/How-Consistent-Are-LLM-Agents-Measuring-Behavioral-Yagubyan/e7d9d5855b184af36df5153a00b3eeac7a02110e

## B.5 Durability, checkpointing, replay, recovery — **the high-risk zone**

**SagaLLM: Context Management, Validation, and Transaction Guarantees for Multi-Agent LLM Planning**
*PVLDB vol. 18* `[V-REV]`; DOI 10.14778/3750601.3750611.
Applies the **Saga compensation pattern** to multi-agent LLM planning, providing transactional guarantees (atomic commit, persistence, snapshot isolation) with validation.
**Why it matters (very high value):** **The single most important academic citation for the mechanism half of the paper's thesis** — it is the existing demonstration that database transaction semantics can be imposed on agent execution. The paper's positioning must be relative to it: SagaLLM assumes *coordinated participants and definable compensations*, whereas network faults produce **unknown outcomes** where you do not even know whether compensation is required.
https://www.vldb.org/pvldb/vol18/p4874-chang.pdf

**"Verified Tool Calls Improve LLM Agent Reliability Under Non-Atomic Failures"** `[P]` — arXiv 2608.02645, Jul 2026. **Abstract read directly. THIS IS THE MOST DIRECT NOVELTY THREAT.**
Verbatim from the abstract: *"Existing agent frameworks typically assume that tool calls are atomic and return binary success or failure signals. However, real-world systems exhibit non-atomic behaviors such as **timeouts after dispatch, delayed visibility, and partial state updates**. These mismatches lead to reliability issues including **duplicate actions**... A lightweight, verification-aware tool wrapper is introduced that augments tool calls with **postcondition verification, verify-before-retry logic, and idempotency keys**."* Evaluated in a controlled simulated environment with injected non-atomic failures; reduces duplicate actions while maintaining task success.
**Why it matters (decisive):** This paper publishes **the context doc's §10 mechanism #6 (reconcile / verify-before-retry) and #2 (idempotency-aware retry) almost verbatim**, and it names the exact failure class (`timeout` with `outcome_unknown`) the paper is built around. **The paper cannot claim verify-before-retry or idempotency keys as a contribution.** It must cite this as the generic-agent precedent and differentiate on: (a) the fault model being *communication-derived and trace-driven* rather than synthetic; (b) the wireless/disaster capability-lifecycle dimension (energy, freshness, mission criticality); (c) the fact that its verification is *postcondition-based on a single tool*, whereas the paper needs verification under node unavailability, where the verifying call itself may fail.
https://arxiv.org/abs/2608.02645

**"DART: Semantic Recoverability for Structured Tool Agents"** `[P]` — arXiv 2605.23311, May 2026. **Abstract read directly.**
Formalizes the gap that *"replaying the entire task is safe but wasteful, while restoring from a local checkpoint is efficient but can leave committed downstream work tied to an upstream history that no longer exists."* Formalizes **semantic recoverability**; DART localizes the failed instance, certifies semantically recoverable boundaries, aligns checkpoints to them, and selects an admissible restore point preserving committed downstream work — **or blocks otherwise**. Key claim: *"controller legality does not imply semantic validity."*
**Why it matters (decisive):** This *is* the theory of what the paper wants to do about recovery boundaries. It occupies the "safe rollback under committed downstream effects" space with formal rigor. The paper should cite it as the theory it applies, and differentiate on the *communication-triggered ambiguity* of whether a boundary was crossed at all.
https://arxiv.org/abs/2605.23311

**"ACRFence: Preventing Semantic Rollback Attacks in Agent Checkpoint-Restore"** `[P]` — arXiv 2603.20625, Mar 2026. **Abstract read directly.**
Verbatim: *"LLM agent frameworks increasingly offer checkpoint-restore... advising developers to make external tool calls safe to retry. **This advice assumes that a retried call will be identical to the original, an assumption that holds for traditional programs but fails for LLM agents, which re-synthesize subtly different requests after restore.** Servers treat these re-generated requests as new, enabling **duplicate payments**, unauthorized reuse of consumed credentials, and other irreversible side effects; we term these **semantic rollback attacks**."* Identifies **Action Replay** and **Authority Resurrection**; proposes ACRFence, recording irreversible tool effects and enforcing **replay-or-fork semantics** on restoration.
**Why it matters (decisive, and a gift):** This is the **strongest single piece of external validation for the paper's core premise** — that *replay after recovery is unsafe for tool-using agents specifically*, because LLM agents regenerate rather than replay identical requests. **The paper should cite this as the motivating result, not compete with it.** It also adds a dimension the context doc lacks: replay can be a *security* problem (authority resurrection), which strengthens the "side_effect_class / authority bound to recovery semantics" primitive in §3.
https://arxiv.org/abs/2603.20625

**"AgentRewind: Recoverable Execution for Long-Horizon LLM Agents"** `[P]` — arXiv 2608.14380, Aug 2026. **Abstract read directly.**
Runtime recovery framework recording **aligned checkpoints of agent context and controlled environment**, allowing return to an earlier state and resumption with information from previous attempts. Contributes **MettleBench** for long-horizon engineering assignments with related requirements. Improves success rate and average checklist progress.
**Why it matters:** The direct systems answer to context/config checkpointing for long-horizon agents. Note the deliberate qualifier **"controlled environment"** — i.e. it checkpoints the *sandbox*, not external side effects. That boundary is the paper's territory.
https://arxiv.org/abs/2608.14380

**"DeltaBox: Scaling Stateful AI Agents with Millisecond-Level Sandbox Checkpoint/Rollback"** `[P]` `[FLAG]` — arXiv 2605.22781.
Millisecond-level checkpoint/rollback of agent **sandboxes** — the environment (not just the conversation) as checkpointable state, at per-step granularity.
**Why it matters:** Supplies the latency number needed to argue checkpointing is affordable — and raises the semantic question it does not answer: sandbox state rolls back, but **external side effects cannot**. Perfect foil.
https://www.semanticscholar.org/paper/DeltaBox%3A-Scaling-Stateful-AI-Agents-with-Sandbox-Dong-He/b1660afbd7c1ed0789cb6f7279530d08047d47ad

**"Self-Healing Agentic Orchestrators for Reliable Tool-Augmented LLM Systems"** `[P]` — arXiv 2606.01416, May 2026. **Abstract read directly.**
Verbatim failure list: *"tool timeouts, malformed arguments, stale context, contradictory evidence, retry loops, and unverified intermediate outputs."* Treats reliability as a **bounded runtime control problem**: maps observable failure signals to failure classes, selects recovery actions **under explicit budgets**, verifies recovered trajectories, records observability traces. On a 100-task fault-injection benchmark vs. static-workflow, retry-only, ReAct, and full-replanning baselines: **98.8% success vs. 94.5% (retry-only) and 93.8% (full replanning)**; a **recovery-budget sweep** shows the largest gap at a single recovery attempt (94.0% vs 85.3%/88.2%); under silent-failure conditions verifier-guided self-healing reduces silent failures to **0.0%**.
**Why it matters (decisive):** This is **the context doc's §10 mechanism set, already built and already evaluated with a budget sweep** — including *bounded recovery* (the paper's "bounded replay") and *stale context*. It directly occupies "failure-aware, budgeted, verification-guided orchestration + fault-injection benchmark." **The paper cannot claim novelty for the mechanism set.** Cite as the generic precedent and differentiate on the communication fault model, the wireless capability lifecycle, and trace-driven evaluation.
https://arxiv.org/abs/2606.01416 · https://github.com/R-Suresh/self-healing-agentic-orchestrator

**"Atomix: Timely, Transactional Tool Use for Reliable Agentic Workflows"** `[P]` `[FLAG]` — arXiv 2602.14849.
Makes tool use **transactional** within agentic workflows; the arXiv HTML contains an explicit **"A.2 Fault Injection Details"** appendix.
**Why it matters (high priority):** Potentially the closest existing system to "execution semantics for agent tool calls, evaluated under fault injection." **Read this in full before finalising the novelty claim** — its fault catalogue is unverified.
https://ar5iv.labs.arxiv.org/html/2602.14849

**"VIGIL: A Reflective Runtime for Self-Healing LLM Agents"** `[P]` — arXiv 2512.07094. A *runtime* (not a prompt strategy) doing reflective self-healing. Differentiate: VIGIL reflects on **behaviour**; the paper addresses **effect** (did my action happen?) — an orthogonal axis.
https://ar5iv.labs.arxiv.org/html/2512.07094

**"Durable Execution for AI Agents: A Design Pattern for Fault-Tolerant Agent Loops"** `[FLAG]` — IEEE document 11638700; venue/year unverified.
The "mature runtime mechanisms fix it" claim, already written for the generic agent setting. https://ieeexplore.ieee.org/document/11638700

**"DelAct: A Replayable Boundary Runtime for Auditable and Governed LLM Agent Workflows"** `[FLAG]` — IEEE doc 11661202. A **replayable boundary** — the primitive that makes post-recovery reconciliation possible. https://ieeexplore.ieee.org/document/11661202

**"State-Aware Runtime for Long-Horizon LLM Agents: A Conceptual Framework and Research Agenda"** `[FLAG]` — Cambridge Engage (preprint platform). Explicitly about a "state-aware runtime" for long-horizon agents. Extremely close framing; venue unverified. https://www.cambridge.org/engage/coe/article-details/6a4abb75810b9dcc82ce84f2

**Industrial durable-execution for agents** `[IND]` — all cite-as-practice, never as evidence:
Temporal (durable agents, LangGraph plugin, Pydantic AI integration) https://temporal.io/blog/temporal-langgraph-plugin-durable-execution · DBOS (embedded durable execution; OpenAI Agents SDK/Pydantic AI/Vercel integrations) https://docs.dbos.dev/integrations/openai-agents · Restate (**durable webhooks** — precisely "the effect happened but the agent never observed the response") https://docs.restate.dev/guides/durable-webhooks · Inngest (**durable endpoints** — durability beyond workflows) https://inngest.vercel.app/blog/introducing-durable-endpoints · Azure **Durable Task for AI Agents** https://learn.microsoft.com/en-us/azure/durable-task/sdks/durable-task-for-ai-agents · LangGraph persistence/checkpointing https://docs.langchain.com/oss/python/langgraph/persistence · **MemGPT/Letta** (agent state as an OS memory-hierarchy problem) https://www.semanticscholar.org/paper/MemGPT%3A-Towards-LLMs-as-Operating-Systems-Packer-Fang/908dad62c0e43d80e3e3cb3c0402f7c71c70499c

> The OS analogy is the field's existing organizing metaphor for agent state, and it is a *storage* analogy. The paper's opportunity: extend it to the parts OSes have that this one lacks — **delivery guarantees, idempotency, crash consistency, and fsync-like durability points.**

## B.6 Secondary items (added in revision; lower priority)

These are real but non-load-bearing. Included for completeness of the artifact; none changes the gap analysis. All `[P]` unless flagged.

**"Threshold Choice, Not Sample Size, Bounds Trustless Verification of Nondeterministic Compound AI Workflows"** — arXiv 2609.10601 (Sep 2026). Finds the **decision threshold**, not sample count, is the binding constraint on what can be *verified* about nondeterministic compound AI workflows.
**Why it matters (the most useful item in this subsection):** A formal/statistical result about what "verified" can even mean for nondeterministic workflows. Directly supports the evaluation-section recommendation to **report error bars and repeat runs**, and pairs with "On Randomness in Agentic Evals." Use it to justify — rather than hand-wave — the statistical treatment of reliability claims. Pairs with the ICLR blogpost "Why AI Evaluations Need Statistical Rigor" https://iclr-blogposts.github.io/2026/blog/2026/why-ai-evaluations-need-error-bars/
https://arxiv-org.ezproxy.obspm.fr/html/2609.10601v1

**"PALADIN: Self-Correcting Language Model Agents to Cure Tool-Failure Cases"** — arXiv 2509.25238. Self-correction loop specifically for tool-failure cases; surfaces the metric **"Catastrophic Success Rate"**.
**Why it matters:** Supplies a *named* metric for the failure mode this paper also cares about (an agent reporting success on a task that actually failed), and it positions itself against CRITIC. Worth a look when defining the metrics table — "catastrophic success" is close to the paper's "duplicate/unsafe side effect misreported as done." https://huggingface.co/papers/2509.25238

**"A Trace-Based Assurance Framework for Agentic AI Orchestration: Contracts, Testing, and Governance"** — arXiv 2603.18096. Assurance framework built on **contracts** over orchestration traces.
**Why it matters:** Contracts (preconditions, postconditions, idempotency) are the natural formal device for tool-call semantics, and this is prior art on using them for agent orchestration. https://huggingface.co/papers/2603.18096

**"On Randomness in Agentic Evals"** — see the main B.4 entry; listed here only to note its companion **"Harness Engineering for Predictable Agentic Systems: An Empirical Study of Deterministic Execution Constraints"** (arXiv 2608.26197), which studies which engineering practices actually make agent execution reproducible. https://arxiv-org.ezproxy.obspm.fr/html/2608.26197v1

**"Graph-Based Self-Healing Tool Routing for Cost-Efficient LLM Agents"** — arXiv 2603.01548. Self-healing tool routing as a graph, optimizing recovery *and cost* jointly.
**Why it matters:** Cost is a real constraint on any retry/replay policy; a paper proposing recovery semantics should state who pays. https://huggingface.co/papers/2603.01548

**"R-LAM: Reproducibility-Constrained Large Action Models for Scientific Workflow Automation"** — arXiv 2601.09749. Reproducibility as a first-class *constraint* on action selection (a distinct posture: predictability over capability). https://huggingface.co/papers/2601.09749

**"Optimizing FaaS Platforms for MCP-enabled Agentic Workflows"** — arXiv 2601.14735. The *academic* treatment of FaaS + MCP agent workflows.
**Why it matters:** A better citation than the vendor blogs (AWS Lambda Durable Functions, Bedrock AgentCore) when the paper needs to justify serverless/durable substrate for tool calls. Note `[FLAG]` the cloud vendors' own "Step Functions for agents" material is third-party and weak — **no authoritative first-party AWS page was found**; cite AWS cautiously. https://ar5iv.labs.arxiv.org/html/2601.14735

**AIRTBench** — arXiv 2506.14682. Red-teaming benchmark; notable as the one place **rate limiting appears as a core *environmental constraint*** rather than a fault. https://ar5iv.labs.arxiv.org/html/2506.14682

**Additional taxonomies found but not central** (all `[P]`): "Beyond the Leaderboard: A Synthesis of Tool-Use, Planning, and Reasoning Failures in LLM Agents" (arXiv 2607.05775) — the "state of the taxonomy" citation; "Silent Failures in Multimodal Agentic Search" (arXiv 2607.19793); a RAG failure taxonomy (ACL Anthology, TrustNLP 2026 workshop `[V-REV]`); "A Survey for LLM Agent Trajectory Analysis" (IEEE doc 11626967, venue/year unverified); "Tool Execution Hallucination in LLM-based Agents" (TechRxiv, not peer-reviewed — distinct from tool *error*: the tool may have succeeded or failed and the model invents the outcome); and an ICML 2026 **workshop** on "Failure Modes in Agentic AI: Reproducible Triggers, Trace Diagnostics, and Verified Fixes" (non-archival, since it signals an active community on exactly this topic).

**Rollback/recovery items (surfaced; details partly unverified):** ChronoMem (version control + *semantic* rollback for agent **memory** — note memory rollback ≠ effect rollback, keep them separate); "From Faulty Memories to Corrected Actions: Dependency-Guided Rollback Repair" (arXiv 2608.10502); REVISE (stepwise rollback for agent workflows); Belayer (arXiv 2608.14635 — fault tolerance for agentic *RL training*, a different problem); Trivium (arXiv 2606.04421, secondary description of SagaLLM's substrate). Also **Tool Re-selection** work on choosing alternative tools/APIs after execution failure (arXiv 2605.06737).

---

# Section C — Agents under network disruption / intermittent connectivity

**Bottom line: the framing exists in industry, the mechanisms exist in durable-execution products, the benchmarks exist for tool faults — but the intersection (a communication fault model injected into agent tool-call execution, in a wireless/disaster setting) was not found.**

## C.1 Network disruption / intermittent connectivity (agent execution)

**Google Cloud — "Disconnected but resilient: Securing agentic AI at the extreme edge"** `[IND]` — March 17, 2026; **fetched and read directly.**
Argues agents at the extreme edge must survive loss of internet connectivity. The proposed mechanism is **graceful degradation of the *model***: frontier model (Gemini) in cloud when bandwidth allows → distilled local model (Gemma) on high-power edge devices when severed → TinyML micro-models on extreme-edge coin-cell IoT sensors. Names "inference loss."
**Why it matters (high value, and a precise differentiation opportunity):** The strongest evidence the *problem framing* is already circulating in industry — and simultaneously the cleanest proof that the *solution* being pursued is **capability degradation, not execution-semantics correctness**. Google's answer to disconnection is "use a smaller model," not "make the tool call idempotent / reconcile the side effect." That gap is exactly the paper's contribution, stated by the most authoritative possible source.
https://cloud.google.com/transform/disconnected-but-resilient-securing-agentic-ai-at-the-extreme-edge/

**Google — "Agent Executor, Google's distributed Agent Runtime"** + `google/ax` `[IND]` `[FLAG]`.
Open-sourced distributed agent runtime ("An open source distributed agent runtime"), with a companion "Agent Substrate."
**Why it matters:** Prior art for the *runtime* half, but it addresses **host/process distribution and durability**, not radio-level partial failure. The gap between "distributed runtime" and "communication-partial-failure-aware runtime" is where the paper can live. `[FLAG]` the open-source date is from a commit message; verify from first-party sources.
https://cloud.google.com/blog/products/ai-machine-learning/agent-executor-googles-distributed-agent-runtime · https://github.com/google/ax

**Cloudflare Agents — recovery harness** `[IND]`.
Documents "**bounded chat recovery**, the **stream-stall watchdog**, **repairing interrupted tool calls**, and stability detection."
**Why it matters (important honesty check):** "Repairing interrupted tool calls" is the disconnect-mid-call mechanism, and a "stream-stall watchdog" is a head-of-line-blocking mechanism — **shipped in production by a major vendor**. The paper must acknowledge that industry runtimes already implement its §10 mechanisms, and differentiate on the *communication fault model*, not on the mechanisms.
https://developers.cloudflare.com/agents/harnesses/think/recovery/index.md

**Ably — "WebSocket reconnection in AI agents: transport recovery vs. session recovery"** `[IND]`.
Distinguishes recovering the *transport* (socket reconnect) from recovering the *session* (agent execution state), arguing agents fail when only the former is handled.
**Why it matters:** The paper's "replay after recovery" problem in industrial terms.
https://ably.com/blog/websocket-reconnection-timeouts-ai-agents

**"Language Model Teams as Distributed Systems"** `[P]` — arXiv 2603.12229.
Frames LLM teams explicitly as distributed systems (invoking Amdahl's Law), discussing asynchronous message passing, bursty interactions, and long execution horizons.
**Why it matters:** The strongest *conceptual* precedent for the paper's methodological move (treating agent systems through a distributed-systems lens) — which means it is also prior art on **the framing itself**. Cite it.
https://ar5iv.labs.arxiv.org/html/2603.12229

**`bradygin/ConsensusLLM`** `[IND]` — "a distributed fault-tolerant LLM service using Multi-Paxos consensus, ensuring continuous AI operations through server failures and network partitions."
**Why it matters:** Direct evidence network partition is being addressed for LLM serving — but at the **model-serving/replication layer**, not the **agent tool-execution layer**. Useful boundary marker.
https://github.com/bradygin/ConsensusLLM/

**Sierra — "Preserving agent behavior while serving LLMs reliably"** `[IND]` — model-provider failover, *not* tool/link failure. Good for showing the literature conflates the two. https://sierra.ai/fr/blog/model-failover
**Gremlin — "The hidden reliability risks in your agentic AI workflows"** `[IND]` — chaos-vendor framing of agent tool unreliability. Motivation only. https://www.gremlin.com/blog/the-hidden-reliability-risks-in-your-agentic-ai-workflows

## C.2 Offloading to intermittently connected / edge devices

Key point: this literature optimises **where computation goes**, not **what happens when the call's outcome is unknown**.

- **"Cached Model-as-a-Resource: Provisioning LLM Agents for Edge Intelligence in Space–Air–Ground Integrated Networks"** — IEEE doc 11352984; arXiv 2403.05826 `[FLAG]` venue probable (IEEE/ACM ToN 2026) but not fully verified. Placement/caching of LLM agents across a satellite-terrestrial intermittently connected network. https://ieeexplore.ieee.org/abstract/document/11352984/references
- **"Robust dependency-aware task offloading for mobile edge computing in low network scenarios using multi-agent DRL"** — *Ad Hoc Networks* 2026, DOI 10.1016/j.adhoc.2026.104179. Dependency-aware offloading explicitly robust to poor networks — the classical-MEC analogue of the paper's claim, with no LLM layer and no unknown-outcome notion. https://www.sciencedirect.com/science/article/abs/pii/S1570870526000454
- **"A Resilient Edge-Cloud Orchestration Framework for Sustaining Tactical Intelligence Continuity in LLM-Enabled V2X Systems"** — IEEE doc 11534623, 2026 (IEEE Access per DOI 10.1109/access.2026.3696386). Handles "temporal desynchronization arising from varying transmission delays." **Closest published systems work**; vehicular/tactical rather than disaster LoRa/DTN, so the application domain remains open. https://ieeexplore.ieee.org/document/11534623
- **"Resilient Edge Intelligence: Integrating Swarm Logic with Lightweight Agents and Localised SLMs"** — IEEE doc 11541396. Localised SLMs as the answer to link death — a plausible **baseline** the paper must beat or subsume. https://ieeexplore.ieee.org/abstract/document/11541396
- **"Compact LLM Deployment and World Model Assisted Offloading in MEC"** — arXiv 2602.13628. World models as a place to represent link-state uncertainty. https://arxiv.org/html/2602.13628v1
- **"LLMs over Networks: Collaborative Intelligence under Resource Constraints"** — arXiv 2605.08626. https://arxiv.org/pdf/2605.08626v1
- **"Fault-Tolerant Aware Task Offloading Based on RL in MEC"** `[FLAG]` and **"Multi-Turn Reasoning LLMs for Task Offloading in MEC"** `[FLAG]` — establish that fault-tolerant offloading is an existing thread. Sharpen: fault-tolerant *offloading policy* ≠ fault-tolerant *agent execution semantics*. https://www.semanticscholar.org/paper/Fault-Tolerant-Aware-Task-Offloading-Based-on-in-Long-Rao/889d98b5a715d0b2ac1cf781832d4f5388ff3ebe

## C.3 Mother papers — tool-execution assumptions

> `[FLAG]` **Verdicts below are inferred from abstracts/titles/snippets. For α³-Bench, 6GAgentGym, WirelessAgent++ and WirelessBench I read full abstracts directly (marked "[abstract read]"). Where a verdict is snippet-only it says so.**

**TopoLLM — "TopoLLM: LLM-driven adaptive tool learning for real-time emergency network topology planning"**
*Digital Communications and Networks* 2026; DOI 10.1016/j.dcan.2025.10.002. `[V-REV]` (venue confirmed via DOI/journal record).
LLM-driven adaptive tool learning that plans emergency communication network topology in real time.
**Tools first-class? NO.** The emergency *network* is the object being planned; the agent's own communication with its tools is not modelled as unreliable. **This is the paper's cleanest gap.**
https://www.sciencedirect.com/science/article/pii/S2352864825001476

**6GAgentGym — "Tool Use, Data Synthesis, and Agentic Learning for Network Management"** `[P]` — arXiv 2603.29656, Mar 2026. **Abstract read directly.**
Closed-loop environment with **42 typed tools** whose *effect classification distinguishes read-only observation from state-mutating configuration*, backed by a learned Experiment Model calibrated on NS-3 data; 6G-Forge bootstraps training trajectories with execution verification; SFT + RL lets an 8B model approach GPT-5 on 6GAgentBench.
**Tools first-class? PARTIAL — and this is important.** It **already distinguishes read-only vs. state-mutating tools**, which is exactly the context doc's §8 requirement ("read-only tool、state-mutating tool、side-effect tool 要分开，因为恢复语义不同"). **The paper cannot claim the read-only/state-mutating distinction as novel.** What it still lacks: the *recovery semantics* dimension — read-only vs. mutating is used for **learning/reward purposes**, not for **retry, replay, or compensation decisions**. Differentiate precisely there. Also note the environment is a **learned model of NS-3**, i.e. tools are assumed available and deterministic.
https://arxiv.org/abs/2603.29656

**WirelessAgent++ — "Automated Agentic Workflow Design and Benchmarking for Wireless Networks"** `[P]` — arXiv 2603.00501, Feb 2026. **Abstract read directly.**
Automates agentic workflow *design* via domain-adapted MCTS over modular operators; contributes **WirelessBench** (WCHW / WCNS / WCMSA covering knowledge reasoning, code-augmented tool use, multi-step decision-making).
**Tools first-class? NO.** The contribution axis is workflow *structure/search* plus benchmarking. Capability benchmark, no failure injection.
https://arxiv.org/abs/2603.00501

**α³-Bench — "A Unified Benchmark of Safety, Robustness, and Efficiency for LLM-Based UAV Agents over 6G Networks"** `[P]` — arXiv 2601.03281, Jan 2026. **Abstract read directly.**
113k conversational UAV episodes; missions adapt to "fluctuating network slices, **latency, jitter, packet loss, throughput**, and edge load variations"; dual action layer (tool calls + agent-to-agent); composite α³ metric with six pillars including **Tool Consistency** and **Network Robustness**; 17 LLMs.
**Tools first-class? PARTIAL — the most important ambiguity.** It **does model network impairment (including packet loss)** — but as *environment conditions the agent reasons about and is scored on*, not as faults that corrupt the agent's own tool-invocation semantics mid-call. No idempotency, no duplicate-side-effect, no unknown-outcome modelling appears. **Highest-priority full-text verification.**
https://arxiv.org/abs/2601.03281 · https://github.com/maferrag/AlphaBench

**WirelessBench — "A Tolerance-Aware LLM Agent Benchmark for Wireless Network Intelligence"** `[P]` — arXiv 2603.21251, Mar 2026. **Abstract read directly. FALSE ALARM — this one is safe.**
"Tolerance-aware" does **not** mean tolerance to network impairment. It means **tolerance-aware *scoring***: catastrophic-error detection (e.g. dB vs. dBm unit confusion), tolerance in grading rather than exact match, plus tool-necessary ray-tracing tasks and CoT-traceable items. Findings: GPT-4o 68% vs. tool-integrated agent 84.64%; 23% of errors are catastrophic failures invisible to exact-match metrics.
**Why it matters anyway (cite it):** It is the sibling benchmark to WirelessAgent++ (same WCHW/WCNS/WCMSA tiers) and its **"catastrophic error invisible to exact-match metrics"** result is a *gift* — it independently establishes, in the wireless-agent setting, that **benchmark scores hide severe failures**. That is precisely the paper's motivation for side-effect-correctness metrics rather than task-success metrics.
https://arxiv.org/abs/2603.21251

**ICG-Restore — "Intent-Constrained, Graph-Enhanced LLM Planning with Minimal-Edit Repair for Post-Disaster Emergency Communication Recovery"**
*AI* (MDPI) 2026, 7(8), 294; DOI 10.3390/ai7080294. `[V-REV]` (venue/year verified).
LLM planning for post-disaster emergency communication **recovery** with intent constraints, graph enhancement, and minimal-edit repair.
**Tools first-class? NO.** "Repair" is repair of the *network plan*, not the agent's transaction log. **Near-miss warning:** a reviewer will ask whether minimal-edit repair already handles post-outage reconvergence — differentiate explicitly.
https://www.ebiotrade.com/newsf/2026-8/20260804081427522.htm

**WirelessAgent — "WirelessAgent: Large language model agents for intelligent wireless networks"** `[FLAG]` venue unverified (IEEE doc 11503159). Benchmark framing is task completion on wireless tasks; no partial-failure semantics. https://ieeexplore.ieee.org/document/11503159

**ComAgent — "ComAgent: Multi-LLM based Agentic AI Empowered Intelligent Wireless Networks"** `[P]`/`[FLAG]` — arXiv 2601.19607; IEEE Wireless Communications attribution **unverified**. Multi-LLM cooperating on wireless control. No partial-failure semantics — but a **multi-LLM design is *more* exposed** to message-loss/unknown-outcome, making it a good motivating example. https://www.emergentmind.com/papers/2601.19607

**Self-healing RAN/core agents (distinct papers, do not conflate)** `[FLAG]`:
- "A Feasibility-Shielded Agentic AI Framework for 6G Self-Healing Core Networks" — IEEE 11577510. A **shield** is *pre-execution admissibility*, i.e. a runtime mechanism the thesis predicts. https://ieeexplore.ieee.org/document/11577510/references
- "Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control" — **"deterministic and auditable"** is notable: determinism/auditability is what makes unknown-outcome tractable. Worth reading. https://www.semanticscholar.org/paper/Agentic-Open-RAN%3A-A-Deterministic-and-Auditable-for-Li-Xu/b39a1b23de07c1705f658631f851d05f50d6f5b0
- "LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience" — TechRxiv, IEEE 11152722. https://www.techrxiv.org/doi/full/10.36227/techrxiv.174284755.59863143/v1
- "GO-MAF: Human-in-the-Loop Multi-Agent Framework for Self-Healing 5/6G Network Operations" — human escalation as fallback, not partial-failure semantics. https://www.semanticscholar.org/paper/GO-MAF%3A-A-Human-in-the-Loop-Multi-Agent-Framework-5-An-Jia/d573aa5a9a507b0daa951cf90ef2236c2be85110
- "AgentRAN: An Agentic AI Architecture for Autonomous Control of Open 6G Networks" — IEEE 11519587. https://ieeexplore.ieee.org/document/11519587/keywords

**Surveys / positioning** `[FLAG]` unless noted:
- "LLM-Powered Agentic AI for 5G/6G Networks: A Tutorial and Survey" — arXiv 2607.16066. Most likely place to find whether the community has *named* the partial-failure problem. https://www.alphaxiv.org/abs/2607.16066
- "6G Needs Agents: Toward Agentic AI-Native Networks" — arXiv 2605.01546. States operational decisions "must explicitly account for uncertainty, adversarial risk, and cross-domain trust boundaries" — the closest a survey comes to naming this concern. https://arxiv.org/pdf/2605.01546v1
- "Towards Resilient and Autonomous Networks: A BlueSky Vision on AI-Native 6G" — arXiv 2605.21395; **ACM SIGKDD 2026** `[V-REV]`. https://dl.acm.org/doi/abs/10.1145/3770855.3818662
- "6G-Bench: An Open Benchmark for Semantic Communication and Network-Level Reasoning" — IEEE 11474618. https://ieeexplore.ieee.org/document/11474618/authors
- "Small Models, Big Impact: Tool-Augmented AI Agents for Wireless Network Planning" — arXiv 2601.13843; probable *IEEE Communications Magazine* 2026 `[FLAG]`. https://papers.cool/arxiv/2601.13843

## C.4 Adjacent systems work that may already study exactly this

> **Read these four before finalising the novelty claim.**

**"Rollback Is Not Undo: Path-Dependent Failures in LLM-Arbitrated Network Control"** — IEEE document 11571400. `[FLAG]` venue/year and abstract unverified (paywalled).
The title asserts the paper's core mechanism point — that rollback ≠ undo under path dependence — **inside the paper's own domain (LLM-arbitrated network control)**. Discovered independently during reconnaissance; not on the context doc's lead list.
**Why it matters (single most dangerous prior work found):** If its content matches its title, it substantially pre-empts the paper's "naive replay/recovery is wrong" argument in the networking setting. **Verify first.**
https://ieeexplore.ieee.org/document/11571400

**"Large Language Models for Agentic NetOps and AIOps: Architectures, Evaluation, and Safety"** `[P]` — arXiv 2605.12729.
Taxonomy of tool privilege levels incl. "Planner–executor (write-limited)"; defines closed-loop operation as integrating "detection, diagnosis, mitigation, and **recovery verification**."
**Why it matters:** "**Recovery verification**" is very close to the paper's verify-before-retry thesis, and the *privilege-level* taxonomy overlaps the paper's `authority` / `side_effect_class` primitives. Cite and differentiate.
https://arxiv-org.ezproxy.obspm.fr/html/2605.12729v2

**"Executor-Side Progressive Risk-Gated Actuation for Agentic AI in Wireless Supervisory Control"** `[P]` — arXiv 2605.02697 (Surrey 5G/6G Innovation Centre).
Gates actuation **at the executor** based on divergence between intent and local state; gate reasons named RISK-DIVERGENCE, LOCAL-CONFLICT, PLANNER-UPGRADE.
**Why it matters:** Executor-side gating under conflict/divergence *is* a runtime mechanism for agent execution in wireless control. Second-highest-priority read.
https://export.arxiv.org/pdf/2605.02697

**"Engineering Trustworthy Agentic AI for Critical Systems"** `[P]` — arXiv 2607.18548, Jul 2026. **Abstract read directly.**
Survey treating trustworthiness as a first-class engineering property across safety/robustness/transparency/accountability/privacy, mapped onto an agentic assurance workflow; examined across **power systems, autonomous vehicles/robotics/UAVs, HPC, and communication networks**.
**Why it matters (high value):** The best umbrella citation for the paper's domain ("critical systems") and it explicitly covers communication networks. Useful for framing, and it identifies "shared failure modes and domain-specific gaps" across domains — which is the space the paper is filling.
https://arxiv.org/abs/2607.18548

**FogROS2-FT: Fault Tolerant Cloud Robotics** — arXiv 2412.05408; IEEE doc 10802613. `[FLAG]`.
**FogROS2-PLR: Probabilistic Latency-Reliability for Cloud Robotics** — IEEE doc 11127588.
**Why they matter:** The robotics/cloud-offload community has *already* built fault tolerance and probabilistic latency-reliability for remote execution over unreliable links. This is the **strongest adjacent prior art for "offloaded action execution under link unreliability"** — cite it, and differentiate (robotics fog computing for ROS 2 actions, not LLM-arbitrated tool calls with side-effect-class-dependent recovery).
https://arxiv.org/abs/2412.05408 · https://ieeexplore.ieee.org/abstract/document/11127588

**"Agentic AI for Robot Control: Flexible but still Fragile"** — AAAI Spring Symposium (AAAI-SS) `[V-REV]`; arXiv 2602.13081.
Explicitly lists "**asynchrony and event handling**" as a limitation.
**Why it matters:** Independent, peer-reviewed confirmation that asynchronous action execution is an unsolved fragility in embodied agents. Strong supporting citation from outside the LLM-agent-benchmark literature.
https://ojs.aaai.org/index.php/AAAI-SS/article/view/42578

**"Proof of Execution: Runtime Verification for Governed AI Agent Actions"** `[P]` — arXiv 2607.05397. Runtime verification that a governed agent action actually ran — directly relevant to closing the unknown-outcome gap by *evidence*, not by assumption. https://arxiv.org/abs/2607.05397

**"AgentSight: System-Level Observability for AI Agents Using eBPF"** `[FLAG]` — kernel-boundary observation of agent behaviour. Methodological enabler: observing at the syscall boundary is how a runtime can *know* whether a side effect landed when the ACK was lost. https://www.semanticscholar.org/paper/AgentSight%3A-System-Level-Observability-for-AI-Using-Zheng-Hu/0e465e7e8502cc8ff9c8272d1cc74ec034353ecb

**"Approved Too Late: Verdict Staleness in LLM-Guarded Self-Adaptive Systems"** — **ACSOS 2026, Main Track** `[V-REV]`.
Directly about **staleness of LLM verdicts** in self-adaptive systems.
**Why it matters (high value):** This is prior art for the paper's **stale-observation** mechanism, in the *self-adaptive-systems* community, peer-reviewed, and it names the exact phenomenon (an approval/verdict that is stale by the time it is acted on). **Cite it, and connect to the self-adaptive-systems literature** — which is the natural academic home for "runtime adapts under uncertainty" and which the context doc currently does not mention at all.
https://2026.acsos.org/details/acsos-2026-papers/5/Approved-Too-Late-Verdict-Staleness-in-LLM-Guarded-Self-Adaptive-Systems

**Self-adaptive systems (SAS) literature — a community the paper should engage:**
- **"Uncertainty in Self-adaptive Systems: A Research Community Perspective"** — *ACM Transactions on Autonomous and Adaptive Systems* `[V-REV]`. Establishes uncertainty as the central SAS concern with an established taxonomy of uncertainty sources and resolution techniques. https://dl.acm.org/doi/full/10.1145/3487921
- **"Software Engineering for Self-Adaptive Robotics: A Research Agenda"** — arXiv 2505.19629. https://arxiv.org/html/2505.19629v1

### Specialized disruption tooling found (verification status varies)

**"FreshCtx: pre-action freshness protection for MCP tools at `tools/call`"** `[IND]` — an MCP community proposal (discussion #852) for pre-action freshness protection at the tool-call boundary.
**Why it matters:** Evidence that the **agent tool-protocol layer is only now acquiring freshness semantics** — and that as of this reconnaissance it lives in a discussion thread, not a spec. Good "the gap is recognised at the protocol level but not standardised" citation.
https://github.com/orgs/modelcontextprotocol/discussions/852

**Model Context Protocol — Cancellation; SEP-1539 "Timeout Coordination"** `[IND]` `[V-URL]`.
MCP's draft spec documents cancellation, and there is an open SEP for **timeout coordination** across MCP operations.
**Why it matters (high value, and a strong novelty argument):** The dominant agent tool protocol **does not yet define timeout / outcome-unknown semantics** — it is an open proposal. That is a *protocol-level* statement of the paper's gap, from the standard body itself.
https://modelcontextprotocol.io/specification/draft/basic/patterns/cancellation · https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1539

## C.5 Disaster-response / crisis-informatics related work (added in revision)

**Why this subsection exists.** An earlier draft of this report omitted the disaster-domain related work, which is a real gap: a paper titled *Disruption-Tolerant Runtime for Tool-Using Agents in **Emergency Communication Networks*** must engage the crisis-informatics and emergency-response agent literature directly, and must show that those systems do not model communication-induced partial failure. Items below were verified live (`[V-URL]`) unless flagged.

**"Agentic AI for Crisis Informatics: A Multi-Agent Framework for Scalable and Reliable Disaster Communication"** — **AMCIS 2026 Proceedings**, SIG ODIS track. `[V-URL]` (page resolves; title confirmed from the AIS eLibrary record).
A multi-agent framework whose title claims **"Reliable Disaster Communication."**
**Why it matters (high priority for the paper):** This is the closest **venue-verified** work in the paper's own application domain, and it makes a *reliability* claim. It must be cited and differentiated explicitly — otherwise a reviewer will reasonably ask why the paper's reliability contribution is distinct from it. Note the framing is multi-agent coordination for scalable disaster comms, **not** tool-execution semantics under link failure.
https://aisel.aisnet.org/amcis2026/sig_odis/sig_odis/6/

**"CLEAR-Command: Coordinated Listening, Extraction, and Allocation for Emergency Response with Large Language Models"** — **NAACL 2025 System Demonstrations** `[V-URL]`, title confirmed from ACL Anthology.
LLM system for emergency response covering listening, extraction, and resource allocation.
**Why it matters:** A peer-reviewed, citable emergency-response LLM system — establishes the domain's existing baseline. It addresses coordination and information extraction, not tool-call failure semantics.
https://aclanthology.org/2025.naacl-demo.3/

**"SentinelAI: A Multi-Agent Framework for Structuring and Linking NG9-1-1 Emergency Incident Data"** `[P]` — arXiv 2603.24856. Abstract read directly.
Data integration/standardization framework for Next-Generation 9-1-1, treating incident data as "a continuous stream of operational updates, where new facts are integrated immediately to provide a timely and unified view of an evolving incident."
**Why it matters:** The **"continuous stream of operational updates" / "timely and unified view of an evolving incident"** framing is a *freshness and consistency* problem stated in emergency-domain language — i.e. it is adjacent to the paper's §10.5 stale-state guard, from the emergency side. Good citation for domain motivation; it does not model tool-execution semantics.
https://arxiv.org/abs/2603.24856

**"Scalable UAV Multi-Hop Networking via Multi-Agent Reinforcement Learning with Large Language Models"** — arXiv 2505.08448 `[P]`; an IEEE Transactions on Mobile Computing version is probable (IEEE doc 11417708) `[FLAG]`. **Abstract read directly.**
Opening line, verbatim: *"In disaster scenarios, establishing robust emergency communication networks is critical, and unmanned aerial vehicles (UAVs) offer a promising solution to rapidly restore connectivity."* Proposes MRLMN, integrating MARL and LLMs to jointly organize UAVs into multi-hop networks.
**Why it matters (high value):** This is **squarely the paper's deployment scenario** — post-disaster UAV relay networks restoring connectivity — and it is LLM-driven. It is the strongest evidence that the paper's *setting* is already active research, which both validates the domain choice and means the paper must differentiate on **execution semantics rather than network organization**: MRLMN decides how to *form* the network, not what happens when an agent's tool call to a UAV times out with unknown outcome. Also note it is the natural citation for why UAV relay is even in scope.
https://arxiv.org/abs/2505.08448

**"TeleResilienceBench: Quantifying Resilience for LLM Reasoning in Telecommunications"** — arXiv 2605.09929 `[P]`. Abstract read directly.
Introduces **"reasoning resilience"**: *"a model may inherit partially completed reasoning from a prior step, an upstream agent, or its own earlier generation, and must continue that reasoning even when it is already going wrong."* Seven telecom sub-domains from the GSMA Open-Telco LLM suite; instances constructed by collecting failures.
**Why it matters (important differentiation, and a near-miss):** This is **partial failure propagating through a multi-step agent pipeline, in the telecom domain** — conceptually very close to the paper's concern. **But it operates at the *reasoning* layer, not the *tool-execution* layer**: the question is whether a model can reason onward from already-corrupted intermediate reasoning, not whether an action's (side) effect is unknown. Cite it and draw that line precisely — the distinction between *reasoning* resilience and *effect* resilience is exactly the axis the paper occupies (and the same axis that separates VIGIL from the proposed runtime).
https://arxiv.org/abs/2605.09929

**Other disaster-domain agent systems found** `[FLAG]` — IEEE pages returned bot-challenge responses (HTTP 202) rather than confirmable content, so these are **venue/year unverified** and should be confirmed before citation:
- "Collaborative GenAI Agents for Emergency Response: A Decentralized, Explainable Multi-Agent Framework" — IEEE doc 11481226. Decentralization implies partition exposure, but the retrieved framing is explainability. https://ieeexplore.ieee.org/document/11481226
- "ResQConnect: Agentic AI for Human-Centered Disaster Response Systems" — IEEE doc 11318466. https://ieeexplore.ieee.org/document/11318466
- "LLM and MCP Enabled AI Agent for Autonomous Multi-Lingual Alerts for Coastal Communities" — IEEE doc 11362367. Notably uses **MCP** for tool access in an alerting system, i.e. a concrete disaster-domain tool-calling agent. https://ieeexplore.ieee.org/abstract/document/11362367
- "Large language model enabled DRL for trajectory optimization and resource allocation in UAV-assisted emergency communication networks" — ScienceDirect S1874490726001862. https://www.sciencedirect.com/science/article/abs/pii/S1874490726001862
- Federated Edge-AI + Digital Twin IoT for landslide prediction / mountain early warning — IEEE docs 11548349 and 11381311. Relevant as the *sensing* substrate for the paper's §7 mountain-monitoring datasets. https://ieeexplore.ieee.org/document/11548349
- Leidos + NVIDIA disaster-response agents — vendor case study, not research. https://www.nvidia.com/en-gb/case-studies/leidos-uses-ai-agents-to-improve-disaster-response/

**Net assessment of C.5.** The disaster-response agent literature is active and venue-visible (NAACL 2025, AMCIS 2026, IEEE), and the UAV-relay emergency-networking literature is directly the paper's setting. **None of it was found to model communication-induced partial failure of the agent's own tool execution.** The disaster papers address coordination, explainability, data structuring, alerting, and network organization; TeleResilienceBench addresses reasoning-layer resilience. This *strengthens* Gap 1 and Gap 2 rather than threatening them — but these citations are **required related work**, not optional, and the paper's related-work section is incomplete without them.

---

# Mechanisms that are NOT novel

The context doc's §13 already anticipates this, but the reconnaissance shows the overlap is **larger** than §13's list of six. Below, each proposed mechanism is mapped to the canonical source that owns it. **None of these can be a contribution.**

| Context doc mechanism (§3 / §9 / §10) | Owned by | Status |
|---|---|---|
| **§10.1 operation state machine** / §9 lifecycle states | Saga (1987); Beldi/OSDI 2020; Temporal & Restate docs; IEEE 11638700 "Durable Execution for AI Agents" | **Not novel.** §13 already concedes. Note this is standard durable-execution design. |
| **§10.2 idempotency-aware retry** | Birrell & Nelson (1984); Helland, ACM Queue (2012); KIP-98; **arXiv 2608.02645 publishes it verbatim for agents** | **Not novel, and already published *for LLM agents*.** Highest-priority cite. |
| **§10.3 lease / lifecycle-aware capability registry** | Gray & Cheriton, *Leases* (1989); Chandra & Toueg (1996); φ-accrual detector (2004) | **Not novel.** Leases are the canonical mechanism; graded suspicion (φ) is the improvement to adopt. |
| **§10.4 bounded + fair replay** | Demers/Keshav/Shenker fair queueing (1989); Chandy & Lamport (1985); Elnozahy et al. survey (2002); MillWheel low watermarks (2013); **arXiv 2606.01416 recovery-budget sweep** | **Not novel** — both "bounded" and "fair" have canonical owners. |
| **§10.5 stale-state / freshness guard** | Terry et al. session guarantees (1994); **Age of Information** (Kaul et al. 2012); **arXiv 2606.01416 "stale context"**; **ACSOS 2026 verdict-staleness**; MCP FreshCtx proposal | **Not novel.** The AoI literature is the rigorous version. |
| **§10.6 reconcile / verify-before-retry** | **arXiv 2608.02645 (verify-before-retry + idempotency keys, for agents)**; **arXiv 2605.23311 DART (admissible restore points)**; **arXiv 2603.20625 ACRFence (replay-or-fork)**; CRITIC (ICLR 2024); arXiv 2605.12729 "recovery verification"; Kubernetes level-triggered reconciliation `[IND]` | **Not novel — this is the most occupied mechanism of the six.** |
| §3 `deadline` on ToolInvocation | AWS Builders' Library timeouts/retries/backoff; MCP SEP-1539 | Not novel. |
| §3 `idempotency_key` | Helland (2012); Stripe idempotency keys `[IND]` | Not novel. |
| §3 `heartbeat` / lease for online status | Chandra & Toueg; Gray & Cheriton; φ-accrual | Not novel. |
| §3 canonical session / event log / audit | Chandy & Lamport; Beldi; Temporal event history; DeltaBox (sandbox checkpoint/rollback) | Not novel. |
| §3 read-only vs **state-mutating vs side-effect tool separation** | **6GAgentGym (arXiv 2603.29656) already distinguishes read-only observation from state-mutating configuration** | **Not novel as a taxonomy** — only the *recovery semantics* bound to it can be claimed. |
| §3 `authority` / permission bound to actions | arXiv 2605.12729 privilege-level taxonomy; ACRFence "Authority Resurrection" | Not novel as a concept. |
| §9 `compensating` state, rollback | Garcia-Molina & Salem (1987); Azure Saga pattern; Elnozahy "output commit" | Not novel — and note compensation is *impossible* once output is committed. |
| §9 "retry budget exhausted" | Google SRE adaptive throttling / retry budgets; arXiv 2608.25403 Adaptive Retry Budgeting | Not novel. |
| §9 head-of-line blocking / starvation | Demers et al. fair queueing (1989); **Autellix (arXiv 2502.13965) already names head-of-line blocking in LLM agent serving** | **Not novel.** Autellix is the agent-specific citation. |
| §9 "long-running workflow, agent process / coordinator restart" | Candea & Fox crash-only software (2003); Gray & Lamport (2006); Temporal/DBOS | Not novel. |
| §9 "network partition → state divergence" | FLP (1985); Chandy & Lamport (1985); Bailis et al. HAT (2014) | Not novel. |
| §12 metrics (completion, recovery latency, duplicate side effects, stale decisions, starvation, progress/liveness) | τ-bench pass^k; ToolMaze PRR; ReliabilityBench R(k,ε,λ) + metamorphic relations; arXiv 2602.16666 12-metric framework | **Not novel as metrics.** Adopt existing ones. |
| The **overall framing** "agents should be treated as distributed systems / runtime semantics matter" | Waldo et al. (1994); **"Language Model Teams as Distributed Systems" (arXiv 2603.12229)**; **"Model or Harness?" (arXiv 2607.28802)**; **"Self-Healing Agentic Orchestrators" (arXiv 2606.01416)**; SAS uncertainty literature | **Not novel.** This is the most important concession: the *thesis* is already stated in the literature. |
| The claim "**fault injection into agents**" as a methodology | ToolMaze, ReliabilityBench, AgentChaos, ChaosLLM, AgentDisruptBench, ToolMisuseBench, WAREX, OperAID, arXiv 2407.00125 survey | **Not novel, and a claim that "no one injects faults into agents" is FALSE and easily refuted.** |

**Explicit warning to the authors.** Any sentence of the form *"we are the first to apply X to LLM agents"* for X ∈ {idempotency, verify-before-retry, retry budgets, checkpointing, staleness guards, fair scheduling} is refutable from citations in this document. So is *"no existing benchmark injects tool failures."*

---

# Real gaps we could still claim

Ranked by how defensible they are against the evidence actually gathered. **All are phrased as "no positive hit found," not "proven absent."**

### Gap 1 — Transport-layer (not tool-API-layer) fault injection into agent tool calls
**The strongest and most load-bearing gap.** Every agent fault-injection harness found injects at the **tool-API / HTTP semantic layer** (timeouts, 429s, malformed output, schema drift, partial responses, stale context), the **context/instruction layer**, or the **infrastructure layer** (Kubernetes pods). **No positive hit** was found for a harness that overlays a **radio/channel/DTN fault model** — packet loss as a channel process, ACK loss, node disconnect mid-call, store-and-forward replay after reconnection — onto an agent's tool invocations.
**Supporting citations to contrast against:** AgentDisruptBench's 20-type taxonomy (tool-call level) · AgentChaos injecting at the shared **HTTP** interface · ReliabilityBench (application faults) · ToolMaze (tool anomalies).
**Phrase as:** *"We are not aware of a benchmark that overlays a communication-channel fault model onto agent tool execution; the surveyed fault catalogues operate at the tool-API, context, or infrastructure layer."*
**Risk:** α³-Bench models packet loss/jitter/throughput; it is the closest to crossing this line. **Read it in full.**

### Gap 2 — Outcome-ambiguous faults as a *first-class injected class*
Distinct from Gap 1 and arguably cleaner: **no benchmark found injects "the action ran but you cannot tell"** as a fault class. AgentDisruptBench's `timeout` class is a *visible* timeout; ToolMaze's faults all admit an alternative path (i.e. the agent can tell the tool failed). **Unknown-outcome and duplicate-delivery appear only as *semantic concerns* in transactional/recovery work (SagaLLM, DART, ACRFence, Atomix, Restate durable webhooks) — never as *injected fault classes* with a measured failure rate.**
**This is the sharpest gap because it is a *taxonomy* gap, not a coverage gap:** the field has visible faults and ambiguous *reasoning*, but not ambiguous *effects*. The paper's §9 list (RPC sent then node drops; action executed but ACK lost; timeout then blind retry duplicating a side effect) is *exactly* the missing class, and ACRFence supplies peer-reviewable evidence that this class causes irreversible real-world harm.
**Phrase as:** *"Existing benchmarks inject failures whose occurrence is observable. We inject failures whose occurrence is epistemically unavailable to the agent, and measure the resulting duplicate side effects."*

### Gap 3 — Binding recovery semantics to capability lifecycle in a disaster network
The context doc's §8 requirement — separate read-only / state-mutating / side-effect tools *because recovery semantics differ* — is genuinely under-served. **6GAgentGym makes the read-only/state-mutating split but uses it for learning, not recovery.** No positive hit found couples a tool's **side-effect class** and **authority** to its **recovery policy** under **degraded capability availability** (degraded → timeout → unavailable → recovering).
This is where the paper's §3 primitives (`side_effect_class`, `authority`, `availability`, capability lifecycle) can be *combined* into something not present: **a recovery policy that is a function of (side-effect class × availability state × freshness/age × mission criticality).** The individual axes are all known; the *product* is not, and it is genuinely emergency-communication-specific because it forces mission criticality and energy into the recovery decision.
**Risk:** arXiv 2605.02697 (executor-side risk-gated actuation) and arXiv 2605.12729 (privilege levels) are close on parts of this. Read both.

### Gap 4 — A communication-specific partial-failure *distribution* from real disaster traces
The context doc's strongest structural asset (§7 datasets: FEMA TEMPO, ITU Disaster Connectivity Map, SitkaNet, avalanche LoRa, LoRaWAN metadata) is that **its fault model can be trace-driven from real disaster telemetry** rather than synthetic. **No positive hit** found for any agent benchmark whose fault process is derived from measured link/outage traces.
This is a real methodological contribution: the fault distribution is *empirically grounded*, and the outage→degradation→recovery lifecycle is *real*, not injected. AI-assisted: this is distinctive and hard to refute.
**Caveat:** trace-driven evaluation of *distributed systems* is old; the contribution is trace-driven **agent execution semantics**, and it should be stated that way. Also verify the §7 datasets actually expose link-level traces (the context doc itself flags SitkaNet and the landslide LoRaWAN set as uncertain on this).

### Gap 5 — The bridge between two literatures that don't cite each other
The cleanest *positioning* gap, and it is well supported: **durable-execution semantics live in systems products and database papers** (Temporal, DBOS, Restate, Beldi, SagaLLM, Atomix), **fault-injection evaluation lives in the ML/agent-benchmark community** (ToolMaze, ReliabilityBench, AgentChaos, AgentDisruptBench), and **wireless-agent benchmarks live in the communications community** (α³-Bench, WirelessBench, WirelessAgent++, 6GAgentGym). **No positive hit found for work that bridges all three.**
**Phrase as:** *"Mature execution semantics are available in systems; rigorous fault injection is available in the agent-benchmark literature; realistic communication impairment models are available in the wireless literature. What does not exist is a runtime that binds them together under a disaster-communication fault model."*

### Gap 6 — Side-effect-correctness metrics rather than task-success metrics
**WirelessBench (arXiv 2603.21251) independently establishes the motivating result in the wireless-agent setting: 23% of errors are catastrophic failures invisible to exact-match metrics.** ReliabilityBench supplies the right correctness criterion (**action metamorphic relations — end-state equivalence**), and τ-bench supplies pass^k. No positive hit found for a wireless/disaster agent benchmark wired to **end-state side-effect equivalence** under communication faults.
**The paper's §12 claim — "让 reviewer 看清 runtime 机制改变了 execution correctness，而不是仅仅多发了几次 tool call" — is exactly this gap, and it is defensible.** Adopt ReliabilityBench's metamorphic end-state relations rather than inventing a metric.

### Gap 7 — Verification when the verifier is itself unavailable
A conceptual gap that follows directly from CRITIC's unexamined assumption (the verifier never fails) and from **arXiv 2608.02645**, whose postcondition verification is specified for a *single tool that responds*. Under a partition, the postcondition check itself times out with unknown outcome — **the verify-before-retry mechanism recurses into the problem it was meant to solve**. No positive hit found for work that treats the verifier's own availability as part of the fault model.
This is a genuinely novel *theoretical* observation and it is cheap to state: it turns "add verification" from a solution into a **dilemma** (retry blind, or verify and possibly fail verification), and the resolution requires exactly the durable log + reconcile machinery the paper proposes. **This is probably the paper's best single conceptual contribution.**

---

## Things to state carefully (honesty constraints)

1. **Do not write "no prior work injects network faults."** Write "the published fault catalogues of the surveyed agent benchmarks operate at the tool-API, context, or infrastructure layer; we are not aware of one that overlays a communication-channel fault model." Coverage of late-2026 preprints is incomplete and several sources were snippet-only.
2. **Do not write "no one injects faults into agents."** This is false and refutable in one paragraph (ToolMaze, ReliabilityBench, AgentChaos, ChaosLLM, AgentDisruptBench, ToolMisuseBench, WAREX, OperAID).
3. **Concede the mechanism set explicitly.** §13 of the context doc lists six non-novel items; the reconnaissance shows at least twelve, including *verify-before-retry* and *bounded fair replay*, which **arXiv 2608.02645 and arXiv 2606.01416 already publish for LLM agents**. Conceding early is far stronger than being caught in review.
4. **Read these six before writing the related-work section** (highest information value first):
   1. **α³-Bench** (arXiv 2601.03281) — does packet loss mutate *tool calls* or only *reasoning context*?
   2. **"Rollback Is Not Undo"** (IEEE 11571400) — how far does it already go, in the paper's own domain?
   3. **"Verified Tool Calls"** (arXiv 2608.02645) — scope and mechanism boundary.
   4. **Atomix** (arXiv 2602.14849) — its "A.2 Fault Injection Details" appendix.
   5. **"Self-Healing Agentic Orchestrators"** (arXiv 2606.01416) — budgeted recovery, to avoid re-deriving it.
   6. **AgentChaos** (arXiv 2608.06790) + **AgentDisruptBench** datasheet — to build an accurate comparison table of *injected fault classes* (the table is the paper's key related-work artifact).
5. **Define "reliability" in the paper.** In current usage (WAREX, τ-bench pass^k) it often means **repeat-run stability**, not **fault tolerance**. Colliding with that usage will confuse reviewers.
6. **Verification discipline.** Roughly two thirds of the 2026 citations here are preprints with unverified venues. Confirm venue/year before the camera-ready; several items (`[FLAG]`) have unresolved uncertainties — notably the TRACE acronym collision, the two different "AgentChaos" projects, and "AgentFail," whose status as paper vs. dataset could not be established.

---

## Provenance and limitations of this reconnaissance

- **Method:** `web_search` was the main tool. DOI-level facts for Section A were then **programmatically verified via the Crossref API** (`[V-CR]`); arXiv abstracts for ~20 key papers were **fetched and read directly** rather than inferred from snippets. URLs in Sections B/C were verified live where possible (`[V-URL]`).
- **What was NOT done:** **No full papers were read.** Judgments of the form "treats tool-execution semantics as first-class" are inferred from abstracts, titles, and snippets — except where marked "[abstract read]," which still means *abstract*, not full text. `[FLAG]` marks every verdict requiring full-text confirmation.
- **Known corrections this reconnaissance produced,** recorded so they are not re-propagated: the lead "AgentTaxo" is not a failure taxonomy; WirelessBench's "tolerance" means *scoring* tolerance, not network tolerance (false alarm); API-Bank's title is "A **Comprehensive** Benchmark"; "AgentChaos" names two distinct projects; the DOI I initially guessed for Demers et al. fair queueing (`10.1145/75246.75256`) belongs to an unrelated atomic-multicast paper — the correct DOIs are `10.1145/75246.75248` / `10.1145/75247.75248`.
- **Companion files:** `recon_sectionB.md` (738 lines, LLM-agent reliability) and `recon_sectionC.md` (499 lines, agents under network disruption) contain the full per-item detail and complete uncertainty logs behind Sections B and C.
