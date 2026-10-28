#!/usr/bin/env python3
"""Focused identity, source, order and no-credit checks for the B59 packet."""
import copy
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'Results/exercise-impl-shard-b59-r01'
RES = ROOT / 'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-b59-reservation.json'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def valid(row, key):
    if row['package_key'] != key or row['source_identity'] != key.split('/', 1)[1]:
        return False
    if row['delivery_type'] != 'source_grounded_manual_parameterized_nonplayback':
        return False
    if row['native_valid'] or row['installed_accepted'] or row['earned_credit']:
        return False
    events = row['printed_score']['events']
    if not events or [e['order'] for e in events] != list(range(1, len(events)+1)):
        return False
    if any(e.get('onset_q') is not None or e.get('duration_q') is not None for e in events):
        return False
    if row['timing_authority']['absolute_bpm'] is not None:
        return False
    if not row['performer_contract']['steps'] or row['conflicts']:
        return False
    source = row['source']
    for tag in ['original_txt', 'original_pdf']:
        ref = source[tag]
        path = ROOT / ref['path']
        if not path.is_file() or digest(path) != ref['sha256']:
            return False
    txt = source['original_txt']
    if txt['locator']:
        lines = (ROOT / txt['path']).read_text().splitlines()
        loc = txt['locator']
        if lines[loc['line_start']-1:loc['line_end']] != txt['exact_lines']:
            return False
    return True

def main():
    keys = json.loads(RES.read_text())['keys']
    manifest = json.loads((OUT / 'packet-manifest.json').read_text())
    seen = []
    rows = []
    for batch in manifest['batches']:
        path = ROOT / batch['packet_path']
        assert digest(path) == batch['packet_sha256']
        checkpoint = ROOT / batch['checkpoint_path']
        assert digest(checkpoint) == batch['checkpoint_sha256']
        part = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(part) == batch['key_count']
        rows += part
        seen += [x['package_key'] for x in part]
    assert seen == keys and len(set(seen)) == 106
    assert all(valid(row, key) for row, key in zip(rows, keys))
    sample = rows[0]
    for change in [lambda x: x.update(package_key='wrong'),
                   lambda x: x.update(earned_credit=True),
                   lambda x: x['printed_score']['events'][0].update(onset_q=0),
                   lambda x: x['source']['original_txt'].update(sha256='0'*64)]:
        corrupt = copy.deepcopy(sample)
        change(corrupt)
        assert not valid(corrupt, keys[0]), 'corrupt/identity/credit case was accepted'
    print(json.dumps({'key_count': len(keys), 'batch_count': len(manifest['batches']),
                      'negative_refusals': 4, 'status': 'PASS'}, sort_keys=True))

if __name__ == '__main__':
    main()
