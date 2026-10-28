"""Targeted causal checks for source relationships and unselected execution."""
import copy
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-a-r01/level040-response-relations-r01'))
from response import build, validate

old_path = ROOT / 'Build/fullscope-private-a-r01/level040-r06/packet.jsonl'
new_path = ROOT / 'Build/fullscope-private-a-r01/level040-r07/packet.jsonl'
old_raw = old_path.read_text().splitlines(keepends=True)
new_raw = new_path.read_text().splitlines(keepends=True)
old = [json.loads(s) for s in old_raw]
new = [json.loads(s) for s in new_raw]
positive = []
for row in range(1, 59):
    if not 43 <= row <= 47:
        assert new_raw[row - 1] == old_raw[row - 1]
        continue
    source, emitted = old[row - 1], new[row - 1]
    contract = copy.deepcopy(emitted['implementation']['source_response_relationship'])
    authority = contract.pop('source_authority')
    assert validate(contract, source)
    assert contract == build(source) == build(copy.deepcopy(source))
    assert [(x['call_ordinal'], x['answer_ordinal']) for x in contract['shared_opening_joins']] == [(1, 7), (2, 8), (3, 9), (4, 10)]
    assert [x['ending_notes'] for x in contract['phrases']] == [['B', 'A'], ['A', 'F#']]
    assert [x['contact_ordinal'] for x in contract['contact_roles'] if x['R_means_harmonic_root_not_rest']] == [6, 12]
    assert not emitted['source_payload']['notation_blocks'][0]['printed_rest_columns']
    assert {k: v for k, v in emitted['implementation'].items() if k != 'source_response_relationship'} == source['implementation']
    for key in ('package_key', 'source_identity', 'source_payload', 'timing_authority', 'status', 'unresolved_reasons'):
        assert source[key] == emitted[key]
    positive.append({'row': row, 'package_key': source['package_key'], 'deterministic': True,
                     'preservation': True, 'shared_opening_joins': 4, 'terminal_root_duties': 2})


def mutate(obj, path, value):
    obj = copy.deepcopy(obj)
    current = obj
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value
    return obj


refusals = []


def refuse(name, call):
    try:
        call()
    except ValueError as error:
        refusals.append({'case': name, 'refused': True, 'reason': str(error)})
    else:
        raise AssertionError(name)


source = old[42]
contract = build(source)
for name, path, value in [
    ('wrong_active_chord', ['contact_roles', 6, 'active_chord'], 'A'),
    ('unchanged_role_across_harmony', ['shared_opening_joins', 0, 'answer_chord_role'], '9'),
    ('root_R_as_rest', ['contact_roles', 5, 'R_means_harmonic_root_not_rest'], False),
    ('changed_opening_join', ['shared_opening_joins', 0, 'answer_ordinal'], 8),
    ('wrong_call_ending', ['phrases', 0, 'ending_notes'], ['B', 'F#']),
    ('wrong_answer_ending', ['phrases', 1, 'ending_notes'], ['B', 'A']),
    ('reversed_phase_order', ['phrases', 0, 'source_order'], 2),
    ('wrong_answer_root', ['phrases', 1, 'final_root_note'], 'A'),
    ('six_contacts_as_six_eighth_meter', ['meter_numerator_denominator'], [6, 8]),
    ('invent_quarter_mapping', ['quarter_unit_mapping'], [1, 1]),
    ('invent_numeric_onsets', ['selected_numeric_onsets'], [[0, 1]]),
    ('invent_gate', ['selected_numeric_acoustic_gates'], [1, 1]),
    ('invent_silence', ['interphrase_silence_duration'], [1, 1]),
    ('invent_velocity', ['numeric_velocity'], 90),
    ('add_drone', ['generated_accompaniment_events'], [{'note': 'A'}]),
    ('extra_note', ['generated_extra_events'], [{'note': 'G#'}]),
    ('observed_center', ['perceived_centers_observed'], ['A', 'F#']),
    ('task_completed', ['source_task_completed'], True),
    ('native_ready', ['native_projection_complete'], True),
    ('credit', ['performance_or_credit_claimed'], True),
]:
    refuse(name, lambda p=path, v=value: validate(mutate(contract, p, v), source))
for name, path, value in [
    ('source_wrong_identity', ['source_identity'], 'printed:l040:wrong'),
    ('source_physical_pitch_corrupt', ['implementation', 'ordered_contacts', 0, 'fret'], 5),
    ('source_finger_corrupt', ['implementation', 'ordered_contacts', 6, 'finger'], 4),
    ('source_wrong_root_role', ['implementation', 'ordered_contacts', 5, 'harmonic_role'], 'rest'),
    ('source_group_changed', ['implementation', 'ordered_contacts', 6, 'source_group'], 1),
    ('source_unpicked_attack', ['implementation', 'ordered_contacts', 6, 'pick_attack'], False),
    ('source_quarter_clock_injection', ['implementation', 'ordered_contacts', 0, 'onset_q'], [0, 1]),
]:
    refuse(name, lambda p=path, v=value: build(mutate(source, p, v)))
assert len(positive) == 5 and len(refusals) == 27
report = {'status': 'PASS', 'positive_count': 5, 'causal_refusal_count': 27, 'positive_cases': positive,
          'causal_refusals': refusals, 'byte_identical_unrelated': 53, 'new_native_integrated_accepted': 0,
          'packet_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
          'scope': 'Source task and conservation checks only; no native/audio/GUI/performance evidence.'}
path = ROOT / 'Results/fullscope-private-a-r01/level040-r07/task-tests.json'
with path.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'status': 'PASS', 'positive': 5, 'causal_refusals': 27}))
