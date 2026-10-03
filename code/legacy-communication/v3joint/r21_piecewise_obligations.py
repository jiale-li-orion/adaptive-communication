# -*- coding: utf-8 -*-
"""顺序1 单测: 分段义务生成器语义(无变更 bit-identical / 升级加密 / 降级保留旧义务 / oid 唯一)。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from exogenous import routine_obligations_by_node, piecewise_routine_obligations, Obligation
fails=[]
def check(n,c,d=""):
    print(("PASS " if c else "FAIL ")+n+("  "+str(d) if d else ""))
    if not c: fails.append(n)

meas={"n0":"displacement","gw0":"rainfall"}; H=48
# 1) 单段恒定 == 原函数 bit-identical
base=routine_obligations_by_node(meas,H,period_s=600)
same=piecewise_routine_obligations(meas,H,[(0,600,"blue")])
check("单段委托与原函数数量一致",len(base)==len(same),(len(base),len(same)))
check("单段委托 oid 集合完全相同",{o.oid for o in base}=={o.oid for o in same})
check("单段委托 window/deadline 完全相同",
      all((a.release_at,a.window,a.deadline)==(b.release_at,b.window,b.deadline)
          for a,b in zip(sorted(base,key=lambda o:o.oid),sorted(same,key=lambda o:o.oid))))

def by_node(obs):
    d={}
    for o in obs: d.setdefault(o.node_id,[]).append(o)
    for v in d.values(): v.sort(key=lambda o:o.release_at)
    return d

# 2) 升级: 4h(14400s) 起 600->300
up=piecewise_routine_obligations(meas,H,[(0,600,"blue"),(14400,300,"yellow")])
u=by_node(up); b=by_node(base)
n0_up=u["n0"]
before=[o for o in n0_up if o.release_at<14400]; after=[o for o in n0_up if o.release_at>=14400]
check("升级前段(4h@600)每节点24条",len(before)==24,len(before))
check("升级后段(44h@300)每节点528条",len(after)==528,len(after))
check("升级后总数多于恒定600",len(up)>len(base),(len(up),len(base)))
# 变更前最后疏义务 release=13800, deadline=13800+2*600=15000 跨过变更点仍保留
cross=[o for o in n0_up if o.release_at==13800]
check("跨变更点旧疏义务保留且deadline=15000",len(cross)==1 and cross[0].deadline==15000,
      [(o.oid,o.deadline) for o in cross])
# 升级后首个密义务 release=14400 window=(14400,14700)
first=after[0]
check("升级后首密义务起于14400、窗口300",first.release_at==14400 and first.window==(14400,14700),
      (first.release_at,first.window))

# 3) 降级: 4h 起 300->600; 旧密义务保留到 deadline
dn=piecewise_routine_obligations(meas,H,[(0,300,"yellow"),(14400,600,"blue")])
d=by_node(dn)
last_dense=[o for o in d["n0"] if o.release_at<14400]
after_d=[o for o in d["n0"] if o.release_at>=14400]
check("降级前密段(4h@300)每节点48条",len(last_dense)==48,len(last_dense))
check("降级后疏段(44h@600)每节点264条",len(after_d)==264,len(after_d))
# release=14100 的密义务 deadline=14100+600=14700 保留到变更后
keep=[o for o in d["n0"] if o.release_at==14100]
check("降级时未到期旧密义务保留(deadline14700>14400)",len(keep)==1 and keep[0].deadline==14700,
      [(o.oid,o.deadline) for o in keep])

# 4) oid 在单个义务集合内全局唯一; 所有 window 合法; 无 release 越界
for tag,obs in (("升级",up),("降级",dn)):
    ids=[o.oid for o in obs]
    check(f"{tag}集合内 oid 唯一",len(ids)==len(set(ids)),(len(ids),len(set(ids))))
check("window 长度=该段周期, deadline=window末+grace",
      all(o.window[1]-o.window[0]==o.grace_s and o.deadline==o.window[1]+o.grace_s for o in up))
check("无 release 超出任务时长",all(o.release_at<H*3600 for o in up))

# 5) 一份变更后密样本可匹配相邻密义务(多对多由 matches 支持,这里仅核对窗口相邻不重叠缺漏)
gaps=[after[i+1].window[0]-after[i].window[0] for i in range(min(20,len(after)-1))]
check("升级后密义务窗口等距300无缺漏",all(g==300 for g in gaps),gaps[:5])

print("\n"+("全部通过" if not fails else f"{len(fails)} 失败: {fails}"))
sys.exit(1 if fails else 0)
