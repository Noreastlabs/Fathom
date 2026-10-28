"""Create one immutable fourteen-key private packet, with one occluded-source limit."""
from copy import deepcopy
import datetime
import hashlib
import json
import time
from pathlib import Path
from pypdf import PdfReader
from chord_tone_contract import RAW, KEYS, HEADING, PRIORITY, contract
from reserve import ROOT, LANE, pin, read, create

def verify_ref(reference):
    actual = pin(reference['path'])
    if actual != {name: reference[name] for name in ('path', 'bytes', 'sha256')}:
        raise ValueError('SOURCE_PIN_REFUSE: ' + reference['path'])
    return actual

def main():
    tick = time.monotonic()
    reservation_path = Path('Results') / LANE / 'reservation.json'
    reservation = read(reservation_path)
    for name in ('original_assignment', 'original_C_prompt', 'r61_handoff', 'r61_index',
                 'category_base', 'official_descriptor', 'frozen_base', 'coverage', 'base_packet'):
        verify_ref(reservation[name])
    for reference in reservation['ordered_authoritative_delta_chain'] + reservation['original_sources']:
        verify_ref(reference)
    assert [row['package_key'] for row in reservation['rows']] == list(KEYS)
    raw = (ROOT / reservation['base_packet']['path']).read_bytes().splitlines(keepends=True)
    old = []
    for row in reservation['rows']:
        line = raw[row['r06_jsonl_line'] - 1]
        assert hashlib.sha256(line).hexdigest() == row['r06_raw_jsonl_line_sha256']
        source_row = json.loads(line)
        assert source_row['package_key'] == row['package_key']
        assert source_row['source_identity'] == row['source_identity']
        assert source_row['contract_category'] == 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
        old.append(source_row)
    pdf, txt = reservation['original_sources']
    page = PdfReader(ROOT / pdf['path']).pages[13].extract_text()
    joined = ' '.join(page.split())
    assert HEADING in joined and PRIORITY in joined
    assert '14 COMMANDS | 56 TONES' in joined and 'Page 14 of 20' in joined
    assert 'Chord Role Pitch Sing String set 1 String set 2' in joined
    paired = (ROOT / txt['path']).read_text()
    assert 'Practice named scale degrees and chord tones in low, middle, and high registers with one silent setup and one attack.' in paired
    assert 'Diagnose a wrong attack; do not slide around until the note is found.' in paired
    joins = []
    for index, row in enumerate(old):
        parts = [*RAW[index], '', '', '']
        assert row['implementation']['task']['printed_components'] == parts
        assert ' '.join(RAW[index]) in joined
        assert row['implementation']['events'] == []
        joins.append({'key': KEYS[index], 'base_jsonl_line': 125 + index,
                      'original_components': parts, 'physical_page': 14,
                      'render_visibility': 'OCCLUDED_BY_PRIORITY_PANEL' if index == 13 else 'VISIBLE'})
    render = pin(Path('Build') / LANE / 'source-page14.png')
    source_path = Path('Build') / LANE / 'source-check.json'
    create(source_path, {
        'original_pdf': pdf, 'original_txt': txt, 'base_packet': reservation['base_packet'],
        'reservation': pin(reservation_path), 'physical_page': 14, 'original_page_text': page,
        'rendered_source_reference': render,
        'render_method': 'Bundled pypdfium2 original page14 at1.5x, inspected by producer C; no new PDF written',
        'exact_selected_joins': joins, 'visible_rows': 13, 'occluded_rows': 1,
        'contradiction': 'PDF text extraction and frozen/r06 source rows retain final G#7alt / 3 / B# / C; the rendered priority panel covers its printed row. Preserve SOURCE_UNRESOLVED pending independent original-source adjudication.',
        'extent': {'literal_header': '14 COMMANDS | 56 TONES', 'actual_commands': 14,
                   'printed_blank_columns': ['Sing', 'String set 1', 'String set 2'],
                   'fixed_note_events_added': 0, 'four_tone_or_attack_schedule_invented': False},
        'locator_note': 'Final official p014-t1-r15/g#7alt remains unchanged despite being fourteen-command final row. No locator correction or invented row.',
        'paired_txt_scope': 'Shared immediate/no-search practice context; page-specific two-string-set table remains distinct from page13 low/mid/high.'})
    output = []
    for index, original in enumerate(old):
        row = deepcopy(original)
        model = contract(index)
        row['schema_version'] = 'fathom-private-source-implementation.62'
        row['implementation']['kind'] = 'private_manual_chord_tone_task'
        row['implementation']['manual_model'] = {
            'path': str(Path('Tools') / LANE / 'chord_tone_contract.py'), 'class': 'ChordToneFlow',
            'pure_python_reference': True,
            'reused_primitives': pin('Tools/fullscope-private-c-r01/level077-r61/degree_contract.py')}
        row['implementation']['task']['contract'] = model
        row['implementation']['task']['response_contract'] = {
            'mode': 'manual_user_response', 'response_fields': model['response_schema'],
            'chosen_plan_fields': model['plan_schema'], 'learner_response': None,
            'completion_claim': None, 'automatic_score': False}
        row['implementation']['task']['source_sequence_recovery'] = {
            'source_check': pin(source_path), 'original_raw_retained': True, 'identity_changed': False}
        if index == 13:
            row['contract_category'] = 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
            row['status'] = 'SOURCE_UNRESOLVED_PRIVATE_PARTIAL_QA_PENDING'
            row['contract_capabilities']['complete_manual_response_contract'] = False
            row['unresolved_reasons'] = [{'disposition': 'SOURCE_UNRESOLVED_ORIGINAL_RENDER_OCCLUSION',
                'reason': 'Complete private task representation retains final PDF-extracted command and B# / C alias, but its rendered row is covered by the priority panel. Model practice start refuses; independent source adjudication is required before implementation-ready classification.'}]
        else:
            row['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
            row['status'] = 'IMPLEMENTED_PRIVATE_QA_PENDING'
            row['contract_capabilities']['complete_manual_response_contract'] = True
            row['unresolved_reasons'] = [{'disposition': 'EXTERNAL_MANUAL_PERFORMANCE_AND_INDEPENDENT_QA_PENDING',
                'reason': 'Usable private chord-tone task/model with chosen external cue and two chosen string-set arrangements. Chord correctness, singing, attack, release, no-search and qualitative speed remain manual. No fixed source voicing/register/timing or performance qualification.'}]
        row['provenance']['manual_r62'] = {
            'base_packet': reservation['base_packet'], 'base_jsonl_line': 125 + index,
            'reservation': pin(reservation_path), 'source_check': pin(source_path),
            'author': '/root/private_c_coherent_batch_resume', 'independent_source_review': 'QA_PENDING',
            'source_note_events_added': False,
            'source_visibility': model['source_visibility']}
        output.append(row)
    packet_path = Path('Build') / LANE / 'chord-tone-overlay.jsonl'
    packet = ROOT / packet_path
    assert not packet.exists()
    packet.write_text(''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n'
                              for row in output))
    seal = {
        'schema_version': 'fathom-private-coherent-batch-seal.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generation_elapsed_seconds': time.monotonic() - tick,
        'reservation': pin(reservation_path), 'base_packet': reservation['base_packet'],
        'packet': pin(packet_path), 'source_check': pin(source_path),
        'model': pin(Path('Tools') / LANE / 'chord_tone_contract.py'),
        'producer': pin(Path('Tools') / LANE / 'produce.py'),
        'exact_attempted_keys': list(KEYS), 'selected_attempted': 14, 'selected_denominator': 14,
        'source_supported_manual_contracts': 13, 'partial_source_unresolved': 1,
        'unattempted_selected_keys': 0, 'deferred_qa_selected_keys': 14,
        'fixed_note_events_added': 0, 'outside_child_keys_created': 0,
        'native_valid': 0, 'integrated': 0, 'independently_reviewed': 0, 'Accepted': 0,
        'construction_status': 'IMPLEMENTED_PRIVATE_QA_PENDING', 'lane_acceptance': 'Pending',
        'deferred_checks': ['independent original-source/interpretation review', 'bulk behavioral/state/permutation QA',
                            'native projection/validation', 'installed app/TAB/audio/fretboard consistency',
                            'physical/listening/response-time observation', 'broad regression/platform/release gates']}
    create(Path('Results') / LANE / 'seal.json', seal)
    print(json.dumps(seal))

if __name__ == '__main__':
    main()
