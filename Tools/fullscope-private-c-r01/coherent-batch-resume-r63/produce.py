"""Whole one-key private packet, source limits explicit; no readiness promotion."""
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import time
from pypdf import PdfReader
from reconstruction_contract import KEY, RAW, PULSE, REALIZATION, SCORING, contract

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-batch-resume-r63')

def pin(path):
    data = (ROOT / path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def create(path, value):
    path = ROOT / path
    assert not path.exists(), 'Immutable output exists'
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def verify(reference):
    assert pin(reference['path']) == reference, 'SOURCE_PIN_REFUSE'

def main():
    tick = time.monotonic()
    rpath = Path('Results') / LANE / 'reservation.json'
    reservation = json.loads((ROOT / rpath).read_text())
    apath = Path('Results') / LANE / 'reservation-authority-addendum.json'
    addendum = json.loads((ROOT / apath).read_text())
    verify(addendum['governing_release'])
    verify(addendum['reservation'])
    for name in ('base_packet', 'frozen_base', 'official_descriptor', 'release', 'lane_local_prompt',
                 'prior_r62_closeout', 'prior_r62_delta', 'prior_r62_next_family'):
        verify(reservation[name])
    for ref in reservation['original_sources']:
        verify(ref)
    assert reservation['package_key'] == KEY and reservation['r06_jsonl_line'] == 158
    raw = (ROOT / reservation['base_packet']['path']).read_bytes().splitlines(keepends=True)[157]
    assert hashlib.sha256(raw).hexdigest() == reservation['r06_raw_jsonl_line_sha256']
    original = json.loads(raw)
    assert original['package_key'] == KEY and original['contract_category'] == 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    reader = PdfReader(ROOT / reservation['original_sources'][0]['path'])
    pages = {str(n): reader.pages[n - 1].extract_text() for n in (17, 18)}
    p17, p18 = (' '.join(pages[str(n)].split()) for n in (17, 18))
    assert 'SOURCE PLAYER ONLY | 64 TONES' in p17
    assert 'RECORD ONCE; TRANSCRIBER SHOULD NOT STUDY THIS PAGE BEFORE THE TEST' in p17
    assert PULSE in p17 and '5 PASSES | 64 ANSWERS' in p18
    assert REALIZATION in p18 and SCORING in p18
    assert 'Bars Contour Degrees Exact notes Chord / function Play' in p18
    joins = []
    for i, (chord, pitches, target) in enumerate(RAW, 1):
        assert f'{i} {chord} {pitches} {target}' in p17
        joins.append({'bar': i, 'chord': chord, 'four_note_source': pitches.split('-'),
                      'structural_target': target, 'original_render_visibility': 'VISIBLE' if i < 16 else 'OCCLUDED'})
    assert sum(len(row['four_note_source']) for row in joins) == 64
    source_path = Path('Build') / LANE / 'source-check.json'
    create(source_path, {'original_sources': reservation['original_sources'], 'base_packet': reservation['base_packet'],
        'reservation': pin(rpath), 'governing_authority_addendum': pin(apath), 'original_page_text': pages,
        'renders': [pin(Path('Build') / LANE / f'source-page{n}.png') for n in (17, 18)],
        'render_method': 'Bundled pypdfium2 original PDF pages17–18 at1.5x, producer inspected, no new PDF authored',
        'exact_sixteen_bar_joins': joins, 'actual_extracted_tones': 64, 'visible_supported_tones': 60,
        'source_discrepancies': ['Final bar16 is retained in PDF extraction/frozen/r06 source but covered in original page17 render.',
                                'Final13–16 worksheet block/label is retained in extraction/frozen/r06 but covered in original page18 render.',
                                'Raw r06 table-field extraction contains footer fragments inside final rows; raw content is preserved, coherent extracted reference is separately bound.'],
        'worksheet': {'printed_passes': 5, 'written_columns': ['Contour', 'Degrees', 'Exact notes', 'Chord / function'],
                      'fifth_column': 'Play', 'extracted_blocks': ['1-4', '5-8', '9-12', '13-16'],
                      'final_block_visible': False, 'literal_answers_header': '64 ANSWERS',
                      'printed_score_dimensions': ['hearing accuracy', 'first-attack fretboard accuracy'],
                      'per_block_score_range': [0, 2], 'printed_maximum': 16},
        'clock_limits': 'No fixed BPM/meter/onset/duration/register/contact; qualitative comfortable pulse/even lengths/immediate playing remain manual.',
        'decision': 'No independent source adjudication. Whole one-key readiness remains Pending; supported partial rehearsal only.'})
    row = deepcopy(original)
    c = contract()
    row['schema_version'] = 'fathom-private-source-implementation.63'
    row['implementation']['kind'] = 'private_partial_model_reconstruction_task'
    row['implementation']['manual_model'] = {'path': str(Path('Tools') / LANE / 'reconstruction_contract.py'),
                                             'class': 'ModelReconstructionFlow', 'pure_python_reference': True,
                                             'reused_primitives': pin('Tools/fullscope-private-c-r01/level077-r61/degree_contract.py')}
    row['implementation']['task']['contract'] = c
    row['implementation']['task']['response_contract'] = {'mode': 'manual_user_response',
        'written_passes': c['written_passes'], 'bars_per_pass': 16, 'exact_notes_per_bar': 4,
        'explicit_unknowns': True, 'learned_or_observed_response': None, 'automatic_score': False,
        'score_declarations': {'blocks': c['worksheet_blocks'], 'range': [0, 2], 'full_score': None,
                               'incomplete_final_block': 'unknown', 'mastery_awarded': False}}
    row['implementation']['task']['source_sequence_recovery'] = {'source_check': pin(source_path),
        'raw_task_and_source_fields_retained': True, 'identity_changed': False, 'independent_source_review': 'QA_PENDING'}
    row['contract_category'] = 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    row['status'] = 'SOURCE_UNRESOLVED_PRIVATE_PARTIAL_QA_PENDING'
    row['contract_capabilities']['complete_manual_response_contract'] = False
    row['unresolved_reasons'] = [{'disposition': 'SOURCE_UNRESOLVED_ORIGINAL_RENDER_OCCLUSION',
        'reason': 'All16/64 original text-stream fields retained;15/60 visible-supported partial playing model implemented. Original final source bar16 and worksheet13–16 row are hidden by original panels. Final bar/full second-register/whole finish refuse pending independent source adjudication.'},
        {'disposition': 'INDEPENDENT_INTERPRETATION_AND_BULK_QA_PENDING',
         'reason': 'Four written passes retain unknown/wrong responses; chosen first-position60-contact rehearsal with manual singing/playing/release/report. No app recording/audio, recognized performance, timing or complete exercise score.'}]
    row['provenance']['manual_r63'] = {'base_packet': reservation['base_packet'], 'base_jsonl_line': 158,
        'reservation': pin(rpath), 'authority_addendum': pin(apath), 'source_check': pin(source_path),
        'author': '/root/private_c_coherent_batch_resume', 'independent_source_review': 'QA_PENDING',
        'source_note_events_added': False, 'source_unresolved': True}
    packet_path = Path('Build') / LANE / 'model-reconstruction-overlay.jsonl'
    assert not (ROOT / packet_path).exists()
    (ROOT / packet_path).write_text(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    seal = {'schema_version': 'fathom-private-coherent-batch-seal.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'generation_runtime_seconds': time.monotonic() - tick,
        'reservation': pin(rpath), 'authority_addendum': pin(apath), 'packet': pin(packet_path),
        'source_check': pin(source_path), 'model': pin(Path('Tools') / LANE / 'reconstruction_contract.py'),
        'producer': pin(Path('Tools') / LANE / 'produce.py'), 'exact_keys': [KEY], 'selected_attempted': 1,
        'selected_denominator': 1, 'source_supported_complete_manual_contracts': 0, 'partial_source_unresolved': 1,
        'unattempted_selected_keys': 0, 'extracted_bars': 16, 'extracted_tones': 64,
        'visible_supported_bars': 15, 'visible_supported_tones': 60, 'written_passes_implemented': 4,
        'full_model_second_register_and_completion': 'SOURCE_UNRESOLVED_REFUSE', 'source_note_events_added': 0,
        'construction_status': 'IMPLEMENTED_PRIVATE_PARTIAL_QA_PENDING', 'lane_acceptance': 'Pending',
        'native_valid': 0, 'integrated': 0, 'independently_reviewed': 0, 'Accepted': 0,
        'historical_C_private_category_counts_unchanged_from_r62': True,
        'deferred_qa': ['independent source occlusion/interpretation adjudication', 'bulk behavior/state/permutation',
                        'native projection', 'installed app/TAB/audio/fretboard', 'physical/listening', 'broad regression/release']}
    create(Path('Results') / LANE / 'seal.json', seal)
    print(json.dumps(seal))

if __name__ == '__main__':
    main()
