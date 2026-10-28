#!/usr/bin/env python3
"""Finite exact-key/source and no-credit verification for the C89 private packet."""
import hashlib
import json
import sys
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT/'Prompts/manager-resume-r01/mass-implementation-shards-r03/shard-c89-reservation.json'
SEAL = ROOT/'Results/exercise-impl-shard-c89-r01/seal.json'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def guard_row(x, old):
    key=x['package_key']
    assert x['source_identity']==key.split('/',1)[1]==old['source_identity']
    assert x['source_refs']==old['source_refs'] and x['source_text']==old['source_payload']['pdf_region_text']
    assert x['printed_fields']==old['implementation']['task']['printed_components']
    assert x['source_refs'][0]['locator']['physical_pages']
    assert all(sha(ROOT/ref['path'])==ref['sha256'] for ref in x['source_refs'])
    assert x['ordered_contacts'] and len({v['position'] for v in x['ordered_contacts']})==len(x['ordered_contacts'])
    assert x['timing_authority']['absolute_bpm'] is None
    assert x['timing_authority']['fixed_onsets'] is False and x['timing_authority']['fixed_durations'] is False
    assert x['delivery_type'].startswith('manual_')
    assert all(value is False for value in x['refusals'].values())
    assert isinstance(x['performer_choices'],list) and isinstance(x['unresolved'],list) and isinstance(x['source_conflicts'],list)


def refuses(x, old):
    try: guard_row(x,old)
    except (AssertionError,KeyError,TypeError): return True
    return False


def check():
    keys=json.loads(RES.read_text())['keys']
    seal=json.loads(SEAL.read_text())
    assert seal['reservation_sha256']==sha(RES)
    assert seal['key_count']==seal['attempted']==seal['source_backed_implemented']==78
    assert seal['remaining_keys']==[]
    assert all(seal[k]==0 for k in ('native_valid','integrated','independently_reviewed','installed_accepted','accepted_count_increment'))
    rows=[]
    for batch in seal['packets']:
        p=ROOT/batch['path']
        assert sha(p)==batch['sha256'] and p.stat().st_size==batch['bytes']
        rows.extend(json.loads(line) for line in p.read_text().splitlines())
    assert [x['package_key'] for x in rows]==keys
    assert len(set(keys))==78
    original={x['package_key']:x for x in map(json.loads,(ROOT/'Build/fullscope-private-c-r01/level089-r06/implementation-packet.jsonl').read_text().splitlines()) if x['package_key'] in keys}
    for x in rows:
        guard_row(x,original[x['package_key']])
    for change in ('source_identity','source_text','source_refs','refusals','timing_authority'):
        x=copy.deepcopy(rows[0])
        if change=='source_identity': x[change]='wrong/source'
        elif change=='source_text': x[change]='tampered source'
        elif change=='source_refs': x[change][0]['sha256']='0'*64
        elif change=='refusals': x[change]['credit_awarded']=True
        else: x[change]['absolute_bpm']=120
        assert refuses(x,original[rows[0]['package_key']]), f'negative guard failed: {change}'
    assert sum(bool(x['unresolved'] or x['source_conflicts']) for x in rows)==seal['unresolved_or_conflict']
    assert len(rows)==78
    print(json.dumps({'result':'PASS','keys':len(rows),'negative_refusals':5,'unresolved_or_conflict':seal['unresolved_or_conflict'],'remaining':0}))


if __name__=='__main__':
    try: check()
    except Exception as exc:
        print(f'FAIL: {exc}',file=sys.stderr)
        raise
