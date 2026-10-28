from pathlib import Path
from pypdf import PdfReader
import copy, datetime, hashlib, json, time, resource

R = Path(__file__).resolve().parents[3]
L = Path('fullscope-private-c-r01/level073-r27')
tick = time.monotonic()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()

def pin(p):
    p = Path(p); b = (R/p).read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def write(p, value):
    p = R/p
    assert not p.exists()
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

base = Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl')
assert pin(base)['sha256'] == '30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
rows = [json.loads(x) for x in (R/base).read_text().splitlines()][34:38]
refs = rows[0]['source_refs']
for ref in refs:
    assert pin(ref['path']) == {k: ref[k] for k in ('path', 'bytes', 'sha256')}
pdf, txt = Path(refs[0]['path']), Path(refs[1]['path'])
reader = PdfReader(R/pdf)
lines = (R/txt).read_text().splitlines()
header = 'FOUR CHORD TONES PER BAR; THE DESTINATION KEY MUST BE CONFIRMED FOR AT LEAST THREE BARS'
audit = 'Name the exact bar where the destination key becomes more convincing than the source key.'
model = Path('Tools')/L/'study_contract.py'
checks = []
for ordinal, row in enumerate(rows):
    page = 13+ordinal
    text = reader.pages[page-1].extract_text()
    norm = ' '.join(text.split())
    assert header in norm and audit in norm and 'Standard tuning.' in norm
    events = row['implementation']['events']
    assert len(events) == 32
    assert all(e['onset_q'] is None and e['duration_q'] is None and e['finger'] is None for e in events)
    joins = row['provenance']['exact_conversion_joins']
    lo, hi = joins[0]['txt_event_lines'][0]-4, joins[-1]['txt_event_lines'][1]
    title, explanation, progression = lines[lo-1:lo+2]
    assert title.upper() in norm and explanation in norm
    chords = [x.strip() for x in progression.split('|')[1:-1]]
    assert len(chords) == 8
    bars = []
    for n, chord in enumerate(chords, 1):
        es = [e for e in events if e['source_absolute_bar'] == n]
        assert len(es) == 4 and all(e['harmonic_context']['chord_symbol'] == chord for e in es)
        bars.append({'source_bar': n, 'printed_chord': chord, 'source_orders': [e['source_order'] for e in es]})
    c = {
        'schema_version': 'fathom-private-eight-bar-study-manual-contract.1',
        'package_key': row['package_key'], 'complete_manual_contract': True,
        'source_header': header, 'source_audit_prompt': audit,
        'source_script': {'title': title, 'explanation': explanation,
                          'printed_progression': progression, 'bars': bars,
                          'events': copy.deepcopy(events),
                          'txt_context_lines': [lo, hi], 'pdf_physical_page': page},
        'source_obligations': [
            'Perform the complete printed eight-bar study in source order.',
            'Four chord tones per bar.',
            'The destination key must be confirmed for at least three bars.',
            explanation, audit],
        'manual_prerequisite': {'own_instrument': True, 'external_player_required': False,
                                'app_supplies_audio': False,
                                'availability': 'learner supplies an actual instrument; no performed availability inferred'},
        'timing_choice': {'timing_plan': None, 'origin': 'learner choice; no fixed pulse, meter or BPM invented'},
        'response_schema': {
            'printed_order': 'yes/no/uncertain', 'four_tones_each_bar': 'yes/no/uncertain',
            'modulation_route_addressed': 'yes/no/uncertain', 'destination_confirmed': 'yes/no/uncertain',
            'destination_bars': {'type': 'distinct list of original bar numbers1..8',
                                 'complete_self_report_minimum': 3, 'fewer_bars': 'retain report; explicit retry required'},
            'audit_response': 'named/uncertain/not_heard',
            'exact_bar': 'integer1..8 for named, otherwise null; subjective, no fixed correct answer',
            'reflection': 'optional explanation as text; empty string allowed'},
        'authored_interface_policy': 'Setup, response fields, manual release and state/token guards are Fathom-authored interface policy. Bar selection is self-report, not an acoustic/harmonic test or three-tonic-chord requirement. No additional source notes or rests.',
        'state_policy': {'order': ['setup', 'ready', 'perform_eight_bars', 'manual_release', 'report', 'complete_manual_reports_or_retry_required'],
                         'token': 'instance/route/generation/pass/action/stage exact match',
                         'retry': 'explicit reason and manual release; preserve prior reports and timing choice',
                         'cancel_reopen': 'retain original stage, script, choice and responses; invalidate tokens and require release',
                         'manual_completion': 'all obligations yes, at least3 distinct source bars selected and exact audit bar named; no evaluated outcome'},
        'fixed_timing_projection': {'status': 'NOT_FIXED', 'onset_q': None, 'duration_q': None, 'bpm': None,
                                    'reason': 'Printed bars/contact order are retained; quarter mapping/gate/tempo are not specified here.'},
        'state_engine_ref': pin(model), 'performance_observed': False, 'automatic_evaluation': False,
        'app_audio_supplied': False, 'Attempt_credit': False, 'mastery_awarded': False}
    row['implementation']['task']['contract'] = c
    row['schema_version'] = 'fathom-private-source-implementation.27'
    row['provenance']['previous_private_packet'] = pin(base)
    row['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
    row['status'] = 'SOURCE_SUPPORTED_MANUAL_TASK'
    row['contract_capabilities']['complete_manual_response_contract'] = True
    row['unresolved_reasons'] = []
    row['field_limitations'] = [{'field': 'fixed_timed_playback', **c['fixed_timing_projection']},
                               {'field': 'self_report', 'status': 'not automatic correctness or performance evidence'}]
    checks.append({'package_key': row['package_key'], 'previous_packet_line': 35+ordinal,
                   'source_contacts': 32, 'physical_page': page, 'txt_context_lines': [lo, hi],
                   'pdf_text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                   'source_header': header, 'source_audit_prompt': audit, 'bars': bars})
sourcecheck = Path('Build')/L/'source-check.json'
write(sourcecheck, {'original_pdf': pin(pdf), 'original_txt': pin(txt), 'rows': checks,
                    'method': 'original PDF text stream and original TXT; not fresh rendered-layout QA'})
out = Path('Build')/L/'eight-bar-study-overlays.jsonl'
assert not (R/out).exists()
(R/out).write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in rows))
seal = {'start_utc': started, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generation_elapsed_seconds': time.monotonic()-tick,
        'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'overlay': pin(out), 'base_packet': pin(base), 'state_engine': pin(model), 'source_check': pin(sourcecheck),
        'exact_replaced_keys': [r['package_key'] for r in rows], 'attempted': 4,
        'source_supported_manual_contracts': 4, 'new_manual_category_promotions': 4,
        'partial_unresolved': 0, 'unattempted': 0, 'source_contacts_retained_exact': 128,
        'native_valid': 0, 'integrated': 0, 'reviewed': 0, 'Accepted': 0}
write(Path('Results')/L/'seal.json', seal)
print(json.dumps(seal))
