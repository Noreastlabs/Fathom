import copy,hashlib,json,sys,re
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
@lru_cache(maxsize=None)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(records,handoff,checkpins=True):
 assert len(records)==handoff['counts']['attempted']
 keys=[r['package_key'] for r in records];ids=[r['source_identity'] for r in records]
 assert len(set(keys))==len(keys) and len(set(ids))==len(ids),'IDENTITY_DUPLICATE'
 identity=hashlib.sha256(json.dumps([[r['package_key'],r['source_identity']] for r in records],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
 assert identity==handoff['ordered_child_identity_sha256'],'IDENTITY_ORDER'
 for r in records:
  assert r['existing_parent_id']=='2.3.1.2.1'
  assert all(r['provenance'][k] is False for k in ['canonical_ids_allocated','native_validated','runtime_admitted','independently_reviewed','accepted']),'AUTHORITY'
  if checkpins:
   for p in r['source_refs']:
    f=ROOT/p['path'];assert f.stat().st_size==p['bytes'] and sha(f)==p['sha256'],'SOURCE_HASH'
  impl=r['implementation'];events=impl.get('events',[])
  assert events or impl.get('task') or impl.get('tasks') or impl.get('ordered_steps') or impl.get('voicings'),'EMPTY_PAYLOAD'
  assert [e['order'] for e in events]==list(range(1,len(events)+1)),'EVENT_ORDER'
  times=[e['onset_q'][0]/e['onset_q'][1] for e in events if e.get('onset_q') is not None]
  assert times==sorted(times),'TIMING_ORDER'
  if r['level']==49:
   parent=r['source_payload']['parent_path'][-1]
   expected=4 if 'MODULE A1' in parent else 12 if any(x in parent for x in ['MODULE A2','MODULE B','MODULE C','MODULE H']) else 8 if any(x in parent for x in ['MODULE D','MODULE E','MODULE G']) else 16 if any(x in parent for x in ['MODULE F','MODULE I','MODULE J']) else 0
   assert len(events)==expected,'EVENT_COMPLETENESS'
  lv=r['level'];sid=r['source_identity'];label=r['source_payload']['label'];expected=None
  module=re.search(r'/module([a-z])/',sid);module=module[1] if module else None
  if lv==52 and label in ['TOP-VOICE TEST','BASS-VOICE TEST']:
   expected=32;assert all(e.get('accent_string')==(1 if label=='TOP-VOICE TEST' else 3) for e in events),'VOICE_ACCENT_STRING'
  if lv==52 and impl.get('interaction_contract'):
   assert impl['interaction_contract']['response_schema'] and all(f.get('default') is None for f in impl['interaction_contract']['response_schema'].values()),'FABRICATED_LEARNER_RESPONSE'
  if lv==53:
   if '-t' in sid and module in ['a','b']:expected=4
   if '-card' in sid and module in ['c','d','f','g']:expected=8
  if lv in [55,56] and '-t' in sid and module in ['a','b']:expected=4
  if lv==54 and module=='i' and '-card' in sid:expected=12
  if lv==58 and module=='g':expected=64
  if lv==58 and '/modulei/p016-' in sid:
   expected=512;assert sum(e['kind'] in ['pitched_chord_contact','dead_stroke'] for e in events)==209,'CAPSTONE_CONTACT_COUNT'
   assert [e['bar'] for e in events]==[i//16+1 for i in range(512)],'CAPSTONE_FORM'
  if lv==59 and '-card' in sid and module in ['d','f','j']:expected={'d':12,'f':18,'j':16}[module]
  if lv==60 and '-card' in sid and module=='d':expected=30
  if lv==60 and '/moduleef/p012-' in sid and re.fullmatch(r'\S+ [EA]-root',label):expected=8
  if lv==64 and re.match(r'J[1-6]\. ',label):expected=8
  if lv in [60,61] and 'capstone:' in label:expected=64
  if lv==61 and '-card' in sid and module=='a':expected=4
  if lv==62 and '-card' in sid and module=='j':expected=8 if label.endswith('bridge') else 2
  if lv==63 and '-card' in sid and module=='g':expected=28
  if lv in [66,70] and '-card' in sid and module=='b':expected=42
  if lv==67 and '-card' in sid and module=='h':expected=2 if label=='Dominant release' else 8
  if lv==69 and '-card' in sid and module=='a':expected=12
  if expected is not None:assert len(events)==expected,('SOURCE_FAMILY_COMPLETENESS',sid,len(events),expected)
  for e in events:
   if e.get('string') is not None:assert 1<=e['string']<=6
   if e.get('fret') is not None:assert 0<=e['fret']<=24
   for m in [e]+(e.get('members') or []):
    n=m.get('printed_note','') or '';st=m.get('string');f=m.get('fret')
    if re.fullmatch(r'[A-G][#b]*',n) and st and f is not None:
     assert ({'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[n[0]]+n.count('#')-n.count('b'))%12==({6:4,5:9,4:2,3:7,2:11,1:4}[st]+f)%12,('PITCH_CONTACT_DISAGREEMENT',sid,e['order'],n,st,f)
 return True
if __name__=='__main__':
 level=int(sys.argv[1]);suffix=('-'+sys.argv[2]) if len(sys.argv)>2 else '';root=ROOT/'Results/fullscope-private-b-r01'/(f'level{level:03d}'+suffix);h=json.loads((root/'handoff.json').read_text());rows=[json.loads(s) for s in (ROOT/h['packet']['path']).read_text().splitlines()]
 validate(rows,h)
 passed=[]
 for name,mut in [('duplicate_identity',lambda x:x.__setitem__(1,copy.deepcopy(x[0]))),('event_order',lambda x:next(r for r in x if r['implementation'].get('events'))['implementation']['events'][0].update(order=999)),('forged_admission',lambda x:x[0]['provenance'].update(runtime_admitted=True)),('source_hash',lambda x:x[0]['source_refs'][0].update(sha256='0'*64))]:
  c=copy.deepcopy(rows);mut(c)
  try:validate(c,h)
  except AssertionError:passed.append(name)
  else:raise AssertionError('corruption accepted: '+name)
 result={'baseline':'PASS','records':len(rows),'events':sum(len(r['implementation'].get('events',[])) for r in rows),'corruption_refusals':passed,'packet':h['packet'],'handoff_sha256':sha(root/'handoff.json'),'validator_sha256':sha(Path(__file__)),'native_app_gui_broad_qa':'NOT_RUN; outside private source production authority'}
 (root/'targeted-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
