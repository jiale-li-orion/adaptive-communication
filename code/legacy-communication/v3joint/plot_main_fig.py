# -*- coding: utf-8 -*-
"""R20 主结果图: (a)服务率 vs 净备份容量(records/h),区分容量稀缺与机会稀疏两类;
(b)四档各 chooser 分组柱,maxcov 黑边高亮、cover2 斜纹。数据读 r08/r20。"""
import json,os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
R="results"
def load(n): return json.load(open(os.path.join(R,n),encoding="utf-8"))
r08=load("v3joint_r08_backup_scarcity.json"); r20=load("v3joint_r20_ablation_fix.json")
PROD=84.0
fig,(ax1,ax2)=plt.subplots(1,2,figsize=(11.5,4.2))

# (a) 容量轴 + 机会稀疏反例
for bytes_,mk,lab in [(78,"o","78 B packets (capacity-scarce)"),(200,"s","200 B packets (opportunity-sparse)")]:
    xs=[];ys=[]
    for tag,v in r08.items():
        if isinstance(v,dict) and "cap_rec_per_h" in v and v["bytes"]==bytes_:
            xs.append(v["cap_rec_per_h"]); ys.append(v["svc"])
    o=sorted(range(len(xs)),key=lambda i:xs[i])
    xs=[xs[i] for i in o]; ys=[ys[i] for i in o]
    ax1.plot(xs,ys,mk+"-",label=lab,ms=6,lw=1.6)
# 标注 r1200/200 反例
v=r08.get("r1200_b200")
if v:
    ax1.annotate("r1200/200: capacity 90/h > production\nbut one packet / 1200 s → .528",
                 xy=(v["cap_rec_per_h"],v["svc"]),xytext=(128,.70),
                 fontsize=8,arrowprops=dict(arrowstyle="->",lw=.8))
ax1.axvline(PROD,ls="--",color="#888",lw=1.2)
ax1.text(PROD+2.5,.40,"production ≈ 84/h",fontsize=8,color="#555",rotation=90,va="bottom")
ax1.set_xlabel("backup net throughput (records / h)"); ax1.set_ylabel("timely obligation coverage")
ax1.set_ylim(.35,1.03); ax1.legend(fontsize=8,loc="lower right"); ax1.grid(alpha=.25)
ax1.set_title("(a) Two scarcity axes: capacity vs. opportunity")

# (b) r20 分组柱
tags=["r300_b78_sat","r600_b78","r900_b78","r1200_b200"]
labels=["saturated\nr300/78","r600/78\n0.69x cap","r900/78\n0.46x cap","r1200/200\nsparse opp."]
chs=["edf","obligation","latest","salvage","cover","cover2","maxcov"]
colors=["#95a5a6","#f39c12","#3498db","#9b59b6","#e67e22","#16a085","#c0392b"]
x=np.arange(len(tags)); w=.115
for j,ch in enumerate(chs):
    vals=[r20[t][ch]["svc"] for t in tags]
    ax2.bar(x+(j-3)*w,vals,w,label=ch,color=colors[j],
            edgecolor="black" if ch=="maxcov" else "none",
            lw=1.5 if ch=="maxcov" else 0,
            hatch="//" if ch=="cover2" else "")
ax2.set_xticks(x); ax2.set_xticklabels(labels,fontsize=8.5)
ax2.set_ylabel("timely obligation coverage"); ax2.set_ylim(.35,1.03)
ax2.set_title("(b) Choosers at identical backup budget (maxcov outlined)")
ax2.legend(fontsize=7.3,ncol=7,loc="lower center",bbox_to_anchor=(.5,-.36),frameon=False,columnspacing=.7)
ax2.grid(axis="y",alpha=.25)
plt.tight_layout()
out=os.path.join(R,"fig_backup_arbitration.png")
plt.savefig(out,dpi=160,bbox_inches="tight"); print("saved",out)
