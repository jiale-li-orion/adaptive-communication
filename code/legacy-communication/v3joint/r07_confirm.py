# -*- coding: utf-8 -*-
"""R07 冻结确认：未参与开发的种子 6-9，只跑决定结论的 4 个臂，验证静态支配稳健。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
import center as C
from center import RollingConfigSearchPolicy, build_policy
from joint_run import run_joint
H=3600
C.ARMS["rolling_search"]=lambda: RollingConfigSearchPolicy(
    routine_period_s=600,uplink_p=.74,backhaul_p=.62,harvest_wh_per_hour=.03,
    capacity_wh=.05,horizon_end_s=48*H,dwell_s=600)
class ScheduledConfigPolicy(C.CenterPolicy):
    def __init__(self,schedule,dwell_s=600):
        super().__init__(); self.sched=sorted(schedule); self.dwell=dwell_s; self._last={}
    def _cfg(self,t):
        for te,c in self.sched:
            if t<te: return c
        return self.sched[-1][1]
    def plan(self,view):
        out=[]; si,rp=self._cfg(view.t_s)
        for nid in view.node_ids:
            if nid in view.in_flight: continue
            l=self._last.get(nid)
            if l is not None and view.t_s-l<self.dwell: continue
            snap=view.reports.get(nid) or {}
            if snap.get("sample_interval_s")==si and snap.get("report_period_s")==rp: continue
            self._last[nid]=view.t_s
            a,b=self.stamp_pair(nid,{"op":C.OP_SET_SAMPLING_INTERVAL,"interval_s":si},
                                    {"op":C.OP_SET_REPORT_PERIOD,"period_s":rp})
            out.append((nid,a)); out.append((nid,b))
        return out
C.ARMS["in_r900"]=lambda: ScheduledConfigPolicy([(4*H,(600,600)),(20*H,(600,900)),(49*H,(600,600))])
SEEDS=(6,7,8,9)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=600,report_period_s=600,routine_period_s=600)
ARMS=[("grid600x600","grid600x600","center",{}),
      ("ODP_joint","odp","gateway",{}),
      ("rolling_MPC","rolling_search","center",{}),
      ("in_r900","in_r900","gateway",{})]
out={}
for tag,arm,place,kw in ARMS:
    rows=[]
    for s in SEEDS:
        r,_,_=run_joint(seed=s,groups=2,arm=arm,placement=place,**BASE,**kw)
        rr=r["routine"]; v=rr["delivered"]/rr["n"]
        rows.append((v,r["communication"]["airtime_uplink_h"]*3600,r["survival"]["mean_final_soc"]))
        print(f"{tag:12s} seed{s} svc={v:.4f} air={rows[-1][1]:.0f} soc={rows[-1][2]:.3f}",flush=True)
    out[tag]=dict(svc=[round(x[0],4) for x in rows],svc_mean=round(st.mean(x[0] for x in rows),4),
        air=round(st.mean(x[1] for x in rows),1),soc=round(st.mean(x[2] for x in rows),4))
    print(f"  -> {tag:12s} mean={out[tag]['svc_mean']:.4f}\n",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r07_confirm_seeds69.json"),"w"),indent=1,ensure_ascii=False)
print("saved r07")
