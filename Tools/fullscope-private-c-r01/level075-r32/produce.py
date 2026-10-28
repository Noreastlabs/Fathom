from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime, hashlib, json, time, resource
from reduction_contract import CARDS, KEYS, ROLES, INSTRUCTION, FOOTER, ANALYSIS, contract

R = Path(__file__).resolve().parents[3]
L = Path('fullscope-private-c-r01/level075-r32')
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
tick = time.monotonic()
def pin(p):
    p = Path(p); b = (R/p).read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def write(p, x):
    p = R/p; assert not p.exists(); p.write_text(json.dumps(x, indent=2, ensure_ascii=False)+'\n')

base = Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256'] == '0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
allrows = [json.loads(x) for x in (R/base).read_text().splitlines()]
rows = allrows[1:9]
assert tuple(r['package_key'] for r in rows) == KEYS
pdf = Path(rows[0]['source_refs'][0]['path']); txt = Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256'] == '2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256'] == '563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page = PdfReader(R/pdf).pages[2].extract_text()
lines = (R/txt).read_text().splitlines()
text = '\n'.join(lines)
norm = lambda x: ' '.join(x.split())
assert '12 CELLS | 96 CONTACTS' in page
assert page.count(INSTRUCTION) == 8 and norm(FOOTER) in norm(page)
assert ANALYSIS in text
analysis_line = lines.index(ANALYSIS) + 1
master_begin = lines.index('MASTER 60-BAR FICTIONAL REPERTOIRE STUDY') + 1
master_end = lines.index('MODULE A - FORM AND HARMONIC ANALYSIS') - 1
master = '\n'.join(lines[master_begin - 1:master_end])
source_checks = []
for i, r in enumerate(rows):
    _, label, chords = CARDS[i]
    block = '\n'.join((label, ' | '.join(chords), 'R  3  7  5 | R  3  7  5', INSTRUCTION))
    assert norm(block) in norm(page)
    assert r['implementation']['events'] == []
    assert r['source_payload']['printed_label'] == label
    assert norm(' | '.join(chords)) in norm(r['source_payload']['pdf_region_text'])
    source_checks.append({'key': r['package_key'], 'base_jsonl_line': i+2,
                          'pdf_page': 3, 'pdf_card': i+1, 'label': label,
                          'chords': list(chords), 'abstract_role_occurrences': list(ROLES),
                          'actual_source_contacts': 0, 'fixed_source_attack_count': None,
                          'exact_pdf_block_match': True})

source_path = Path('Build')/L/'source-check.json'
write(source_path, {'original_pdf': pin(pdf), 'original_txt': pin(txt), 'base_packet': pin(base),
                   'method': 'pypdf text stream; no fresh rendered visual QA',
                   'physical_page': 3, 'literal_header': '12 CELLS | 96 CONTACTS',
                   'actual_enumerated_cards': 8, 'matched_card_blocks': source_checks,
                   'full_page_footer': FOOTER, 'module_a_txt_line': analysis_line,
                   'module_a_txt_instruction': ANALYSIS,
                   'master_chart_context_locator': {'txt_line_start': master_begin, 'txt_line_end': master_end},
                   'master_chart_context': master,
                   'cross_format_scope': 'TXT supplies module-wide analysis and master chart context; card-specific timing is not inferred from it.'})

overlay = []
for i, original in enumerate(rows):
    r = deepcopy(original)
    r['schema_version'] = 'fathom-private-source-implementation.32'
    c = contract(i)
    c['master_chart_context'] = {'source_ref': pin(txt), 'line_start': master_begin, 'line_end': master_end,
                               'text': master, 'scope': 'analysis context only; no card timing/texture import'}
    r['implementation']['task']['contract'] = c
    r['implementation']['task']['response_contract'] = {
        'mode': 'manual_user_response', 'response_fields': c['response_schema'],
        'learner_choice_fields': c['learner_choice_schema'], 'learner_response': None,
        'completion_claim': None, 'automatic_score': False,
        'source_answer_policy': 'Original chart/pattern are reference, not a filled learner answer.'}
    r['implementation']['manual_model'] = {'path': str(Path('Tools')/L/'reduction_contract.py'),
                                          'class': 'ReductionFlow', 'pure_python_reference': True}
    r['unresolved_reasons'] = [
        {'disposition': 'PAGE_EXTENT_RECONCILIATION_REQUIRED',
         'reason': 'Printed12cells/96contacts versus8enumeratedcards. Eightcard manual scope is implemented; largerpageextent not resolved.',
         'source_location': 'original PDFp3 and TXT ModuleA96contacts'},
        {'disposition': 'LEARNER_REALIZATION_REQUIRED_FOR_FIXED_PLAYBACK',
         'reason': 'Source gives chord symbols/abstractroles; no fixed role-to-chord timing, fret, register or exact contacts. Manual choice contract is implemented.'}]
    r['status'] = 'PRIVATE_MANUAL_CONTRACT_IMPLEMENTED_PENDING_REVIEW'
    r['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
    r['contract_capabilities']['complete_manual_response_contract'] = True
    r['contract_capabilities']['page_extent_resolved'] = False
    r['contract_capabilities']['fixed_playback_realization_complete'] = False
    r['provenance']['manual_r32'] = {'base_packet': pin(base), 'base_jsonl_line': i+2,
                                  'source_check': pin(source_path), 'author': 'private producer C',
                                  'independent_source_review': 'Pending', 'no_contact_or_key_invention': True}
    overlay.append(r)

packet = Path('Build')/L/'harmonic-reduction-overlay.jsonl'
p = R/packet; assert not p.exists()
p.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in overlay))
referral = Path('Results')/L/'page-extent-referral.json'
write(referral, {'schema_version': 'fathom-private-source-extent-referral.1', 'status': 'PENDING_DISTINCT_SOURCE_DISPOSITION',
                'original_pdf': pin(pdf), 'original_txt': pin(txt), 'base_packet': pin(base),
                'source_check': pin(source_path), 'exact_keys': list(KEYS),
                'literal_pdf_header': '12 CELLS | 96 CONTACTS', 'txt_module_a': ANALYSIS,
                'observed_extent': 'Eight printed card blocks on PDFp3 match eight official keys; each has four chord symbols and eight abstract harmonic role labels.',
                'question': 'Does the12cell/96contact heading describe missing source material, a carried-over total, or another extent? No disposition is inferred.',
                'preserved_facts': {'new_keys': 0, 'original_event_arrays': 'eight empty arrays unchanged',
                                     'source_role_occurrences': 64, 'roles_are_contacts': False,
                                     'fixed_attack_count': None, 'page_extent_complete': False},
                'manual_contract_scope': 'Eight exact cards only; structured choices and source obligations; larger extent unresolved.',
                'source_conflict_count_increment': 0, 'canonical_allocation': False,
                'reviewer': None, 'source_acceptance': False})
seal = {'utc': started, 'generation_elapsed_seconds': time.monotonic()-tick,
        'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'base_packet': pin(base), 'overlay': pin(packet), 'model': pin(Path('Tools')/L/'reduction_contract.py'),
        'source_check': pin(source_path), 'extent_referral': pin(referral),
        'exact_replaced_keys': list(KEYS), 'attempted': 8,
        'source_supported_manual_contracts': 8, 'partial_unresolved_exact_card_contracts': 0,
        'unattempted': 0, 'unresolved_larger_page_extent_questions': 1,
        'source_contacts_retained_exact': 0, 'abstract_source_role_occurrences': 64,
        'native_valid': 0, 'integrated': 0, 'reviewed': 0, 'Accepted': 0}
write(Path('Results')/L/'seal.json', seal)
print(json.dumps(seal))
