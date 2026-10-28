#!/usr/bin/env python3
"""Materialize five source symbolic action contracts in a fresh full Level48 packet."""
import copy,datetime,hashlib,json,re,resource,time
from pathlib import Path
import pdfplumber
from actions import build,practice
ROOT=Path(__file__).resolve().parents[3];LANE='fullscope-private-a-r01'
OLD=ROOT/f'Build/{LANE}/level048-r05';OUT=ROOT/f'Build/{LANE}/level048-r06';RES=ROOT/f'Results/{LANE}/level048-r06'
PROMPT=ROOT/f'Prompts/{LANE}/level048-symbolic-action-segments-r01/full-template-prompt.md'
def ref(p):
 p=Path(p);return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def dump(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def tokens(row):return [x for x in re.split(r'-+',row.split('|',1)[1]) if x and x!='|']
def main():
 start=datetime.datetime.now(datetime.timezone.utc);timer=time.perf_counter()
 assert ref(OLD/'packet.jsonl')['sha256']=='69b33bce2774d40818de5a4be63dc00ea75a1a3c50938472c0e553e7a443db72'
 assert ref(PROMPT)['sha256']=='84082165bc156d94f567e389eb5ce48db2ef2e60c0761f85c9b698f6992a7b6f'
 if OUT.exists() or RES.exists():raise FileExistsError('Fresh output roots required')
 raw=(OLD/'packet.jsonl').read_text().splitlines(keepends=True);rs=[json.loads(x) for x in raw];assert len(rs)==62
 txt,pdf=[{k:v for k,v in x.items() if k!='locator'} for x in rs[0]['source_refs'][:2]]
 assert ref(ROOT/txt['path'])==txt and ref(ROOT/pdf['path'])==pdf
 lines=(ROOT/txt['path']).read_text().splitlines()
 assert 'r = rest; = = held tone.' in '\n'.join(lines[:32])
 with pdfplumber.open(ROOT/pdf['path']) as d:pages={n:d.pages[n-1].extract_text() for n in range(1,6)}
 for phrase in ['Play the call alone and sing the desired answer target.',
   'Count one full silent bar, then play the response.',
   'Reduce the gap to the written barline without losing the phrase boundary.',
   'Replay the pair with the opposite pick start for every actual attack.',
   'Replace only the final response note; keep the rhythm and opening unchanged.',
   'Record all five pairs and identify whether the answer sounds related or merely adjacent.']:
  assert phrase in ' '.join(pages[5].split()),phrase
 checks=6;counts={'sounding_events':0,'picked_excitation_groups':0,'unpicked_arrivals':0,'holds':0,'rest_slots':0};audit=[]
 for index,r in enumerate(rs[:5],1):
  before=copy.deepcopy(r);page=r['source_refs'][1]['locator']['physical_pages'][0]
  loc=r['source_refs'][0]['locator'];assert lines[loc['line_start']-1:loc['line_end']]==r['source_payload']['exact_unit_lines'];checks+=1
  pdfrows={label:[tokens(row) for row in re.findall(label+r'\|[^\s]+',pages[page])] for label in ('Nte','Atk')}
  for bar in (1,2):
   slots=[x for x in r['implementation']['symbolic_count_slots'] if x['bar']==bar]
   line=slots[0]['source_count_line'];assert len(slots)==8
   assert tokens(lines[line])==[s['note'] for s in slots]
   assert tokens(lines[line+4])==[s['attack_mark'] for s in slots]
   assert [s['note'] for s in slots] in pdfrows['Nte']
   assert [s['attack_mark'] for s in slots] in pdfrows['Atk'];checks+=4
  action=build(r);protocol=practice(r)
  r['implementation']['symbolic_action_segments']=action
  r['implementation']['local_pair_practice_protocol']=protocol
  r['implementation']['source_gate_rule']=action['source_gate_constraint']
  r['source_refs'].append({**pdf,'locator':{'physical_pages':[5],'heading':'LOCAL-PAIR PRACTICE PROTOCOL and AUDIT'}})
  r['provenance']['symbolic_action_supplement']={'previous_packet':ref(OLD/'packet.jsonl'),
    'producer':ref(Path(__file__)),'transducer':ref(Path(__file__).with_name('actions.py')),
    'independent_review':False,'source_originals':[txt,pdf]}
  assert r['status']==before['status'] and r['timing_authority']==before['timing_authority']
  assert r['unresolved_reasons']==before['unresolved_reasons']
  assert r['implementation']['ordered_contacts']==before['implementation']['ordered_contacts']
  assert r['implementation']['sounding_events']==before['implementation']['sounding_events'];checks+=4
  for k,v in action['counts'].items():counts[k]+=v
  audit.append({'row':index,'package_key':r['package_key'],'source_identity':r['source_identity'],
     'source_sounding_events':len(r['implementation']['sounding_events']),'actions':len(action['actions']),
     'original_contacts_and_timing_unchanged':True,'status_unchanged':True,'counts':action['counts']})
 assert counts['sounding_events']==57 and counts['picked_excitation_groups']==38
 assert sum(len(r['implementation']['symbolic_action_segments']['actions']) for r in rs[:5])==80
 OUT.mkdir();RES.mkdir()
 dump(OUT/'original-module-a-guidance.json',{'original_pdf':pdf,'original_txt':txt,
   'pages':pages,'extraction':'Original physical-page text; no raster/visual review claimed'})
 with (OUT/'packet.jsonl').open('x') as f:
  for i,r in enumerate(rs):f.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' if i<5 else raw[i])
 reread=(OUT/'packet.jsonl').read_text().splitlines(keepends=True);assert reread[5:]==raw[5:]
 context=json.loads((OLD/'level-source-context.json').read_text());context['module_a_symbolic_actions']={
   'source':ref(OUT/'original-module-a-guidance.json'),'rows':[1,2,3,4,5],
   'silent_bar_rehearsal_is_separate_from_written_pair':True,'shuffle_ratio_selected':False}
 dump(OUT/'level-source-context.json',context);dump(OUT/'remaining-keys.json',[])
 dump(OUT/'changed-key-audit.json',audit)
 info={'status':'PASS','source_checks':checks,'changed_rows':[1,2,3,4,5],'unchanged_record_bytes':57,
   'source_counts':counts,'symbolic_slots':80,'added_practice_protocols':5,
   'rehearsal_silent_bars_per_pair':1,'added_printed_original_bars':0,'readiness_change':0,
   'new_independent_native_integrated_accepted':0}
 dump(RES/'semantic-checks.json',info)
 previous=json.loads((ROOT/f'Results/{LANE}/level048-r05/seal.json').read_text());inputs={x['path']:x for x in previous['source_inputs']}
 for p in [OLD/'packet.jsonl',OLD/'level-source-context.json',PROMPT,Path(__file__),Path(__file__).with_name('actions.py'),OUT/'original-module-a-guidance.json',OUT/'changed-key-audit.json']:
  z=ref(p);inputs[z['path']]=z
 seal={**previous,'started_utc':start.isoformat(),'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'elapsed_seconds':time.perf_counter()-timer,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'packet':ref(OUT/'packet.jsonl'),'context':ref(OUT/'level-source-context.json'),
  'remaining_keys_reference':ref(OUT/'remaining-keys.json'),'source_inputs':list(inputs.values()),
  'targeted_checks':ref(RES/'semantic-checks.json'),
  'command':'Bundled Python -B Tools/fullscope-private-a-r01/level048-symbolic-action-segments-r01/produce.py',
  'limits':'Source symbolic ownership only. Shuffle ratio/numeric onsets/gates/playback remain unselected. No readiness or acceptance increase.'}
 dump(RES/'seal.json',seal)
 (RES/'handoff.md').write_text('# Level48 r06 — five local conversation action contracts\n\n'
  'Materialized80 printed beat/offbeat actions for57 source sounding events:38 picked excitation groups,19 unpicked arrivals,5 held-tone slots and18 rest slots. A hold now names the preceding source event; legato arrivals remain attached to their picked excitation; explicit rests end the source sound. Pitch-transition and scope boundaries are not represented as acoustic noteoffs. The P3/P4 final held notes have no invented post-scope release.\n\n'
  'Allfive pairs retain the complete PDF5 practice protocol, including a separate one-full-silent-bar rehearsal stage, reduction to the written barline, opposite starts only for actual attacks, final-response-note replacement and manual recording/audit duties. The rehearsal schedule adds no printed source bar or sound. No vocal audio, replacement pitch, initial attack-direction vector, observed performance, or recording feature is invented.\n\n'
  'All62 identities and original contact objects remain;57 unrelated rows are byte-identical. Counts remain3manual/21deliberate-choice/38partial. Thesefive remain partial because shuffle ratio/clock and acoustic realization are unselected. No new independent/native/integrated/Accepted. Native/app/GUI/performance checks NOT_RUN.\n')
 print(json.dumps({'packet':seal['packet'],'counts':counts,'runtime_seconds':seal['elapsed_seconds'],'peak_rss_bytes':seal['process_peak_rss_bytes']}))
if __name__=='__main__':main()
