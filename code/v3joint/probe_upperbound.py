# -*- coding: utf-8 -*-
"""上界诊断（不可实现，仅定边界）：若偷看中断窗、只在窗内加密，相对全程 fixed900 能省多少代价？
这决定 C-up 滚动控制器的最大可能收益；上界都赢不了 fixed 就应关闭联合项。"""
import os, sys, statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
import center
from center import CenterPolicy, OP_SET_REPORT_PERIOD
from joint_run import run_joint

class OracleWindowPolicy(CenterPolicy):
    """偷看 outage[lo,hi)：窗内 fast、窗外 slow。仅上界诊断，不是可实现策略。"""
    name="ub"
    def __init__(self, lo_h, hi_h, fast=900, slow=3600, dwell=600):
        super().__init__(); self.lo=lo_h*3600; self.hi=hi_h*3600
        self.fast=fast; self.slow=slow; self.dwell=dwell; self._last={}
    def plan(self, view):
        out=[]
        for nid in view.node_ids:
            if nid in view.in_flight: continue
            l=self._last.get(nid)
            if l is not None and view.t_s-l<self.dwell: continue
            want = self.fast if self.lo<=view.t_s<self.hi else self.slow
            if view.known_report_period(nid)==want: continue
            self._last[nid]=view.t_s
            out.append((nid,self.stamp(nid,op=OP_SET_REPORT_PERIOD,period_s=want)))
        return out

SEEDS=list(range(8))
def run(arm, rate, policy_factory=None, up=.74):
    if policy_factory is not None:
        center.ARMS[arm]=policy_factory
    rs=[run_joint(seed=s,groups=2,arm=arm,task_hours=12,tail_hours=1,
                  outage_start_h=4.0,outage_hours=8.0,uplink_p_arrive=up,
                  enable_backup=True,backup_rate_s=rate,backup_bytes=78,
                  placement=("gateway" if arm=="ub" else "center"))[0] for s in SEEDS]
    def m(p):
        v=[]
        for r in rs:
            x=r
            for k in p.split("."): x=x[k]
            v.append(x)
        return st.mean(v)
    return dict(rout=round(st.mean(r["routine"]["delivered"]/r["routine"]["n"] for r in rs),4),
                event=round(m("event.deliver_rate"),4),
                air=round(m("communication.airtime_uplink_h")*3600,1),
                cmd=round(m("communication.downlink_attempts"),2))

for rate in (120,300,600):
    print(f"\n### rate={rate} full bh8 ###")
    print("  local3600   ", run("local",rate))
    print("  fixed900全程", run("fixed900",rate))
    print("  UB窗内900   ", run("ub",rate,lambda: OracleWindowPolicy(4,12,900,3600)))
    print("  UB窗内300   ", run("ub",rate,lambda: OracleWindowPolicy(4,12,300,3600)))
