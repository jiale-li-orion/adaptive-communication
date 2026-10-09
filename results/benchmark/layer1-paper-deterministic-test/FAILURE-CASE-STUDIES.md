# Layer-1 Failure Case Studies

These are rule-selected illustrative diagnostics from the frozen deterministic paper test; they do not change the benchmark or effect estimates.

## Delivery-only failure

- `paper:test:O1:2024:w0:seed-100::comm.local_policy`
- routine: {'n': 168, 'delivered': 162, 'missing_collection': 0, 'missing_delivery': 6, 'censored': 0, 'aoi_mean_s': 2863.0282485875705, 'aoi_p50_s': 2220, 'aoi_p90_s': 6420, 'aoi_p95_s': 8580, 'no_observation_s': 18000, 'latency_mean_s': 866.6666666666666, 'latency_p50_s': 0, 'latency_p90_s': 3600, 'latency_p95_s': 3600}
- failed obligation classes: {'COLLECTED_BUT_NEVER_HEARD_AT_GATEWAY': 3, 'LATE_TO_GATEWAY': 3}
- first failed obligation: `n15:routine:00005` (release 18000s, deadline 25200s, first gateway heard 28800)

## Energy / collection failure

- `paper:test:O4:2024:w0:seed-100::comm.ea_aoi`
- dead nodes: ['n13']
- dead-node lifecycle: {'n13': {'first_alive_false_s': 39000, 'last_sample_taken_at_s': 38400, 'power': {'soc_initial_wh': 0.03, 'soc_final_wh': 0.0004485143039999421, 'harvested_wh': 0.0, 'consumed_wh': 0.029551485696000055, 'deficit_s': 7740, 'dead_at_s': None}, 'missing_collection_obligations': 1, 'first_missing_obligation': {'oid': 'n13:routine:00011', 'kind': 'routine', 'node_id': 'n13', 'release_at': 39600, 'collected': False, 'delivered': False, 'censored': False, 'delivered_at': None, 'latency_s': None, 'deadline': 46800, 'first_heard_at': None, 'first_received_at': None, 'heard_on_time': False, 'received_on_time': False, 'n_matching': 0, 'n_heard': 0, 'n_received': 0, 'heard': False}}}

## Task-revision execution failure

- `paper:test:O2:2024:w0:seed-100::comm.mission_comply`
- task schedule: [[0, 3600, 'blue'], [21600, 300, 'yellow']]
- outage: {'outage_start_s': 14400, 'outage_end_s': 28800}
- first plan/sent/applied: {'plan': 21600, 'sent': 36000, 'applied': 36000}
- nodes with both dense settings applied: ['n00', 'n01', 'n03', 'n04', 'n06', 'n11']
- revision completion rate: 0.2857142857142857
- failure classes: {'COLLECTED_BUT_NEVER_HEARD_AT_GATEWAY': 36, 'COLLECTION_MISS_NO_MATCHING_SAMPLE': 706, 'LATE_TO_GATEWAY': 132, 'ON_TIME_GATEWAY_BUT_LATE_CENTER': 5}

Full obligation rows and trace-derived counts are in `failure-case-studies.json`.
