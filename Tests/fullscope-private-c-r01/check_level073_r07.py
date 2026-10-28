from pathlib import Path
import json,copy,hashlib,datetime
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl';checks=0

def ck(v,m):
 global checks
 checks+=1
 if not v:raise ValueError(m)
def validate(rows):
 prior=[json.loads(x) for x in (ROOT/'Build/fullscope-private-c-r01/level073-r06/implementation-packet.jsonl').read_text().splitlines()]
 ck([r['package_key'] for r in rows]==[r['package_key'] for r in prior],'identity/order')
 ck(sum(len(r['implementation']['events']) for r in rows)==628,'printed contact count')
 sourcepins={}
 for r,old in zip(rows,prior):
  for s in r['source_refs']:
   if s['path'] not in sourcepins:sourcepins[s['path']]=hashlib.sha256((ROOT/s['path']).read_bytes()).hexdigest()
   ck(sourcepins[s['path']]==s['sha256'],'source pin')
  es=r['implementation']['events'];ck([(e['printed_note'],e['string_name'],e['fret']) for e in es]==[(e['printed_note'],e['string_name'],e['fret']) for e in old['implementation']['events']],'contact identity')
  ck(not r['implementation']['canonical_ids_allocated'] and not r['implementation']['playback_admitted'],'admission')
  for e in es:
   midi={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}[e['string_name']]+e['fret'];ck(e['written_pitch_theory']['midi_at_stated_standard_tuning']==midi,'written tuning')
  if '/modulec/' in r['source_identity']:
   ck(r['contract_category']=='TIMED_SOURCE_EVENT_CONTRACT','C source metric category')
   p=r['implementation']['performance_plan'];ck(len(p['practice_passes'])==3,'solo/combined passes')
   ck(p['practice_passes'][0]['voice']=='1' and p['practice_passes'][1]['voice']=='2' and p['practice_passes'][2]['mode']=='combined','pass sequence')
   for i,e in enumerate(es):
    ck(e['onset_q'] is None and e['duration_q'] is None,'invented quarter meter')
    ck(e['bar_time']['onset_bar']==[i%4,1] and e['bar_time']['structural_duration_bar']==[1,1],'printed four bar slots')
    if e['attack']=='held':
     a=es[e['tie_from_source_order']-1];ck(e['voice']==a['voice'],'held cross voice');ck((e['printed_note'],e['string_name'],e['fret'])==(a['printed_note'],a['string_name'],a['fret']),'held identity');ck(e['bar_time']['onset_bar'][0]==a['bar_time']['onset_bar'][0]+1,'held bar adjacency')
   expected=[[i+1,i+5] for i in range(4)];ck(p['practice_passes'][2]['same_bar_groups']==expected,'parallel groups')
  if '/modulef/' in r['source_identity']:
   p=r['implementation']['performance_plan'];ck(p['loop_sequence']==list(range(1,13))+[9,10,11,12],'final tonic repeat');ck(p['loop_occurrences']==16 and len(es)==12,'printed vs repeated occurrences')
 return True
rows=[json.loads(x) for x in P.read_text().splitlines()];validate(rows);positive=checks;cs=next(i for i,r in enumerate(rows) if '/modulec/' in r['source_identity']);fs=next(i for i,r in enumerate(rows) if '/modulef/' in r['source_identity']);he=next(i for i,e in enumerate(rows[cs]['implementation']['events']) if e['attack']=='held')
mutations=[('source_hash',lambda rs:rs[0]['source_refs'][0].update(sha256='0'*64)),('invented_meter',lambda rs:rs[cs]['implementation']['events'][0].update(onset_q=0)),('held_wrong_voice',lambda rs:rs[cs]['implementation']['events'][he].update(voice='9')),('held_wrong_contact',lambda rs:rs[cs]['implementation']['events'][he].update(fret=99)),('missing_solo_pass',lambda rs:rs[cs]['implementation']['performance_plan']['practice_passes'].pop(0)),('sequential_not_parallel',lambda rs:rs[cs]['implementation']['performance_plan']['practice_passes'][2].update(same_bar_groups=[[1,2],[3,4],[5,6],[7,8]])),('missing_tonic_repeat',lambda rs:rs[fs]['implementation']['performance_plan'].update(loop_sequence=list(range(1,13)))),('canonical_allocation',lambda rs:rs[0]['implementation'].update(canonical_ids_allocated=True))]
neg=[]
for name,mutation in mutations:
 r=copy.deepcopy(rows);mutation(r)
 try:validate(r)
 except ValueError as e:neg.append({'case':name,'refused':True,'reason':str(e)})
 else:raise AssertionError(name)
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','positive_checks':positive,'total_checks_including_refusals':checks,'negative_cases':neg,'packet_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'native_gui_shared':'NOT_RUN'};dest=ROOT/'Results/fullscope-private-c-r01/level073-r07/integrity.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
