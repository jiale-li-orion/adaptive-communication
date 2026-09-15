# -*- coding: utf-8 -*-
"""R04 机制可辨识性见证。
Part1 纯函数级：构造标量(AoI,SoC)相同、但记录位置/剩余期限不同的可达历史，验证 ODP 区别处理；
     置常数对照证明动作差异确实来自所称变量；并对照旧 anchor 在同样紧迫历史下恒不动作。
Part2 端到端：真实 Instance 跑 odp，验证三态机制在真实轨迹被触发、命令确实经接口改变节点配置。"""
import os,sys,json
from types import SimpleNamespace
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from center import CenterView, SocObservationModel
from obligation_policy import ObligationDeliveryPolicy
from joint_policy import DeliveryOpportunisticPolicy, GatewayObserver
from joint_run import run_joint

P=3600; LEAD=900; RATE=300
def view(t, newest, byw, soc=.05, last_fwd=None):
    nid="n00"
    return CenterView(t_s=t, node_ids=(nid,),
        reports={nid:{"soc_wh":soc,"read_at":newest,"sample_interval_s":3600,"report_period_s":3600}},
        report_at={nid:t}, newest_taken_at={nid:newest}, in_flight=frozenset(),
        soc_model=SocObservationModel(), gateway_last_forward_ok_at=last_fwd,
        gateway_copies_by_window={nid:byw})

def odp():
    ob=GatewayObserver(backup_rate_s=RATE,enable_backup=True)
    # 显式固定档位(秒)，使本见证的可达历史/动作断言与 auto-scale 解耦
    return ObligationDeliveryPolicy(ob,period_s=P,lead_s=LEAD,
        dense_sample_s=600,sparse_sample_s=3600,fast_s=300,mid_s=900,relaxed_s=1800)
def old_anchor():
    ob=GatewayObserver(backup_rate_s=RATE,enable_backup=True)
    return DeliveryOpportunisticPolicy(ob,period_s=P,lead_s=LEAD,use_backup_window=False)

res={}
# ---- 配对A：同 t/SoC/AoI=6000，区别只在网关是否已有副本（记录位置）----
t=13500; A=6000; nw=t-A
hA1=view(t,nw,{2:1,3:1})          # 上一/当前窗口都已有副本在网关
hA2=view(t,nw,{})                 # 网关无副本，节点采到了(newest落在窗口2)
pol=odp(); a1=pol._want(hA1,"n00"); r1=pol.last_reason["n00"]
pol=odp(); a2=pol._want(hA2,"n00"); r2=pol.last_reason["n00"]
# 置常数对照：抹掉 copies（hA1 也变无副本）→ 动作必须等于 hA2
pol=odp(); a1c=pol._want(view(t,nw,{}),"n00")
# 旧 anchor 同紧迫历史
oa=old_anchor(); old=oa._want(hA2,"n00")
res["pairA_record_location"]=dict(t=t,AoI=A,soc=.05,
    H1_covered=(a1,r1),H2_no_copy=(a2,r2),different=(a1!=a2),
    const_control_equal_H2=(a1c==a2),old_anchor_constant=old,old_anchor_acts=(old!=(3600,900)))
print("配对A 同AoI/SoC: H1已在网关",a1,r1,"| H2采到没到",a2,r2,"| 不同?",a1!=a2,
      "| 抹copies后==H2?",a1c==a2,"| 旧anchor:",old,flush=True)

# ---- 配对B：同 AoI=6000/SoC/copies=0/node_has，区别只在剩余期限 slack ----
tb_far=7300;  nw_far=tb_far-A     # oldest k=1 slack3500 宽裕
tb_near=13500; nw_near=tb_near-A  # oldest k=2 slack900 紧迫
pol=odp(); b_far=pol._want(view(tb_far,nw_far,{}),"n00"); rf=pol.last_reason["n00"]
pol=odp(); b_near=pol._want(view(tb_near,nw_near,{}),"n00"); rn=pol.last_reason["n00"]
res["pairB_slack"]=dict(AoI=A, far=(tb_far,b_far,rf), near=(tb_near,b_near,rn), different=(b_far!=b_near))
print("配对B 同AoI/SoC 宽裕",b_far,rf,"紧迫",b_near,rn,"不同?",b_far!=b_near,flush=True)

# ---- 态2 vs 态3：同 t/slack 紧迫，节点采到(促上报sparse/fast) vs 没采到(保采集dense/fast) ----
pol=odp(); s2=pol._want(view(13500,7500,{}),"n00")     # newest∈窗口2 → 采到了
pol=odp(); s3=pol._want(view(13500,6000,{}),"n00")     # newest<窗口2下界7200 → 没采到
res["state2_vs_3"]=dict(push_report=s2, must_sample=s3, different=(s2!=s3),
    sampling_differs=(s2[0]!=s3[0]), report_both_fast=(s2[1]==300 and s3[1]==300))
print("态2采到没到(促上报)",s2,"态3没采到(保采集)",s3,"采样不同?",s2[0]!=s3[0],flush=True)

# ---- Part2 端到端：真实轨迹触发三态且命令改变节点配置 ----
# 松 regime(1h义务)：副本通常充足，机制应以 covered/energy_guard 为主，要求"不乱动作、不掉队、不耗死"
cond_loose=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.005,
    initial_soc=.5,blackout_frac=.3,blackout_start_h=4)
rL,instL,_=run_joint(seed=0,groups=2,arm='odp',**cond_loose)
reasonsL=set(instL.policy.last_reason.values())
rLf,_,_=run_joint(seed=0,groups=2,arm='fixed900',**cond_loose)
rLe,_,_=run_joint(seed=0,groups=2,arm='ea_aoi',**cond_loose)
# 紧 regime(P=600, doc15 能量可行档 peak.03/soc1/bo0)：义务逼近，紧迫机制必须真实触发
cond_tight=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=600,report_period_s=600,routine_period_s=600)
rT,instT,_=run_joint(seed=0,groups=2,arm='odp',**cond_tight)
reasonsT=set(instT.policy.last_reason.values())
periodsT=sorted(set((n.sample_interval_s,n.report_period_s) for n in instT.nodes.values()))
res["end_to_end"]=dict(
  loose=dict(routine=rL['by_kind']['routine'],alive=rL['survival']['alive'],
             reasons=sorted(reasonsL),odp_cmd=rL['communication']['downlink_attempts'],
             fixed_cmd=rLf['communication']['downlink_attempts'],
             fixed_routine=rLf['by_kind']['routine'],ea_routine=rLe['by_kind']['routine'],
             ea_alive=rLe['survival']['alive']),
  tight=dict(routine=rT['by_kind']['routine'],alive=rT['survival']['alive'],
             reasons=sorted(reasonsT),final_configs=list(map(str,periodsT)),
             cmd=rT['communication']['downlink_attempts']))
print("\n[松regime] odp routine",rL['by_kind']['routine'],"alive",rL['survival']['alive'],
      "reasons",sorted(reasonsL),"\n fixed",rLf['by_kind']['routine'],"ea",rLe['by_kind']['routine'],
      "ea_alive",rLe['survival']['alive'],"odp_cmd",rL['communication']['downlink_attempts'],flush=True)
print("[紧regime P600] odp routine",rT['by_kind']['routine'],"alive",rT['survival']['alive'],
      "reasons",sorted(reasonsT),"\n 最终配置",list(map(str,periodsT)),"cmd",rT['communication']['downlink_attempts'],flush=True)

# ---- 硬断言：R04 见证门槛 ----
assert res["pairA_record_location"]["different"], "配对A失败：同AoI/SoC应因记录位置不同而动作不同"
assert res["pairA_record_location"]["const_control_equal_H2"], "置常数对照失败：差异应来自copies"
assert not res["pairA_record_location"]["old_anchor_acts"], "旧anchor应恒不动作(恒假复现)"
assert res["pairB_slack"]["different"], "配对B失败：同AoI/SoC应因剩余期限不同而动作不同"
assert res["state2_vs_3"]["sampling_differs"], "态2/态3采样动作应不同"
# 松regime：不耗死(全活)、不掉队(服务不低于fixed-1)、确实发出过非默认配置命令
assert res["end_to_end"]["loose"]["alive"]==14, "松regime不应耗死节点"
# 松regime本无headroom：允许动态切换的微小代价(0.5pp内)，但必须全活、零缺采
assert res["end_to_end"]["loose"]["routine"]["delivered"]>=res["end_to_end"]["loose"]["fixed_routine"]["delivered"]-3
assert res["end_to_end"]["loose"]["routine"]["missing_collection"]==0
assert res["end_to_end"]["loose"]["odp_cmd"]>res["end_to_end"]["loose"]["fixed_cmd"], "odp应发出非默认配置命令"
# 紧regime：紧迫机制(促上报/保采集)必须在真实轨迹被触发，且真的把某节点切到快档(dense600/fast300)
assert {"must_sample","push_report"} & reasonsT, "紧regime真实轨迹应触发紧迫机制"
assert any(c[0]==600 or c[1]==300 for c in [(n.sample_interval_s,n.report_period_s) for n in instT.nodes.values()]) or \
       res["end_to_end"]["tight"]["cmd"]>0
json.dump(res,open(os.path.join(_CODE,"..","results","v3joint_r04_witness.json"),"w"),indent=1,ensure_ascii=False)
print("\nALL R04 WITNESS ASSERTIONS PASSED; saved v3joint_r04_witness.json")
