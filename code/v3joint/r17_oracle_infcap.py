# -*- coding: utf-8 -*-
"""J5-a 宽松上界: 备份净荷无限大(容量不再约束),保留各档真实机会稀疏度(rate)。
回答: 只受'离散机会时刻+样本到网关延迟+义务deadline'约束,最多能救多少义务。
对比 cover 在真实容量下的结果,看上界空间。6种子。"""
import os,sys,json,statistics as st
_HERE=os.path.dirname(os.path.abspath(__file__)); _CODE=os.path.dirname(_HERE)
for p in [_HERE,_CODE]+[os.path.join(_CODE,d) for d in ("physics","runtime","experiments","analysis","monitoring","instance")]:
    if p not in sys.path: sys.path.insert(0,p)
from joint_run import run_joint
SEEDS=(0,1,2,3,4,5)
BASE=dict(task_hours=48,tail_hours=1,outage_start_h=4,outage_hours=16,enable_backup=True,
    harvest_mode='solar',harvest_peak_wh_per_hour=.03,initial_soc=1.,blackout_frac=0.,
    sample_interval_s=600,report_period_s=600,routine_period_s=600)
# 真实档 cover 结果(来自 r14) 供对照
COVER={"r300_b78":.9776,"r600_b78":.9063,"r900_b78":.6985,"r1200_b200":.9214}
RATES={"r300_b78":300,"r600_b78":600,"r900_b78":900,"r1200_b200":1200}
out={}
for tag,rate in RATES.items():
    sv=[]
    for sd in SEEDS:
        r,_,_=run_joint(seed=sd,groups=2,arm="grid600x600",backup_rate_s=rate,
                        backup_bytes=1000000,backup_chooser="cover",**BASE)  # 净荷近无限
        sv.append(r["routine"]["delivered"]/r["routine"]["n"])
    out[tag]=dict(oracle_infcap=round(st.mean(sv),4),lo=round(min(sv),3),hi=round(max(sv),3),
                  cover_real=COVER[tag])
    print(f"{tag:10s} infcap上界={out[tag]['oracle_infcap']:.4f}[{out[tag]['lo']},{out[tag]['hi']}]  cover真实容量={COVER[tag]:.4f}  gap={out[tag]['oracle_infcap']-COVER[tag]:+.4f}",flush=True)
json.dump(out,open(os.path.join(_CODE,"..","results","v3joint_r17_oracle_infcap.json"),"w"),indent=1,ensure_ascii=False)
print("saved r17 oracle infcap")
