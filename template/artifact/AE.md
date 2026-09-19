# Artifact Evaluation Guide

This is the reviewer's entry point. Replace every `<...>` before submission.

The paper's claims and their current statuses are in [`results/CLAIMS.md`](../results/CLAIMS.md);
the frozen values that verdicts compare against are in
[`results/reference/`](../results/reference/README.md).

## 1. Scope

<一段话：制品是什么、覆盖哪些主张、哪些主张需要凭据。>

## 2. Environment

Measured on the machine that produced the frozen reference results. Reviewers should not have to guess
the environment.

| Item | Value |
|---|---|
| OS | `<...>` |
| CPU | `<...>` |
| Memory | `<...>` |
| Language runtime | `<...>` |
| Third-party packages | `<...>` |
| GPU | `<...>` |
| Disk | `<...>` |
| Network | `<获取依赖是否需要在线的哪一步>` |
| Credentials | `<哪些主张需要，哪些不需要>` |

## 3. Obtaining the artifact

```bash
git clone <仓库地址>
cd <目录>
make deps     # 第三方包（幂等）
make data     # 数据集（幂等）
```

If a check finds an acquired dependency missing, it prints the command that fetches it rather than
raising an unexplained error.

## 4. Getting Started

```bash
make check
```

Prints one PASS or FAIL line per check and exits non-zero on any failure.

## 5. Repeating each claim

| Claim | Command | Expected verdict | Time |
|---|---|---|---|
| C1 | `<命令>` | `<期望读数>` | `<实测或估计>` |

## 6. What this artifact does not do

<不做的部分：未复现的第三方系统、需要凭据的实验、明确列为 future work 的内容。>

## 7. Normative material

| Content | Where |
|---|---|
| <规范性声明> | `spec/` |
| 结果登记册 | `results/README.md` |
| 主张及其状态 | `results/CLAIMS.md` |
| 冻结判定基准 | `results/reference/` |
