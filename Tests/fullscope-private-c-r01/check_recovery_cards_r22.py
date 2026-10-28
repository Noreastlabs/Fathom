from pathlib import Path
import datetime, hashlib, json, resource, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-c-r01'))
from recovery_card_contract_r22 import RecoveryCardSession
checks = 0


def ck(value, label):
    global checks
    checks += 1
    if not value:
        raise AssertionError(label)


def refused(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


packet = ROOT / 'Build/fullscope-private-c-r01/level073-r22/recovery-card-overlays.jsonl'
rows = [json.loads(s) for s in packet.read_text().splitlines()]
base = {r['package_key']: r for r in map(json.loads, (ROOT/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines())}
ck(len(rows) == len({r['package_key'] for r in rows}) == 12, 'twelve exact existing recovery keys')
opens = {1: 64, 2: 59, 3: 55, 4: 50, 5: 45, 6: 40}
for r in rows:
    c = r['implementation']['task']['contract']
    original = base[r['package_key']]['implementation']['events']
    ck(r['implementation']['events'] == c['printed_contacts'] == original, 'original24 contact objects exactly preserved')
    for ref in [*r['source_refs'], c['state_engine_ref']]:
        ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest() == ref['sha256'], 'source/engine pin')
    for e, alternate in zip(original, c['authored_upper_octave_candidate']):
        ck(alternate['chosen_string_number'] == e['string_number'] and alternate['chosen_fret'] == e['fret']+12, 'same-string explicit authored upper octave')
        ck(opens[alternate['chosen_string_number']]+alternate['chosen_fret'] == alternate['derived_standard_tuning_midi'] == e['written_pitch_theory']['midi_at_stated_standard_tuning']+12, 'source and authored pitch parity')
        ck(12 <= alternate['chosen_fret'] <= 22 and alternate['canonical_id'] is None, 'finite actual candidate frets no IDs')
        ck(alternate['retained_note_spelling'] == e['printed_note'] and alternate['retained_harmonic_role'] == e['printed_role'] and alternate['onset_q'] is None and alternate['duration_q'] is None, 'role/note identity no timing invented')
    source_interval = original[1]['written_pitch_theory']['midi_at_stated_standard_tuning']-original[0]['written_pitch_theory']['midi_at_stated_standard_tuning']
    ck(c['authored_upper_octave_candidate'][1]['derived_standard_tuning_midi']-c['authored_upper_octave_candidate'][0]['derived_standard_tuning_midi'] == source_interval, 'printed interval retained rather than nearest pitch rewrite')
    s = RecoveryCardSession(c)
    ck(s.current_contact() is None and not s.snapshot()['selected_alternate'], 'no unstated context or automatic alternate selection')
    ck(refused(lambda: s.bind_context('foreign chord', 'pulse', 'form', 'landmark')), 'exact original active chord required')
    ck(refused(lambda: s.report_contact('printed_pair', 1, 'synthetic')), 'context before reports')
    ck(refused(s.select_upper_octave_candidate), 'original pair before chosen repeat')
    s.bind_context(c['active_chord'], 'Synthetic external pulse', 'Synthetic surrounding form', 'Synthetic next chord change')
    ck(s.current_contact() == original[0], 'first exact source contact')
    ck(refused(lambda: s.bind_context(c['active_chord'], 'new', 'new', 'new')), 'context cannot silently replace')
    ck(refused(lambda: s.report_contact('printed_pair', 2, 'synthetic')), 'target cannot skip weak-note contact')
    ck(refused(lambda: s.report_contact('printed_pair', True, 'synthetic')), 'bool order refused')
    ck(refused(lambda: s.report_contact('chosen_upper_octave', 1, 'synthetic')), 'phase bypass refused')
    s.report_contact('printed_pair', 1, 'Synthetic first source contact')
    ck(refused(lambda: s.report_resolution(True, True, 'synthetic')), 'both contacts before resolution report')
    ck(s.current_contact() == original[1], 'exact named target next')
    s.report_contact('printed_pair', 2, 'Synthetic named target')
    ck(s.current_contact() is None, 'pair stops for manual landmark report')
    ck(refused(lambda: s.report_resolution(1, True, 'synthetic')), 'explicit bool resolution reports')
    s.report_resolution(False, True, 'Synthetic stopped form')
    ck(refused(s.select_upper_octave_candidate) and not s.snapshot()['manual_task_reports_complete'], 'failed pulse/form report not completion')
    s.retry_current_pair('Synthetic retry after stopped form')
    ck(s.snapshot()['history'][-1]['prior_outcome']['pulse_and_form_continued_self_report'] is False, 'failed source report retained')
    for i in (1, 2):
        s.report_contact('printed_pair', i, 'Synthetic retry contact')
    s.report_resolution(True, False, 'Synthetic missed landmark')
    ck(refused(s.select_upper_octave_candidate), 'late resolution not complete')
    s.retry_current_pair('Synthetic retry after missed landmark')
    for i in (1, 2):
        s.report_contact('printed_pair', i, 'Synthetic retry contact')
    s.report_resolution(True, True, 'Synthetic manual pulse and landmark reports')
    chosen = s.select_upper_octave_candidate()
    ck(chosen == c['authored_upper_octave_candidate'] and s.current_contact() == chosen[0], 'explicit candidate selection starts alternate')
    chosen[0]['chosen_fret'] = -99
    ck(s.current_contact()['chosen_fret'] >= 12, 'selected route detached')
    for i in (1, 2):
        s.report_contact('chosen_upper_octave', i, 'Synthetic upper-octave contact')
    s.report_resolution(True, True, 'Synthetic repeat resolution and pulse report')
    ck(s.snapshot()['manual_task_reports_complete'] and not s.snapshot()['outcome']['timing_or_sound_verified'], 'completed manual report sequence not observed acoustic pass')
    before = s.snapshot()
    s.cancel()
    ck(refused(s.current_contact) and refused(lambda: s.retry_current_pair('synthetic')), 'cancelled actions guarded')
    s.reopen()
    ck(s.snapshot() == before, 'cancel/reopen preserves reports/history/choice')
    s.retry_current_pair('Synthetic repeat review')
    ck(s.snapshot()['selected_alternate'] and not s.snapshot()['manual_task_reports_complete'] and s.current_contact() == c['authored_upper_octave_candidate'][0], 'repeat retains chosen source but resets only current manual reports')
    ck(not any(s.snapshot()[k] for k in ['sound_or_timing_observed', 'app_audio_supplied', 'Attempt_credit', 'mastery_awarded']), 'no sound/timing/audio/credit claims')
am = next(r for r in rows if r['source_payload']['printed_label'].startswith('Am7:'))
amc = am['implementation']['task']['contract']
ck([e['written_pitch_theory']['midi_at_stated_standard_tuning'] for e in amc['printed_contacts']] == [47, 60] and [e['derived_standard_tuning_midi'] for e in amc['authored_upper_octave_candidate']] == [59, 72], 'Am7 original13-semitone written leap preserved')
dest = ROOT / 'Results/fullscope-private-c-r01/level073-r22/integrity.json'
ck(not dest.exists(), 'immutable result')
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result': 'PASS', 'checks': checks,
          'complete_manual_contracts': 12, 'new_category_promotions': 12,
          'packet_sha256': hashlib.sha256(packet.read_bytes()).hexdigest(),
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'all_performance_reports_synthetic': True, 'native_app_gui': 'NOT_RUN'}
dest.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
