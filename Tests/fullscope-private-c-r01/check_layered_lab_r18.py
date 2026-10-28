from pathlib import Path
import copy, datetime, hashlib, json, resource, sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-c-r01'))
from layered_lab_contract_r18 import LayeredLabSession

checks = 0


def check(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)


def refuses(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


packet = ROOT / 'Build/fullscope-private-c-r01/level076-r18/layered-lab-overlay.json'
r = json.loads(packet.read_text())
c = r['implementation']['task']['contract']
layers = c['worksheet_layer_order']
key = 'exercise-completeness-r01/level076/moduleg/p013-u001/moduleglayeredsixteenbartranscriptionlab'
check(r['package_key'] == key and r['source_identity'] == key.split('/', 1)[1], 'one exact unchanged official key')
for ref in [*r['source_refs'], c['state_engine_ref'], c['source_extraction_provenance']['source_stream_artifact']]:
    path = ROOT / ref['path']
    check(path.stat().st_size == ref['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == ref['sha256'], 'source/engine pin')
original = next(ROOT / ref['path'] for ref in r['source_refs'] if ref['path'].endswith('.txt'))
source_lines = original.read_text().splitlines()
check(len(c['source_bars']) == 16 and sum(len(b['melodic_spellings_in_source_order']) for b in c['source_bars']) == 64, 'sixteen bars sixty-four ordered melody spellings')
for i, bar in enumerate(c['source_bars'], 1):
    check(bar['bar_number'] == i and bar['source_txt_line'] == 148 + i, 'exact ordered bar locator')
    check([bar[k] for k in ['Bar', 'Chord', 'Bass', 'Rhythm clue', 'Melodic layer', 'Arrangement']] == [x.strip() for x in source_lines[147+i].split('|')], 'all six original fields exact')
check(c['source_bars'][-1]['Rhythm clue'] == 'half + whole', 'unresolved precise ending timing not silently rewritten')
check(len(r['implementation']['source_field_occurrences']) == 80, 'single source script eighty literal pitch occurrences')
check([x['source_order'] for x in r['implementation']['source_field_occurrences']] == list(range(1, 81)), 'deterministic literal ordering')
check(all(x['onset_q'] is None and x['duration_q'] is None for x in r['implementation']['source_field_occurrences']), 'no inferred native timing')
check(len(c['verification_reference']) == 4 and len(c['verification_passes']) == 6 and len(c['manual_score_layers']) == 6, 'all original worksheet/verification components')

responses = lambda label: [f'Synthetic {label} response bar {i}' for i in range(1, 17)]


def filled_session(mode='partner', exposure=False):
    session = LayeredLabSession(c)
    session.bind_source(mode, 'Synthetic external source', 'Synthetic performance/recording report', prior_learner_exposure=exposure)
    for layer in layers:
        session.commit_layer(layer, responses(layer), [0, 1, 2, 1])
    return session


s = LayeredLabSession(c)
check(s.source_player_view()['bars'] == c['source_bars'], 'source-player script available before learner response')
check(s.learner_view()['source_bars'] is None and s.learner_view()['reference'] is None, 'learner source hidden')
check(refuses(lambda: s.commit_layer(layers[0], responses('before source'), [0]*4)), 'external prerequisite first')
check(refuses(lambda: s.bind_source('app_generated', 'synthetic', 'synthetic')), 'app-supplied audio forbidden')
check(refuses(lambda: s.bind_source('partner', 'synthetic', 'synthetic', recording_reference='synthetic file')), 'no fake partner recording')
check(refuses(lambda: s.bind_source('recording', 'synthetic', 'synthetic', prior_learner_exposure=1)), 'exposure must be explicit bool')
s.bind_source('recording', 'Synthetic external recording', 'Recorded once: synthetic self-report', recording_reference=None)
check(s.snapshot()['source']['recording_reference'] is None, 'recording self-report allowed without invented printed file requirement')
check(refuses(lambda: s.bind_source('partner', 'other', 'other')), 'source cannot silently replace after binding')
check(refuses(s.reveal_reference), 'early reveal refused')
check(refuses(lambda: s.score_layer('Rhythm', 2, 'synthetic')), 'early score refused')
check(refuses(lambda: s.commit_layer(layers[1], responses('bass'), [0]*4)), 'printed layer order')
check(refuses(lambda: s.commit_layer(layers[0], responses('form')[:15], [0]*4)), 'partial all-sixteen-bars row refused')
check(refuses(lambda: s.commit_layer(layers[0], ['']*16, [0]*4)), 'empty responses refused; explicit uncertainty required')
check(refuses(lambda: s.commit_layer(layers[0], responses('form'), [0]*3)), 'each four-bar block confidence required')
for bad in [True, -1, 3, 1.0, '2', None]:
    check(refuses(lambda: s.commit_layer(layers[0], responses('form'), [bad]*4)), 'invalid confidence refused')
for n, layer in enumerate(layers):
    answer = responses(layer)
    s.commit_layer(layer, answer, [0, 1, 2, 1])
    answer[0] = 'mutation'
    check(s.snapshot()['worksheet'][layer]['bar_responses'][0] != 'mutation', 'detached input')
    check(s.learner_view()['source_bars'] is None, 'source hidden until explicit completed reveal')
    if n < 6:
        check(refuses(s.reveal_reference), 'reference withheld across every partial stage')
check(refuses(lambda: s.commit_layer(layers[0], responses('duplicate'), [0]*4)), 'no overwrite without revision')
check(s.complete(), 'all seven rows complete')
check(len(s.relisten_priority()) == 7, 'all low-confidence blocks explicit')
check(refuses(lambda: s.report_relisten(layers[0], 2, 'synthetic')), 'low confidence priority preserved')
check(refuses(lambda: s.report_relisten(layers[0], True, 'synthetic')), 'block bool rejected')
for layer in layers:
    s.report_relisten(layer, 1, 'Synthetic targeted re-listen')
check(s.relisten_priority() == [], 'each zero block can be serviced without infinite priority lock')
s.report_relisten(layers[0], 2, 'Synthetic later nonzero block')
view = s.reveal_reference()
check(view['source_bars'] == c['source_bars'] and view['reference'] == c['verification_reference'], 'all source/reference fields revealed after complete worksheet')
view['source_bars'][0]['Chord'] = 'mutation'
check(s.source_player_view()['bars'][0]['Chord'] == 'Cmaj7', 'reference output detached')
for layer in c['manual_score_layers']:
    s.score_layer(layer, 0, 'Synthetic uncertainty')
check(refuses(lambda: s.score_layer('native correctness', 2, 'synthetic')), 'unknown score category refused')
check(refuses(lambda: s.score_layer('Rhythm', True, 'synthetic')), 'manual score bool refused')
s.score_layer('Rhythm', 2, 'Synthetic manual revision')
check(s.snapshot()['history'][-1]['previous']['score_self_report'] == 0, 'manual score revision retained')
for name in c['verification_passes']:
    s.report_verification(name, 'Synthetic external verification self-report')
check(len(s.snapshot()['verifications']) == 6, 'all six source verification passes supported')
check(refuses(lambda: s.report_verification('automatic recognition', 'synthetic')), 'unprinted automated verification refused')
check(refuses(lambda: s.correct_faulty_block(['Synthetic']*4, 1)), 'classification before correction')
check(refuses(lambda: s.begin_repair('RHYTHM', layers[2], 1, 'synthetic')), 'cannot repair harmony under rhythm classification')
check(refuses(lambda: s.begin_repair('OTHER', layers[2], 1, 'synthetic')), 'exact six error classes required')

for error, allowed_layers in c['error_to_worksheet_layers'].items():
    for layer in allowed_layers:
        before = s.snapshot()
        s.begin_repair(error, layer, 2, 'Synthetic classified disagreement')
        check(refuses(lambda: s.report_complete_block_replay('synthetic', False)), 'replay after correction')
        check(refuses(lambda: s.correct_faulty_block(['Synthetic']*3, 1)), 'four-bar selected block complete')
        s.correct_faulty_block(['Synthetic correction']*4, 0)
        now = s.snapshot()
        for other in layers:
            if other != layer:
                check(now['worksheet'][other] == before['worksheet'][other], 'unrelated source layer remains exact')
        check(now['worksheet'][layer]['bar_responses'][:4] == before['worksheet'][layer]['bar_responses'][:4] and now['worksheet'][layer]['bar_responses'][8:] == before['worksheet'][layer]['bar_responses'][8:], 'other blocks unchanged')
        check(now['worksheet'][layer]['bar_responses'][4:8] == ['Synthetic correction']*4, 'exact four-bar replacement')
        check(c['error_to_score_layer'][error] not in now['scores'], 'affected score invalidated')
        check(refuses(lambda: s.begin_repair(error, layer, 3, 'synthetic')), 'next repair waits for whole-block replay')
        check(refuses(lambda: s.correct_faulty_block(['Synthetic again']*4, 1)), 'second unreviewed overwrite refused')
        check(refuses(lambda: s.score_layer('Rhythm', 1, 'synthetic')), 'score cannot bypass unresolved block replay')
        check(refuses(lambda: s.restart_worksheet('synthetic')), 'cannot discard pending block replay')
        check(refuses(lambda: s.report_complete_block_replay('synthetic', 0)), 'explicit damage check required')
        s.report_complete_block_replay('Synthetic complete-block replay and comparison', True)
        check(s.snapshot()['history'][-1]['followup_classification_needed'] and not s.snapshot()['history'][-1]['performance_observed'], 'damage report remains manual followup not success')
        check(s.source_player_view()['bars'] == c['source_bars'], 'repairs never rewrite original source script')

before = s.snapshot()
s.cancel()
for fn in [s.reveal_reference, s.learner_view, s.source_player_view, lambda: s.report_verification('Roots only', 'synthetic')]:
    check(refuses(fn), 'cancelled operations refused')
s.reopen()
check(s.snapshot() == before, 'cancel/reopen preserves all responses/history/source')
s.restart_worksheet('Synthetic deliberate new transcription pass')
check(s.learner_view()['source_bars'] is None and s.learner_view()['prior_reference_disclosure'], 'revision hides current reference but retains prior exposure')
check(s.snapshot()['history'][-1]['previous_worksheet'] == before['worksheet'], 'prior worksheet retained')
s.commit_layer(layers[0], ['uncertain']*16, [0]*4)
check(s.snapshot()['worksheet'][layers[0]]['prior_reference_disclosure'], 'new response does not pretend blind after reveal')
check(refuses(s.reveal_reference), 'revision again requires all seven rows')
t = filled_session(exposure=True)
check(all(row['prior_external_source_exposure'] for row in t.snapshot()['worksheet'].values()), 'self-recording/source-study exposure disclosed')
u = LayeredLabSession(c)
u.report_prior_learner_source_exposure('Synthetic learner previously studied source')
u.bind_source('partner', 'Synthetic partner', 'Synthetic played source', prior_learner_exposure=False)
check(u.learner_view()['prior_external_source_exposure'], 'external exposure recorded')
for state in [s.snapshot(), t.snapshot(), u.snapshot()]:
    check(not any(state[k] for k in ['app_audio_supplied', 'performance_observed', 'Attempt_credit', 'mastery_awarded']) and state['automatic_pass_threshold'] is None, 'no acoustic/audio/credit or borrowed threshold claims')

dest = ROOT / 'Results/fullscope-private-c-r01/level076-r18/integrity.json'
check(not dest.exists(), 'immutable evidence destination')
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result': 'PASS',
          'checks': checks, 'complete_manual_contracts': 1, 'new_category_promotions': 1,
          'packet_sha256': hashlib.sha256(packet.read_bytes()).hexdigest(),
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'all_responses_performances_and_listens_synthetic': True,
          'native_app_gui': 'NOT_RUN'}
dest.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
