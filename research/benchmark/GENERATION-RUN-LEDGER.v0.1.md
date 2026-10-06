# Layer-1 v0.6 Generation Run Ledger

状态：**CURRENT GENERATION PROVENANCE LEDGER**  
对应流程：[`CASE-GENERATION-PIPELINE.v0.1.md`](CASE-GENERATION-PIPELINE.v0.1.md)

本文件只记录“生成器执行发生了什么”，不记录方法成绩。

## Run r1 — provisional / rejected as release artifact

目录：`local_research/current/benchmark/generated/layer1-v0.6-preoracle-r1/`

生成结果本身完整：

- source task cells: 27
- eligible compositions: 51
- geometry signatures: 6,045
- base scenarios: 77,556
- `ALL_WORLD_PHYSICAL` bases: 46,770
- `MIXED_WORLD_PHYSICAL` bases: 30,786
- dynamic cases: 1,262,790
- structure IDs: 499,608

内容层校验：三个 gzip artifact 的解压 canonical JSONL SHA-256 与 manifest **全部一致**，行数也全部一致。

但 raw gzip container SHA-256 中：

- `geometry-signatures.jsonl.gz`: match
- `base-scenarios.jsonl.gz`: mismatch
- `cases.jsonl.gz`: mismatch

同一 writer 的 10,000-row 双生成 smoke test 可得到完全相同的 raw gzip bytes，因此 gzip 算法本身是确定性的。r1 的外层执行曾返回 internal failure，而目录随后显示已经完整生成；最保守解释是执行 harness replay/concurrent write 造成 manifest 与最终 gzip container 不属于同一次单写者 run。

**Disposition：REJECTED_AS_RELEASE_ARTIFACT。** r1 保留在 ignored local workspace 作为 provenance，不进入 oracle / split / paper statistics。

修复：generator 增加 exclusive sibling lock、existing-target refusal 与 `COMPLETE.json` final marker。正式 r2 必须通过 raw artifact SHA、canonical SHA、ID/derivation audit 后才能进入下一阶段。

## Run r2 — complete / audited

状态：`PASS_GENERATION_AND_CONTENT_AUDIT`

目标目录：`local_research/current/benchmark/generated/layer1-v0.6-preoracle-r2/`

生成结果：

- source task cells: 27
- eligible compositions: 51
- geometry signatures: 6,045
- base scenarios: 77,556
- `ALL_WORLD_PHYSICAL` bases: 46,770
- `MIXED_WORLD_PHYSICAL` bases: 30,786
- dynamic cases: 1,262,790
- structure IDs: 499,608

正式流式审计结果：PASS。

- `base-scenarios.jsonl.gz` raw SHA-256: `5f4f5530ba9b039d99ba0ae43d57c30be4f706b5f55326b8906da549858c94bf`
- `cases.jsonl.gz` raw SHA-256: `7fa88e7e883f008a03705ac960635c205caafaae9972f56904fd6f7cfd6eff1f`
- `geometry-signatures.jsonl.gz` raw SHA-256: `dca0e39504b2ac87e974296ceef4234a44fede196d530238a075232157b773a3`
- canonical uncompressed hashes分别为：
  - base: `5104a68276095a82ea3fcc78918dbfcc6a8bfec387b60a6c69f3b4e0ab09b287`
  - cases: `670a148aa9c71f5afbbce6da2029457e9d780522a192c1a1286a9c99cca8878e`
  - geometry: `25bf52ee6457cdf7ff6cb68272935a8185a8dcca718bdbfc27bd31a74d86dbee`

审计已核对：artifact hash、canonical hash、rows、ID 重算、frozen-axis membership、base/case 引用、fallback budget derivation。

## Run r3 — independent reproduction

状态：`PASS_BYTE_AND_CANONICAL_REPRODUCTION`

目录：`local_research/current/benchmark/generated/layer1-v0.6-preoracle-r3/`

r3 在相同 generator/source/trace/axes 内容下独立生成。与 r2 对账：

- counts: exact match；
- artifact bytes: exact match；
- raw gzip SHA-256: 3/3 exact match；
- canonical uncompressed SHA-256: 3/3 exact match；
- row counts: 3/3 exact match。

因此 v0.6 generation content 已达到 byte-level deterministic reproduction。

注意：r2/r3 运行时 generator 文件内容已由 manifest 的 `generator_code_sha256` 精确绑定，但 git working tree 尚未提交本轮 single-writer/geometry-audit hardening。下一步先提交这些改动，再从 clean commit 生成 official r4；r4 artifact content 必须继续与 r2/r3 一致。

## Official clean-tree run r4

状态：`PASS_OFFICIAL_CLEAN_TREE_GENERATION`

目录：`local_research/current/benchmark/generated/layer1-v0.6-preoracle-r4/`

生成时 clean HEAD：`0ad64380b82ab940bf2ba0cd8c6570583d20d776`。

r4 自身流式 audit：PASS。结果与 r2/r3 完全一致：

- source task cells: 27
- eligible compositions: 51
- geometry signatures: 6,045
- base scenarios: 77,556
- base structures: 36,270
- `ALL_WORLD_PHYSICAL` bases: 46,770
- `ALL_WORLD_PHYSICAL` base structures: 18,504
- `MIXED_WORLD_PHYSICAL` bases: 30,786
- dynamic cases: 1,262,790
- pre-oracle structure IDs: 499,608
- variants / physical base: 27

三次 run 的 generator code SHA 完全一致：`7c9d87fa6390e4860ad132e5166405306ab51d3cc9ab15a6ff2c79d026c36ad3`。

r2/r3/r4 三方对账：

- counts exact match；
- artifact byte sizes exact match；
- artifact raw SHA-256 3/3 exact match；
- canonical uncompressed SHA-256 3/3 exact match；
- row counts 3/3 exact match。

正式 artifact hashes：

- base raw: `5f4f5530ba9b039d99ba0ae43d57c30be4f706b5f55326b8906da549858c94bf`
- base canonical: `5104a68276095a82ea3fcc78918dbfcc6a8bfec387b60a6c69f3b4e0ab09b287`
- cases raw: `7fa88e7e883f008a03705ac960635c205caafaae9972f56904fd6f7cfd6eff1f`
- cases canonical: `670a148aa9c71f5afbbce6da2029457e9d780522a192c1a1286a9c99cca8878e`
- geometry raw: `dca0e39504b2ac87e974296ceef4234a44fede196d530238a075232157b773a3`
- geometry canonical: `25bf52ee6457cdf7ff6cb68272935a8185a8dcca718bdbfc27bd31a74d86dbee`

**Disposition：OFFICIAL_PRE_ORACLE_GENERATION_RUN。** 该状态只关闭“method-independent generation + reproducibility”门，不产生 hardness / EvidenceNeed / benchmark-admit 主张。

Admission 条件：

1. `COMPLETE.json` 存在且绑定 `MANIFEST.json` SHA-256；
2. 三个 artifact raw SHA-256 与 manifest 一致；
3. canonical-uncompressed SHA-256 与行数一致；
4. base/case/structure IDs 可由内容重算；
5. geometry signature 可追溯到全部 equivalent trace slices；
6. fallback budget 可由 base full-state physical derivation重算；
7. frozen-axis membership 全部通过；
8. artifact raw/canonical hashes 与 r2/r3 完全一致；
9. `MANIFEST.inputs.git_commit` 必须等于生成时 clean HEAD。

以上 9 项全部通过。

