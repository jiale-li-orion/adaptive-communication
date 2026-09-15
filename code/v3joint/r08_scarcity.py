# -*- coding: utf-8 -*-
"""R08 方向探针：备份稀缺度扫描。当前 rate=300/78B 吞吐≈18记录/600s > 产出14，备份不稀缺;
北斗真实频度更慢。扫 rate 找"备份硬稀缺"拐点，看 suppressed(有货装不下)与服务损失，
判断义务级内容/配额仲裁(X1/X3/X4)是否存在静态/EDF拿不到的空间。不调策略，只刻画资源面。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
# (rate_s, bytes)：净荷=bytes-20B header，位移记录6B/条
GRID=[(120,78),(300,78),(600,78),(900,78),(1200,78),(600,200),(1200,200)]
out={}
for rate,bytes_ in GRID:
    sv=[];opp=[];rec=[];sup=[];pkt=[]
    for s in SEEDS:
        r,_,_=run_joint(seed=s,groups=2,arm="grid600x600",backup_rate_s=rate,backup_bytes=bytes_,**BASE)
        rr=r["routine"]; b=r["backup"]; sv.append(rr["delivered"]/rr["n"])
        opp.append(b.get("backup_opportunities",0)); rec.append(b.get("backup_records",0))
        sup.append(b.get("backup_suppressed",0)); pkt.append(b.get("backup_packets",0))
    key=f"r{rate}_b{bytes_}"
    # 粗吞吐: (bytes-20)//6 条/包 * (3600/rate) 包/h ; 产出=14节点/600s=84条/h
    cap_per_pkt=max(1,(bytes_-20)//6); cap_per_h=cap_per_pkt*3600/rate
    out[key]=dict(rate_s=rate,bytes=bytes_,cap_rec_per_h=round(cap_per_h,1),
        svc=round(st.mean(sv),4),svc_min=round(min(sv),3),svc_max=round(max(sv),3),
        opp=round(st.mean(opp),0),rec=round(st.mean(rec),0),sup=round(st.mean(sup),0),pkt=round(st.mean(pkt),0))
    print(f"{key:10s} 容量≈{cap_per_h:5.0f}记录/h(产出84) svc={out[key]['svc']:.4f}[{out[key]['svc_min']},{out[key]['svc_max']}] "
          f"opp={out[key]['opp']:.0f} rec={out[key]['rec']:.0f} sup={out[key]['sup']:.0f} pkt={out[key]['pkt']:.0f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r08_backup_scarcity.json"),"w"),indent=1,ensure_ascii=False)
print("产出参考: 13位移节点 * 6份/h = 78 记录/h; 容量/产出<1 即硬稀缺")
