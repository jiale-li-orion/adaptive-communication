import math
from itmlogic.preparatory_subroutines.qlrpfl import qlrpfl
from itmlogic.lrprop import lrprop

def run(freq_mhz, dist_km, elevs, hg=(2.0,2.0)):
    npts=len(elevs)
    spacing=dist_km/(npts-1)
    pfl=[npts-1, spacing]+list(elevs)  # pfl[0]=n_intervals, pfl[1]=spacing(km), pfl[2:]=elevations
    prop={'pfl':pfl,'hg':list(hg),'freq':freq_mhz,'ens':301.0,'gme':157e-9,
          'klim':5,'mdvar':3,'pol':1,'eps':15.0,'sgm':0.005,'mdp':-1}
    prop=qlrpfl(prop)
    prop['d']=dist_km
    aref,prop=lrprop(dist_km,prop)
    return aref

if __name__=='__main__':
    fs=lambda d,f=868.0: 20*math.log10(max(d,1e-3))+20*math.log10(f)+32.44
    for d in (1.0,5.0,20.0):
        a=run(868.0,d,[100.0]*80)
        print(f'flat {d:5.1f}km 868MHz: ITM={a:6.1f} dB | free-space={fs(d):6.1f} dB | excess={a-fs(d):6.1f} dB')
    e=[100.0]*20+[500.0]*10+[100.0]*50
    a=run(868.0,5.0,e); print(f'5km with 500m ridge: ITM={a:6.1f} dB | excess over FS={a-fs(5.0):6.1f} dB')
