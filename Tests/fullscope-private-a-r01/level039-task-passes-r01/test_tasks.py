"""Focused source-task obligations, exact preservation and causal refusals."""
import copy
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-a-r01/level039-task-passes-r01'))
import tasks

old_path = ROOT / 'Build/fullscope-private-a-r01/level039-r04/packet.jsonl'
new_path = ROOT / 'Build/fullscope-private-a-r01/level039-r05/packet.jsonl'
old_raw = old_path.read_text().splitlines(keepends=True)
new_raw = new_path.read_text().splitlines(keepends=True)
old = [json.loads(s) for s in old_raw]
new = [json.loads(s) for s in new_raw]
changed = list(range(6, 11)) + list(range(18, 28))
expected_roots = [[('D', 4), ('B', 7)], [('A', 9), ('B', 7)], [('A', 9), ('G', 11)],
                  [('E', 14), ('G', 11), ('e', 14)], [('E', 14), ('D', 16), ('e', 14)]]
positive = []
for row in range(1, 38):
    if row not in changed:
        assert old_raw[row - 1] == new_raw[row - 1]
        continue
    a, b = old[row - 1], new[row - 1]
    field = 'source_task_passes' if row <= 10 else 'source_cadence_relationship'
    c = copy.deepcopy(b['implementation'][field])
    authority = c.pop('source_authority')
    assert authority['originals'] == [{k: v for k, v in r.items() if k != 'locator'} for r in a['source_refs'][:2]]
    if row <= 10:
        assert tasks.validate(c, a)
        assert c == tasks.box(a) == tasks.box(copy.deepcopy(a))
        actual_roots = sorted({(e['string_label'], e['fret']) for e in c['root_contacts']})
        assert actual_roots == sorted(expected_roots[row - 6])
        assert sum(len(x['contact_ordinals']) for x in c['passes']) == 72
        assert c['passes'][0]['spoken_degrees_by_contact'] != c['passes'][1]['spoken_degrees_by_contact']
    else:
        partner = old[(row + 1 if row % 2 == 0 else row - 1) - 1]
        binding = c['partner_predecessor_binding']
        assert tasks.validate(c, a, partner, binding)
        assert c == tasks.cadence(a, partner, binding) == tasks.cadence(copy.deepcopy(a), copy.deepcopy(partner), copy.deepcopy(binding))
        assert c['shared_seed']['notes'] == ['B', 'C#', 'E', 'C#']
        assert c['source_ending']['notes'] == (['B', 'A'] if row % 2 == 0 else ['A', 'F#'])
        assert c['conditional_repair']['steps'][1]['contact_ordinals'] == [3, 4, 5, 6]
    assert {k: v for k, v in b['implementation'].items() if k != field} == a['implementation']
    for key in ('package_key', 'source_identity', 'source_payload', 'timing_authority', 'status', 'unresolved_reasons', 'capabilities'):
        assert a[key] == b[key]
    positive.append({'row': row, 'package_key': a['package_key'], 'deterministic': True, 'preserved': True})

refusals = []


def refuse(name, call):
    try:
        call()
    except ValueError as error:
        refusals.append({'case': name, 'refused': True, 'reason': str(error)})
    else:
        raise AssertionError('Accepted causal mutation: ' + name)


def mutate(value, path, replacement):
    value = copy.deepcopy(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    return value


source = old[5]
contract = tasks.box(source)
for name, path, value in [
    ('wrong_tonic_degree', ['passes', 0, 'spoken_degrees_by_contact', 0], 'b3'),
    ('merged_degree_pass', ['passes', 1, 'task'], 'say_both_at_once'),
    ('omit_repeated_endpoint', ['passes', 0, 'contact_ordinals'], list(range(1, 13)) + list(range(14, 25))),
    ('accent_A_instead_of_F_sharp', ['passes', 2, 'accent_contact_ordinals'], [1, 6, 11]),
    ('numeric_velocity_invention', ['passes', 2, 'numeric_velocity'], 96),
    ('fixed_quarter_clock', ['selected_numeric_clock'], [1, 1]),
    ('acoustic_gate_invention', ['numeric_acoustic_gates'], [1, 1]),
    ('invented_sung_pitch', ['root_location_manual_duty', 'generated_events'], [{'midi': 66}]),
    ('performance_claim', ['performance_or_credit_claimed'], True),
]:
    refuse(name, lambda p=path, v=value: tasks.validate(mutate(contract, p, v), source))

a, b = old[17], old[18]
binding = new[17]['implementation']['source_cadence_relationship']['partner_predecessor_binding']
cad = tasks.cadence(a, b, binding)
for name, path, value in [
    ('wrong_partner_key', ['partner_predecessor_binding', 'package_key'], old[20]['package_key']),
    ('wrong_shared_seed', ['shared_seed', 'notes', 2], 'F#'),
    ('wrong_final_tonic', ['source_ending', 'final_tonic'], 'F#'),
    ('extra_postcadence_note', ['generated_new_notes'], ['E']),
    ('remove_postcadence_silence', ['ending_constraint', 'postcadence_silence_required_qualitatively'], False),
    ('invent_release_time', ['ending_constraint', 'numeric_note_release_or_silence_duration'], [1, 4]),
    ('automatic_partner_branch', ['ordered_manual_tasks', 1, 'selected_destination'], 'A'),
    ('invent_call_time', ['ordered_manual_tasks', 1, 'numeric_call_time'], [3, 1]),
    ('attach_entire_seed', ['conditional_repair', 'steps', 1, 'contact_ordinals'], [1, 2, 3, 4, 5, 6]),
    ('observed_error', ['conditional_repair', 'trigger_observed'], True),
]:
    refuse(name, lambda p=path, v=value: tasks.validate(mutate(cad, p, v), a, b, binding))
refuse('source_contact_order', lambda: tasks.box(mutate(source, ['implementation', 'ordered_contacts', 0, 'ordinal'], 2)))
refuse('source_degree_mismatch', lambda: tasks.box(mutate(source, ['implementation', 'ordered_contacts', 0, 'minor_degree'], '1')))
refuse('source_timing_injection', lambda: tasks.box(mutate(source, ['implementation', 'ordered_contacts', 0, 'onset_q'], [0, 1])))
refuse('cross_position_partner', lambda: tasks.cadence(a, old[20], binding))
refuse('source_extra_contact', lambda: tasks.cadence(mutate(a, ['implementation', 'ordered_contacts'], a['implementation']['ordered_contacts'] + [a['implementation']['ordered_contacts'][-1]]), b, binding))
assert len(positive) == 15 and len(refusals) == 24
assert sum(r['status']['production'] == 'SOURCE_SUPPORTED_IMPLEMENTATION_READY' for r in new) == 2
report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': refusals,
          'positive_count': 15, 'causal_refusal_count': 24, 'unrelated_byte_identical': 22,
          'packet_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
          'new_native_integrated_accepted': 0, 'scope': 'Source/task integrity; no runtime/GUI/performance test.'}
path = ROOT / 'Results/fullscope-private-a-r01/level039-r05/task-tests.json'
with path.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'status': 'PASS', 'positive': 15, 'causal_refusals': 24}))
