# -*- coding: utf-8 -*-
"""论文图3：风险窗(P=300)静态配置前沿 vs 端到端AoI闭环(服务-空口)。读 v3joint_tight.json。"""
import os, sys, json, statistics as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
_RES=os.path.join(_CODE,"..","results")
d=json.load(open(os.path.join(_RES,"v3joint_tight.json")))
def ms(a,k): return st.mean(x[k] for x in d[a])
grid=["grid3600x900","grid1800x900","grid900x600","grid900x300","grid600x600","grid600x300"]
gx=[ms(a,"air") for a in grid]; gy=[ms(a,"rout") for a in grid]
fig,ax=plt.subplots(figsize=(6.4,4.3))
# Pareto 前沿（按 air 排序，保留 rout 递增包络）
order=sorted(range(len(grid)),key=lambda i:gx[i])
px,py=[],[]; best=-1
for i in order:
    if gy[i]>best: best=gy[i]; px.append(gx[i]); py.append(gy[i])
ax.plot(px,py,"-",color="#2c6fbb",lw=1.6,zorder=1,label="Static config. frontier")
ax.scatter(gx,gy,s=55,color="#2c6fbb",zorder=2,label="Static point (sample x report s)")
lab={"grid600x300":"600x300","grid600x600":"600x600","grid900x300":"900x300",
     "grid900x600":"900x600","grid1800x900":"1800x900","grid3600x900":"3600x900"}
off={"600x300":(-2,10),"600x600":(-4,12),"900x300":(8,4),"900x600":(-2,14),
     "1800x900":(10,8),"3600x900":(10,-2)}
for a in grid:
    l=lab[a]; dx,dy=off[l]
    ax.annotate(l,(ms(a,"air"),ms(a,"rout")),xytext=(dx,dy),textcoords="offset points",fontsize=8)
for a,mk,cc in [("ea_aoi","X","#c0392b"),("eh_aoi","D","#e67e22")]:
    ax.scatter(ms(a,"air"),ms(a,"rout"),s=130,marker=mk,color=cc,zorder=3,
               edgecolor="k",linewidth=.6,label={"ea_aoi":"End-to-end AoI+SoC loop","eh_aoi":"Joint EH-AoI loop"}[a])
ax.set_xlabel("Uplink airtime over 48 h (s)")
ax.set_ylabel("Routine obligations delivered on time")
ax.set_title("Risk-window regime (obligation period 300 s, 16-h outage)")
ax.grid(alpha=.25); ax.legend(fontsize=8,loc="lower right")
ax.set_ylim(0,1.0); ax.set_xlim(90,1760)
fig.tight_layout()
out=os.path.join(_RES,"v3joint_frontier.png"); fig.savefig(out,dpi=200)
print("saved",out)
