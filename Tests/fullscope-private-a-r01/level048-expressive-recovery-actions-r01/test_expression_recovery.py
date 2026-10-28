#!/usr/bin/env python3
"""Causal source expression, recovery and retained target-heading checks."""
import copy, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
BASE = ROOT / f'Tools/{LANE}/level048-expressive-recovery-actions-r01'
sys.path.insert(0, str(BASE))


def module(name):
    spec = importlib.util.spec_from_file_location(name, BASE / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


actions, expression, contracts = module('actions'), module('expression'), module('contracts')
old = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r12/packet.jsonl').read_text().splitlines()]
new = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r13/packet.jsonl').read_text().splitlines()]
positive, negative = [], []
expressive_count = 0
for row in [25, 45, 46, 47, 48, 49, 50]:
    before, after = old[row - 1], new[row - 1]
    action = actions.build(before, row)
    assert action == actions.build(copy.deepcopy(before), row) == after['implementation']['symbolic_action_segments']
    for a in action['actions']:
        if 'expressive_source_constraint' not in a:
            continue
        expressive_count += 1
        c = a['expressive_source_constraint']
        assert a['new_pick_attack'] and c['one_picked_excitation'] and c['numeric_trajectory'] is None
        assert not c['constant_source_or_target_scalar_playback_permitted'] and not c['native_realization_complete']
        event = before['implementation']['sounding_events'][a['event_ordinal'] - 1]
        assert c['source_constraints'] == event['source_pitch_constraints']
    if row == 25:
        emitted = copy.deepcopy(after['implementation']['source_expressive_model'])
        emitted.pop('source_pdf')
        emitted.pop('physical_pages')
        assert emitted == contracts.model(before)
        assert [x['bar'] for x in emitted['source_guidance_reconciliation']] == [2, 4, 6, 8]
    else:
        emitted = copy.deepcopy(after['implementation']['source_recovery_actions'])
        coverage = emitted.pop('source_coverage')
        assert coverage['full_written_grid_in_pdf'] is (row <= 47)
        assert emitted == contracts.recovery(before, row, action)
        assert not emitted['automatic_error_detection'] and not emitted['trigger_observed']
    assert before['implementation']['sounding_events'] == after['implementation']['sounding_events']
    assert before['source_payload'] == after['source_payload'] and before['status'] == after['status']
    positive.append({'row': row, 'exact_materialized_match': True, 'source_music_status_unchanged': True})
assert expressive_count == 4
all_cards = [r for r in new if r['implementation'].get('sounding_events')]
assert len(all_cards) == 38
assert sum(r['implementation']['symbolic_action_segments']['counts']['sounding_events'] for r in all_cards) == 614
assert sum(r['implementation']['symbolic_action_segments']['counts']['picked_excitation_groups'] for r in all_cards) == 517


def reject(name, row, mutate, check):
    bad = copy.deepcopy(old[row - 1])
    mutate(bad)
    try:
        check(bad, row)
    except ValueError as error:
        negative.append({'case': name, 'row': row, 'refusal': str(error)})
    else:
        raise AssertionError(name)


reject('shade fabricated100 cents', 49, lambda r: r['implementation']['sounding_events'][0]['bend'].update(exact_cents=100), actions.build)
reject('shade fixed source scalar playback', 49, lambda r: r['implementation']['sounding_events'][0].update(selected_fixed_playback_midi=48), actions.build)
reject('full bend fixed target playback', 25, lambda r: r['implementation']['sounding_events'][5].update(selected_fixed_playback_midi=69), actions.build)
reject('fabricated full bend curve', 25, lambda r: r['implementation']['sounding_events'][5]['source_pitch_constraints'].update(continuous_curve=[[0, 67], [1, 69]]), actions.build)
reject('full bend endpoint altered', 25, lambda r: r['implementation']['sounding_events'][5].update(pitch_encoding_midi=70), actions.build)
reject('expressive event wrongly marked complete', 49, lambda r: r['implementation']['sounding_events'][0].update(expressive_pitch_realization_complete=True), actions.build)
reject('shade direction reversed', 49, lambda r: r['implementation']['sounding_events'][0]['bend'].update(direction='toward B'), actions.build)
reject('full bend loses reference endpoint token', 25, lambda r: r['implementation']['sounding_events'][5].update(source_contact_ordinals=[6]), actions.build)
reject('unpicked recovery gains attack', 45, lambda r: r['implementation']['sounding_events'][1].update(pick_attack=True), actions.build)
reject('root heading silently repaired to written G', 25,
       lambda r: r['source_payload']['exact_unit_lines'].__setitem__(r['source_payload']['exact_unit_lines'].index('BAR 2 - A7 RESPONSE - P1 - beat-1 target A root'), 'BAR 2 - A7 RESPONSE - P1 - beat-1 target G root'),
       lambda r, row: contracts.model(r))
reject('late response loses tonic resolution', 48, lambda r: r['implementation']['sounding_events'].pop(),
       lambda r, row: contracts.recovery(r, row, actions.build(old[row - 1], row)))
reject('source-return C changed', 49, lambda r: r['implementation']['sounding_events'][1].update(source_note='C#'),
       lambda r, row: contracts.recovery(r, row, actions.build(old[row - 1], row)))
reject('tonic-reset A removed', 50, lambda r: r['implementation']['sounding_events'][0].update(source_note='G'),
       lambda r, row: contracts.recovery(r, row, actions.build(old[row - 1], row)))
report = {'status': 'PASS', 'positive_cases': positive, 'causal_refusals': negative,
          'expressive_actions_with_unselected_curves': 4, 'whole_written_action_card_count': 38,
          'whole_written_source_events': 614, 'whole_written_picked_groups': 517,
          'native_runtime_app_performance': 'NOT_RUN'}
p = ROOT / f'Results/{LANE}/level048-r13/expression-recovery-tests.json'
with p.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive_cases': len(positive), 'causal_refusals': len(negative), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
