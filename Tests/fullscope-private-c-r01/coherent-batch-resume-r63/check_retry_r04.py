"""One affected nullable-written causal/recovery path; no wider model campaign."""
from copy import deepcopy
import datetime
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-batch-resume-r63')
sys.path.insert(0, str(ROOT / 'Tools' / LANE))
import reconstruction_contract_r03 as prior
import reconstruction_contract_r04 as model
from produce import pin, verify

spec = importlib.util.spec_from_file_location('prior_producer_fixture', Path(__file__).with_name('check_integrity.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
checks = refusals = 0


def check(ok, label):
    global checks
    assert ok, label
    checks += 1


def refuse(flow, call, label):
    global refusals
    before = deepcopy(flow.__dict__)
    try:
        call()
    except model.Refusal:
        check(flow.__dict__ == before, label + ': refused without mutation')
        refusals += 1
    else:
        raise AssertionError('Expected refusal: ' + label)


def written(flow, unknown=True, source_setup=True):
    if source_setup:
        flow.set_source(flow.token(), fixture.PLAN)
    for name in model.PASSES:
        flow.begin_written(flow.token(), {'key': model.KEY, 'pass': name,
            'recording_reference': fixture.PLAN['recording']['reference'], 'ready': True})
        flow.heard(flow.token(), {'heard_source': 'yes'})
        flow.request_stop(flow.token())
        flow.release(flow.token(), fixture.RELEASE)
        if name == 'exact_notes':
            bars = [p.split('-') for _, p, _ in model.RAW]
        elif name == 'chord_function':
            bars = [{'chord': c, 'function': 'Unassessed manual declaration.'} for c, _, _ in model.RAW]
        else:
            bars = ['Unassessed manual declaration.'] * 16
            if name == 'contour' and unknown:
                bars[0] = None
        flow.commit_written(flow.token(), {'bars': bars, 'notes': 'Synthetic fixture; no hearing observation.'})
        flow.next_written(flow.token())


def causal_path(cls):
    flow = cls(model.KEY)
    written(flow)
    plan = fixture.choices(flow)
    flow.choose_first_position(flow.token(), plan)
    fixture.play_register(flow)
    flow.reveal_source(flow.token())
    second = deepcopy(plan)
    second['position'] = {'minimum_fret': 16, 'maximum_fret': 20, 'rationale': 'Synthetic authored octave-up frame.'}
    second['contacts'] = [dict(c, fret=c['fret'] + 12, midi=c['midi'] + 12) for c in plan['contacts']]
    second['octave_shift_semitones'] = 12
    flow.begin_second_register(flow.token(), second)
    fixture.play_register(flow)
    flow.declare_scores(flow.token(), {b: {'hearing_accuracy': 0, 'first_attack_fretboard_accuracy': 0} for b in model.BLOCKS})
    return flow


def main():
    tick = time.monotonic()
    seal = json.loads((ROOT / 'Results' / LANE / 'seal-r04.json').read_text())
    for key in ('packet', 'model', 'producer', 'source_check', 'reservation', 'retry_correction_reservation', 'prior_source_reviewed_seal'):
        verify(seal[key]); check(True, 'sealed ' + key)
    newrow = json.loads((ROOT / seal['packet']['path']).read_text())
    oldseal = json.loads((ROOT / seal['prior_source_reviewed_seal']['path']).read_text())
    for key in ('model', 'packet'):
        verify(oldseal[key]); check(True, 'historical r03 ' + key)
    oldrow = json.loads((ROOT / oldseal['packet']['path']).read_text())
    for key in ('package_key', 'source_identity', 'level', 'existing_parent_id', 'source_refs', 'source_payload', 'timing_authority', 'field_limitations'):
        check(newrow[key] == oldrow[key], 'same exact source ' + key)
    check(newrow['implementation']['events'] == oldrow['implementation']['events'], 'no source event change')
    check(newrow['contract_capabilities'] == oldrow['contract_capabilities'], 'no acceptance capability change')
    old = causal_path(prior.FullModelReconstructionFlow)
    check(old.state == 'both_registers_reported' and old.responses['contour']['bars'][0] is None, 'historical causal terminal state')
    refuse(old, lambda: old.finish(old.token()), 'historical unknown finish')
    refuse(old, lambda: old.restart_written(old.token(), 'Diagnosed retained unknown contour.'), 'historical reproduced restart trap')
    flow = causal_path(model.FullModelReconstructionFlow)
    check(flow.state == 'both_registers_reported', 'r04 same causal terminal state')
    refuse(flow, lambda: flow.finish(flow.token()), 'r04 unknown finish remains refused')
    refuse(flow, lambda: flow.restart_written(flow.token(), ''), 'r04 missing diagnosis')
    before = deepcopy(flow.__dict__)
    token = flow.token()
    flow.restart_written(token, 'Resolve the retained unknown contour through written reconstruction.')
    check(flow.state == 'ready_written' and flow.responses == {}, 'r04 reachable written recovery')
    check(flow.revealed is True and flow.reference_history == before['reference_history']
          and flow.response_history == before['response_history'], 'prior response/source reveal history retained')
    check(flow.generation == before['generation'] + 1 and flow.register == flow.bar == flow.pass_index == 0, 'new current attempt owner and source order')
    check(flow.contacts is None and flow.first_contacts is None and flow.position is None
          and flow.score_declarations is None and flow.hearing_reports == {} and flow.pitch_matches is None, 'attempt-specific choices/scores cleared')
    refuse(flow, lambda: flow.begin_written(token, {}), 'r04 stale pre-retry owner')
    flow.cancel(flow.token()); flow.reopen(flow.token())
    refuse(flow, lambda: flow.begin_written(flow.token(), {}), 'r04 cancellation retains release fence')
    flow.release(flow.token(), fixture.RELEASE)
    check(flow.state == 'ready_written', 'r04 safe written resume after explicit release')
    written(flow, unknown=False, source_setup=False)
    check(flow.state == 'choose_first_position' and flow.responses['contour']['bars'][0] is not None,
          'r04 all four replacement written passes can proceed')
    check(flow.revealed is True and flow.reference_history == before['reference_history']
          and flow.response_history[:4] == before['response_history'], 'no fresh blind assessment or historical response erasure')
    print(json.dumps({'schema_version': 'fathom-private-affected-retry-causal-check.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.monotonic() - tick,
        'checks_passed': checks, 'causal_refusals_passed': refusals,
        'historical_failure_reproduced': True, 'corrected_same_key_recovery': True,
        'synthetic_full_register_walkthroughs': 2, 'bars_total': 64,
        'post_retry_written_passes': 4, 'outcome': 'PASS', 'selected_keys': 1,
        'new_attempted_identities': 0, 'independently_behavior_reviewed': 0, 'Accepted': 0,
        'inputs': [pin(Path('Tests') / LANE / 'check_retry_r04.py'), seal['packet'], seal['model']],
        'synthetic_reports_are_observations': False,
        'not_run': ['independent affected broader review', 'unrelated B/ModuleF families', 'native', 'installed app', 'listening', 'release']}))


if __name__ == '__main__':
    main()
