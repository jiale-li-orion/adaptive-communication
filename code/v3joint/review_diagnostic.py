"""Read-only behavioral audit: collect arrival events without changing the simulator."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from types import SimpleNamespace
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'code/v3joint'))
from joint_run import run_joint
from network import Center, Instance
from scoring import evaluate
from joint_policy import DeliveryOpportunisticPolicy, GatewayObserver

original_receive = Center.receive
original_heard = Instance._note_gateway_heard

def audit(arm, **condition):
    first_received, first_heard, arrivals = {}, {}, Counter()
    snapshot_regressions = []
    backup_arrivals = Counter()
    def observe_receive(self, item, t_s):
        for sample in item.payload or ():
            first_received.setdefault(sample.sample_id, t_s)
            arrivals[sample.sample_id] += 1
            if item.kind == 'backup':
                backup_arrivals[sample.sample_id] += 1
        prev = self.reports.get(item.node_id)
        if prev and item.snapshot and item.snapshot['read_at'] < prev['read_at']:
            snapshot_regressions.append({'at': t_s, 'node_id': item.node_id,
                'old_read_at': prev['read_at'], 'new_read_at': item.snapshot['read_at'],
                'old_soc_wh': prev['soc_wh'], 'new_soc_wh': item.snapshot['soc_wh'],
                'path': item.kind})
        return original_receive(self, item, t_s)
    def observe_heard(self, node, t_s, batch):
        for sample in batch:
            first_heard.setdefault(sample.sample_id, t_s)
        return original_heard(self, node, t_s, batch)
    Center.receive, Instance._note_gateway_heard = observe_receive, observe_heard
    try:
        res, inst, obligations = run_joint(seed=0, groups=2, arm=arm,
                                          collect_rows=True, **condition)
    finally:
        Center.receive, Instance._note_gateway_heard = original_receive, original_heard
    replay, _, _ = run_joint(seed=0, groups=2, arm=arm, collect_rows=True, **condition)
    assert res == replay, 'Observer changed a result field'
    revised_log = copy.copy(inst.log)
    revised_log.transit = {sid: copy.copy(tr) for sid, tr in inst.log.transit.items()}
    for sid, tr in revised_log.transit.items():
        tr.received_at = first_received.get(sid)
        tr.heard_at = first_heard.get(sid)
    rescored = evaluate(obligations, revised_log,
        condition['task_hours'] + condition['tail_hours'], inst.nodes.keys(),
        task_hours=condition['task_hours'], collect_rows=True)
    original_rows = {r['oid']: r for r in res['rows']}
    changed_rows = [{'oid': r['oid'], 'before': original_rows[r['oid']]['delivered'],
                     'after': r['delivered'], 'deadline': r['deadline'],
                     'old_first_received_at': original_rows[r['oid']]['first_received_at'],
                     'true_first_received_at': r['first_received_at']}
                    for r in rescored['rows']
                    if r['delivered'] != original_rows[r['oid']]['delivered']]
    return {'arm': arm, 'seed': 0, 'condition': condition,
        'official_by_kind': res['by_kind'], 'first_arrival_by_kind': rescored['by_kind'],
        'survival': res['survival'], 'backup': res['backup'],
        'observer_all_result_fields_identical': res == replay,
        'dead_with_enough_final_energy_to_sample': [nid for nid, node in inst.nodes.items()
                                                   if not node.alive and node.soc_wh >= node.p.sample_wh],
        'final_report_periods_s': {nid: node.report_period_s for nid,node in inst.nodes.items()},
        'arrival_events': sum(arrivals.values()), 'distinct_arriving_samples': len(arrivals),
        'samples_delivered_more_than_once': sum(v > 1 for v in arrivals.values()),
        'samples_delivered_by_backup_more_than_once': sum(v > 1 for v in backup_arrivals.values()),
        'received_at_later_than_first': sum(tr.received_at != first_received.get(sid)
                                           for sid,tr in inst.log.transit.items()),
        'heard_at_later_than_first': sum(tr.heard_at != first_heard.get(sid)
                                        for sid,tr in inst.log.transit.items()),
        'snapshot_regressions_count': len(snapshot_regressions),
        'snapshot_regressions_first_10': snapshot_regressions[:10],
        'changed_rows_count': len(changed_rows), 'changed_rows_first_20': changed_rows[:20],
        'note': 'Observer only. Re-scoring uses first arrivals; policies and trajectories are unchanged. No simulator fix or causal intervention.'}

def branch_audit():
    observer = GatewayObserver(backup_rate_s=300)
    observer.plane = SimpleNamespace(backhaul_available=lambda _: False)
    result = []
    for period in (3600, 300):
        for use_window in (False, True):
            policy = DeliveryOpportunisticPolicy(observer, period_s=period,
                                                 use_backup_window=use_window)
            wants = set()
            for t in range(0, 48 * 3600, 60):
                view = SimpleNamespace(t_s=t, soc_of=lambda _: 0.05,
                                       gateway_copies_in_window={})
                wants.add(policy._want(view, 'n00'))
            result.append(dict(period_s=period, use_backup_window=use_window,
                               generated_targets=sorted(wants)))
    return dict(scope='Constructed healthy/primary-down/no-copy views, all ticks in 48h; branch audit, not business performance',
                rows=result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/v3joint_review_diagnostic.json'))
    parser.add_argument('--include-tight', action='store_true',
                        help='Also replay seed 0 of probe_diag_tight openloop, which is much slower')
    args = parser.parse_args()
    condition = dict(task_hours=48, tail_hours=1, outage_start_h=4.0, outage_hours=16.0,
        enable_backup=True, backup_rate_s=300, backup_bytes=78, harvest_mode='solar',
        initial_soc=0.5, harvest_peak_wh_per_hour=0.005, blackout_frac=0.3, blackout_start_h=4.0)
    records = []
    cases = [(arm, condition) for arm in ('fixed900', 'ea_aoi')]
    if args.include_tight:
        tight = dict(task_hours=48, tail_hours=1, outage_start_h=4., outage_hours=16.,
            enable_backup=True, backup_rate_s=300, backup_bytes=78, harvest_mode='solar',
            initial_soc=1., harvest_peak_wh_per_hour=.03, blackout_frac=0.,
            sample_interval_s=300, report_period_s=300, routine_period_s=300)
        cases.append(('fixed900', tight))
    for arm, config in cases:
        r = audit(arm, **config)
        records.append(r)
        print(json.dumps({k:r[k] for k in ('arm','condition','official_by_kind',
                         'first_arrival_by_kind','survival','changed_rows_count',
                         'observer_all_result_fields_identical')}, ensure_ascii=False), flush=True)
    files = ['code/instance/network.py', 'code/instance/scoring.py', 'code/instance/center.py',
             'code/monitoring/opportunity.py', 'code/v3joint/joint_run.py',
             'code/v3joint/joint_plane.py', 'code/v3joint/joint_policy.py']
    payload = {'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=REPO, text=True).strip(),
               'source_sha256': {f: hashlib.sha256((REPO/f).read_bytes()).hexdigest() for f in files},
               'scope': 'Existing published conditions, seed 0; observer and branch diagnostics only, no new candidate or simulator fix',
               'branch_audit': branch_audit(), 'records': records}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    print(f'Saved {args.output}', flush=True)
