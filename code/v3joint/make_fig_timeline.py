# -*- coding: utf-8 -*-
"""Figure: single-node causal timeline (seed0/n00, stressed) — SoC death vs sampling regime."""
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT="/home/orion/Communications/应急通信/project1/agentic communication"
for p in [ROOT+"/code/v3joint",ROOT+"/libs/pylibs"]+[ROOT+"/code/"+d for d in
          ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
COND=dict(task_hours=48,tail_hours=1,outage_start_h=4.0,outage_hours=16.0,
          enable_backup=True,backup_rate_s=300,backup_bytes=78,harvest_mode="solar",
          harvest_peak_wh_per_hour=0.005,initial_soc=0.5,blackout_frac=0.3,
          blackout_start_h=4.0,trace=True)
ARMS=[("Energy-AoI (ea)","ea_aoi",True,True,"#d62728"),
      ("Joint EH-AoI (eh, lit.)","eh_aoi",True,True,"#ff7f0e"),
      ("Delivery-anchored","cup",False,True,"#2ca02c"),
      ("Open-loop fixed","fixed900",True,True,"#1f77b4")]
nid="n00"
fig,(ax1,ax2)=plt.subplots(2,1,figsize=(9,6.4),sharex=True)
_death_labeled=False
for label,arm,uw,gs,color in ARMS:
    _,inst,_=run_joint(seed=0,groups=2,arm=arm,cup_use_window=uw,cup_gate_sampling=gs,**COND)
    ts=[];soc=[];si=[];alive=[]
    for ev in inst.trace_events:
        if ev[2]=="state" and ev[1]==nid:
            ts.append(ev[0]/3600);soc.append(ev[5]*1000);si.append(ev[3]);alive.append(ev[6])
    ts=np.array(ts);soc=np.array(soc);si=np.array(si);alive=np.array(alive)
    ax1.plot(ts,soc,color=color,lw=1.8,label=label)
    ax2.plot(ts,si,color=color,lw=1.6)
    died=np.where((alive[:-1]>0)&(alive[1:]==0))[0]
    if len(died):
        k=died[0]
        ax1.scatter([ts[k+1]],[soc[k+1]],color=color,zorder=5,s=60,marker="x",lw=2.2)
        global_death = not _death_labeled
        if global_death:
            ax1.annotate("permanent death at h16:\nbattery later recharges but\nthe node never reports again",
                         (ts[k+1],1.5),xytext=(21,10),fontsize=8,color="k",
                         arrowprops=dict(arrowstyle="->",color="grey",lw=1))
            _death_labeled=True
for ax in (ax1,ax2):
    ax.axvspan(4,20,color="grey",alpha=0.15)
ax1.text(12,43.5,"backhaul outage h4–h20",ha="center",fontsize=8.5,color="dimgrey")
ax2.text(12,2200,"backhaul outage h4–h20",ha="center",fontsize=8.5,color="dimgrey")
ax1.axhline(0.47,color="k",ls=":",lw=1)  # one sample energy 4.7e-4 Wh = 0.47 mWh
ax1.text(30,1.6,"one-sample energy floor (below it the node is declared dead)",fontsize=7.5)
ax1.set_ylabel("battery state of charge (mWh)")
ax1.legend(fontsize=8,loc="center left",bbox_to_anchor=(0.50,0.52),framealpha=0.9)
ax1.set_title("Node n00 under a 16-h backhaul outage + weak harvesting: end-to-end-AoI closed loops "
              "drain and die, open-loop survives",fontsize=9.5)
ax2.set_ylabel("sampling interval (s)");ax2.set_yticks([600,3600])
ax2.set_ylim(0,3900)
ax2.text(0.3,750,"dense 600 s (6\u00d7 sampling, closed loops)",fontsize=7.5)
ax2.text(0.3,3450,"sparse 3600 s (open-loop / delivery-anchored)",fontsize=7.5)
ax2.set_xlabel("elapsed time (h)")
fig.tight_layout()
out=ROOT+"/results/v3joint_timeline.png"
fig.savefig(out,dpi=150,bbox_inches="tight");print("saved",out)
