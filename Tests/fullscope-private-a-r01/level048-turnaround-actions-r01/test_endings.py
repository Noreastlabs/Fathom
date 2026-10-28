#!/usr/bin/env python3
"""Finite ending/action refusals and source-wording retention controls."""
import copy, hashlib, importlib.util, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
BASE = ROOT / f'Tools/{LANE}/level048-turnaround-actions-r01'


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actions, endings = module('actions'), module('endings')
old = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r11/packet.jsonl').read_text().splitlines()]
new = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r12/packet.jsonl').read_text().splitlines()]
positive, negative = [], []
for row in range(27, 33):
    before, after = old[row - 1], new[row - 1]
    action = actions.build(before, row)
    assert action == actions.build(copy.deepcopy(before), row) == after['implementation']['symbolic_action_segments']
    ending = endings.build(before, row, action)
    emitted = copy.deepcopy(after['implementation']['source_turnaround_contract'])
    emitted.pop('source_pdf')
    emitted.pop('physical_page')
    assert ending == emitted and not ending['next_chorus_event_generated']
    assert before['source_payload'] == after['source_payload']
    assert before['implementation']['sounding_events'] == after['implementation']['sounding_events']
    assert before['status'] == after['status'] and before['timing_authority'] == after['timing_authority']
    positive.append({'row': row, 'exact_materialized_match': True, 'source_events_status_unchanged': True})
assert new[30]['implementation']['source_turnaround_contract']['counted_silence_slot_ordinals'] == list(range(5, 15))
assert len(new[30]['implementation']['source_turnaround_contract']['written_pickup_events']) == 2
approach = new[31]['implementation']['source_turnaround_contract']
assert approach['emitted_semitone_delta'] == -1 and approach['source_guidance_reconciliation']['source_direction_wording'] == 'one-time lower approach to E'
assert not approach['source_guidance_reconciliation']['source_pitch_or_wording_repair_applied']
assert len(new[31]['unresolved_reasons']) == len(old[31]['unresolved_reasons']) + 1


def check_ending(record, row):
    # Existing source ownership provides context; this check targets ending joins.
    return endings.build(record, row, actions.build(old[row - 1], row))


def reject(name, row, mutate, check):
    bad = copy.deepcopy(old[row - 1])
    mutate(bad)
    try:
        check(bad, row)
    except ValueError as error:
        negative.append({'case': name, 'row': row, 'refusal': str(error)})
    else:
        raise AssertionError(name)


reject('close ends on E instead of A', 27, lambda r: r['implementation']['sounding_events'][-1].update(source_note='E'), check_ending)
reject('G# appears before E7 source bar', 28, lambda r: r['implementation']['sounding_events'][1].update(source_note='G#'), check_ending)
reject('guide-tone target changed', 29, lambda r: r['implementation']['sounding_events'][5].update(source_note='E'), check_ending)
reject('blue note moved across E7 downbeat', 30, lambda r: r['implementation']['sounding_events'][2]['relative_position'].update(bar=2), check_ending)
reject('two-note pickup collapsed', 31, lambda r: r['implementation']['sounding_events'].pop(), check_ending)
reject('pickup moved to beat3', 31, lambda r: r['implementation']['sounding_events'][-2]['relative_position'].update(beat=3), check_ending)
reject('counted silence shortened', 31, lambda r: r['implementation']['symbolic_count_slots'][4].update(kind='hold'), check_ending)
reject('F approach pitch changed to match lower wording', 32, lambda r: r['implementation']['sounding_events'][6].update(physical_fret=6), check_ending)
reject('F-to-E legato adds pick attack', 32, lambda r: r['implementation']['sounding_events'][7].update(pick_attack=True), check_ending)
reject('explicit rest adds a contact', 27, lambda r: r['implementation']['symbolic_count_slots'][4].update(source_contact_ordinals=[1]), actions.build)
reject('orphan initial hold', 27, lambda r: r['implementation']['symbolic_count_slots'][0].update(kind='hold', note='=', attack_mark='=', source_contact_ordinals=[]), actions.build)
reject('high-blues legato changes string', 30, lambda r: r['implementation']['sounding_events'][2].update(string_label='E'), actions.build)
report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': negative,
          'literal_lower_word_and_actual_descending_F_to_E_both_retained': True,
          'two_stop_time_attacks_and_ten_source_rest_slots_retained': True,
          'numeric_clock_gate_native_runtime_app_performance': 'NOT_RUN'}
p = ROOT / f'Results/{LANE}/level048-r12/ending-tests.json'
with p.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive_cases': len(positive), 'causal_refusals': len(negative), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
