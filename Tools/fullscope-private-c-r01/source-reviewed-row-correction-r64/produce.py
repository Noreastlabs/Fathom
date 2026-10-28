"""Create one immutable private correction overlay after exact source adjudication."""
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import time
from source_reviewed_chord_tone import KEY, contract, source_authority
ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/source-reviewed-row-correction-r64')

def pin(path):
    b = (ROOT / path).read_bytes()
    return {'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}

def create(path, value):
    path = ROOT / path
    assert not path.exists(), 'Immutable output already exists'
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def verify(reference):
    assert pin(reference['path']) == reference, 'SOURCE_PIN_REFUSE'

def main():
    tick = time.monotonic()
    rpath = Path('Results') / LANE / 'reservation.json'
    reservation = json.loads((ROOT / rpath).read_text())
    for name in ('frozen_base', 'base_packet', 'prior_r62_reservation', 'prior_r62_packet', 'prior_r62_model',
                 'r63_final_closeout', 'r63_effective_delta', 'source_decision', 'release', 'local_prompt'):
        verify(reservation[name])
    for reference in reservation['original_sources']:
        verify(reference)
    raw = (ROOT / reservation['base_packet']['path']).read_bytes().splitlines(keepends=True)[137]
    assert hashlib.sha256(raw).hexdigest() == reservation['r06_raw_jsonl_line_sha256']
    prior_lines = (ROOT / reservation['prior_r62_packet']['path']).read_bytes().splitlines(keepends=True)
    assert [hashlib.sha256(line).hexdigest() for line in prior_lines[:13]] == reservation['unchanged_other13_family_line_hashes']
    assert hashlib.sha256(prior_lines[13]).hexdigest() == reservation['prior_r62_raw_line14_sha256']
    row = json.loads(prior_lines[13])
    assert row['package_key'] == KEY and row['status'] == 'SOURCE_UNRESOLVED_PRIVATE_PARTIAL_QA_PENDING'
    row = deepcopy(row)
    c = contract()
    row['schema_version'] = 'fathom-private-source-implementation.64'
    row['implementation']['manual_model'] = {'path': str(Path('Tools') / LANE / 'source_reviewed_chord_tone.py'),
        'class': 'SourceReviewedChordToneFlow', 'pure_python_reference': True,
        'source_decision': source_authority(), 'reused_r62_model': reservation['prior_r62_model']}
    row['implementation']['task']['contract'] = c
    row['implementation']['task']['source_sequence_recovery']['independent_source_accept'] = source_authority()
    row['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
    row['status'] = 'IMPLEMENTED_PRIVATE_QA_PENDING'
    row['contract_capabilities']['complete_manual_response_contract'] = True
    row['unresolved_reasons'] = [{'disposition': 'INDEPENDENT_BEHAVIOR_AND_DOWNSTREAM_QA_PENDING',
        'reason': 'Exact independent source Accept/Correct enables G#7alt/third/B# or C. Original render is still occluded; chosen contacts/string sets/registers and qualitative clocks remain unprinted. Source review alone is no behavioral/native/app/listening/official acceptance.'}]
    row['provenance']['manual_r64'] = {'reservation': pin(rpath), 'prior_r62_packet': reservation['prior_r62_packet'],
        'prior_r62_jsonl_line': 14, 'original_r06_jsonl_line': 138, 'source_decision': source_authority(),
        'author': '/root/private_c_coherent_batch_resume', 'behavioral_review': 'QA_PENDING',
        'original_render_occlusion_preserved': True, 'source_note_events_added': False, 'new_attempted_identity': False}
    packet_path = Path('Build') / LANE / 'source-reviewed-chord-tone-overlay.jsonl'
    assert not (ROOT / packet_path).exists()
    (ROOT / packet_path).write_text(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    seal = {'schema_version': 'fathom-private-exact-row-correction-seal.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'generation_runtime_seconds': time.monotonic() - tick,
        'reservation': pin(rpath), 'prior_r62_packet': reservation['prior_r62_packet'], 'source_decision': source_authority(),
        'packet': pin(packet_path), 'model': pin(Path('Tools') / LANE / 'source_reviewed_chord_tone.py'),
        'producer': pin(Path('Tools') / LANE / 'produce.py'), 'exact_keys': [KEY], 'selected_corrected': 1,
        'selected_denominator': 1, 'new_attempted_identities': 0, 'complete_private_manual_contracts': 1,
        'partial_source_unresolved': 0, 'unattempted_selected_keys': 0, 'unchanged_other13_family_keys': 13,
        'source_reviewed': 1, 'independently_behavior_reviewed': 0, 'native_valid': 0, 'integrated': 0, 'Accepted': 0,
        'source_note_events_added': 0, 'construction_status': 'IMPLEMENTED_PRIVATE_QA_PENDING', 'lane_acceptance': 'Pending',
        'deferred_qa': ['combined independent behavior/bulk state/permutation', 'native', 'installed app', 'physical/listening', 'broad regression/release']}
    create(Path('Results') / LANE / 'seal.json', seal)
    print(json.dumps(seal))

if __name__ == '__main__':
    main()
