"""Small producer-integrity sample; broad behavioral/state/permutation QA stays deferred."""
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-batch-resume-r62')
sys.path.insert(0, str(ROOT / 'Tools' / LANE))
import chord_tone_contract as model
from produce import verify_ref
from reserve import pin, read

checks, refusals, results = 0, 0, []

def check(condition, criterion):
    global checks
    if not condition:
        raise AssertionError(criterion)
    checks += 1

def refuse(call, criterion, flow=None):
    global refusals
    before = deepcopy(flow.__dict__) if flow is not None else None
    try:
        call()
    except (model.Refusal, ValueError):
        if flow is not None:
            check(flow.__dict__ == before, criterion + ': no mutation')
        refusals += 1
        results.append(criterion)
    else:
        raise AssertionError('Did not refuse: ' + criterion)

PLAN = {'prerequisites': {'original_workbook': True, 'own_instrument': True},
        'cue_provider': {'kind': 'external_human', 'reference': 'synthetic manual partner fixture', 'ready': True}}

def contact(string, fret):
    return {'string': string, 'fret': fret, 'midi': model.TUNING[string] + fret}

def arrangements(pitch='E'):
    # These are authored fixture choices, never claimed as workbook-fixed contacts.
    if pitch == 'E':
        first = [contact('D', 2), contact('G', 0), contact('B', 0)]
        second = [contact('A', 3), contact('D', 2), contact('G', 0), contact('B', 0), contact('e', 0)]
    else:
        first = [contact('D', 5), contact('G', 0), contact('B', 0)]
        second = [contact('A', 3), contact('D', 5), contact('G', 0), contact('B', 0), contact('e', 3)]
    return {'string_set_1': {'strings': [c['string'] for c in first], 'target': first[0], 'voicing': first},
            'string_set_2': {'strings': [c['string'] for c in second], 'target': second[-1], 'voicing': second}}

def confirmation(flow):
    chord, role, _ = model.RAW[flow.index]
    return {'key': flow.key, 'chord': chord, 'role': role, 'ready': True}

def ready(flow, sung='E', choice='E'):
    flow.set_plan(flow.token(), PLAN)
    flow.begin(flow.token(), confirmation(flow))
    flow.heard(flow.token(), {'heard_chord_and_role': 'yes'})
    flow.sung_name(flow.token(), {'pitch_name': sung, 'singing_attempted': True})
    flow.choose_arrangements(flow.token(), arrangements(choice))

def play_release_reveal(flow):
    flow.setup_target(flow.token(), True)
    flow.attack(flow.token(), True)
    flow.release(flow.token(), True)
    if flow.stage == 0:
        flow.reveal(flow.token())

def report(flow, speed='immediate', diagnosis=''):
    return {'key': flow.key, 'chord': model.RAW[flow.index][0], 'role': model.RAW[flow.index][1],
            'string_set': model.SETS[flow.stage], 'target': flow.target()['arrangement']['target'],
            'named_pitch': flow.named_pitch, 'attack_count': 1,
            'common': {name: 'yes' for name in model.COMMON},
            'stage_duties': {name: 'yes' for name in (('sung_pitch_correct',) if flow.stage == 0 else model.TRANSFER)},
            'response_speed': speed, 'diagnosis': diagnosis, 'notes': 'Synthetic report, not an observed performance.'}

def main():
    tick = time.monotonic()
    reservation = read(Path('Results') / LANE / 'reservation.json')
    seal = read(Path('Results') / LANE / 'seal.json')
    packet = [json.loads(line) for line in (ROOT / seal['packet']['path']).read_text().splitlines()]
    source = [json.loads(line) for line in (ROOT / reservation['base_packet']['path']).read_text().splitlines()]
    check([row['package_key'] for row in packet] == list(model.KEYS), 'whole family exact source order')
    check(len({row['package_key'] for row in packet}) == 14, 'fourteen unique existing keys')
    check(sum(row['status'] == 'IMPLEMENTED_PRIVATE_QA_PENDING' for row in packet) == 13, '13/14 ready privately')
    check(sum(row['status'] == 'SOURCE_UNRESOLVED_PRIVATE_PARTIAL_QA_PENDING' for row in packet) == 1, '1/14 occlusion unresolved')
    for index, (row, reserved) in enumerate(zip(packet, reservation['rows'])):
        original = source[reserved['r06_jsonl_line'] - 1]
        for name in ('package_key', 'source_identity', 'level', 'existing_parent_id', 'source_refs',
                     'source_payload', 'timing_authority', 'field_limitations'):
            check(row[name] == original[name], f'{index + 1}: original {name} retained')
        for name in ('events', 'tab_blocks', 'source_field_occurrences', 'canonical_ids_allocated', 'playback_admitted'):
            check(row['implementation'][name] == original['implementation'][name], f'{index + 1}: original {name} retained')
        check(row['implementation']['task']['printed_components'] == [*model.RAW[index], '', '', ''],
              f'{index + 1}: six exact source columns')
        check(row['contract_capabilities']['native_valid'] is False
              and row['contract_capabilities']['installed'] is False
              and row['contract_capabilities']['Accepted'] is False, f'{index + 1}: no acceptance promotion')
        flow = model.ChordToneFlow(row['package_key'])
        check('reference_pitch' not in flow.learner_view(), f'{index + 1}: source answer starts withheld')
        check(row['implementation']['task']['contract']['source_absolute_contact_voicing_timing'] is None,
              f'{index + 1}: fixed source voicing/timing remains unknown')
        check(row['implementation']['task']['contract']['source_note_events'] == [], f'{index + 1}: no56-tone fabrication')
    # One complete correct two-set flow is sufficient for this early smoke sample.
    flow = model.ChordToneFlow(model.KEYS[0])
    ready(flow)
    check('reference_pitch' not in flow.learner_view(), 'correct response receives no early reference')
    refuse(lambda: flow.reveal(flow.token()), 'early source answer reveal', flow)
    refuse(lambda: flow.finish(flow.token()), 'early task finish', flow)
    play_release_reveal(flow)
    check(flow.learner_view()['reference_pitch'] == 'E', 'reference reveal only after initial playing/release')
    flow.report(flow.token(), report(flow, speed='slow'))
    check(flow.history[-1]['data']['source_priority_guidance'] == model.PRIORITY,
          'slow manual response returns exact priority guidance')
    check(flow.history[-1]['data']['performance_verified'] is False, 'manual report is no performance observation')
    flow.next_set(flow.token())
    flow.begin(flow.token())
    play_release_reveal(flow)
    flow.report(flow.token(), report(flow))
    refuse(lambda: flow.next_set(flow.token()), 'no invented third string set', flow)
    flow.finish(flow.token())
    check(flow.state == 'completed' and flow.history[-1]['data']['mastery_awarded'] is False,
          'complete two-set manual task awards no mastery')
    # Wrong/unknown responses are accepted structurally before comparison, with diagnosis after playing.
    wrong = model.ChordToneFlow(model.KEYS[0])
    ready(wrong, sung='G', choice='G')
    check(wrong.state == 'silent_setup' and 'reference_pitch' not in wrong.learner_view(),
          'wrong chosen pitch remains playable without hidden correction')
    play_release_reveal(wrong)
    refuse(lambda: wrong.report(wrong.token(), report(wrong)), 'wrong response needs diagnosis after playing', wrong)
    wrong.report(wrong.token(), report(wrong, diagnosis='Chosen G differed from E; retry without searching.'))
    check(wrong.state == 'needs_retry' and wrong.response_history[0]['pitch_name'] == 'G', 'wrong response retained')
    unknown = model.ChordToneFlow(model.KEYS[1])
    unknown.set_plan(unknown.token(), PLAN)
    unknown.begin(unknown.token(), confirmation(unknown))
    unknown.heard(unknown.token(), {'heard_chord_and_role': 'uncertain'})
    unknown.sung_name(unknown.token(), {'pitch_name': None, 'singing_attempted': True})
    check(unknown.named_pitch is None and unknown.state == 'choose_arrangements', 'unknown sung response retained')
    unknown.cannot_respond(unknown.token(), 'Cannot locate target yet.', True)
    check(unknown.state == 'needs_retry' and unknown.named_pitch is None, 'inability invents no answer')
    held = model.ChordToneFlow(model.OCCLUDED_KEY)
    held.set_plan(held.token(), PLAN)
    refuse(lambda: held.begin(held.token(), confirmation(held)), 'occluded source refuses practice start', held)
    # Small causal schema, provenance and ownership refusal sample; no state sweep.
    refuse(lambda: model.ChordToneFlow('invented-key'), 'new/nonexisting source key')
    bad = deepcopy(arrangements())
    bad['string_set_1']['voicing'][0]['fret'] = True
    refuse(lambda: model.validate_arrangements(bad), 'boolean fret masquerading as integer')
    bad = deepcopy(arrangements())
    bad['string_set_1']['target'] = contact('e', 0)
    refuse(lambda: model.validate_arrangements(bad), 'target outside chosen voicing')
    bad = deepcopy(arrangements())
    bad['string_set_2'] = deepcopy(bad['string_set_1'])
    refuse(lambda: model.validate_arrangements(bad), 'duplicate chosen string-set arrangement')
    badref = dict(reservation['original_sources'][0], sha256='0' * 64)
    refuse(lambda: verify_ref(badref), 'source-pin corruption refuses')
    fresh = model.ChordToneFlow(model.KEYS[0])
    old_token = fresh.token()
    fresh.set_plan(fresh.token(), PLAN)
    refuse(lambda: fresh.begin(old_token, confirmation(fresh)), 'stale action/source owner', fresh)
    refuse(lambda: fresh.begin(wrong.token(), confirmation(fresh)), 'foreign flow/source owner', fresh)
    badconfirmation = dict(confirmation(fresh), role='7')
    refuse(lambda: fresh.begin(fresh.token(), badconfirmation), 'wrong exact source role', fresh)
    fresh.begin(fresh.token(), confirmation(fresh))
    fresh.cancel(fresh.token())
    fresh.reopen(fresh.token())
    refuse(lambda: fresh.begin(fresh.token(), confirmation(fresh)), 'reopen requires physical release', fresh)
    fresh.release(fresh.token(), True)
    check(fresh.state == 'ready', 'interrupted hearing resumes only after release')
    inputs = [pin(Path('Tools') / LANE / name) for name in ('chord_tone_contract.py', 'produce.py', 'reserve.py')]
    inputs += [pin(Path('Tests') / LANE / 'check_integrity.py'), pin(seal['packet']['path']), pin(Path('Results') / LANE / 'reservation.json')]
    print(json.dumps({'schema_version': 'fathom-private-cheap-integrity-sample.1',
                      'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'elapsed_seconds': time.monotonic() - tick, 'checks_passed': checks,
                      'causal_refusals_passed': refusals, 'refusal_criteria': results,
                      'full_two_set_synthetic_walkthroughs': 1, 'selected_packet_rows': 14,
                      'ready_private_rows': 13, 'source_unresolved_rows': 1, 'inputs': inputs,
                      'unexecuted': ['bulk behavioral/state/permutation', 'independent source/interpretation',
                                     'native', 'installed app', 'physical/listening', 'broad regression'],
                      'synthetic_manual_reports_are_observations': False, 'outcome': 'PASS'}))

if __name__ == '__main__':
    main()
