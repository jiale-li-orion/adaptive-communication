#!/usr/bin/env python3
"""Derive pinned Connecta SGP4 geometry for an explicit site coordinate."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import math

from sgp4.api import Satrec, jday

ROOT=Path(__file__).resolve().parents[3]
TLE=ROOT/'data/downloads/connecta_gp_2026-09-22/connecta_iot.tle'
START=datetime(2026,9,22,8,0,0,tzinfo=timezone.utc)
HOURS=48
STEP_S=60
THRESHOLDS=(0,5,10,20,30)


def gmst(dt):
    jd,fr=jday(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second+dt.microsecond/1e6)
    x=jd+fr
    t=(x-2451545.0)/36525.0
    deg=280.46061837+360.98564736629*(x-2451545.0)+0.000387933*t*t-t*t*t/38710000.0
    return math.radians(deg%360)


def observer_eci(dt, lat_deg, lon_deg, alt_m):
    a=6378.137; f=1/298.257223563; e2=f*(2-f)
    lat=math.radians(lat_deg); lon=math.radians(lon_deg); h=alt_m/1000
    n=a/math.sqrt(1-e2*math.sin(lat)**2)
    x=(n+h)*math.cos(lat)*math.cos(lon)
    y=(n+h)*math.cos(lat)*math.sin(lon)
    z=(n*(1-e2)+h)*math.sin(lat)
    th=gmst(dt)
    return (math.cos(th)*x-math.sin(th)*y, math.sin(th)*x+math.cos(th)*y, z)


def elev_deg(sat,dt,lat_deg,lon_deg,alt_m):
    sec=dt.second+dt.microsecond/1e6
    jd,fr=jday(dt.year,dt.month,dt.day,dt.hour,dt.minute,sec)
    e,r,_=sat.sgp4(jd,fr)
    if e: return None
    ox,oy,oz=observer_eci(dt,lat_deg,lon_deg,alt_m)
    rx,ry,rz=r[0]-ox,r[1]-oy,r[2]-oz
    lat=math.radians(lat_deg); lon_eci=math.radians(lon_deg)+gmst(dt)
    ux,uy,uz=math.cos(lat)*math.cos(lon_eci),math.cos(lat)*math.sin(lon_eci),math.sin(lat)
    rng=math.sqrt(rx*rx+ry*ry+rz*rz)
    return math.degrees(math.asin((rx*ux+ry*uy+rz*uz)/rng))


def derive(lat,lon,alt_m):
    lines=[x.strip() for x in TLE.read_text().splitlines() if x.strip()]
    sats=[(lines[i],Satrec.twoline2rv(lines[i+1],lines[i+2])) for i in range(0,len(lines),3)]
    summary={}
    for thr in THRESHOLDS:
        vis=[]
        for k in range(HOURS*3600//STEP_S):
            dt=START+timedelta(seconds=k*STEP_S)
            els=[elev_deg(s,dt,lat,lon,alt_m) for _,s in sats]
            vis.append(any(x is not None and x>=thr for x in els))
        windows=[]; st=None
        for k,x in enumerate(vis+[False]):
            if x and st is None: st=k
            if not x and st is not None:
                windows.append((st,k)); st=None
        gaps=[]; prev=0
        for a,b in windows:
            gaps.append((a-prev)*STEP_S); prev=b
        gaps.append((len(vis)-prev)*STEP_S)
        total=sum((b-a)*STEP_S for a,b in windows)
        summary[str(thr)]={
            'visible_fraction':sum(vis)/len(vis),
            'windows':len(windows),
            'total_visible_min':total/60,
            'mean_window_min':total/60/len(windows) if windows else 0,
            'max_gap_min':max(gaps)/60,
            'windows_utc':[
                {
                    'start':(START+timedelta(seconds=a*STEP_S)).isoformat(),
                    'end':(START+timedelta(seconds=b*STEP_S)).isoformat(),
                    'duration_min':(b-a)*STEP_S/60,
                } for a,b in windows
            ],
        }
    return {
        'status':'orbit-derived geometry, not measured contact/PHY success',
        'site':{'lat':lat,'lon':lon,'alt_m':alt_m},
        'start_utc':START.isoformat(),'hours':HOURS,'step_s':STEP_S,
        'satellites':[n for n,_ in sats],'thresholds':summary,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--lat',type=float,required=True)
    ap.add_argument('--lon',type=float,required=True)
    ap.add_argument('--alt-m',type=float,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    out=derive(a.lat,a.lon,a.alt_m)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!='windows_utc'} for k,v in out['thresholds'].items()},indent=2))


if __name__=='__main__':
    main()
