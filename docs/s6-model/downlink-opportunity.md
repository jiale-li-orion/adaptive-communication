# 控制面的可达机会：标准定义的下行约束

> 来源：2026-09-13 对 3GPP / OMA / LoRa Alliance 规范正文的核实（原始规范 PDF 见 `recon/灾前监测/标准原文/`）。
> 每一条 clause 编号均在该次会话中从下载的规范正文读出；推算值标「本文推导」。
> **本文件改变 `docs/s6-model/system-model.md` 的信道模型**：当前模型的下行与节点是否上行无关，而标准规定它有关。

## 1. 结论

**在低功耗广域监测网络中，下行不是"随时可调用的远程函数"，而是由节点自身的唤醒时刻表给出的机会窗口。** 这不是实现缺陷，是三个标准体系各自明确定义的行为。

这直接决定了 agent 的一条命令**什么时候能被送出**，与它重试多少次无关。

## 2. LoRaWAN Class A

- 下行只能在一次上行之后的 RX1 / RX2 两个接收窗口内发生；节点回到休眠后没有接收窗口。
- 因此：**下行机会数 ≤ 上行次数**。节点每小时上行一次，agent 每小时最多只有一次下发机会，与重试预算取值无关。
- 上行本身受占空比限制。

## 3. NB-IoT / LTE-M 的 PSM

**规范原文（TS 23.682 V19.3.0, clause 4.5.4 "UE Power Saving Mode"）**：

> "A UE in PSM is **not immediately reachable for mobile terminating services**. A UE using PSM is available for mobile terminating services during the time it is in connected mode and for the period of an Active Time that is after the connected mode."

> "The UE is in PSM until a mobile originated event (e.g. periodic RAU/TAU, mobile originated data or detach) requires the UE to initiate any procedure towards the network."

**工程含义**：对野外设备下发指令只有三条路——

1. 等它下一次 periodic TAU（周期由 **T3412 / T3412 extended** 决定，**最长可达数百天**）；
2. 等它因自身 MO 数据 / 信令醒来，此时有 **T3324（Active Time，通常数十秒至数分钟）** 的下行窗口；
3. 不"唤醒再下发"，改用网络侧缓存：**MT NIDD / SCEF** 或 **device trigger**，由网络在终端变可达的瞬间投递。

TS 23.682 clause 4.5.4 把后两条写成标准解法：

> "A network side application may send an SMS or a device trigger to trigger an application on UE to initiate communication with the SCS/AS, which is delivered when the UE becomes reachable."
> "Alternatively a network side application may request monitoring of reachability for data to receive a notification when it is possible to send downlink data immediately to the UE."

**核实依据的规范版本**（均从正文首页读出）：TS 23.682 V19.3.0 (2025-12)、TS 24.301 V19.7.0 (2026-06)（PSM 进入条件 cl 5.3.11、eDRX 协商 cl 5.3.12、paging 补偿 cl 5.6.2）、TS 24.008 V20.0.0 (2026-06)（eDRX/PTW 取值 cl 10.5.5.32）、TS 36.304 V19.2.0 (2026-06)（可达性语义 cl 7.3）、TS 36.331 V19.3.0、TS 36.213 V19.4.0。

**eDRX 是与 PSM 并列的另一条路线**：eDRX 让终端周期性短暂可达（PTW，Paging Time Window），代价是平均功耗上升。**PSM 与 eDRX 的取舍就是"控制面机会 vs 能耗"这条曲线本身**，这是标准已经参数化的折中。

## 4. LwM2M 的 Queue Mode

OMA LwM2M 的 **Queue Mode** 正是为休眠设备设计的：服务器把请求排队，等设备再次可达时投递。已核实的文档：

| 文档 | 版本字符串（文件自身印刷） |
|---|---|
| LightweightM2M Core | `OMA-TS-LightweightM2M_Core-V1_1_1-20190617-A` |
| LightweightM2M Core | `OMA-TS-LightweightM2M_Core-V1_2_2-20240613-A` |

对象定义在 Core 规范的 **Appendix E（Normative）**：E.4 Device、E.5 Connectivity Monitoring、E.6 Firmware Update、E.7 Location、E.8 Connectivity Statistics。OMNA Registry 的 `lwm2m/{3,4,5,6,7}.xml` 是同一份定义的机器可读镜像。

> ⚠️ **不要引用 `OMA-TS-LightweightM2M_Core-V1_1_1-20190617-C`**：该 URL 返回 404。OMA 实际使用 **`-A`（Approved）** 后缀。

## 5. LoRa Alliance：用多播绕开机会约束

FUOTA 套件是"**当单播下行机会不够时，标准给出的架构级解法**"：

| TS 编号 | 文档 | 角色 | Class 要求 | 可靠性模型 |
|---|---|---|---|---|
| **TS003 v1.0.0** | LoRaWAN Application Layer Clock Synchronization | 前置条件：秒级绝对时间 | Class A 即可 | **逐命令确认**（`MUST be individually acknowledged`） |
| **TS004 v1.0.0** | LoRaWAN Fragmented Data Block Transport | 数据面：固件分片广播 | **Class B 或 Class C** | **无逐片确认**，FEC 冗余 + `FragStatusReq` 稀疏统计 |
| **TS005 v1.0.0** | LoRaWAN Remote Multicast Setup | 控制面：建组 + 编程 Class B/C 分发窗口 | **Class B 或 Class C 二选一**（§4.5 Class C / §4.6 Class B） | 单播建立有确认；多播分发本身无确认 |

**TS 编号的唯一证据来源是 TR002 v1.0.0 §6.1 References 的印刷文本**（三份 PDF 自身均未印刷该编号）。注意 **TS005 是多播、TS004 是分片，二者容易记反**。

> ⚠️ **TR002 的性质**：文档自身声明 `This Technical Recommendation has been adopted by the Alliance but is not a specification subject to the provisions of the Alliance's IPR Policy.` → **它是 Technical Recommendation，不是强制性 Specification**，合规文件中不应作为规范引用。
>
> ⚠️ **不存在名为 "FUOTA Application Layer" 的 LoRa Alliance 文档**：TR002 §3 Table 1 `Package Identifier List` 已把当时的 FUOTA 包列尽，无此项；`resource_hub-sitemap.xml`（110 条）中 FUOTA 相关仅 4 条（TR002 + TS003/TS004/TS005）。正确表述是"**由三份规范构成的 FUOTA 应用层套件**"。

**含义**：标准承认"逐设备单播下发"在许多场景不可行，于是提供了**广播/多播 + 稀疏状态回收**的替代路径。这与本文 runtime 的"逐操作确认 + 调和"是两条不同的工程路线，值得在方法章里作为对照表述。

## 6. 对本文系统模型的三处修改

1. **控制面机会必须显式建模。** 当前 `code/runtime/disruption_env.py::call` 只查 `_link_success_p(node)` 与 Gilbert-Elliott 状态，**下行成功与节点是否上行无关**；`mission_sim.py` 的命令路径也是独立的逐轮伯努利。标准规定它们相关。
2. **遥测间隔与控制面速率不是两个独立参数。** 论文 §四 现表述为"两个独立参数，不能互相折算"——在 Class A / PSM 下它们**被 MAC 耦合**：上行节奏就是下行机会的上界。
3. **这解释了等预算对照的结果。** 预算 3→20 时写入从 11,520 涨到 144,115（12.5 倍），恰好一次率只从 26.2% 涨到 44.2%（1.7 倍），预算 20 时两臂空口已无法区分（区间跨 0）。**正确的解释不是"策略趋同"，而是"重试买不到下行机会"。**

## 7. 由此得到的新实验轴

| 组网/配置策略 | 机会来源 | 预期 |
|---|---|---|
| 定时上报（现状） | 每小时 1 次固定 | 重试预算饱和，重现现有结果 |
| 定时 + 事件触发上行 | 汛期密集 | 数据与**控制面可达性同时改善**，零硬件成本 |
| 关键站点 Class C（网关侧有电） | 常开接收窗口 | 用能量预算换控制面可达性，可量化折中 |
| 多播/组播下发（TS004/TS005 路线） | 与上行无关 | 对照组：架构级解法 vs 运行时语义 |

**这不是射频意义上的覆盖增强。** 对 88.5% 的永久遮挡点位，射频手段无效（SF7→SF12 仅 +14 dB，遮挡超额损耗 71–107 dB）；而"给节点上行机会"是零硬件成本、且同时改善数据时效与控制面的杠杆。

## 8. 与动作分类的接口

**只有需要下行投递的动作才受机会约束**，这使 §4 的动作分类多出一个维度：

- **只读类**（读状态/链路/电量）：需要下行请求 + 上行回复 → **受机会约束，且有歧义**
- **状态设置类**：需要下行 → 受机会约束；按值幂等者重复无害
- **独立逻辑操作类**（告警确认、触发采集、看门狗、补传、链路切换、中继启用）：需要下行 → 受机会约束；**重复有害**
- **节点侧自主动作**（本地规则、本地触发、断网缓存）：**不受机会约束**，这正是"本地规则 + 缓存"基线能与 runtime 竞争的原因

**推论**：runtime 的收益上界被机会约束封住，而"本地规则 + 缓存 + 队列化接触窗口交付（LwM2M Queue Mode 思路）"这条强基线恰好也在利用同一个机会窗口。**必须在这条基线下比较**，否则无法区分"runtime 更好"与"我们用了更多的机会"。
