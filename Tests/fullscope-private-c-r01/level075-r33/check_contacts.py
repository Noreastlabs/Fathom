from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import datetime, hashlib, importlib.util, json, resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r33')
spec=importlib.util.spec_from_file_location('contacts',R/'Tools'/L/'tab_contacts.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
checks=0;refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok: raise AssertionError(label)
def refuse(fn,label):
    global refusals
    try: fn()
    except m.Refusal: refusals+=1;check(True,label)
    else: raise AssertionError('accepted '+label)
def pin(p):
    b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
base=[json.loads(x) for x in (R/basepath).read_text().splitlines()][9:13]
packetpath=Path('Build')/L/'role-contact-overlay.jsonl'
rows=[json.loads(x) for x in (R/packetpath).read_text().splitlines()]
projection=json.loads((R/'Build'/L/'source-contact-projection.json').read_text())['cards']
# Independent literal contact and MIDI vectors from printed p4. No production parser in this oracle.
groups=[
 [[('e',0,64),('B',1,60),('G',0,55)], [('e',0,64),('B',1,60),('G',2,57)],
  [('e',1,65),('B',3,62),('G',2,57)], [('e',1,65),('B',0,59),('G',0,55)]],
 [[('B',1,60),('G',0,55),('D',2,52)] if i%2==0 else [('B',None,None),('G',None,None),('D',None,None)] for i in range(8)],
 [[('e',0,64),('B',1,60),('G',0,55)] if i%2==0 else [('e',None,None),('B',None,None),('G',None,None)] for i in range(8)],
 [[x] for x in [('G',4,59),('G',5,60),('G',7,62),('B',5,64),('B',6,65),('B',8,67),
                 ('e',5,69),('e',7,71),('e',8,72),('e',7,71),('e',5,69)]]]
columns=[[2,8,14,20],list(range(2,18,2)),[2,4,8,10,14,16,20,22],[2,4,6,10,12,14,16,18,20,22,24]]
check(len(rows)==4 and [r['package_key'] for r in rows]==list(m.KEYS),'four exact official keys')
totals={'pitched':0,'muted':0,'timed':0}
for case,(old,row,expected,payload) in enumerate(zip(base,rows,groups,projection)):
    for field in ('package_key','source_identity','source_refs','source_payload','existing_parent_id','level'):
        check(row[field]==old[field],'original '+field)
    check(old['implementation']['events']==[],'prior omission explicit')
    check(row['implementation']['task']==old['implementation']['task'],'original task retained')
    events=row['implementation']['events'];check(events==payload['events'],'packet/projection equality')
    check(len(events)==sum(len(g) for g in expected),'exact contact count')
    ordinal=0
    for i,group in enumerate(expected,1):
        for string,fret,midi in group:
            e=events[ordinal];ordinal+=1
            check(e['source_order']==ordinal and e['attack_group']==i,'group/order')
            check((e['string'],e['fret'],e['midi'])==(string,fret,midi),'literal/MIDI oracle')
            check(e['source_literal']==('x' if fret is None else str(fret)),'literal')
            check(e['source_column_zero_based']==columns[case][i-1],'source layout coordinate')
            literal_line=old['source_payload']['pdf_region_text'].splitlines()[e['source_line_in_region']-1]
            body=literal_line.split('|')[1]; c=e['source_column_zero_based']
            check(body[c:c+e['source_token_width']]==e['source_literal'],'source token custody')
            check(e['is_rest'] is False and e['finger'] is None and e['sounded_duration_q'] is None,'no rests/finger/gate')
            if midi is None:
                totals['muted']+=1
                check(e['kind']=='muted_string_stroke' and e['derived_pitch_name'] is None,'muted not pitched')
            else:
                totals['pitched']+=1
                check(e['kind']=='pitched_string_contact' and e['pitch_derivation']=='printed standard tuning + numeric fret','pitch lineage')
            if case==1:
                totals['timed']+=1
                check(Fraction(*e['onset_q'])==Fraction(i-1,2),'eighth onset')
                check(Fraction(*e['duration_q'])==Fraction(1,2),'rhythmic span')
                check(e['timing_kind']=='SOURCE_RELATIVE_RHYTHMIC_SLOT_NOT_SOUND_GATE','not sound gate')
            else:
                check(e['onset_q'] is None and e['duration_q'] is None,'unresolved timing stays null')
    check(row['implementation']['role_context']['table'][-1]==['Silence','Rest / cue watch','Transitions','Prepare next entrance'],'genuine silence role retained separately')
    check(not row['implementation']['role_context']['full_role_workflow_implemented'],'no full manual task claim')
    check(not row['contract_capabilities']['native_valid'] and not row['contract_capabilities']['installed'] and not row['contract_capabilities']['Accepted'],'downstream zero')
    check(row['contract_category']==('TIMED_SOURCE_EVENT_CONTRACT' if case==1 else 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'),'only supported grid promoted')
    if case!=1: check(row['timing_authority']==old['timing_authority'],'other timing unchanged')
check(totals=={'pitched':47,'muted':24,'timed':24},'whole finite contact census')
check([e['derived_pitch_name'] for e in rows[0]['implementation']['events'][-3:]]==['F4','B3','G3'],'lastGlabel exactprinted F/B/G')
check(rows[0]['implementation']['source_contact_recovery']['source_tail_instruction']=='C Am Dm G','Glabel unchanged')
check(rows[3]['implementation']['source_contact_recovery']['source_tail_instruction']=='fill begins after beat 3','full fill bound preserved')
last=rows[1]['implementation']['events'][-1]
check(Fraction(*last['onset_q'])+Fraction(*last['duration_q'])==4,'one fourquarter grid')
check(rows[1]['timing_authority']['fixed_bpm'] is None and not rows[1]['timing_authority']['sounded_gate_resolved'],'no fixed tempo/gate')

invalid=[None,'','e|----|','H|--1--|','e|--0--','e|--r--|','e|--0x?--|','e|--25--|','e|--01--|',
         'e|--0--|\ne|--1--|','B|--1--|\ne|--0--|','e|--10--|\nB|---1--|']
for value in invalid:refuse(lambda value=value:m.parse_tab(value),'malformed or unsafe TAB')
# Ragged trailing padding is preserved as source layout; it creates neither rests nor extra time.
ragged=m.parse_tab('e|--0----|\nB|--1-|')
check(len(ragged['events'])==2 and ragged['attack_group_count']==1,'ragged trailing dashes not fabricated contacts')
check(all(e['onset_q'] is None for e in ragged['events']),'ragged layout not time')
double=m.parse_tab('e|--10--|\nB|--12--|')
check([(e['fret'],e['midi']) for e in double['events']]==[(10,74),(12,71)],'aligned two-digit fret supported')
parsed=m.parse_tab(base[1]['source_payload']['pdf_region_text'])['events'];count='1 & 2 & 3 & 4 &'
before=deepcopy(parsed);timed=m.muted_verse_grid(m.KEYS[1],parsed,count)
check(parsed==before and all(e['onset_q'] is None for e in parsed),'grid projection leaves untimed input unchanged')
check(timed==rows[1]['implementation']['events'],'grid replay exact')
for key in (m.KEYS[0],m.KEYS[2],m.KEYS[3],'invented'):
    refuse(lambda key=key:m.muted_verse_grid(key,parsed,count),'other key cannot borrow timing')
for badcount in ('1 2 3 4','1 e & a 2 e & a 3 e & a 4 e & a','1 & 2 & 3 &','1 & 2 & 3 & 5 &',None):
    refuse(lambda badcount=badcount:m.muted_verse_grid(m.KEYS[1],parsed,badcount),'count grid mismatch')
for n in range(24):
    for field,value in [('source_order',99),('attack_group',99),('string','e'),('source_literal','9'),
                        ('source_column_zero_based',99),('midi',99),('fret',99),('is_rest',True)]:
        q=deepcopy(parsed);q[n][field]=value
        refuse(lambda q=q:m.muted_verse_grid(m.KEYS[1],q,count),'finite contact drift')
for q in (parsed[:-1],parsed+[parsed[0]],list(reversed(parsed))):
    refuse(lambda q=q:m.muted_verse_grid(m.KEYS[1],q,count),'finite count/order drift')
questions=json.loads((R/'Results'/L/'source-questions.json').read_text())
check(questions['status']=='PENDING_DISTINCT_SOURCE_DISPOSITION' and not questions['source_acceptance'],'questions pending')
check(questions['exact_keys']==list(m.KEYS) and questions['source_conflict_count_increment']==0,'no new key/conflict claim')
out=R/'Results'/L/'integrity.json';assert not out.exists()
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,
        'causal_refusals':refusals,'exact_keys':4,'source_contacts':71,'pitched':47,'muted':24,
        'timed_contacts':24,'timed_attack_groups':8,'timed_cases':1,'pending_cases':3,
        'packet':pin(packetpath),'base':pin(basepath),
        'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'native_runs':0,'app_runs':0,'actual_performance_observed':False}
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
