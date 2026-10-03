# -*- coding: utf-8 -*-
"""R06 机理验证(二)：合法前馈分段(知道 manifest 确定的中断计划 4-20h，不读随机未来)。
采样必须全程=义务周期(中断窗靠备份救、放松采样=断备份粮)；唯一残留成本红利问题：
中断中上报能否降到恰好喂饱备份(300s/78B)而省 LoRa 空口，同时不掉服务。
另含反假设对照：中断中放松采样，预期服务崩。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
import center as C
from center import build_policy
from joint_run import run_joint
# 同 placement 静态对照：前馈分段必须由现场网关经 LoRa 本地执行(中断中回传断、中心不可达)
C.ARMS["g600_gw"]=lambda: build_policy("grid600x600")
H=3600; PRE=4*H; POST=20*H; END=49*H
class ScheduledConfigPolicy(C.CenterPolicy):
    """按已知中断计划分段的前馈静态配置；段切换才发一次成对命令，in_flight/dwell 保护。"""
    def __init__(self,schedule,dwell_s=600):
        super().__init__(); self.sched=sorted(schedule); self.dwell=dwell_s
        self._last={}; self.name="sched"
    def _cfg(self,t):
        for t_end,cfg in self.sched:
            if t<t_end: return cfg
        return self.sched[-1][1]
    def plan(self,view):
        out=[]; si,rp=self._cfg(view.t_s)
        for nid in view.node_ids:
            if nid in view.in_flight: continue
            last=self._last.get(nid)
            if last is not None and view.t_s-last<self.dwell: continue
            snap=view.reports.get(nid) or {}
            if snap.get("sample_interval_s")==si and snap.get("report_period_s")==rp: continue
            self._last[nid]=view.t_s
            a,b=self.stamp_pair(nid,
                {"op":C.OP_SET_SAMPLING_INTERVAL,"interval_s":si},
                {"op":C.OP_SET_REPORT_PERIOD,"period_s":rp})
            out.append((nid,a)); out.append((nid,b))
        return out
def mk(pre,inn,post):
    sch=[(PRE,pre),(POST,inn),(END,post)]
    return lambda: ScheduledConfigPolicy(sch)
# 窗外(pre/post)都满配(600,600)；只变中断中配置
ARMS={
 "g600_gw":            None,                                   # gateway-placement 静态对照
 "sched_full600":      mk((600,600),(600,600),(600,600)),   # 校验:应≈grid600x600
 "in_r300":            mk((600,600),(600,300),(600,600)),   # 中断中更快报
 "in_r600":            mk((600,600),(600,600),(600,600)),
 "in_r900":            mk((600,600),(600,900),(600,600)),   # 中断中放慢报(省空口?)
 "in_r1200":           mk((600,600),(600,1200),(600,600)),
 "in_relaxS1800":      mk((600,600),(1800,600),(600,600)),  # 反假设:放松采样
 "in_both1800":        mk((600,600),(1800,1800),(600,600)),
}
for k,v in ARMS.items():
    if v is not None: C.ARMS[k]=v
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    backup_rate_s=300,backup_bytes=78,harvest_mode='solar',harvest_peak_wh_per_hour=.03,
    initial_soc=1.,blackout_frac=0.,sample_interval_s=600,report_period_s=600,routine_period_s=600)
out={}
for tag in ARMS:
    sv=[];air=[];soc=[];cmd=[];rec=[]
    for s in SEEDS:
        r,_,_=run_joint(seed=s,groups=2,arm=tag,placement="gateway",**BASE)
        rr=r["routine"]; sv.append(rr["delivered"]/rr["n"])
        air.append(r["communication"]["airtime_uplink_h"]*3600)
        soc.append(r["survival"]["mean_final_soc"]); cmd.append(r["communication"]["downlink_attempts"])
        rec.append(r["backup"]["backup_records"])
    out[tag]=dict(svc=round(st.mean(sv),4),svc_min=round(min(sv),3),svc_max=round(max(sv),3),
        air=round(st.mean(air),1),soc=round(st.mean(soc),4),cmd=round(st.mean(cmd),1),brec=round(st.mean(rec),0))
    print(f"{tag:14s} svc={out[tag]['svc']:.4f}[{out[tag]['svc_min']},{out[tag]['svc_max']}] air={out[tag]['air']:.0f}s soc={out[tag]['soc']:.3f} cmd={out[tag]['cmd']:.0f} brec={out[tag]['brec']:.0f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r06_scheduled.json"),"w"),indent=1,ensure_ascii=False)
print("saved")
