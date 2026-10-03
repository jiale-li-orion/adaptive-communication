# -*- coding: utf-8 -*-
"""R20 行为见证(witness): 证明 cover 族变体真正进入统一引擎且行为不同,
不再像修复前那样全部退回 EDF。两部分:
 (1) 合成单机会直接调 _cover_family_pack,断言选样集合差异;
 (2) 端到端 r600 单种子,断言 cover_l0only/cover_local/cover2/maxcov 的 svc != edf。"""
import os,sys,types
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_plane import JointControlPlane

def newpol(v):
    pol=object.__new__(JointControlPlane)
    pol.backup_chooser=v; pol._cover_seen=set()
    pol.sample_bytes={"displacement":6}; pol.period_s=600; pol._obl_index={}
    return pol
def mk(sid,node,taken,heard,okeys):
    it=types.SimpleNamespace(heard_at_s=heard,node_id=node,payload=[])
    s=types.SimpleNamespace(sample_id=sid,node_id=node,measurand="displacement",taken_at=taken)
    return (0,it,s,frozenset(okeys))
def ids(picked): return sorted(sx.sample_id for _,sp in picked.values() for sx in sp)
fails=[]
def check(name,cond,detail=""):
    print(("PASS " if cond else "FAIL ")+name+("  "+detail if detail else ""))
    if not cond: fails.append(name)

# --- 场景1: 层0占2条(12B), cap=18 还能补1条 -> cover 补层1, cover_l0only 不补
stream=[mk("a","n1",600,601,{1}), mk("b","n2",600,602,{2}), mk("c","n1",700,701,{1})]
pc=newpol("cover")._cover_family_pack(stream,1000,18)[0]
pl=newpol("cover_l0only")._cover_family_pack(stream,1000,18)[0]
check("S1 cover 层1补满第3条", ids(pc)==["a","b","c"], str(ids(pc)))
check("S1 cover_l0only 仅层0两条", ids(pl)==["a","b"], str(ids(pl)))

# --- 场景2: 跨包 seen 持久 vs cover_local 每包重置; cover2 严格层1拒纯冗余
def two_pack(v):
    pol=newpol(v)
    p1=pol._cover_family_pack([mk("a","n1",600,601,{1})],1000,6)[0]   # 第一包发义务1
    p2=pol._cover_family_pack([mk("d","n1",700,701,{1})],1100,6)[0]   # 第二包只有义务1的更新(纯冗余)
    return ids(p1),ids(p2)
c1,c2=two_pack("cover"); l1,l2=two_pack("cover_local"); x1,x2=two_pack("cover2")
check("S2 cover 第二包层1仍补冗余更新", c2==["d"], str(c2))
check("S2 cover_local 重置seen把更新当层0新装", l2==["d"], str(l2))
check("S2 cover2 严格层1拒绝纯冗余(包空)", x2==[], str(x2))

# --- 场景3: maxcov 按边际覆盖选(容量只够1条): x覆盖2义务 vs y覆盖1但更早dl
# y taken=0 -> dl=1200(更早); x taken=600 -> dl=1800
stream=[mk("y","n1",0,1,{3}), mk("x","n2",600,2,{1,2})]
pm=newpol("maxcov")._cover_family_pack(stream,1000,6)[0]
pcv=newpol("cover")._cover_family_pack(stream,1000,6)[0]
check("S3 maxcov 选边际覆盖更大的x(2义务)", ids(pm)==["x"], str(ids(pm)))
check("S3 cover 层0按dl早选y(1义务) -> 两算法确实不同", ids(pcv)==["y"], str(ids(pcv)))

# --- 场景4: maxcov 无新覆盖也不停发(纯冗余时阶段2补满)
pol=newpol("maxcov"); pol._cover_seen={1,2}
p4,u4=pol._cover_family_pack([mk("r","n1",600,900,{1})],1000,6)
check("S4 maxcov 纯冗余仍发送(不停发)", ids(p4)==["r"] and u4==6, f"{ids(p4)} used={u4}")

# --- Part2: 端到端 r600 单种子, 修复前四个变体==edf(.5038 系), 修复后应不同
from joint_run import run_joint
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
def svc(ch):
    r,_,_=run_joint(seed=0,groups=2,arm="grid600x600",backup_rate_s=600,backup_bytes=78,
                    backup_chooser=ch,**BASE)
    return round(r["routine"]["delivered"]/r["routine"]["n"],4)
res={ch:svc(ch) for ch in ["edf","cover","cover_l0only","cover_local","cover2","maxcov"]}
print("端到端 r600 seed0:",res)
edf=res["edf"]
for v in ["cover_l0only","cover_local","cover2","maxcov"]:
    check(f"P2 {v} 不再退回EDF", abs(res[v]-edf)>0.005, f"{v}={res[v]} edf={edf}")
check("P2 cover 主结果保持高位(>0.85)", res["cover"]>0.85, f"cover={res['cover']}")

print("\n"+("全部见证通过" if not fails else f"{len(fails)} 条失败: {fails}"))
sys.exit(1 if fails else 0)
