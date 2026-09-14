# -*- coding: utf-8 -*-
"""Figure: phase diagram of closed-loop AoI policy degradation vs open-loop."""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT="/home/orion/Communications/应急通信/project1/agentic communication"
g=json.load(open(ROOT+"/results/v3joint_phase.json",encoding="utf-8"))
PEAKS=[0.003,0.005,0.008,0.012,0.020]; OUT=[0,4,8,16,32]
def mat(arm, metric="rout"):
    return np.array([[g[f"{p}|{o}|{arm}"][metric] for o in OUT] for p in PEAKS])
fixed=mat("fixed900")
ea =(mat("ea_aoi")-fixed)*100
eh =(mat("eh_aoi")-fixed)*100
anchor=mat("anchor")
fig,axs=plt.subplots(1,3,figsize=(12.5,3.9),sharey=True)
fig.subplots_adjust(left=0.07,right=0.91,top=0.78,bottom=0.16,wspace=0.22)
vmin=min(ea.min(),eh.min());
def heat(ax,M,fmt,title,cbarlabel,cmap="Reds_r",show_abs=False):
    im=ax.imshow(M,cmap=cmap,aspect="auto",vmin=(-75 if not show_abs else 0.98),
                 vmax=(0 if not show_abs else 1.0))
    ax.set_xticks(range(len(OUT)));ax.set_xticklabels([str(o) for o in OUT])
    ax.set_xlabel("backhaul outage length (h)")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j,i,fmt(M[i,j]),ha="center",va="center",fontsize=7,
                    color="k")
    ax.set_title(title,fontsize=10)
    return im
heat(axs[0],ea,lambda v:f"{v:.1f}","(a) Energy-AoI policy\n(SoC-gated dense sampling)","loss (pp)")
axs[0].set_ylabel("energy-harvest peak (Wh/h)\n(weak → strong)")
axs[0].set_yticks(range(len(PEAKS)));axs[0].set_yticklabels([f"{p:.3f}" for p in PEAKS])
im1=heat(axs[1],eh,lambda v:f"{v:.1f}","(b) Joint EH-AoI threshold\n(Arafa-style, literature)","loss (pp)")
im2=heat(axs[2],anchor,lambda v:f"{v:.3f}","(c) Delivery-anchored / open-loop\n(this work)","routine",cmap="Greens",show_abs=True)
cb=fig.colorbar(im1,ax=axs[:2].tolist(),fraction=0.06,pad=0.10,shrink=0.85,
                label="routine service loss vs open-loop (pp)")
cb2=fig.colorbar(im2,ax=axs[2],fraction=0.10,pad=0.12,shrink=0.85,
                 label="routine service ratio")
fig.suptitle("Closed-loop AoI control degrades exactly when backhaul is long and energy is scarce; "
             "open-loop stays \u22650.998 across the whole plane",fontsize=9.5,y=0.99)
out=ROOT+"/results/v3joint_phase.png"
fig.savefig(out,dpi=150,bbox_inches="tight");print("saved",out)
