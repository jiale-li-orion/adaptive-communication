# -*- coding: utf-8 -*-
"""诊断 A: piecewise 义务密度在单一升级 schedule 下为何随小时跳变。"""
import os,sys
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from deployment import build_deployment
from exogenous import piecewise_routine_obligations, routine_obligations_by_node, rule_obligations_for_truth, wang_fragment_truth, displacement_series

dep=build_deployment(groups=2,per_group=None)
meas={k:v.measurand for k,v in nodes_from(dep).items()} if False else None
from network import nodes_from
nodes=nodes_from(dep); meas={k:v.measurand for k,v in nodes.items()}
print("meas=",meas)
SCH=[(0,600,"blue"),(6*3600+150,300,"yellow")]
obs=piecewise_routine_obligations(meas,48,SCH)
print("piecewise routine 总数",len(obs))
from collections import Counter,defaultdict
perh=defaultdict(Counter)
for o in obs:
    perh[int(o.release_at//3600)][o.measurand]+=1
for h in [0,5,6,7,13,14,19,20,24,25,36,37,47]:
    print(f"h{h:2d}: {dict(perh[h])}")
# 检查升级段每节点义务数
up=[o for o in obs if o.release_at>=6*3600+150]
by=Counter((o.node_id) for o in up)
print("升级段各节点义务数:",dict(sorted(by.items())))
