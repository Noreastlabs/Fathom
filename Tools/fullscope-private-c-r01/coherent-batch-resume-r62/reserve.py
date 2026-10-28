"""Reserve only exact existing Level77 page14 children before construction."""
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LANE = Path('fullscope-private-c-r01/coherent-batch-resume-r62')

def pin(path):
    path = Path(path)
    data = (ROOT / path).read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def read(path):
    return json.loads((ROOT / path).read_text())

def create(path, value):
    path = ROOT / path
    if path.exists():
        raise ValueError('Immutable output already exists: ' + str(path))
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def effective_rows():
    index = read('Results/fullscope-private-c-r01/range-category-index-r10.json')
    effective = {row['package_key']: dict(row) for row in index['rows']}
    chain = []
    path = Path('Results/fullscope-private-c-r01/range-effective-delta-r61.json')
    while True:
        delta = read(path)
        assert pin(delta['base_effective_index']['path']) == delta['base_effective_index']
        chain.append((pin(path), delta))
        prior = delta.get('prior_ordered_delta')
        if not prior:
            break
        assert pin(prior['path']) == prior
        path = Path(prior['path'])
    for _, delta in reversed(chain):
        for row in delta['rows']:
            effective[row['package_key']].update(row)
    return effective, [identity for identity, _ in reversed(chain)]

def main():
    packet = Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl')
    raw = (ROOT / packet).read_bytes().splitlines(keepends=True)
    selected = [(i + 1, json.loads(line)) for i, line in enumerate(raw)
                if 'level077/modulef/p014-' in json.loads(line)['package_key']]
    assert len(selected) == 14
    keys = [row['package_key'] for _, row in selected]
    assert len(set(keys)) == 14
    effective, chain = effective_rows()
    descriptor = Path('Planning/Fathom-Exercise-WBS-Annex-v1.json')
    annex = read(descriptor)
    base = Path(annex['base']['path'])
    assert pin(base)['sha256'] == annex['base']['sha256']
    official = {}
    with (ROOT / base).open('rb') as stream:
        for i, line in enumerate(stream, 1):
            row = json.loads(line)
            if row.get('package_key') in keys:
                assert row['exercise']['source_identity'] == row['proposal']['source_identity']
                assert row['status'] == row['proposal']['status'] == 'Pending'
                official[row['package_key']] = {
                    'jsonl_line': i, 'raw_jsonl_line_sha256': hashlib.sha256(line).hexdigest(),
                    'source_identity': row['exercise']['source_identity'],
                    'existing_parent_id': row['existing_parent_id'], 'status': row['status']}
    assert len(official) == 14
    # Current descriptor says all 2,411 C children remain official Pending.
    assert annex['current_view']['children']['parent_child_counts']['2.3.1.3.1'] == {
        'total': 2411, 'Pending': 2411, 'Accepted': 0}
    output_rows = []
    for line_number, row in selected:
        current = effective[row['package_key']]
        category = current.get('effective_category', current['category'])
        assert category == 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
        assert current['effective_payload']['path'] == str(packet)
        assert row['existing_parent_id'] == '2.3.1.3.1' and row['level'] == 77
        assert official[row['package_key']]['source_identity'] == row['source_identity']
        assert official[row['package_key']]['existing_parent_id'] == '2.3.1.3.1'
        output_rows.append({
            'package_key': row['package_key'], 'source_identity': row['source_identity'],
            'level': 77, 'existing_parent_id': '2.3.1.3.1', 'r06_jsonl_line': line_number,
            'r06_raw_jsonl_line_sha256': hashlib.sha256(raw[line_number - 1]).hexdigest(),
            'official_frozen_base_row': official[row['package_key']],
            'current_private_category': category,
            'printed_components': row['implementation']['task']['printed_components'],
            'source_locator': row['source_refs'][0]['locator']})
    sources = [pin(selected[0][1]['source_refs'][i]['path']) for i in (0, 1)]
    assert sources[0]['sha256'] == 'bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
    assert sources[1]['sha256'] == '54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
    result = {
        'schema_version': 'fathom-private-coherent-family-reservation.1',
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'owner': '/root/private_c_coherent_batch_resume',
        'family': 'Level077 ModuleF physical page14 immediate chord-tone realization, complete fourteen-row table',
        'selected_keys': 14, 'selected_denominator': 14, 'range_denominator': 2411,
        'reserve_status': 'EXACT_EXISTING_KEYS_PRIVATE_CONSTRUCTION_ONLY',
        'original_assignment': pin('Prompts/manager-resume-r02/20260930T2241Z-c-coherent-manual-batch-resume-r62-full-template-prompt.md'),
        'original_C_prompt': pin('Prompts/fullscope-private-c-r01/full-template-prompt.md'),
        'r61_handoff': pin('Results/fullscope-private-c-r01/level077-r61/handoff.md'),
        'r61_index': pin('Results/fullscope-private-c-r01/range-effective-delta-r61.json'),
        'category_base': pin('Results/fullscope-private-c-r01/range-category-index-r10.json'),
        'ordered_authoritative_delta_chain': chain, 'official_descriptor': pin(descriptor),
        'frozen_base': pin(base), 'coverage': pin(annex['coverage']['path']),
        'base_packet': pin(packet), 'original_sources': sources, 'rows': output_rows,
        'guards': {'all_fourteen_existing_official_keys': True,
                   'all_current_private_categories_pending': True,
                   'official_C_children_pending': 2411, 'transferred_levels_excluded': [78, 79, 81, 89],
                   'accepted_or_frozen_packet_keys_selected': 0, 'global_identity_REFUSE_unchanged': True,
                   'queue_places_used': 0, 'shared_writer_claimed': False, 'native_heavy_slot_claimed': False},
        'source_policy': 'Preserve raw source fields. Two printed string-set columns require explicit chosen arrangements. No assumed fixed voicing, octave, tempo, fourth tone, or numeric assessment. Interpretation and behavioral qualification await independent QA.'}
    create(Path('Results') / LANE / 'reservation.json', result)
    create(Path('Results') / LANE / 'reservation-attempts.json', {'attempts': [
        {'attempt': 1, 'exit_code': 1, 'finding': 'Ordinal sweep refused absent r18 delta before reservation or construction; empty roots only.',
         'correction': 'Follow hash-validated prior_ordered_delta links: r19 references r17; r18 is a separate child-release receipt.'},
        {'attempt': 2, 'exit_code': 1, 'finding': 'Frozen base schema uses exercise.source_identity and proposal.source_identity; no reservation or construction written.',
         'correction': 'Inspect exact row schema and verify both nested source identities and Pending statuses.'},
        {'attempt': 3, 'exit_code': 0, 'finding': 'Exact hash-bound fourteen-key reservation created.'}]})
    print(json.dumps({'reservation': pin(Path('Results') / LANE / 'reservation.json'),
                      'family': result['family'], 'keys': keys,
                      'official_row_lines': [official[key]['jsonl_line'] for key in keys],
                      'ordered_deltas': len(chain)}))

if __name__ == '__main__':
    main()
