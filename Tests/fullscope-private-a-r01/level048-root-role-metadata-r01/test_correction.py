#!/usr/bin/env python3
"""Causal protection of real rests and immutable musical payloads."""
import copy, hashlib, importlib.util, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
LANE = 'fullscope-private-a-r01'
spec = importlib.util.spec_from_file_location('correct', ROOT / f'Tools/{LANE}/level048-root-role-metadata-r01/correct.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
old = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r09/packet.jsonl').read_text().splitlines()]
new = [json.loads(s) for s in (ROOT / f'Build/{LANE}/level048-r10/packet.jsonl').read_text().splitlines()]
assert len(old) == len(new) == 62
for before, after in zip(old, new):
    m.validate(before, after)
    assert before['implementation'] == after['implementation']
block = {'block_index': 1, 'printed_rest_columns': [0, 4, 8], 'notation_rows': [
    {'label': 'Rol', 'tokens': [{'column': 0, 'text': 'R'}]},
    {'label': 'Nte', 'tokens': [{'column': 0, 'text': 'A'}, {'column': 4, 'text': 'R'}, {'column': 8, 'text': 'r'}]}]}
assert m.removable(block) == {0}
refusals = []
for name, note in [('uppercase actual rest at role column', 'R'), ('lowercase actual rest at role column', 'r'),
                   ('held tone cannot be relabeled root attack', '='), ('unknown sounding note', '?')]:
    bad = copy.deepcopy(block)
    bad['notation_rows'][1]['tokens'][0]['text'] = note
    try:
        m.removable(bad)
    except ValueError as error:
        refusals.append({'case': name, 'refusal': str(error)})
    else:
        raise AssertionError(name)
removed = m.correct(old[0])[1][0]
first = next(b for b in new[0]['source_payload']['notation_blocks'] if b['block_index'] == removed['block_index'])
real_col = first['printed_rest_columns'][0]


def mutate_hint(record, column, restore):
    b = next(b for b in record['source_payload']['notation_blocks'] if b['block_index'] == removed['block_index'])
    if restore:
        b['printed_rest_columns'].append(column)
    else:
        b['printed_rest_columns'].remove(column)


for name, mutate in [
    ('false root hint restored', lambda r: mutate_hint(r, removed['column'], True)),
    ('genuine rest hint deleted', lambda r: mutate_hint(r, real_col, False)),
    ('sounding fret changed', lambda r: r['implementation']['ordered_contacts'][0].update(fret=0)),
    ('actual typed rest deleted', lambda r: r['implementation']['ordered_rest_locations'].pop()),
    ('Accepted flag promoted', lambda r: r['status'].update(Accepted=True))]:
    bad = copy.deepcopy(new[0])
    mutate(bad)
    try:
        m.validate(old[0], bad)
    except ValueError as error:
        refusals.append({'case': name, 'refusal': str(error)})
    else:
        raise AssertionError(name)
report = {'status': 'PASS', 'exact_record_deltas_validated': 62, 'genuine_R_and_r_rest_controls': True,
          'causal_refusals': refusals, 'native_runtime_app_checks': 'NOT_RUN'}
p = ROOT / f'Results/{LANE}/level048-r10/correction-tests.json'
with p.open('x') as out:
    json.dump(report, out, indent=2)
    out.write('\n')
print(json.dumps({'positive_records': 62, 'causal_refusals': len(refusals), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
