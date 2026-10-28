#!/usr/bin/env python3
"""Bounded packet identity, source integrity, timing/order and causal corruption refusals."""
from pathlib import Path
import sys,json,hashlib,copy,datetime
ROOT=Path(__file__).resolve().parents[2]
checks=0

def require(ok,message):
 global checks
 checks+=1
 if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(records,expected):
 require(len(records)==len(expected),'count')
 require(len({r['package_key'] for r in records})==len(records),'duplicate')
 require({r['source_identity']:r['package_key'] for r in records}==expected,'identity')
 seen={}
 for r in records:
  require(r['existing_parent_id']=='2.3.1.3.1','parent')
  require(r['source_payload']['pdf_region_text'].strip(),'empty payload')
  require(r['implementation']['canonical_ids_allocated'] is False and r['implementation']['playback_admitted'] is False,'allocation/admission')
  for ref in r['source_refs']:
   p=ROOT/ref['path'];key=(ref['path'],ref['sha256'],ref['bytes'])
   if key not in seen:seen[key]=p.stat().st_size==ref['bytes'] and sha(p)==ref['sha256']
   require(seen[key],'source hash')
  es=r['implementation']['events'];require([e['source_order'] for e in es]==list(range(1,len(es)+1)),'event order')
  for e in es:
   if e['onset_q'] is not None:
    require(e['onset_q']>=0 and e['duration_q']>0,'timing')
    require(e['onset_q_fraction'][0]/e['onset_q_fraction'][1]==e['onset_q'],'rational onset')
   if e.get('attack')=='held':
    a=es[e['tie_from_source_order']-1]
    require(all(a[k]==e[k] for k in ['string_name','fret','printed_note']),'held identity')
    require(a['onset_q']+a['duration_q']==e['onset_q'],'held adjacency')
  if r['status'].startswith('SOURCE_SUPPORTED_'):require(not r['unresolved_reasons'],'false ready')

def main():
 level=int(sys.argv[1]);revision=sys.argv[2] if len(sys.argv)>2 else 'r03';dest=ROOT/'Build/fullscope-private-c-r01'/f'level{level:03d}-{revision}'
 packet=dest/'implementation-packet.jsonl';records=[json.loads(s) for s in packet.read_text().splitlines()];expected={}
 with (ROOT/'Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl').open() as f:
  for s in f:
   r=json.loads(s)
   if r['exercise']['level']==level:expected[r['exercise']['source_identity']]=r['package_key']
 check(records,expected);base_checks=checks;negative=[]
 cases=[('missing',lambda r:r.pop()),('duplicate',lambda r:r.append(copy.deepcopy(r[0]))),('source_corruption',lambda r:r[0]['source_refs'][0].update(sha256='0'*64)),('allocation',lambda r:r[0]['implementation'].update(canonical_ids_allocated=True)),('empty_shell',lambda r:r[0]['source_payload'].update(pdf_region_text=''))]
 eventrow=next((i for i,r in enumerate(records) if r['implementation']['events']),None)
 if eventrow is not None:cases.append(('event_order',lambda r:r[eventrow]['implementation']['events'][0].update(source_order=999)))
 for name,mutate in cases:
  r=copy.deepcopy(records);mutate(r)
  try:check(r,expected)
  except ValueError as e:negative.append({'case':name,'refused':True,'reason':str(e)})
  else:raise AssertionError('corruption accepted '+name)
 if level==73:
  require(sum(len(r['implementation']['events']) for r in records)==628,'L73 exact official contacts')
  aa=[r for r in records if '/modulea/' in r['source_identity']];require(len(aa)==5,'L73 A5')
  for r in aa:
   es=r['implementation']['events'];require([e['onset_q'] for e in es]==list(range(8)),'printed quarter grid');require(es[4]['attack']=='held','barline sustain');require(r['status']=='SOURCE_SUPPORTED_RELATIVE_EVENTS','A relative ready')
 out={'schema':'fathom-private-integrity.1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'level':level,'packet_path':str(packet.relative_to(ROOT)),'packet_sha256':sha(packet),'result':'PASS','positive_checks':base_checks,'total_checks_including_refusals':checks,'negative_cases':negative,'runtime_native_gui':'NOT_RUN: private integrity only'}
 p=ROOT/'Results/fullscope-private-c-r01'/f'level{level:03d}-{revision}'/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'level':level,'result':'PASS','checks':checks,'negative':len(negative),'packet_sha256':out['packet_sha256']}))
if __name__=='__main__':main()
