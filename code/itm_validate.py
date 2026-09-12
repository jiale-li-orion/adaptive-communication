import math, numpy as np, sys
sys.path.insert(0,'/home/orion/Communications/code')
from mountain_lora_feasibility import itm_point_to_point, read_hgt, profile, haversine_km, elev_at

fs=lambda d,f=868.0: 20*math.log10(d)+20*math.log10(f)-27.55

print("=== A. sensitivity to the TERRAIN PROFILE (same distance, diff terrain) ===")
n=200; d=10.0
flat=[2000.0]*n
ridge=[2000.0]*(n//2)+[3200.0]*(n//2)          # 1200 m wall right at the midpoint
slope=list(np.linspace(2000,3200,n))            # monotonic climb
for nm,p in [("flat 2km elev",flat),("1200m ridge",ridge),("2000->3200 slope",slope)]:
    a,reg=itm_point_to_point(868.0,d,(2.0,2.0),p)
    print(f"  {nm:<20} aref={a:6.1f} dB  regime={reg:<16} excess over FS={a-fs(d):6.1f} dB")

print("\n=== B. distance sweep, real Yigong terrain (flat-ish vs real) ===")
dem=read_hgt("N30E094"); tile="N30E094"
gw=(30.330,94.780)
for d in (1,2,5,10,20,30):
    # real profile along a bearing
    pt=(gw[0]-d/111.0*0.6, gw[1]+d/111.0*0.8)
    dreal=haversine_km(gw,pt)
    prof=profile(dem,tile,gw,pt,200)
    a,reg=itm_point_to_point(868.0,dreal,(2.0,2.0),prof)
    print(f"  d={dreal:5.2f} km  FS={fs(dreal):5.1f}  ITM={a:6.1f}  excess={a-fs(dreal):6.1f}  {reg}")

print("\n=== C. does ITM see the profile? real vs flattened at identical distance ===")
pt=(30.200,94.930); d=haversine_km(gw,pt); prof=profile(dem,tile,gw,pt,200)
a_real,r1=itm_point_to_point(868.0,d,(2.0,2.0),prof)
flat=[float(np.mean(prof))]*200
a_flat,r2=itm_point_to_point(868.0,d,(2.0,2.0),flat)
a_smooth,reg3=itm_point_to_point(868.0,d,(2.0,2.0),list(np.linspace(prof[0],prof[-1],200)))
print(f"  real profile      aref={a_real:6.1f}  {r1}")
print(f"  flat (mean elev)  aref={a_flat:6.1f}  {r2}")
print(f"  smooth ramp       aref={a_smooth:6.1f}  {reg3}")
print(f"  --> terrain penalty (real - flat) = {a_real-a_flat:.1f} dB")
