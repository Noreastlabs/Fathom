"""Causal checks for completion boundaries, partial timing and unselected duties."""
import copy
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-a-r01/level040-completion-actions-r01'))
from completion import build, validate

old_path = ROOT / 'Build/fullscope-private-a-r01/level040-r05/packet.jsonl'
new_path = ROOT / 'Build/fullscope-private-a-r01/level040-r06/packet.jsonl'
old_raw = old_path.read_text().splitlines(keepends=True)
new_raw = new_path.read_text().splitlines(keepends=True)
old = [json.loads(s) for s in old_raw]
new = [json.loads(s) for s in new_raw]
positive = []
for row in range(1, 59):
    if not 48 <= row <= 52:
        assert new_raw[row - 1] == old_raw[row - 1]
        continue
    source, emitted = old[row - 1], new[row - 1]
    contract = copy.deepcopy(emitted['implementation']['source_completion_cadence'])
    authority = contract.pop('source_authority')
    assert validate(contract, source)
    assert contract == build(source) == build(copy.deepcopy(source))
    assert [x['contact_ordinal'] for x in contract['explicit_source_beat_one_anchors']] == [1, 5, 9]
    assert [x['note'] for x in contract['explicit_source_beat_one_anchors']] == ['D', 'G#', 'F#']
    assert sum(x['source_beat'] is None for x in contract['contact_roles']) == 9
    assert [x['return_note'] for x in contract['completion_targets']] == ['F#', 'B']
    assert (contract['later_source_pass'] is not None) == (row >= 50)
    assert not emitted['source_payload']['notation_blocks'][0]['printed_rest_columns']
    assert {k: v for k, v in emitted['implementation'].items() if k != 'source_completion_cadence'} == source['implementation']
    for key in ('package_key', 'source_identity', 'source_payload', 'timing_authority', 'status', 'unresolved_reasons'):
        assert source[key] == emitted[key]
    positive.append({'row': row, 'package_key': source['package_key'], 'deterministic': True,
                     'preservation': True, 'known_beat_anchors': 3, 'other_beats_unselected': 9})


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


source = old[49]
contract = build(source)
for name, path, value in [
    ('wrong_active_chord', ['contact_roles', 4, 'active_chord'], 'D'),
    ('outside_as_scale_degree', ['contact_roles', 0, 'pentatonic_degree'], 'b6'),
    ('root_R_as_rest', ['contact_roles', 0, 'R_means_harmonic_root_not_rest'], False),
    ('move_beat_one_arrival', ['explicit_source_beat_one_anchors', 1, 'source_beat'], 2),
    ('invent_internal_beat', ['contact_roles', 1, 'source_beat'], 2),
    ('invent_meter', ['meter_numerator_denominator'], [4, 4]),
    ('invent_quarter_mapping', ['quarter_unit_mapping'], [1, 1]),
    ('invent_gate', ['selected_numeric_acoustic_gates'], [1, 1]),
    ('extra_approach_note', ['generated_extra_events'], [{'note': 'G'}]),
    ('select_slide_target', ['later_source_pass', 'selected_completion_contact'], 5),
    ('select_slide_origin', ['later_source_pass', 'selected_approach_origin'], {'string_label': 'B', 'fret': 8}),
    ('select_slide_curve', ['later_source_pass', 'selected_curve_or_start_time'], 'linear'),
    ('mark_second_pass_complete', ['later_source_pass', 'source_pass_completed'], True),
    ('slide_both_completion_notes', ['later_source_pass', 'completion_tones_to_approach'], 2),
    ('remove_second_pass_obligation', ['later_source_pass'], None),
    ('observed_blur', ['conditional_blur_repair', 'trigger_observed'], True),
    ('native_ready', ['native_projection_complete'], True),
    ('credit', ['performance_or_credit_claimed'], True),
]:
    refuse(name, lambda p=path, v=value: validate(mutate(contract, p, v), source))
refuse('extend_p13_pass_to_P1', lambda: validate(mutate(build(old[47]), ['later_source_pass'], contract['later_source_pass']), old[47]))
refuse('source_physical_pitch_corrupt', lambda: build(mutate(source, ['implementation', 'ordered_contacts', 0, 'fret'], 11)))
refuse('source_wrong_completion_flag', lambda: build(mutate(source, ['implementation', 'ordered_contacts', 1, 'completion_tone'], True)))
refuse('source_wrong_root_role', lambda: build(mutate(source, ['implementation', 'ordered_contacts', 0, 'harmonic_role'], 'rest')))
refuse('source_slide_in_direct_pass', lambda: build(mutate(source, ['implementation', 'ordered_contacts', 4, 'pick_attack'], False)))
refuse('source_quarter_clock_injection', lambda: build(mutate(source, ['implementation', 'ordered_contacts', 0, 'onset_q'], [0, 1])))
assert len(positive) == 5 and len(refusals) == 24
report = {'status': 'PASS', 'positive_count': 5, 'causal_refusal_count': 24, 'positive_cases': positive,
          'causal_refusals': refusals, 'byte_identical_unrelated': 53, 'new_native_integrated_accepted': 0,
          'packet_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
          'scope': 'Source task and conservation checks only; no native/audio/GUI/performance evidence.'}
path = ROOT / 'Results/fullscope-private-a-r01/level040-r06/task-tests.json'
with path.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'status': 'PASS', 'positive': 5, 'causal_refusals': 24}))
