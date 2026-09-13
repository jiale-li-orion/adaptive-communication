# 逐 episode 的语义控制回路聚合：**closure 高、amplification 高** ⇒ 落到预注册分支 1

日期：2026-09-13。goal `goal-9f210612`。基线 `660dc67`。工具：`code/analysis/episode_lifecycle.py`。

## 问题

`intent` 层的失败率**不能**翻译成系统失败：同一节点为同一目标重试 20 次、前 19 次被 layer 1 拒、
第 20 次成功，intent 层是 95% failure，**控制回路层是 100% closed**。

> **Agent 是真的失去了控制，还是只是为了完成同一个控制动作喊了太多遍？**

## episode 定义（冻结）

一次**语义上的远端状态改变需求**：planner 第一次产生与当前目标**不同**的 target 时开始，
所有为该 target 的重试都属同一 episode（复用 `plan` 事件的 `intent_reason`：
`target_change` 开新 episode、`resend` 留在旧、`unknown_state` 看 target 变没变）。
终局五类：`closed` / `superseded` / `deadline` / `node_dead` / `censored`。
**superseded 与 censored 都不算 failure**，单列。（`intent_reason` 已作为**诊断字段**进 `plan` 事件。）

## 结果（3 种子，`aoi`）

| 条件 | intent n | **episode n** | **amplification** | **closure rate**（严格分母） | attempts/closed | wasted/closed | obsolete apply |
|---|---:|---:|---:|---:|---:|---:|---:|
| `adm_noout` | 732 | 198 | **3.70×** | **91.2%**（165/181） | 3.7 | 3.4 | **41** |
| `adm_out3` | 457 | 113 | **4.04×** | **80.0%**（72/90） | 4.9 | 5.3 | **13** |
| `burst_iid_c0.05` | 732 | 198 | 3.70× | 91.2% | 3.7 | 3.4 | 41 |
| **`polar_c0.05`** | **1159** | **66** | **17.56×** | **62.5%**（40/64） | **1.0** | **28.0** | **0** |

（`deadline` 型未闭合：`noout` 16 / `out3` 18 / `polar` 24。）

## 判定：**预注册分支 1**

> **closure 高 + amplification 高** ⇒ 关掉 authority failure，转向 planning / intent economy；
> **优先拿成熟的 durable reconciliation / device shadow 做强基线**，不得硬包装成新 runtime。

**三条硬结论**：

1. **`out3` 下 closure 仍有 80.0%**（9 h 接入中断）。⇒ **§7.83 那个"layer 1 拒了 97%"绝不等于控制失败**：
   被拒的绝大多数是**同一 episode 的重复敲门**，最终回路是闭合的。**你预判的分叉成立。**
2. **amplification 3.7–4.0×**：完成一次 semantic state change 平均要喊 **3.7–4.9 次**，
   `wasted reasoning per closed effect` 3.4–5.3。**这是可主张的 agent-infra 量**，
   而且它**不会把有用的 retry 误判成失败**。
3. **`polar` 是另一种形态**：amplification **17.56×**、`attempts/closed = 1.0`（闭合的 episode 一次就成）、
   wasted/closed **28.0**。⇒ 无谓开销集中在**始终没闭合的那 24 个 episode** 上，
   而不是分散在各 episode 内部。**这是"少量 episode 长期进不了网络"的形状。**

## 尚未做到的一处（不掩饰）

`terminal layer` 我**只做到了** `deadline / node_dead / censored / superseded`，
**没有把"最后一次尝试死在第 1 层还是第 2 层"作为终局类别**——目标要求的是后者。
所以**分支 2 与分支 3 现在还不能对号入座**。`intent_fate.py` 的四层比例是**聚合级**的，
要做 episode 级的分层终局，需要在 episode 内记录**最后一次尝试的层**。**这是下一轮。**

## 另外两处待查

- `adm_noout` 与 `burst_iid_c0.05` 四个数**逐位相同**（732/198/91.2%/41）。两者登记 config 不同，
  疑为 `build_kwargs` 未把 burst 键传到该条件，**未查证，不作结论**。
- `obsolete_apply`（supersede 之后才生效）判据偏松：现在是"旧 target 的值在更晚的新 target 之后
  仍出现 applied"。**这是 execution-layer stale effect 的第一个非零证据**（`noout` 41 / `out3` 13），
  但判据要收紧后才可承重。

---

## 十、补齐终局层（第 1 / 第 2 层）与最终分支选择

按"整条 episode 的尝试里**有没有任何一次**过了 layer 1"分：全被拒 ⇒ **layer1**（center→gateway 回传不可达）；
有过 `sent` ⇒ **layer2**（节点侧机会稀缺）。

| 条件 | episode n | closed | **layer1** | **layer2** | superseded | censored | **closure rate** |
|---|---:|---:|---:|---:|---:|---:|---:|
| `adm_noout` | 198 | 165 | **7** | **9** | 3 | 14 | **91.2%** |
| `adm_out3` | 113 | 72 | **0** | **18** | 5 | 18 | **80.0%** |
| **`polar_c0.05`** | 66 | 40 | **14** | **10** | 2 | 0 | **62.5%** |

**⇒ 四条预注册判据的对号入座**：

- **分支 1 主导**（closure 高 80–91%、amplification 高 3.7–4.0×）⇒
  **关掉 authority failure，转向 planning / intent economy，并拿成熟 durable reconciliation 做强基线。**
- **分支 2 只有一个小立足点**：`polar` 的 layer1 = 14 个 episode（占 66 的 21%），
  形态是"少量 episode 在有效期内始终进不了网络"。**不主导。**
- **分支 3 只有一个小立足点**：`out3` 的 layer2 = 18 个 episode（占 113 的 16%），
  且 `out3` 的 layer1 恰为 **0**。**不主导**，但它与 §7.83 的聚合结论（`out3` 第二层 63.6%）方向一致。
- **分支 4 不适用**：终局里 `node_dead` = 0（三条件全为 0）。

**⇒ 最终判定：分支 1。** 一句话答案：

> **Agent 没有真的失去控制。它只是为了完成同一个控制动作喊了太多遍。**
> `out3` 那种 9 小时接入中断下，**80% 的语义状态改变最终仍然完成**，平均喊 4.9 次；
> `polar` 下 amplification 到 **17.56×**，而**闭合的那些 episode 一次就成**（attempts/closed = 1.0）——
> 无谓开销集中在**始终没闭合的少数 episode** 上。

**据此，三个原判断的新位置**：
- **authority failure（"知道了却改变不了世界"）**：按 episode 级证据**不成立**，收掉。
  它此前看起来成立，是因为把"同一 episode 的重复敲门"数成了失败。
- **agent infra 的 backpressure**：**反而变强**——`planning amplification` 3.7–17.6×、
  `wasted reasoning per closed effect` 3.4–28.0 是**不会把有用 retry 误判成失败**的量。
  但它**必须先与成熟 desired-state reconciliation / device shadow 对比**，
  否则就是重复已有系统（我早期已被成熟 shadow 教训过一次）。
- **`report_period` 方法线**：**关闭**。它只买 layer 2，而 layer 2 只在 `out3` 有 18 个 episode 的立足点。
