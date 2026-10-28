#!/usr/bin/env python3
"""Finite density/dynamics causal checks; no performance or native evidence."""
import copy, hashlib, importlib.util, json, resource, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
BASE = ROOT / f'Tools/{LANE}/level048-density-dynamics-r01'


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actions, shapes = module('actions'), module('shapes')
old = [json.loads(x) for x in (ROOT / f'Build/{LANE}/level048-r08/packet.jsonl').read_text().splitlines()]
new = [json.loads(x) for x in (ROOT / f'Build/{LANE}/level048-r09/packet.jsonl').read_text().splitlines()]
start = time.perf_counter()
positive, negative = [], []
for row in range(18, 24):
    before, after = old[row - 1], new[row - 1]
    action = actions.build(before, row)
    assert action == actions.build(copy.deepcopy(before), row) == after['implementation']['symbolic_action_segments']
    if row < 21:
        shape = shapes.density(before, row, old[17])
        emitted = copy.deepcopy(after['implementation']['source_density_contract'])
        emitted.pop('source_locator')
        emitted['target_comparison'].pop('baseline_source_binding')
        assert shape == emitted
        assert sum(b['sounding_event_count'] for b in shape['bars']) == len(before['implementation']['sounding_events'])
    else:
        shape = shapes.dynamics(before, row, action)
        emitted = copy.deepcopy(after['implementation']['source_dynamic_shape'])
        emitted.pop('source_locator')
        assert shape == emitted
        assert len(shape['slot_bindings']) == len(before['implementation']['sounding_events']) + action['counts']['holds']
        assert all(b['numeric_velocity'] is None and b['numeric_amplitude'] is None and b['acoustic_envelope'] is None
                   for b in shape['slot_bindings'])
        assert all(not b['new_pick_attack'] for b in shape['slot_bindings'] if b['binding_kind'] == 'held_event')
    assert before['implementation']['sounding_events'] == after['implementation']['sounding_events']
    assert before['status'] == after['status'] and before['timing_authority'] == after['timing_authority']
    positive.append({'row': row, 'materialized_contract_match': True, 'source_events_timing_status_unchanged': True})
assert new[19]['implementation']['source_density_contract']['target_comparison']['status'] == 'SOURCE_GUIDANCE_RECONCILIATION_PENDING'
assert not new[19]['implementation']['source_density_contract']['target_comparison']['same_downbeat_pitch_sequence']
assert len(new[19]['unresolved_reasons']) == len(old[19]['unresolved_reasons']) + 1


def reject(name, row, mutate, check):
    bad = copy.deepcopy(old[row - 1])
    mutate(bad)
    try:
        check(bad)
    except ValueError as error:
        negative.append({'case': name, 'row': row, 'refusal': str(error)})
    else:
        raise AssertionError(name)


def dyn_change(record, change):
    lines = record['source_payload']['exact_unit_lines']
    index = next(i for i, s in enumerate(lines) if s.startswith('Dyn|'))
    lines[index] = change(lines[index])


def dynamic(row):
    return lambda record: shapes.dynamics(record, row, actions.build(record, row))


reject('density omits tone', 18, lambda r: r['implementation']['sounding_events'].pop(), lambda r: shapes.density(r, 18, old[17]))
reject('dense mismatch silently corrected to G#', 20,
       lambda r: r['implementation']['sounding_events'][14].update(source_note='G#'), lambda r: shapes.density(r, 20, old[17]))
reject('dense offbeat slide creates attack', 20,
       lambda r: r['implementation']['sounding_events'][15].update(pick_attack=True), lambda r: shapes.density(r, 20, old[17]))
reject('wrong qualitative initial level', 21, lambda r: dyn_change(r, lambda s: s.replace('p', 'f', 1)), dynamic(21))
reject('numeric velocity substituted for source mark', 21, lambda r: dyn_change(r, lambda s: s.replace('p', '64', 1)), dynamic(21))
reject('dynamic marker shifted off count column', 21, lambda r: dyn_change(r, lambda s: s.replace('Dyn|p', 'Dyn|-p', 1)), dynamic(21))
reject('dynamic assigned to rest', 21, lambda r: dyn_change(r, lambda s: s.replace('p---p-------p', 'p---p---p---p', 1)), dynamic(21))
reject('held source dynamic omitted', 21, lambda r: dyn_change(r, lambda s: s[:-4] + '----'), dynamic(21))
reject('source dynamic bar omitted', 22, lambda r: dyn_change(r, lambda s: s.rsplit('|', 1)[0]), dynamic(22))
reject('diminuendo replaced by rising endpoint', 23, lambda r: dyn_change(r, lambda s: s.replace('|p---p---p---p---p', '|f---f---f---f---f')), dynamic(23))
reject('orphan source hold', 21,
       lambda r: r['implementation']['symbolic_count_slots'][0].update(kind='hold', note='=', attack_mark='=', source_contact_ordinals=[]), lambda r: actions.build(r, 21))
reject('density source row outside scope', 18, lambda r: None, lambda r: actions.build(r, 17))
report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': negative,
          'scope': 'Finite source density, source dynamic markers and symbolic action ownership; no general external validator claim.',
          'native_audio_app_tests': 'NOT_RUN', 'elapsed_seconds': time.perf_counter() - start,
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
path = ROOT / f'Results/{LANE}/level048-r09/shape-tests.json'
with path.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive': len(positive), 'causal_refusals': len(negative), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}))
