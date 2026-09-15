# -*- coding: utf-8 -*-
"""R06 机理验证(一)：紧regime下 .984 是谁救回来的——备份 on/off 分解。
若 off 时服务掉到~2/3(中断16/48h窗全废)、on 时靠备份回到.98，则证明中断窗交付依赖备份，
"中断中放松采样"是错误方向(会断备份粮)。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=600,report_period_s=600,routine_period_s=600)
outm={}
for en in (True,False):
    sv=[];rec=[];pkt=[];air=[];soc=[]
    for s in SEEDS:
        r,_,_=run_joint(seed=s,groups=2,arm="grid600x600",enable_backup=en,**BASE)
        rr=r["routine"]; sv.append(rr["delivered"]/rr["n"])
        b=r["backup"]; rec.append(b.get("backup_records",0)); pkt.append(b.get("backup_packets",0))
        air.append(r["communication"]["airtime_uplink_h"]*3600); soc.append(r["survival"]["mean_final_soc"])
    outm[f"backup_{en}"]=dict(svc=round(st.mean(sv),4),svc_min=round(min(sv),3),svc_max=round(max(sv),3),
        backup_records=round(st.mean(rec),0),packets=round(st.mean(pkt),0),
        air_s=round(st.mean(air),1),soc=round(st.mean(soc),4))
    print(f"backup={en}: svc={st.mean(sv):.4f} [{min(sv):.3f},{max(sv):.3f}]  "
          f"backup_records={st.mean(rec):.0f} packets={st.mean(pkt):.0f} air={st.mean(air):.0f}s soc={st.mean(soc):.3f}",flush=True)
outm["in_outage_obligations_displacement"]=13*16*6
json.dump(outm,open(os.path.join(_CODE,"..","results","v3joint_r06_backup_mech.json"),"w"),indent=1,ensure_ascii=False)
print("saved r06_backup_mech")
