import math
from mountain_lora_link import itm_loss

def run(freq_mhz, dist_km, elevs, hg=(2.0,2.0)):
    losses, _aref, _fs = itm_loss(freq_mhz, dist_km, hg, elevs, qr_pct=(50.0,))
    return losses[50.0]

if __name__=='__main__':
    fs=lambda d,f=868.0: 20*math.log10(max(d,1e-3))+20*math.log10(f)+32.44
    for d in (1.0,5.0,20.0):
        a=run(868.0,d,[100.0]*80)
        print(f'flat {d:5.1f}km 868MHz: ITM={a:6.1f} dB | free-space={fs(d):6.1f} dB | excess={a-fs(d):6.1f} dB')
    e=[100.0]*20+[500.0]*10+[100.0]*50
    a=run(868.0,5.0,e); print(f'5km with 500m ridge: ITM={a:6.1f} dB | excess over FS={a-fs(5.0):6.1f} dB')
