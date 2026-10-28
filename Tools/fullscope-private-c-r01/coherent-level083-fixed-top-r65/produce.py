"""One coherent41-key overlay with shared source/model; cheap pin/schema checks only."""
from copy import deepcopy
import datetime
import hashlib
import json
from pathlib import Path
import time
from fixed_top_model import ROOT, LANE, DATA, cards, contract


def pin(path):
    data = (ROOT / path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def verify(ref):
    identity = pin(ref['path'])
    assert identity['sha256'] == ref['sha256']
    if 'bytes' in ref:
        assert identity['bytes'] == ref['bytes']


def create(path, value):
    with (ROOT / path).open('x') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def main():
    tick = time.monotonic()
    rpath = Path('Results') / LANE / 'reservation.json'
    reservation = json.loads((ROOT / rpath).read_text())
    for name in ('exact_key_source_row_scope', 'original_packet', 'current_census',
                 'current_census_clarification', 'prior_ordered_delta', 'current_registry',
                 'prior_reviewed32', 'release', 'local_prompt'):
        verify(reservation[name])
    for source in reservation['original_sources']:
        verify(source)
    scope = json.loads((ROOT / reservation['exact_key_source_row_scope']['path']).read_text())
    original = (ROOT / reservation['original_packet']['path']).read_bytes().splitlines(keepends=True)
    data = cards()
    assert [row['package_key'] for row in data] == reservation['exact_keys']
    model_path = Path('Tools') / LANE / 'fixed_top_model.py'
    shared_path = Path('Build') / LANE / 'shared-task-contract.json'
    shared = contract(data[0]['package_key'])
    for key in ('source_card', 'source_sibling_candidates', 'module_C', 'audit_questions'):
        shared.pop(key)
    shared.update({'per_key_resolution': 'Pinned source-cards.json by exact key; FixedTopFlow/contract(key) resolves complete source-specific behavior.',
                   'source_cards': pin(DATA), 'model': pin(model_path),
                   'moduleAB': 'One original chord; four textures and the four source choice-audit questions.',
                   'moduleC': 'Three original chords/roles in order; an explicit fourth chosen substitute; four textures per harmony and source motion/substitute audit.',
                   'manual_recovery': 'Failed singing/unknown role/attack/duty/audit needs diagnosis and accessible same-step retry; lost melody reduces to bass+melody before repeating the interrupted texture; a diagnosed full chosen-register restart preserves prior history.'})
    create(shared_path, shared)
    output = []
    for i, (selected, card) in enumerate(zip(scope['rows'], data), 1):
        raw = original[selected['current_payload']['jsonl_line'] - 1]
        assert hashlib.sha256(raw).hexdigest() == selected['current_raw_jsonl_line_sha256']
        row = json.loads(raw)
        assert row['package_key'] == card['package_key'] and row['source_identity'] == card['source_identity']
        assert row['existing_parent_id'] == '2.3.1.3.1'
        # Original source payload/events/clocks/printed table/context remain byte-value exact.
        row['schema_version'] = 'fathom-private-source-implementation.65.1'
        row['status'] = 'IMPLEMENTED_PRIVATE_QA_PENDING'
        row['contract_category'] = 'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
        row['contract_capabilities'].update({'complete_manual_contract': True, 'native_valid': False,
            'installed': False, 'Accepted': False, 'playback_admitted': False})
        row['implementation']['manual_model'] = {'path': str(model_path), 'class': 'FixedTopFlow',
            'model_sha256': pin(model_path)['sha256'], 'shared_contract': pin(shared_path),
            'source_cards': dict(pin(DATA), json_array_item=i)}
        row['implementation']['task']['fixed_top_behavior'] = {'literal_top': card['literal_top'],
            'source_harmonies': card['source_harmonies'], 'source_changing_roles': card['literal_roles'],
            'four_stage_order': ['melody', 'root_melody', 'shell_melody', 'full_voicing'],
            'source_specific_audit': 'AB choice audit' if card['module'] == 'AB' else 'C fixed-top/motion/additional substitute audit',
            'contracts_resolved_from_exact_model_key': card['package_key']}
        row['unresolved_reasons'] = ['Independent broad private behavioral/source review pending.',
            'Native/app/listening/physical/release gates not run; no actual performance or source-clock measurement.']
        row['provenance']['manual_r65'] = {'reservation': pin(rpath),
            'source_check': pin(Path('Build') / LANE / 'source-check.json'),
            'producer_render_inspection': pin(Path('Results') / LANE / 'source-render-inspection.json'),
            'previous_payload': dict(reservation['original_packet'], jsonl_line=selected['current_payload']['jsonl_line']),
            'source_contract_data': dict(pin(DATA), json_array_item=i), 'behavioral_review': 'QA_PENDING'}
        output.append(row)
    packet_path = Path('Build') / LANE / 'fixed-top-overlay.jsonl'
    with (ROOT / packet_path).open('x') as stream:
        for row in output:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    seal = {'schema_version': 'fathom-private-coherent-batch-seal.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generation_runtime_seconds': time.monotonic() - tick, 'reservation': pin(rpath),
        'packet': pin(packet_path), 'model': pin(model_path), 'producer': pin(Path('Tools') / LANE / 'produce.py'),
        'source_cards': pin(DATA), 'shared_contract': pin(shared_path),
        'source_check': pin(Path('Build') / LANE / 'source-check.json'),
        'source_render_inspection': pin(Path('Results') / LANE / 'source-render-inspection.json'),
        'exact_keys': reservation['exact_keys'], 'selected_denominator': 41,
        'private_constructed_QA_PENDING': 41, 'partial_source_unresolved': 0,
        'unattempted_selected_keys': 0, 'new_attempted_identities': 0,
        'source_harmonies': 53, 'AB_keys': 35, 'C_keys': 6,
        'independently_source_reviewed': 0, 'independently_behavior_reviewed': 0,
        'native_valid': 0, 'integrated': 0, 'Accepted': 0,
        'construction_status': 'IMPLEMENTED_PRIVATE_QA_PENDING', 'lane_acceptance': 'Pending',
        'deferred_qa': ['independent source/behavior bulk matrix', 'native projection', 'installed app/TAB/audio/fretboard',
                        'actual physical/listening', 'platform/regression/whole-curriculum/release']}
    create(Path('Results') / LANE / 'seal.json', seal)
    print(json.dumps(seal))


if __name__ == '__main__':
    main()
