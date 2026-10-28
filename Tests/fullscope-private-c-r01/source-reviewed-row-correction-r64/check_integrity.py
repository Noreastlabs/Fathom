"""One corrected two-set walkthrough and small source/schema/causal refusal sample."""
from copy import deepcopy
import datetime
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/source-reviewed-row-correction-r64')
sys.path.insert(0, str(ROOT / 'Tools' / LANE))
import source_reviewed_chord_tone as m
from produce import pin, verify

checks, refusals, labels = 0, 0, []
def check(ok, name):
    global checks
    if not ok:
        raise AssertionError(name)
    checks += 1

def refuse(call, name, flow=None):
    global refusals
    before = deepcopy(flow.__dict__) if flow else None
    try:
        call()
    except (ValueError, AssertionError):
        if flow:
            check(flow.__dict__ == before, name + ': no mutation')
        refusals += 1
        labels.append(name)
    else:
        raise AssertionError('No refusal: ' + name)

PLAN = {'prerequisites': {'original_workbook': True, 'own_instrument': True},
        'cue_provider': {'kind': 'external_human', 'reference': 'synthetic manual cue fixture', 'ready': True}}
def c(string, fret):
    return {'string': string, 'fret': fret, 'midi': m.base.TUNING[string] + fret}
CHOICES = {'string_set_1': {'strings': ['D', 'G', 'B'], 'target': c('G', 5),
                          'voicing': [c('D', 6), c('G', 5), c('B', 4)]},
           'string_set_2': {'strings': ['A', 'D', 'G', 'B', 'e'], 'target': c('e', 8),
                          'voicing': [c('A', 11), c('D', 10), c('G', 10), c('B', 9), c('e', 8)]}}
CONFIRM = {'key': m.KEY, 'chord': 'G#7alt', 'role': '3', 'ready': True}

def ready(flow, name='C', cue='yes'):
    flow.set_plan(flow.token(), PLAN)
    flow.begin(flow.token(), CONFIRM)
    flow.heard(flow.token(), {'heard_chord_and_role': cue})
    flow.sung_name(flow.token(), {'pitch_name': name, 'singing_attempted': True})
    flow.choose_arrangements(flow.token(), CHOICES)

def play(flow):
    flow.setup_target(flow.token(), True)
    flow.attack(flow.token(), True)
    flow.release(flow.token(), True)
    if flow.stage == 0:
        flow.reveal(flow.token())

def report(flow, diagnosis=''):
    return {'key': m.KEY, 'chord': 'G#7alt', 'role': '3', 'string_set': m.SETS[flow.stage],
            'target': flow.target()['arrangement']['target'], 'named_pitch': flow.named_pitch,
            'attack_count': 1, 'common': {n: 'yes' for n in m.COMMON},
            'stage_duties': {n: 'yes' for n in (('sung_pitch_correct',) if flow.stage == 0 else m.TRANSFER)},
            'response_speed': 'immediate', 'diagnosis': diagnosis,
            'notes': 'Synthetic manual report, not an actual hearing/singing/guitar observation.'}

def main():
    tick = time.monotonic()
    D = ROOT / 'Results' / LANE
    r = json.loads((D / 'reservation.json').read_text())
    s = json.loads((D / 'seal.json').read_text())
    for name in ('packet', 'model', 'producer', 'reservation', 'prior_r62_packet'):
        verify(s[name])
        check(True, 'exact sealed ' + name)
    row = json.loads((ROOT / s['packet']['path']).read_text())
    prior = json.loads((ROOT / r['prior_r62_packet']['path']).read_text().splitlines()[13])
    for name in ('package_key', 'source_identity', 'level', 'existing_parent_id', 'source_refs',
                 'source_payload', 'timing_authority', 'field_limitations'):
        check(row[name] == prior[name], 'original ' + name + ' retained')
    for name in ('events', 'tab_blocks', 'source_field_occurrences', 'canonical_ids_allocated', 'playback_admitted'):
        check(row['implementation'][name] == prior['implementation'][name], 'original ' + name + ' retained')
    check(row['implementation']['task']['printed_components'] == ['G#7alt', '3', 'B# / C', '', '', ''], 'exact source literal and blank choices')
    check(row['status'] == 'IMPLEMENTED_PRIVATE_QA_PENDING' and row['contract_capabilities']['complete_manual_response_contract'], 'one corrected private ready row')
    check(not row['contract_capabilities']['native_valid'] and not row['contract_capabilities']['installed']
          and not row['contract_capabilities']['Accepted'], 'source decision is no acceptance promotion')
    check(m.PC['B#'] == m.PC['C'] == m.base.answer_pc(13), 'printed enharmonic alternatives supported')
    flow = m.SourceReviewedChordToneFlow(m.KEY)
    ready(flow)
    check('reference_pitch' not in flow.learner_view(), 'source answer withheld before playing')
    refuse(lambda: flow.reveal(flow.token()), 'early source reveal', flow)
    play(flow)
    check(flow.learner_view()['reference_pitch'] == 'B# / C', 'literal answer retained at explicit reveal')
    flow.report(flow.token(), report(flow))
    flow.next_set(flow.token())
    flow.begin(flow.token())
    play(flow)
    flow.report(flow.token(), report(flow))
    refuse(lambda: flow.next_set(flow.token()), 'no third string set', flow)
    flow.finish(flow.token())
    check(flow.state == 'completed' and flow.history[-1]['data']['mastery_awarded'] is False, 'two-set finish awards no mastery')
    alias = m.SourceReviewedChordToneFlow(m.KEY)
    ready(alias, name='B#')
    check(alias.named_pitch == 'B#' and 'reference_pitch' not in alias.learner_view(), 'B# learner response retained without early correction')
    old = m.base.ChordToneFlow(m.KEY)
    old.set_plan(old.token(), PLAN)
    refuse(lambda: old.begin(old.token(), CONFIRM), 'historical r62 source refusal preserved', old)
    refuse(lambda: m.SourceReviewedChordToneFlow(m.base.KEYS[0]), 'correction cannot take another family key')
    uncertain = m.SourceReviewedChordToneFlow(m.KEY)
    ready(uncertain, cue='uncertain')
    play(uncertain)
    refuse(lambda: uncertain.report(uncertain.token(), report(uncertain)), 'uncertain cue needs diagnosis', uncertain)
    uncertain.report(uncertain.token(), report(uncertain, 'Need another clear chord/role cue.'))
    check(uncertain.state == 'needs_retry', 'uncertain cue cannot complete')
    bad = deepcopy(CHOICES)
    bad['string_set_2']['target']['fret'] = True
    refuse(lambda: m.base.validate_arrangements(bad), 'boolean chosen fret')
    bad = dict(r['source_decision'], sha256='0' * 64)
    refuse(lambda: verify(bad), 'source decision pin corruption')
    stale = alias.token()
    alias.setup_target(alias.token(), True)
    refuse(lambda: alias.attack(stale, True), 'stale exact source/action owner', alias)
    alias.attack(alias.token(), True)
    refuse(lambda: alias.release(alias.token(), False), 'false physical release', alias)
    print(json.dumps({'schema_version': 'fathom-private-cheap-integrity-sample.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
        'checks_passed': checks, 'causal_refusals_passed': refusals, 'refusal_criteria': labels,
        'complete_two_set_synthetic_walkthroughs': 1, 'selected_corrected_keys': 1, 'new_attempted_identities': 0,
        'source_reviewed': 1, 'independently_behavior_reviewed': 0, 'outcome': 'PASS',
        'synthetic_reports_are_observations': False, 'inputs': [pin(Path('Tests') / LANE / 'check_integrity.py'), s['model'], s['packet']],
        'not_run': ['combined independent behavior/bulk state/permutation', 'native', 'installed app', 'physical/listening', 'broad regression/release']}))

if __name__ == '__main__':
    main()
