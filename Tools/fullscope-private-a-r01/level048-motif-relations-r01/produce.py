#!/usr/bin/env python3
"""Eight source motif relationships and one-bar action contracts; no generated music."""
import copy,datetime,hashlib,json,re,resource,time
from pathlib import Path
import pdfplumber
from actions import build
from relations import relation
ROOT=Path(__file__).resolve().parents[3];LANE='fullscope-private-a-r01'
OLD=ROOT/f'Build/{LANE}/level048-r07';OUT=ROOT/f'Build/{LANE}/level048-r08';RES=ROOT/f'Results/{LANE}/level048-r08'
PROMPT=ROOT/f'Prompts/{LANE}/level048-motif-relations-r01/full-template-prompt.md'
def ref(p):
 p=Path(p);return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def dump(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def tokens(row):return [x for part in row.split('|')[1:] for x in re.split(r'-+',part) if x]
def main():
 start=datetime.datetime.now(datetime.timezone.utc);timer=time.perf_counter()
 assert ref(OLD/'packet.jsonl')['sha256']=='de8e9c4ced6bbdcefc895a8415be2b3305112d90296e24389af1df6eec4ef11e'
 assert ref(PROMPT)['sha256']=='a1205f4c67c7b253b9aefd6ada7b9019e0d0722b6691c32bdfa159afc4fc153e'
 if OUT.exists() or RES.exists():raise FileExistsError('Fresh output roots required')
 raw=(OLD/'packet.jsonl').read_text().splitlines(keepends=True);rs=[json.loads(x) for x in raw];assert len(rs)==62
 seed=copy.deepcopy(rs[9]);seed_ref={'packet':ref(OLD/'packet.jsonl'),'line':10,'package_key':seed['package_key'],'record_canonical_sha256':digest(seed)}
 txt,pdf=[{k:v for k,v in x.items() if k!='locator'} for x in seed['source_refs'][:2]]
 assert ref(ROOT/txt['path'])==txt and ref(ROOT/pdf['path'])==pdf
 lines=(ROOT/txt['path']).read_text().splitlines()
 with pdfplumber.open(ROOT/pdf['path']) as d:pages={n:d.pages[n-1].extract_text() for n in (8,9)}
 checks=0;counts={'sounding_events':0,'picked_excitation_groups':0,'unpicked_arrivals':0,'holds':0,'rest_slots':0};audit=[]
 for index in range(10,18):
  r=rs[index-1];before=copy.deepcopy(r);page=8 if index<=13 else 9
  loc=r['source_refs'][0]['locator'];assert lines[loc['line_start']-1:loc['line_end']]==r['source_payload']['exact_unit_lines'];checks+=1
  for label,field in [('Nte','note'),('Atk','attack_mark')]:
   original=[line for line in r['source_payload']['exact_unit_lines'] if line.startswith(label+'|')];assert len(original)==1
   expected=tokens(original[0]);assert expected==[s[field] for s in r['implementation']['symbolic_count_slots']]
   assert expected in [tokens(row) for row in re.findall(label+r'\|[^\s]+',pages[page])];checks+=2
  action=build(r);link=relation(seed,r,index);link['seed_source_binding']=seed_ref
  r['implementation']['symbolic_action_segments']=action
  r['implementation']['source_gate_rule']=action['source_gate_constraint']
  r['implementation']['printed_motif_relation']=link
  r['provenance']['motif_relation_supplement']={'previous_packet':ref(OLD/'packet.jsonl'),'producer':ref(Path(__file__)),
   'action_transducer':ref(Path(__file__).with_name('actions.py')),'relation_code':ref(Path(__file__).with_name('relations.py')),
   'source_originals':[txt,pdf],'independent_review':False}
  assert r['implementation']['ordered_contacts']==before['implementation']['ordered_contacts']
  assert r['implementation']['sounding_events']==before['implementation']['sounding_events']
  assert r['unresolved_reasons']==before['unresolved_reasons'] and r['status']==before['status']
  assert r['timing_authority']==before['timing_authority'];checks+=4
  for k,v in action['counts'].items():counts[k]+=v
  audit.append({'row':index,'package_key':r['package_key'],'source_identity':r['source_identity'],
   'original_record_canonical_sha256':digest(before),'new_record_canonical_sha256':digest(r),
   'source_counts':action['counts'],'relation_kind':link['kind'],'contacts_timing_status_unchanged':True})
 assert counts['sounding_events']==47 and counts['picked_excitation_groups']==30
 OUT.mkdir();RES.mkdir()
 dump(OUT/'original-module-c-pages.json',{'source_pdf':pdf,'pages':pages,'extraction':'Original physical-page text; no raster review claimed'})
 dump(OUT/'changed-key-audit.json',audit)
 with (OUT/'packet.jsonl').open('x') as f:
  for i,r in enumerate(rs,1):f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' if 10<=i<=17 else raw[i-1])
 reread=(OUT/'packet.jsonl').read_text().splitlines(keepends=True);assert all(reread[i-1]==raw[i-1] for i in range(1,63) if not 10<=i<=17)
 context=json.loads((OLD/'level-source-context.json').read_text());context['module_c_printed_relations']={
   'source':ref(OUT/'original-module-c-pages.json'),'rows':list(range(10,18)),'seed':seed_ref,
   'scope':'Source examples only, not automatic generation of new variants','shuffle_ratio_selected':False}
 dump(OUT/'level-source-context.json',context);dump(OUT/'remaining-keys.json',[])
 info={'status':'PASS','source_checks':checks,'changed_rows':list(range(10,18)),'unchanged_record_bytes':54,
  'source_counts':counts,'symbolic_slots':64,'seed_and_printed_relations':8,'source_events_generated':0,
  'readiness_change':0,'new_independent_native_integrated_accepted':0}
 dump(RES/'semantic-checks.json',info)
 previous=json.loads((ROOT/f'Results/{LANE}/level048-r07/seal.json').read_text());inputs={x['path']:x for x in previous['source_inputs']}
 for p in [OLD/'packet.jsonl',OLD/'level-source-context.json',PROMPT,Path(__file__),Path(__file__).with_name('actions.py'),
  Path(__file__).with_name('relations.py'),OUT/'original-module-c-pages.json',OUT/'changed-key-audit.json']:
  z=ref(p);inputs[z['path']]=z
 seal={**previous,'started_utc':start.isoformat(),'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'elapsed_seconds':time.perf_counter()-timer,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'packet':ref(OUT/'packet.jsonl'),'context':ref(OUT/'level-source-context.json'),'source_inputs':list(inputs.values()),
  'remaining_keys_reference':ref(OUT/'remaining-keys.json'),'targeted_checks':ref(RES/'semantic-checks.json'),
  'command':'Bundled Python -B Tools/fullscope-private-a-r01/level048-motif-relations-r01/produce.py',
  'limits':'Eight exact printed relationships, no generative transform. Shuffle/onset/gate realization remains unselected; no readiness or admission changes.'}
 dump(RES/'seal.json',seal)
 (RES/'handoff.md').write_text('# Level48 r08 — printed motif relations\n\n'
  'Rows10–17 now have64 symbolic source actions for47 sounding events/30 picked attacks, plus exact relationships between the printed seed and its seven variants. Echo preserves exact events; displacement is one printed subdivision, with no constant elapsed-delay claim. Reversal retains its separately printed attacks. Register shift changes the firstfive events by24 semitones and the last by12, and changes the second attack. Recolor preserves the printed rhythm while changing named pitches/articulation. Expansion preserves the opening and ordered seed pitches but retimes later notes. Reduction uses printed A–C#–A, not a literal deletion from the seed.\n\n'
  'No new music, uniform transpose, fabricated shuffle ratio, timing, acoustic gate, performance or credit is generated. All62 keys/contacts remain;54 unrelated records are byte-identical. Counts remain3manual/21choice/38partial. The four ModuleB source target-guidance mismatches remain intact for Curriculum. Native/app/GUI/performance checks NOT_RUN; no independent/native/integrated/Accepted increase.\n')
 print(json.dumps({'packet':seal['packet'],'counts':counts,'runtime_seconds':seal['elapsed_seconds'],'peak_rss_bytes':seal['process_peak_rss_bytes']}))
if __name__=='__main__':main()
