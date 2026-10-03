# -*- coding: utf-8 -*-
"""R05 bounded headroom：紧 regime(P600, peak.03/soc1/bo0/oh16) 公平比较。
强静态 grid 前沿 vs ea_aoi vs ODP 完整联合 vs ODP 只门控上报消融。
服务相同时比真实成本(末电/命令/空口/备份报文)。未来信息搜索不在本件。"""
import os,sys,json,math,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
import center as C
from center import RollingConfigSearchPolicy
# 普通滚动搜索 MPC 强基线：按**场景声明参数**构造（不进默认 ARMS，见 center.py L1093）。
# 合法信息：标称采能率=声明 peak、链路概率=.74/.62、容量.05；不用任何未来真值。
C.ARMS["rolling_search"] = lambda: RollingConfigSearchPolicy(
    routine_period_s=600, uplink_p=.74, backhaul_p=.62,
    harvest_wh_per_hour=.03, capacity_wh=.05, horizon_end_s=48*3600, dwell_s=600)
def t95(n): return {4:2.776,6:2.571,8:2.365}.get(n,2.131)
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=600,report_period_s=600,routine_period_s=600)
# (标签, arm, 额外kw)
ARMS=[("grid600x600","grid600x600",{}),
      ("grid900x600","grid900x600",{}),
      ("grid1800x900","grid1800x900",{}),
      ("fixed900","fixed900",{}),
      ("ea_aoi","ea_aoi",{}),
      ("rolling_MPC","rolling_search",{}),
      ("ODP_joint","odp",{}),
      ("ODP_report_only","odp",{"odp_gate_sampling":False})]
def svc(r): return r["routine"]["delivered"]/r["routine"]["n"]
def coll(r):
    rr=r["routine"]; return (rr["n"]-rr.get("missing_collection",0)-rr.get("censored",0))/rr["n"]
data={}
for tag,arm,kw in ARMS:
    rows=[]
    for s in SEEDS:
        r,inst,_=run_joint(seed=s,groups=2,arm=arm,**BASE,**kw)
        rows.append(dict(svc=svc(r),coll=coll(r),alive=r["survival"]["alive"],
            final_soc=r["survival"]["mean_final_soc"],cmd=r["communication"]["downlink_attempts"],
            air_s=round(r["communication"]["airtime_uplink_h"]*3600,1),
            backup=r["backup"].get("backup_packets",0)))
        print(f"{tag:16s} seed{s} svc={rows[-1]['svc']:.3f} coll={rows[-1]['coll']:.3f} alive={rows[-1]['alive']:.0f} soc={rows[-1]['final_soc']:.3f} cmd={rows[-1]['cmd']} air={rows[-1]['air_s']}",flush=True)
    n=len(rows); m=st.mean(x['svc'] for x in rows); sd=st.pstdev(x['svc'] for x in rows)*math.sqrt(n/(n-1)) if n>1 else 0
    data[tag]=dict(rows=rows,svc_mean=round(m,4),svc_ci=round(t95(n)*sd/math.sqrt(n),4),
        coll_mean=round(st.mean(x['coll'] for x in rows),4),
        alive_mean=round(st.mean(x['alive'] for x in rows),2),
        soc_mean=round(st.mean(x['final_soc'] for x in rows),4),
        cmd_mean=round(st.mean(x['cmd'] for x in rows),1),
        air_mean=round(st.mean(x['air_s'] for x in rows),1),
        backup_mean=round(st.mean(x['backup'] for x in rows),2))
    print(f"  -> {tag:16s} svc={m:.4f}±{data[tag]['svc_ci']:.4f} coll={data[tag]['coll_mean']:.3f} alive={data[tag]['alive_mean']} soc={data[tag]['soc_mean']} cmd={data[tag]['cmd_mean']} air={data[tag]['air_mean']}\n",flush=True)
# 对最强静态 grid600x600 的配对差
base=[x['svc'] for x in data['grid600x600']['rows']]
print("=== 配对差 vs grid600x600 (pp) ===",flush=True)
for tag,_,_ in ARMS:
    d=[(data[tag]['rows'][i]['svc']-base[i])*100 for i in range(len(SEEDS))]
    print(f"  {tag:16s} Δ={st.mean(d):+6.2f}pp  更优{sum(1 for x in d if x>0.05)}/{len(d)} 更差{sum(1 for x in d if x<-0.05)}/{len(d)}",flush=True)
json.dump(data,open(os.path.join(_CODE,"..","results","v3joint_r05_headroom.json"),"w"),indent=1,ensure_ascii=False)
print("saved v3joint_r05_headroom.json")
