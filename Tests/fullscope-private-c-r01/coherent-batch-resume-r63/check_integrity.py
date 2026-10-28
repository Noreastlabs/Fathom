"""One full synthetic model walkthrough plus cheap source/schema/causal guards; no broad campaign."""
from copy import deepcopy
import datetime
import json
from pathlib import Path
import sys
import time
ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-batch-resume-r63')
sys.path.insert(0, str(ROOT / 'Tools' / LANE))
import reconstruction_contract_r03 as m
from produce import pin, verify

checks, refusals, refusal_labels = 0, 0, []
def check(ok, label):
    global checks
    if not ok:
        raise AssertionError(label)
    checks += 1

def refuse(call, label, flow=None):
    global refusals
    before = deepcopy(flow.__dict__) if flow else None
    try:
        call()
    except (ValueError, AssertionError):
        if flow:
            check(flow.__dict__ == before, label + ': no mutation')
        refusals += 1
        refusal_labels.append(label)
    else:
        raise AssertionError('Failed to refuse: ' + label)

PLAN = {'prerequisites': {'original_workbook': True, 'own_instrument': True},
        'recording': {'kind': 'external_recording', 'reference': 'synthetic external source fixture',
                      'declared_sha256': None, 'ready': True},
        'source_declarations': {'recorded_once': 'yes', 'transcriber_did_not_study_source_card': 'yes'}}
RELEASE = {'learner_released': True, 'external_source_stopped': True}

def written(flow, wrong=False, unknown=False):
    flow.set_source(flow.token(), PLAN)
    for name in m.PASSES:
        flow.begin_written(flow.token(), {'key': m.KEY, 'pass': name,
            'recording_reference': PLAN['recording']['reference'], 'ready': True})
        flow.heard(flow.token(), {'heard_source': 'yes'})
        flow.request_stop(flow.token())
        flow.release(flow.token(), RELEASE)
        if name == 'exact_notes':
            bars = [p.split('-') for _, p, _ in m.RAW]
            if wrong:
                bars[0][0] = 'F'
            if unknown:
                bars[0][0] = None
        elif name == 'chord_function':
            bars = [{'chord': c, 'function': 'manual function declaration, no automatic oracle'} for c, _, _ in m.RAW]
        else:
            bars = ['manual ' + name + ' declaration'] * 16
        flow.commit_written(flow.token(), {'bars': bars, 'notes': 'Synthetic written fixture; no hearing observation.'})
        flow.next_written(flow.token())

def choices(flow):
    notes = [n for bar in flow.responses['exact_notes']['bars'] for n in bar]
    contacts = []
    for note in notes:
        pc = m.PC[note] if note is not None else 4
        options = [{'string': s, 'fret': f, 'midi': base + f}
                   for s, base in m._legacy.TUNING.items() for f in range(4, 9) if (base + f) % 12 == pc]
        assert options
        contacts.append(options[0])
    return {'position': {'minimum_fret': 4, 'maximum_fret': 8, 'rationale': 'Authored synthetic chosen five-fret frame.'},
            'contacts': contacts, 'source_scope_ack': True}

def play_register(flow):
    for bar in range(16):
        flow.sung_bar(flow.token(), True)
        flow.play_bar(flow.token(), True)
        flow.release(flow.token(), RELEASE)
        flow.report_bar(flow.token(), {'key': m.KEY, 'bar': bar + 1, 'contacts': flow.target()['contacts'],
            'sing_count': 1, 'attack_counts': [1, 1, 1, 1], 'common': {n: 'yes' for n in m.COMMON},
            'diagnosis': '', 'notes': 'Synthetic manual report, no performance observation.'})
        flow.next_bar(flow.token())

def main():
    tick = time.monotonic()
    rpath = Path('Results') / LANE / 'reservation.json'
    r = json.loads((ROOT / rpath).read_text())
    seal = json.loads((ROOT / 'Results' / LANE / 'seal-r03.json').read_text())
    for name in ('packet', 'model', 'producer', 'source_check', 'reservation'):
        verify(seal[name])
        check(True, 'sealed ' + name + ' identity')
    row = json.loads((ROOT / seal['packet']['path']).read_text())
    original = json.loads((ROOT / r['base_packet']['path']).read_text().splitlines()[157])
    for name in ('package_key', 'source_identity', 'level', 'existing_parent_id', 'source_refs',
                 'source_payload', 'timing_authority', 'field_limitations'):
        check(row[name] == original[name], 'original ' + name + ' retained')
    for name in ('events', 'tab_blocks', 'source_field_occurrences', 'canonical_ids_allocated', 'playback_admitted'):
        check(row['implementation'][name] == original['implementation'][name], 'original ' + name + ' retained')
    check(row['implementation']['task']['table_fields'] == original['implementation']['task']['table_fields'], 'raw extraction/footer fragments retained')
    check(len(m.RAW) == 16 and sum(len(p.split('-')) for _, p, _ in m.RAW) == 64, 'all16bars/64tones')
    check(m.RAW[-1] == ('Gmaj7', 'F#-D-B-G', 'F#'), 'independently accepted finalbar literal')
    check(m.BLOCKS == ('1-4', '5-8', '9-12', '13-16'), 'all four source worksheet blocks')
    check(row['status'] == 'IMPLEMENTED_PRIVATE_QA_PENDING' and row['contract_category'] == 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT', 'one privately ready source-supported contract')
    check(not row['contract_capabilities']['native_valid'] and not row['contract_capabilities']['installed']
          and not row['contract_capabilities']['Accepted'], 'source review does not grant runtime/official acceptance')
    flow = m.FullModelReconstructionFlow(m.KEY)
    check('source_reference' not in flow.learner_view(), 'source card withheld initially')
    written(flow)
    refuse(lambda: flow.reveal_source(flow.token()), 'source reveal before first-register playing', flow)
    plan = choices(flow)
    flow.choose_first_position(flow.token(), plan)
    refuse(lambda: flow.finish(flow.token()), 'early whole-model finish', flow)
    play_register(flow)
    check(flow.state == 'first_register_reported' and flow.bar == 16, 'all sixteen first-register bars reported')
    flow.reveal_source(flow.token())
    check(flow.pitch_matches is True and len(flow.learner_view()['source_reference']) == 16, 'full64-tone symbolic reference after playing')
    second = deepcopy(plan)
    second['position'] = {'minimum_fret': 16, 'maximum_fret': 20, 'rationale': 'Chosen octave-up synthetic frame.'}
    second['contacts'] = [dict(c, fret=c['fret'] + 12, midi=c['midi'] + 12) for c in plan['contacts']]
    second['octave_shift_semitones'] = 12
    bad = dict(second, octave_shift_semitones=0)
    refuse(lambda: flow.begin_second_register(flow.token(), bad), 'same sounding register is no transfer', flow)
    flow.begin_second_register(flow.token(), second)
    play_register(flow)
    check(flow.state == 'both_registers_reported' and flow.register == 1, 'all sixteen second-register bars reported')
    refuse(lambda: flow.finish(flow.token()), 'missing manual score declarations', flow)
    scores = {block: {'hearing_accuracy': 0, 'first_attack_fretboard_accuracy': 0} for block in m.BLOCKS}
    bad = deepcopy(scores)
    bad['13-16']['hearing_accuracy'] = True
    refuse(lambda: flow.declare_scores(flow.token(), bad), 'boolean manual score masquerading as0–2', flow)
    flow.declare_scores(flow.token(), scores)
    check(flow.history[-1]['data']['declared_total'] == 0, 'printed manual score0 has no invented passing threshold')
    flow.finish(flow.token())
    check(flow.state == 'completed' and flow.history[-1]['data']['mastery_awarded'] is False
          and flow.history[-1]['data']['performance_verified'] is False, 'manual task finish is no performance/mastery/acceptance')
    wrong = m.FullModelReconstructionFlow(m.KEY)
    written(wrong, wrong=True)
    wrong.choose_first_position(wrong.token(), choices(wrong))
    check(wrong.target()['contacts'][0]['midi'] % 12 == m.PC['F'] and 'source_reference' not in wrong.learner_view(), 'wrong written pitch stays playable, no hidden correction')
    unknown = m.FullModelReconstructionFlow(m.KEY)
    written(unknown, unknown=True)
    refuse(lambda: unknown.choose_first_position(unknown.token(), choices(unknown)), 'unknown written note never filled from source', unknown)
    unknown.diagnose_unable(unknown.token(), 'Need another written hearing for the unknown note.')
    check(unknown.state == 'needs_written_retry', 'unknown diagnosis retained')
    bad = dict(seal['source_check'], sha256='0' * 64)
    refuse(lambda: verify(bad), 'source/provenance pin corruption')
    refuse(lambda: m.FullModelReconstructionFlow('new-key'), 'nonexisting child key')
    stale = wrong.token()
    wrong.sung_bar(wrong.token(), True)
    refuse(lambda: wrong.play_bar(stale, True), 'stale source/action token', wrong)
    wrong.cancel(wrong.token())
    wrong.reopen(wrong.token())
    refuse(lambda: wrong.sung_bar(wrong.token(), True), 'reopen needs physical/source release', wrong)
    wrong.release(wrong.token(), RELEASE)
    check(wrong.state == 'sing_bar', 'interrupted bar resumes after release')
    print(json.dumps({'schema_version': 'fathom-private-cheap-integrity-sample.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
        'checks_passed': checks, 'causal_refusals_passed': refusals, 'refusal_criteria': refusal_labels,
        'complete_synthetic_model_walkthroughs': 1, 'bars_in_that_walkthrough': 32,
        'chosen_contacts_in_that_walkthrough': 128, 'selected_keys': 1, 'source_reviewed_keys': 1,
        'independently_behavior_reviewed': 0, 'inputs': [pin(Path('Tests') / LANE / 'check_integrity.py'), seal['packet'], seal['model']],
        'synthetic_reports_are_observations': False, 'outcome': 'PASS',
        'not_run': ['bulk state/permutation/behavior', 'native', 'installed app', 'physical/listening', 'broad regression/release']}))

if __name__ == '__main__':
    main()
