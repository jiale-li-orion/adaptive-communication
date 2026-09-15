# Task v1.2 — 22 · R04 机制可辨识性：义务感知联合策略的正确实例化

日期：2026-09-15。承接 [21](21-r01-measurement-r02-model-validity-2026-09-15.md)，闭合矩阵 **R04**
（partly_analyzed_old_candidate_fails → 新候选通过可辨识见证）。**只证明候选真在做所宣称的选择、
动作能生效；不宣称它更优（那是 R05/R06）。** 5 锚点、18/18 全过。

## 1. 旧候选为什么是假阴性（doc19 R1 的代码级确认）

`DeliveryOpportunisticPolicy._want`：`k=t//P; slack=(k+2)P−t`，当前窗口内恒有 `P<slack≤2P`：
- `use_backup_window=False`（主表 anchor）：`urgent=slack<P` **永假**，恒输出 (3600,900)；
- 完整 C-up：`enter=slack≤lead+rate=1200`，P=3600 时同样永假；
- 进入宽限期后，上一窗口的负债被新窗口 index 覆盖（`gateway_copies_in_window` 只查 `t//P`），
  紧急分支每周期被清零、永远等不到。

所以 doc12/主表"anchor≈固定、联合无增益"是**候选未被正确实例化**的假阴性，不能用来关闭联合控制。

## 2. 正确实例化：ObligationDeliveryPolicy（`code/v3joint/obligation_policy.py`，arm=`odp`）

- **追踪最老未完成的具体义务及其固定绝对截止**：routine 义务 i 窗口 [iP,(i+1)P]、deadline=(i+2)P
  （与 exogenous/评分器同源、公开服务配置）。未截止且网关无合格副本的窗口只可能是 cur−1（宽限期）
  或 cur，取更老者；其 slack=(k+2)P−t 随 t **真实递减到 0**，紧急动作在正确时刻触发，不靠抬阈值。
- **三态（doc19 §3，全部网关位置合法可见量）**：
  1. cur−1/cur 窗口网关都已有副本 → 稀疏采样/适中上报，不重复密采（`covered_at_gateway`）；
  2. 节点已采到窗口样本（网关听过的 newest_taken 落在窗口）但网关无副本 → 只**促上报**、采样维持
     稀疏省电（`push_report`）；
  3. 连窗口样本都没采到 → 在"下令→Class A 生效→采/报→赶下一次交付机会"前置期内才**密采+快报**
     （`must_sample`），来不及就不浪费；能量低于健康线一律稀疏保命（`energy_guard`）。
- **修 doc19 R7**：主路是否在喂改用网关自己的转发反馈 `gateway_last_forward_ok_at`（超过
  `primary_stale_s` 未成功转发即视为受阻），**不读** `backhaul_available` 环境真值；并真正调用了旧
  策略漏掉的下一次备用机会相位 `next_backup_in_s`。
- 视图扩展：`CenterView.gateway_copies_by_window`（网关按义务窗口的副本台账），只由 `_gateway_view`
  填，中心视图不填；默认 None，旧行为与锚点逐位不变。

## 3. 可辨识性见证（`r04_witness.py`，全部断言通过）

**纯函数级（构造可达历史，标量 AoI=6000s、SoC=0.05 Wh 完全相同）**：

| 配对 | 相同量 | 区别 | 动作 |
|---|---|---|---|
| A 记录位置 | t/AoI/SoC 同 | H1 网关已有副本 vs H2 无副本 | H1 (3600,900) covered ≠ H2 (3600,300) push_report |
| B 剩余期限 | AoI/SoC/copies 同 | slack 3500(宽裕) vs 900(紧迫) | (3600,900) ≠ (3600,300) |
| 态2/态3 | t/slack 紧迫同 | 采到没到 vs 没采到 | (3600,300) 促上报 ≠ (600,300) 保采集 |

- **置常数对照**：把 copies 抹掉（H1 也设无副本）后其动作与 H2 相同 → 动作差异确实来自副本/记录
  位置变量，不是隐藏旁路（满足"置常数即无差异"的可辨识门）。
- **旧 anchor 反例**：同样紧迫历史（新策略 slack=900 触发快报）下，旧 anchor 仍恒 (3600,900)。

**端到端（真实 Instance，非 mock）**：
- 松 regime（1h 义务，stressed seed0）：odp routine **671/672、14 台全活**，与 fixed900 持平，远好于
  ea_aoi 的 148/672、活 2 台；机制以 covered/energy_guard 为主（松任务本就不需要密采），发 38 条
  非默认配置命令做能量保护，不瞎动作。
- 紧 regime（P=600，doc15 能量可行档 peak.03/soc1/bo0）：`ahead/covered/must_sample/push_report`
  **四态全部真实触发**，节点最终配置出现 (600,600) 密采密报、(3600,300) 稀疏+快报、(3600,900) 常规
  三档，802 条命令，14 台全活，交付 1631/4032（缺采 2258 仍是 P600 能量物理边界，见 doc21 §4）。

## 4. 这一步能/不能下什么结论

- **能**：联合控制候选现在被正确实例化；它确实依据"未完成具体义务＋绝对截止＋记录所在段＋下一次
  机会"做差异化、且动作能经现有命令接口真正改变节点配置；旧"联合无增益"是恒假 bug 的假阴性，撤销。
- **不能**：R04 不证明 odp 更优。松 regime 无 headroom（副本总充足）；紧 regime 它全活、会动作，
  但 1631/4032 是否优于**同等信息/预算下的强静态点与普通规则**，必须由 R05（headroom）/R06（公平
  对照＋延迟感知 MPC 强基线＋耦合消融＋冻结种子）回答。若被覆盖则关闭候选，不升级为"智能控制无用"。

## 5. 下一步 R05
紧 regime 单一合法工作点，公平比较 odp vs 强静态 grid 前沿 vs 现成普通规则（fixed/oblig_slack/
pacing/ea），同服务看真实成本、同成本看服务；未来信息搜索仅作机会见证、不作上界。
