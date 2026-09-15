# -*- coding: utf-8 -*-
"""论文主结果图: (a)服务率 vs 备份容量/产出比 相变; (b)四档各chooser分组柱(cover高亮)。"""
import json,os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R="results"
def load(n): return json.load(open(os.path.join(R,n),encoding="utf-8"))
r08=load("v3joint_r08_backup_scarcity.json"); r14=load("v3joint_r14_cover_fixed.json")
PROD=78.0
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(11,4.0))

# (a) phase transition
xs,ys=[],[]
for tag,v in r08.items():
    if isinstance(v,dict) and "cap_rec_per_h" in v:
        xs.append(v["cap_rec_per_h"]/PROD); ys.append(v["svc"])
order=sorted(range(len(xs)),key=lambda i:xs[i])
xs=[xs[i] for i in order]; ys=[ys[i] for i in order]
ax1.plot(xs,ys,"o-",color="#333",lw=1.8,ms=6)
ax1.axvline(1.0,ls="--",color="#c0392b",lw=1.3)
ax1.text(1.03,.55,"capacity = production",color="#c0392b",fontsize=9,rotation=90,va="center")
ax1.set_xscale("log"); ax1.set_xlabel("backup net throughput / production (records/h)")
ax1.set_ylabel("timely obligation coverage"); ax1.set_ylim(.35,1.02)
ax1.set_title("(a) Scarcity phase transition (item-level packing)")
ax1.grid(alpha=.25)

# (b) grouped bars
tags=["r300_b78_sat","r600_b78","r900_b78","r1200_b200"]
labels=["saturated\nr300/78B","r600/78B\n0.69x","r900/78B\n0.46x","r1200/200B\n1.15x sparse"]
chs=["edf","obligation","latest","salvage","cover"]
colors=["#95a5a6","#f39c12","#3498db","#9b59b6","#c0392b"]
import numpy as np
x=np.arange(len(tags)); w=.16
for j,ch in enumerate(chs):
    vals=[r14[t][ch]["svc"] if isinstance(r14[t][ch],dict) else r14[t][ch] for t in tags]
    ax2.bar(x+(j-2)*w,vals,w,label=ch,color=colors[j],
            edgecolor="black" if ch=="cover" else "none",lw=1.4 if ch=="cover" else 0)
ax2.set_xticks(x); ax2.set_xticklabels(labels,fontsize=8.5)
ax2.set_ylabel("timely obligation coverage"); ax2.set_ylim(.35,1.02)
ax2.set_title("(b) Choosers at identical backup budget (cover in red)")
ax2.legend(fontsize=8,ncol=5,loc="lower center",bbox_to_anchor=(.5,-.34),frameon=False)
ax2.grid(axis="y",alpha=.25)
plt.tight_layout()
out=os.path.join(R,"fig_backup_arbitration.png")
plt.savefig(out,dpi=160,bbox_inches="tight"); print("saved",out)
