# -*- coding: utf-8 -*-
"""R20 修复 R17: 用稳定 oid 做逐义务配对(替换错误的 (node,taken_at) 键)。
断言各臂行数一致、oid 唯一且集合相同; 逐义务比较 received_on_time,定位真实差异。"""
import os,sys,itertools
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600,
    backup_rate_s=600,backup_bytes=78,collect_rows=True)
ARMS=["edf","latest","cover","cover_l0only","cover_local","cover2","maxcov"]
def run(ch,sd=0):
    r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_chooser=ch,**BASE)
    rows=r["rows"]
    oids=[x["oid"] for x in rows]
    assert len(oids)==len(set(oids)), f"{ch}: oid 不唯一"
    return {x["oid"]:bool(x["received_on_time"]) for x in rows}, len(rows)
D={}; nrows={}
for ch in ARMS:
    D[ch],nrows[ch]=run(ch)
print("各臂行数:",nrows)
assert len(set(nrows.values()))==1, "行数不一致"
ks=set.intersection(*[set(d) for d in D.values()])
assert len(ks)==nrows[ARMS[0]], "oid 集合不一致"
print(f"共同 oid={len(ks)} (键唯一、行数一致、集合相同)\n")
def rate(d): return sum(d[k] for k in ks)/len(ks)
print("按期中心收到率:",{ch:round(rate(D[ch]),4) for ch in ARMS},"\n")
for a,b in itertools.combinations(ARMS,2):
    ab=[k for k in ks if D[a][k] and not D[b][k]]
    ba=[k for k in ks if D[b][k] and not D[a][k]]
    same=sum(D[a][k]==D[b][k] for k in ks)
    print(f"{a:12s} vs {b:12s}: 一致{same}/{len(ks)}={same/len(ks):.3f}  {a}成{b}败={len(ab):3d}  {b}成{a}败={len(ba):3d}")
# 重点: cover 救回而 maxcov 没救 / 反之, 抽样看
for a,b in [("cover","maxcov"),("cover","cover2"),("cover","cover_local"),("cover","cover_l0only")]:
    ab=[k for k in ks if D[a][k] and not D[b][k]]
    ba=[k for k in ks if D[b][k] and not D[a][k]]
    print(f"\n[{a} vs {b}] {a}独有救回 {len(ab)} 个, {b}独有救回 {len(ba)} 个")
    if ab: print("  ",a,"独有样例 oid:",sorted(ab)[:8])
    if ba: print("  ",b,"独有样例 oid:",sorted(ba)[:8])
