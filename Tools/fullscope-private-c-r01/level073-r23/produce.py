from pathlib import Path
from pypdf import PdfReader
import copy, datetime, hashlib, json, resource, time
ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/level073-r23')
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()

def pin(path):
    p = ROOT / path
    return {'path': str(path), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}

def write(path, value):
    p = ROOT/path
    assert not p.exists(), str(path)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

base = Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl')
assert pin(base)['sha256'] == '30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
pdf = next((ROOT/'Notes/music/guitar project/PDF version').glob('*Level_73_*')).relative_to(ROOT)
txt = next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*')).relative_to(ROOT)
assert pin(pdf)['sha256'] == '7cc4c0098855c8e6d4b90063fb947b763e32a4225d66b77821f9e23f763779f9'
assert pin(txt)['sha256'] == '63fed22776f4fcfd61ac9b7783b456c8996f2b438c06886d585bff2ee01afd15'
reader = PdfReader(ROOT/pdf)
lines = (ROOT/txt).read_text().splitlines()
header = 'ESTABLISH SOURCE -> REINTERPRET PIVOT -> PLAY NEW DOMINANT -> CONFIRM TONIC'
instruction = ('Each chord receives a four-tone arpeggio. Hold the pivot chord for one extra beat during the first pass, '
               'but keep the bar count unchanged. A second pass removes the extra emphasis and relies on harmony alone.')
page_checks = []
for page in (5, 6):
    extracted = reader.pages[page-1].extract_text()
    assert header in extracted and instruction in ' '.join(extracted.split())
    page_checks.append({'physical_page': page, 'full_joined_instruction_exact': True,
                        'header_exact': True, 'extracted_text_sha256': hashlib.sha256(extracted.encode()).hexdigest()})
engine = Path('Tools')/LANE/'pivot_route_contract.py'
source_check = Path('Build')/LANE/'source-check.json'
write(source_check, {'original_pdf': pin(pdf), 'original_txt': pin(txt), 'physical_pages': page_checks,
                     'method': 'pypdf original PDF text stream; layout not visually requalified',
                     'joined_instruction': instruction, 'header': header})
rows = [json.loads(s) for s in (ROOT/base).read_text().splitlines()][5:11]
assert len(rows) == 6 and all('/moduleb/' in r['package_key'] for r in rows)
for r in rows:
    events = r['implementation']['events']
    join = r['provenance']['exact_conversion_joins'][0]
    start_line, end_line = join['txt_event_lines']
    label, pivot_function, progression = lines[start_line-4:start_line-1]
    assert label == r['source_payload']['printed_label'] and progression.startswith('Progression: | ')
    chords = join['facts']['chords']
    assert progression == 'Progression: | '+' | '.join(chords)+' |'
    assert len(events) == 16 and [e['source_order'] for e in events] == list(range(1,17))
    bars = [{'bar_number': n, 'chord_symbol': chords[n-1],
             'role': ['establish_source', 'reinterpret_pivot', 'new_dominant', 'confirm_tonic'][n-1],
             'source_orders': list(range((n-1)*4+1, n*4+1)),
             'printed_contacts': copy.deepcopy(events[(n-1)*4:n*4])} for n in range(1,5)]
    c = {'schema_version': 'fathom-private-pivot-route-contract.1', 'package_key': r['package_key'],
         'source_header': header, 'source_instruction': instruction,
         'source_instruction_ref': {'pdf': pin(pdf), 'physical_page': join['pdf_physical_page'], 'verification': pin(source_check)},
         'route_label': label, 'pivot_dual_function': pivot_function, 'progression': progression,
         'source_route_txt_lines': [start_line-3, end_line], 'bars': bars,
         'source_obligations': {'four_tones_per_chord': 4, 'route_bar_count': 4, 'pivot_bar': 2,
                                'first_pass': 'Hold pivot chord for one extra beat without changing bar count.',
                                'second_pass': 'Remove extra emphasis and rely on harmony alone.'},
         'prerequisites': ['Own guitar/instrument and ability to perform the printed route manually; no app-generated sound.',
                           'Performer supplies pulse/hold placement; this schema does not choose a fixed metric realization.'],
         'response_fields': [
             {'id': 'setup', 'fields': ['own_instrument_available:true', 'pulse_description:text', 'hold_placement_plan:text', 'pivot_restatement:text']},
             {'id': 'each_bar', 'fields': ['current_action_token', 'bar_number:source_order', 'played_as_shown:yes/no/uncertain', 'explanation:text']},
             {'id': 'first_pass_pivot_bar', 'fields': ['pivot_extra_beat:yes/no/uncertain', 'hold_placement:text']},
             {'id': 'each_pass_summary', 'fields': ['four_bar_count_preserved:yes/no/uncertain', 'tonic_confirmation:yes/no/uncertain', 'explanation:text']},
             {'id': 'second_pass_summary', 'fields': ['extra_emphasis_removed:yes/no/uncertain', 'harmony_only_comparison:text']},
             {'id': 'manual_release', 'fields': ['current_action_token', 'instrument_released:true']},
             {'id': 'retry', 'fields': ['reason:text', 'explicit_manual_release_before_retry']}
         ],
         'authored_interface_policy': 'Fathom-authored fields and sequencing expose all printed obligations. Free-text placement is learner choice, not a printed file-format, timing or voicing requirement. All reports are self-reports, not inspected audio.',
         'state_policy': {'order': ['setup', 'ready', 'bar1', 'bar2', 'bar3', 'bar4', 'summary', 'manual_release', 'second_pass_same_bars', 'manual_release'],
                          'negative_or_uncertain': 'Retain reports, require explicit retry and manual release; never credit success.',
                          'cancel_reopen': 'Retain context/reports/history; invalidate old instance/pass/action callbacks and confirm manual release on reopen.',
                          'repeat': 'Explicit retry only; retain history and invalidate old callbacks.',
                          'token_scope': 'In-memory instance, exact route, generation, pass and action revision; no canonical identity allocation or persistence.'},
         'fixed_timing_projection': {'status': 'UNRESOLVED', 'reason': 'Exact pulse placement, held arpeggio tone or voicing, and metric distribution of the extra beat are unprinted. Manual contract retains the obligation without synthesizing a numeric grid.',
                                     'onset_q': None, 'duration_q': None, 'bpm': None},
         'state_engine_ref': pin(engine), 'automatic_evaluation': False, 'performance_observed': False,
         'app_audio_supplied': False, 'Attempt_credit': False, 'mastery_awarded': False}
    r['implementation']['task']['contract'] = c
    r['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
    r['status'] = 'SOURCE_SUPPORTED_MANUAL_TASK'
    r['schema_version'] = 'fathom-private-source-implementation.23'
    r['contract_capabilities']['complete_manual_response_contract'] = True
    r['unresolved_reasons'] = []
    r['provenance']['previous_private_packet'] = pin(base)
    r['field_limitations'] = [{'field': 'fixed_timed_playback', **c['fixed_timing_projection']}]
out = Path('Build')/LANE/'pivot-route-overlays.jsonl'
assert not (ROOT/out).exists()
(ROOT/out).write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in rows))
seal = {'start_utc': start, 'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generation_elapsed_seconds': time.monotonic()-tick, 'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'overlay': pin(out), 'base_packet': pin(base), 'state_engine': pin(engine), 'source_check': pin(source_check),
        'exact_replaced_keys': [r['package_key'] for r in rows], 'attempted': 6, 'source_supported_manual_contracts': 6,
        'new_manual_category_promotions': 6, 'partial_unresolved_manual_contracts': 0, 'fixed_timed_projection_unresolved': 6,
        'unattempted': 0, 'source_contacts_retained_exact': 96, 'native_valid': 0, 'integrated': 0, 'reviewed': 0, 'Accepted': 0}
write(Path('Results')/LANE/'seal.json', seal)
print(json.dumps(seal))
