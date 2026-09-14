import json, os, sys
REPO = '/home/orion/Communications/应急通信/project1/agentic communication'
CODE = os.path.join(REPO, 'code')
for p in ('code/v2probe' if False else os.path.join(CODE,'v2probe'),
          os.path.join(CODE,'analysis'), os.path.join(CODE,'experiments'),
          os.path.join(CODE,'instance'), os.path.join(CODE,'monitoring'),
          os.path.join(CODE,'physics'), os.path.join(CODE,'runtime'), CODE):
    if p not in sys.path: sys.path.insert(0, p)
os.chdir(REPO)
import backup_model as bm
from instance_run import one_seed
from trace_seed_timeline import build_kwargs
from first_heard_sufficiency import CONDITIONS, PLACEMENT, predicted_up_ticks

cfg = json.load(open('results/instance_ccorral_iid_c0.05.json', encoding='utf-8'))['config']
base = build_kwargs(dict(cfg)); base.pop('trace', None); base.pop('cache_service', None)

def ledger(cond, seed):
    over = CONDITIONS[cond]; kw = {**base, **over}
    run = one_seed(seed, arm='local', placement=PLACEMENT, trace=True, obligation_ledger=True, **kw)
    end_s = int((base['task_hours']+base['tail_hours'])*3600)
    up = bm.up_hours_from_ticks(predicted_up_ticks(seed, kw, end_s), end_s)
    return bm.rows_from_run(run), up, end_s

# PB 最大的格：P1 r300 K4 (=1.55) 与 r30 K4；逐义务比较 edf / opportunity / all
for cond, rate, K in [('P1_backhaul_4h7h', 300, 4), ('P1_backhaul_4h7h', 30, 4)]:
    print('\n' + '='*90); print(f'{cond}  rate={rate} K={K}  逐种子归因 (all / edf / opportunity)'); print('='*90)
    edf_eq_opp = True
    edf_extra_examples = []
    for seed in range(20):
        rows, up, end_s = ledger(cond, seed)
        r_all = bm.replay(rows, 'backup_all', rate, K, end_s, up)
        r_edf = bm.replay(rows, 'backup_edf', rate, K, end_s, up)
        r_opp = bm.replay(rows, 'backup_opportunity', rate, K, end_s, up)
        if r_edf.per_oid != r_opp.per_oid:
            edf_eq_opp = False
        extra = [o for o in rows if r_edf.per_oid[o.oid] and not r_all.per_oid[o.oid]]
        lost = [o for o in rows if r_all.per_oid[o.oid] and not r_edf.per_oid[o.oid]]
        if extra and len(edf_extra_examples) < 8:
            for o in extra:
                edf_extra_examples.append((seed, o.oid, o.release_at, o.deadline, o.h))
        if extra or lost:
            print(f' seed{seed:2d}: all={r_all.n_final_delivered} edf={r_edf.n_final_delivered}'
                  f' opp={r_opp.n_final_delivered}  EDF比all多救{len(extra)} 反向{len(lost)}')
    print(f' >>> EDF 与 opportunity 逐义务完全相同: {edf_eq_opp}')
    print(' >>> EDF 比 all 多救的义务 (seed,oid,release,deadline,h*):')
    for e in edf_extra_examples: print('    ', e)

# 主例 r120 K9：为什么无差别——统计每个 down 机会的池规模 vs K
print('\n' + '='*90); print('主例 P1 r120 K9：备用机会的待发池规模分布（解释为何 K9 下无需选择）'); print('='*90)
import statistics
for cond in ('P0_no_outage','P1_backhaul_4h7h','P2_access_4h7h'):
    pool_sizes = []
    for seed in range(20):
        rows, up, end_s = ledger(cond, seed)
        sent=set(); t=120
        while t <= end_s:
            cur=t//3600; upnow = cur<len(up) and up[cur]
            if not upnow:
                pool=[o for o in rows if o.oid not in sent and o.h is not None and o.h<=t
                      and o.deadline>=t and not (o.confirmed_at is not None and o.confirmed_at<=t)]
                if pool: pool_sizes.append(len(pool))
                for o in bm.order_pool('backup_edf', pool, t, bm._history_at(t,up))[:9]: sent.add(o.oid)
            t+=120
    if pool_sizes:
        print(f'  {cond:18s} 非空备用机会数={len(pool_sizes)} 池规模 mean={statistics.mean(pool_sizes):.2f}'
              f' max={max(pool_sizes)}  >K9的次数={sum(1 for x in pool_sizes if x>9)}/{len(pool_sizes)}')
