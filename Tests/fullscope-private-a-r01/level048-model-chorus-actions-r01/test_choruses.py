#!/usr/bin/env python3
"""Causal source-form, pitch-scope and symbolic ownership checks."""
import copy, hashlib, importlib.util, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
BASE = ROOT / f'Tools/{LANE}/level048-model-chorus-actions-r01'


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actions, chorus = module('actions'), module('chorus')
old = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r10/packet.jsonl').read_text().splitlines()]
new = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r11/packet.jsonl').read_text().splitlines()]
positive, negative = [], []
for row in (24, 26):
    before, after = old[row - 1], new[row - 1]
    action = actions.build(before, row)
    assert action == actions.build(copy.deepcopy(before), row) == after['implementation']['symbolic_action_segments']
    form = chorus.build(before, row)
    emitted = copy.deepcopy(after['implementation']['source_model_chorus'])
    emitted.pop('source_pdf')
    emitted.pop('physical_pages')
    assert form == chorus.build(copy.deepcopy(before), row) == emitted
    assert len(form['bars']) == 12 and sum(len(b['source_event_ordinals']) for b in form['bars']) == len(before['implementation']['sounding_events'])
    assert not form['capstone_completed_or_qualified'] and form['numeric_onsets'] is None
    assert before['source_payload'] == after['source_payload'] and before['status'] == after['status']
    for hold in [a for a in action['actions'] if a['kind'] == 'hold']:
        owner = before['implementation']['sounding_events'][hold['owner_event_ordinal'] - 1]
        assert owner['relative_position']['bar'] == hold['source_position']['bar']
        assert not hold['new_pick_attack']
    positive.append({'row': row, 'deterministic_exact_contract_match': True, 'source_unchanged': True,
                     'twelve_target_joins': True, 'capstone_not_claimed': True})
f, h = new[23]['implementation'], new[25]['implementation']
assert f['symbolic_action_segments']['picked_excitation_groups'][-1]['source_requires_silence_at_end']
assert h['symbolic_action_segments']['picked_excitation_groups'][-1]['logical_end_reason'] == 'printed_scope_ends_release_unselected'
assert not h['symbolic_action_segments']['picked_excitation_groups'][-1]['source_requires_silence_at_end']
assert any(e['source_note'] == 'F#' and e['relative_position']['bar'] == 4 and e['harmonic_role'] == '13'
           for e in h['sounding_events'])


def reject(name, row, mutate, check):
    bad = copy.deepcopy(old[row - 1])
    mutate(bad)
    try:
        check(bad, row)
    except ValueError as error:
        negative.append({'case': name, 'row': row, 'refusal': str(error)})
    else:
        raise AssertionError(name)


def heading_change(record, text, replacement):
    lines = record['source_payload']['exact_unit_lines']
    index = next(i for i, s in enumerate(lines) if s.startswith(text))
    lines[index] = replacement(lines[index])


reject('minor model outside pitch', 24, lambda r: r['implementation']['sounding_events'][1].update(source_note='Eb'), chorus.build)
reject('G# completion outside E7', 26, lambda r: r['implementation']['sounding_events'][1].update(source_note='G#'), chorus.build)
reject('target delayed from beat one', 24, lambda r: r['implementation']['sounding_events'][0]['relative_position'].update(phase='offbeat'), chorus.build)
reject('wrong chord in printed form', 24, lambda r: heading_change(r, 'BAR 5 ', lambda s: s.replace('D7', 'A7')), chorus.build)
reject('target role changed', 26, lambda r: r['implementation']['sounding_events'][0].update(harmonic_role='5'), chorus.build)
reject('missing source bar heading', 24, lambda r: r['source_payload']['exact_unit_lines'].remove(next(s for s in r['source_payload']['exact_unit_lines'] if s.startswith('BAR 12 '))), chorus.build)
reject('legato receives extra attack', 24, lambda r: r['implementation']['sounding_events'][1].update(pick_attack=True), actions.build)
reject('legato on another string', 24, lambda r: r['implementation']['sounding_events'][1].update(string_label='G'), actions.build)
reject('rest receives a pitch contact', 24, lambda r: r['implementation']['symbolic_count_slots'][2].update(source_contact_ordinals=[1]), actions.build)
reject('bar sequence reordered', 24, lambda r: r['implementation']['symbolic_count_slots'].reverse(), actions.build)
reject('source event omitted', 26, lambda r: r['implementation']['sounding_events'].pop(), actions.build)
report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': negative,
          'source_F_sharp_over_A7_control': 'retained as printed13',
          'modelH_final_release': 'unselected; next bar is a symbolic scope boundary only',
          'native_runtime_app_performance': 'NOT_RUN'}
p = ROOT / f'Results/{LANE}/level048-r11/chorus-tests.json'
with p.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive_cases': len(positive), 'causal_refusals': len(negative), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
