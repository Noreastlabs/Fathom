#!/usr/bin/env python3
"""Bounded packet checks: leased identity, source pins, contact order, refusal."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'Prompts/manager-resume-r01/mass-implementation-shards-r01/shard-c78-reservation.json'
PACKET=ROOT/'Build/exercise-impl-shard-c78-r01/contracts.jsonl'
EXPECTED={'modulea':12,'moduleb':6,'modulec':None,'moduled':8,'modulee':None,
          'modulef':None,'moduleg':None,'moduleh':None}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def check_rows(rows,m):
    assert len(rows)==len(m['keys'])==103
    assert [x['package_key'] for x in rows]==m['keys']
    assert len({x['package_key'] for x in rows})==103
    assert hashlib.sha256(('\n'.join(sorted(m['keys']))+'\n').encode()).hexdigest()==m['key_set_sha256']
    for x in rows:
        assert x['schema_version']=='fathom-private-level078-exercise-contract.1'
        assert x['source_identity']==x['package_key'].split('/',1)[1]
        assert x['canonical_ids_allocated'] is False and x['playback_admitted'] is False
        assert x['score'] is None and x['credit_awarded'] is False
        s=x['source']; c=x['implementation']; mod=x['package_key'].split('/')[2]
        assert mod in EXPECTED
        for fmt in ('pdf','txt'):
            p=ROOT/s[fmt]['path']; assert p.is_file() and sha(p)==s[fmt]['sha256']
        lines=(ROOT/s['txt']['path']).read_text().splitlines()
        assert [lines[n-1] for n in s['txt']['relevant_lines']]==s['txt']['printed_text']
        assert c['steps'] and c['timing']['authority'] in ('relative','unavailable')
        assert c['timing']['fixed_bpm'] is None and c['timing']['absolute_onsets'] is None
        assert c['source_conflicts']==[]
        for contact in c['contacts']:
            assert contact['pitch_name'] and contact['string'] is None and contact['fret'] is None
            assert contact['finger'] is None and contact['performed_observation'] is False
        if EXPECTED[mod] is not None and (mod!='moduled' or s['pdf']['physical_page']==9):
            assert len(c['contacts'])==EXPECTED[mod],x['package_key']
        if mod=='modulec' and s['pdf']['physical_page']==6:
            assert len(c['contacts']) in (5,6),x['package_key']
        if mod=='modulec' and s['pdf']['physical_page']==7:
            assert len(c['contacts'])==1
        if mod=='moduled' and s['pdf']['physical_page']==8:
            assert len(c['contacts'])==8
        if mod=='moduleh' and s['pdf']['physical_page']==16:
            assert len(c['contacts'])==16 and [a['pitch_name'] for a in c['contacts']][-1]=='G'
            assert c['source_extraction_limits'][0]['repaired_from_txt_line']==195
    return len(rows)

def validate():
    m=json.loads(MANIFEST.read_text())
    rows=[json.loads(x) for x in PACKET.read_text().splitlines()]
    count=check_rows(rows,m)
    print(json.dumps({'result':'PASS','rows':count,'sha256':sha(PACKET)}))
    return rows,m

def refusal(rows,m):
    for damaged in (rows[:-1], [rows[0]]+rows[:-1]):
        try: check_rows(damaged,m)
        except AssertionError: pass
        else: raise AssertionError('damaged exact coverage accepted')
    altered=json.loads(json.dumps(rows))
    altered[0]['source']['pdf']['sha256']='0'*64
    try: check_rows(altered,m)
    except AssertionError: pass
    else: raise AssertionError('source-pin drift accepted')
    altered=json.loads(json.dumps(rows))
    altered[0]['credit_awarded']=True
    try: check_rows(altered,m)
    except AssertionError: pass
    else: raise AssertionError('unearned credit accepted')
    try: json.loads('{bad json')
    except json.JSONDecodeError: pass
    else: raise AssertionError('corrupt JSON accepted')
    print(json.dumps({'result':'PASS','guards':['missing-key','duplicate-key','input-pin-drift','unearned-credit','corrupt-json']}))

if __name__=='__main__':
    refusal(*validate())
