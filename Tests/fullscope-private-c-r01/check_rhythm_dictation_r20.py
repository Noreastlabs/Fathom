from pathlib import Path
import datetime, hashlib, json, resource, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-c-r01'))
from rhythm_dictation_contract_r20 import RhythmDictationSession
checks = 0


def ck(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)


def refusal(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


packet = ROOT / 'Build/fullscope-private-c-r01/level076-r20/rhythm-dictation-overlays.jsonl'
rows = [json.loads(line) for line in packet.read_text().splitlines()]
ck(len(rows) == 14 and len({r['package_key'] for r in rows}) == 14, 'exact fourteen distinct children')
ck([r['implementation']['task']['contract']['source_dictation_number'] for r in rows] == [*range(1, 10), *range(11, 16)], 'combined10/16 ambiguity excluded')
for r in rows:
    c = r['implementation']['task']['contract']
    txt_ref = next(x for x in r['source_refs'] if x['path'].endswith('.txt'))
    original = (ROOT / txt_ref['path']).read_text().splitlines()[c['original_txt_line']-1]
    ck(original == f"Dictation {c['source_dictation_number']}: {c['source_rhythm_string']}", 'exact original line including ties/spaces')
    ck(c['source_rhythm_string'] in r['source_payload']['pdf_region_text'], 'same exact PDF card string')
    ck(''.join(x['character'] for x in c['ordered_literal_characters']) == c['source_rhythm_string'], 'literal character order preserved without timing')
    for ref in [*r['source_refs'], c['state_engine_ref']]:
        ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest() == ref['sha256'], 'source/engine binding')
    s = RhythmDictationSession(c)
    ck(s.source_player_view()['rhythm_script'] == c['source_rhythm_string'], 'source-player script available independently')
    ck(s.learner_view()['rhythm_reference'] is None, 'learner reference initially hidden')
    ck(refusal(lambda: s.report_hearing('synthetic')), 'source declaration before hearing')
    ck(refusal(lambda: s.bind_external_source('synthetic', 'app_audio', 'synthetic')), 'app-supplied sound forbidden')
    ck(refusal(lambda: s.bind_external_source('synthetic', 'unpitched_contacts', 'synthetic', 1)), 'explicit bool study report')
    s.bind_external_source('Synthetic external player', 'unpitched_contacts', 'Synthetic interpretation, no audio inspected')
    ck(refusal(lambda: s.bind_external_source('other', 'unpitched_contacts', 'other')), 'source immutable')
    ck(refusal(lambda: s.submit_contacts('synthetic', 'synthetic')), 'hearing before contacts')
    ck(refusal(s.reveal_rhythm_reference), 'own response before reveal')
    ck(refusal(lambda: s.report_rhythm_stability(True, 'synthetic')), 'contacts before stability')
    s.report_hearing('Synthetic heard source')
    s.submit_contacts('Synthetic contact transcription', 'Synthetic tie/grouping uncertainty')
    ck(refusal(lambda: s.submit_contacts('overwrite', 'overwrite')), 'no silent answer overwrite')
    ck(s.reveal_rhythm_reference()['rhythm_reference'] == c['source_rhythm_string'], 'own transcription then exact source reference')
    ck(refusal(lambda: s.report_rhythm_stability(1, 'synthetic')), 'stability bool required')
    s.report_rhythm_stability(False, 'Synthetic unstable rhythm')
    ck(not s.manual_responses_complete(), 'not-stable response remains unresolved')
    s.report_rhythm_stability(True, 'Synthetic manual stable report')
    ck(s.manual_responses_complete() and s.snapshot()['pitch_or_chord'] is None, 'unpitched source completes without fake pitch answer')
    ck(refusal(lambda: s.submit_pitch_or_chord('Cmaj7')), 'no invented harmonic answer for unpitched source')
    before = s.snapshot()
    s.cancel()
    ck(refusal(s.learner_view) and refusal(lambda: s.report_hearing('synthetic')), 'cancel guards')
    s.reopen()
    ck(s.snapshot() == before, 'cancel/reopen retains all state')
    s.revise_contacts('Synthetic new transcription pass')
    ck(s.learner_view()['rhythm_reference'] is None and s.learner_view()['prior_reference_disclosure'], 'prior reveal retained without copying reference into new answer')
    ck(s.snapshot()['history'][-1]['contacts'] == before['contacts'], 'prior contacts history retained')
    ck(refusal(lambda: s.submit_contacts('synthetic', 'synthetic')), 'new hearing report for revised pass')
    s.report_hearing('Synthetic heard again')
    s.submit_contacts('uncertain', 'uncertain')
    ck(s.snapshot()['contacts']['prior_reference_disclosure'], 'new answer acknowledges previous reveal')
    t = RhythmDictationSession(c)
    t.bind_external_source('Synthetic pitched source', 'external_pitch_or_chord', 'Synthetic performer-selected pitch', True)
    t.report_hearing('Synthetic pitched hearing report')
    t.submit_contacts('Synthetic rhythm answer', 'Synthetic grouping report')
    ck(refusal(lambda: t.submit_pitch_or_chord('Synthetic chord')), 'pitched answer cannot precede stable rhythm')
    t.report_rhythm_stability(True, 'Synthetic stable report')
    ck(not t.manual_responses_complete(), 'declared pitched-source response still pending')
    t.submit_pitch_or_chord('uncertain')
    ck(t.manual_responses_complete() and t.snapshot()['contacts']['prior_source_study_self_report'], 'explicit uncertain pitch answer allowed; source study retained')
    t.report_rhythm_stability(False, 'Synthetic stability retracted')
    ck(t.snapshot()['pitch_or_chord'] is None and not t.manual_responses_complete(), 'new instability invalidates stale pitch answer')
    ck(t.snapshot()['history'][-1]['previous_pitch_response']['answer_self_report'] == 'uncertain', 'invalidated pitch response remains history')
    ck(not any(t.snapshot()[x] for x in ['performance_observed', 'app_audio_supplied', 'Attempt_credit', 'mastery_awarded']), 'no audio/performance/credit claims')
dest = ROOT / 'Results/fullscope-private-c-r01/level076-r20/integrity.json'
ck(not dest.exists(), 'immutable output')
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result': 'PASS', 'checks': checks,
          'complete_manual_contracts': 14, 'new_category_promotions': 14,
          'packet_sha256': hashlib.sha256(packet.read_bytes()).hexdigest(),
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'all_responses_and_audio_reports_synthetic': True, 'native_app_gui': 'NOT_RUN'}
dest.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
