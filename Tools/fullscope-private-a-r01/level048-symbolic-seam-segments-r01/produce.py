#!/usr/bin/env python3
"""Four immutable source seam contracts; keep downbeat guidance mismatch visible."""
import copy,datetime,hashlib,json,re,resource,time
from pathlib import Path
import pdfplumber
from actions import build
ROOT=Path(__file__).resolve().parents[3];LANE='fullscope-private-a-r01'
OLD=ROOT/f'Build/{LANE}/level048-r06';OUT=ROOT/f'Build/{LANE}/level048-r07';RES=ROOT/f'Results/{LANE}/level048-r07'
PROMPT=ROOT/f'Prompts/{LANE}/level048-symbolic-seam-segments-r01/full-template-prompt.md'
def ref(p):
 p=Path(p);return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def dump(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def tokens(row):return [x for part in row.split('|')[1:] for x in re.split(r'-+',part) if x]
def main():
 start=datetime.datetime.now(datetime.timezone.utc);timer=time.perf_counter()
 assert ref(OLD/'packet.jsonl')['sha256']=='910b0764f2a6249161eebd60e5b550b5dd678cb55ef1615793a9398f8b12dc8b'
 assert ref(PROMPT)['sha256']=='651f24b236e8900536563bf029e545042cec7f6b2383eea02c0845a6e7bb7af6'
 if OUT.exists() or RES.exists():raise FileExistsError('Fresh output roots required')
 raw=(OLD/'packet.jsonl').read_text().splitlines(keepends=True);rs=[json.loads(x) for x in raw];assert len(rs)==62
 txt,pdf=[{k:v for k,v in x.items() if k!='locator'} for x in rs[5]['source_refs'][:2]]
 assert ref(ROOT/txt['path'])==txt and ref(ROOT/pdf['path'])==pdf
 lines=(ROOT/txt['path']).read_text().splitlines()
 with pdfplumber.open(ROOT/pdf['path']) as d:pages={n:d.pages[n-1].extract_text() for n in (6,7)}
 assert 'A7 -> D7 -> E7 -> A7' in pages[6]
 checks=1;counts={'sounding_events':0,'picked_excitation_groups':0,'unpicked_arrivals':0,'holds':0,'rest_slots':0};audit=[];mismatches=[]
 for index in range(6,10):
  r=rs[index-1];before=copy.deepcopy(r);page=6 if index<8 else 7
  loc=r['source_refs'][0]['locator'];assert lines[loc['line_start']-1:loc['line_end']]==r['source_payload']['exact_unit_lines'];checks+=1
  source=r['source_payload']['exact_unit_lines']
  route=re.search(r'Route: (P\d -> P\d -> P\d -> P\d)\.',source[1]);assert route
  route_labels=route[1].split(' -> ');assert route[1] in pages[page]
  slots=r['implementation']['symbolic_count_slots']
  for label,field in [('Nte','note'),('Atk','attack_mark')]:
   original=[line for line in source if line.startswith(label+'|')];assert len(original)==1
   expected=tokens(original[0]);actual=[s[field] for s in slots];assert expected==actual
   pdfrows=[tokens(row) for row in re.findall(label+r'\|[^\s]+',pages[page])]
   assert expected in pdfrows;checks+=2
  targets=re.findall(r'Beat-one targets: ([^\n]+)',pages[page])[(index-6)%2]
  groups=[x.strip().rstrip('.') for x in targets.split('|')];assert groups[-1]=='C#/A'
  events=r['implementation']['sounding_events'];starts=[next(e for e in events if e['relative_position']=={'bar':bar,'beat':1,'phase':'beat'}) for bar in (1,2,3,4)]
  arrival=next(e for e in events if e['relative_position']=={'bar':4,'beat':1,'phase':'offbeat'})
  assert starts[-1]['source_note']=='C' and arrival['source_note']=='C#' and arrival['attack']=='slide_arrival'
  mismatch={'kind':'printed_downbeat_guidance_vs_literal_notation','status':'SOURCE_GUIDANCE_RECONCILIATION_PENDING',
   'source_pdf_page':page,'exact_printed_guidance':'Beat-one targets: '+targets,
   'guidance_bar4_targets':['C#','A'],
   'written_bar4_downbeat':{'event_ordinal':starts[-1]['ordinal'],'note':'C','position':starts[-1]['relative_position'],'attack':starts[-1]['attack']},
   'written_C_sharp_arrival':{'event_ordinal':arrival['ordinal'],'note':'C#','position':arrival['relative_position'],'attack':'slide_arrival'},
   'disposition':'Keep both exact source statements; Curriculum must clarify the target label before that claim can be admitted. Do not move or replace literal notes.',
   'source_pitch_or_timing_repair_applied':False}
  action=build(r)
  r['implementation']['symbolic_action_segments']=action
  r['implementation']['source_gate_rule']=action['source_gate_constraint']
  r['implementation']['source_seam_route']={'source_route_text':source[1],'position_by_bar':route_labels,
   'chord_by_bar':['A7','D7','E7','A7'],'chord_schedule_source_pdf_page':6,
   'written_first_event_by_bar':[{'bar':j,'event_ordinal':e['ordinal'],'note':e['source_note']} for j,e in enumerate(starts,1)],
   'printed_target_guidance':groups,'do_not_pause_for_shift':True,'numeric_shift_duration':None,
   'target_guidance_reconciliation':mismatch}
  r['unresolved_reasons'].append({'field':'bar4_downbeat_target_guidance','code':'SOURCE_UNRESOLVED',
   'reason':'PDF prints C#/A as bar4 beat-one targets, but original TAB plays C on beat1 then C# at the offbeat. Literal traversal is preserved; target-label reconciliation awaits Curriculum.'})
  r['provenance']['symbolic_seam_supplement']={'previous_packet':ref(OLD/'packet.jsonl'),
   'producer':ref(Path(__file__)),'transducer':ref(Path(__file__).with_name('actions.py')),'source_originals':[txt,pdf],'independent_review':False}
  assert r['implementation']['ordered_contacts']==before['implementation']['ordered_contacts']
  assert r['implementation']['sounding_events']==before['implementation']['sounding_events']
  assert r['status']==before['status'] and r['timing_authority']==before['timing_authority'];checks+=3
  for k,v in action['counts'].items():counts[k]+=v
  mismatches.append({'row':index,'package_key':r['package_key'],'source_identity':r['source_identity'],**mismatch})
  audit.append({'row':index,'package_key':r['package_key'],'source_identity':r['source_identity'],
    'counts':action['counts'],'unchanged_original_events':True,'unchanged_timing_status':True})
 assert counts['sounding_events']==92 and counts['picked_excitation_groups']==77
 OUT.mkdir();RES.mkdir()
 dump(OUT/'original-module-b-pages.json',{'source_pdf':pdf,'pages':pages,'extraction':'Original physical-page text; no raster review claimed'})
 dump(OUT/'source-target-guidance-mismatches.json',mismatches);dump(OUT/'changed-key-audit.json',audit)
 with (OUT/'packet.jsonl').open('x') as f:
  for i,r in enumerate(rs,1):f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' if 6<=i<=9 else raw[i-1])
 reread=(OUT/'packet.jsonl').read_text().splitlines(keepends=True);assert all(reread[i-1]==raw[i-1] for i in range(1,63) if not 6<=i<=9)
 context=json.loads((OLD/'level-source-context.json').read_text());context['module_b_symbolic_actions']={
   'source':ref(OUT/'original-module-b-pages.json'),'rows':[6,7,8,9],
   'target_guidance_mismatches':ref(OUT/'source-target-guidance-mismatches.json'),'shuffle_ratio_selected':False}
 dump(OUT/'level-source-context.json',context);dump(OUT/'remaining-keys.json',[])
 info={'status':'PASS','source_checks':checks,'changed_rows':[6,7,8,9],'unchanged_record_bytes':58,
  'source_counts':counts,'symbolic_slots':128,'added_seam_route_contracts':4,'target_guidance_mismatches_retained':4,
  'source_pitch_or_timing_repairs':0,'readiness_change':0,'new_independent_native_integrated_accepted':0}
 dump(RES/'semantic-checks.json',info)
 previous=json.loads((ROOT/f'Results/{LANE}/level048-r06/seal.json').read_text());inputs={x['path']:x for x in previous['source_inputs']}
 for p in [OLD/'packet.jsonl',OLD/'level-source-context.json',PROMPT,Path(__file__),Path(__file__).with_name('actions.py'),
  OUT/'original-module-b-pages.json',OUT/'source-target-guidance-mismatches.json',OUT/'changed-key-audit.json']:
  z=ref(p);inputs[z['path']]=z
 seal={**previous,'started_utc':start.isoformat(),'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'elapsed_seconds':time.perf_counter()-timer,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'packet':ref(OUT/'packet.jsonl'),'context':ref(OUT/'level-source-context.json'),'source_inputs':list(inputs.values()),
  'remaining_keys_reference':ref(OUT/'remaining-keys.json'),'targeted_checks':ref(RES/'semantic-checks.json'),
  'command':'Bundled Python -B Tools/fullscope-private-a-r01/level048-symbolic-seam-segments-r01/produce.py',
  'limits':'Source symbolic ownership/position routes only. Numeric shuffle/gates and bar4 target-guidance reconciliation stay unresolved. No pitch repair/readiness/admission increase.'}
 dump(RES/'seal.json',seal)
 (RES/'handoff.md').write_text('# Level48 r07 — four seam action contracts\n\n'
  'Rows6–9 now have128 symbolic source actions,92 sounding segments and77 picked excitation groups. Exact four-position routes and A7/D7/E7/A7 source schedules accompany holds, explicit rests and unpicked destinations. No additional pick, note, timed shift, shuffle ratio or acoustic envelope is generated.\n\n'
  'Source guidance requires Curriculum reconciliation: allfour PDF6–7 “Beat-one targets” labels name C#/A for bar4, while every written bar4 starts picked C on beat1 and slides to C# at the offbeat. Both are preserved and pinned. The literal C-to-C# traversal is not unknown or altered; no target-label claim is admitted by this producer. Exact affected keys/locators are in source-target-guidance-mismatches.json.\n\n'
  'All62 identities and original contacts remain;58 unrelated records are byte-identical, including allfive preceding ModuleA supplements. Counts stay3manual/21choice/38partial. New independent/native/integrated/Accepted counts are zero; native/app/GUI/performance tests NOT_RUN.\n')
 print(json.dumps({'packet':seal['packet'],'counts':counts,'runtime_seconds':seal['elapsed_seconds'],'peak_rss_bytes':seal['process_peak_rss_bytes']}))
if __name__=='__main__':main()
