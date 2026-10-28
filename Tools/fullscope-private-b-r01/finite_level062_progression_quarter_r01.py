"""Twelve exact progression routes, source introductory quarter phase; private only."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];NAME='finite-level062-progression-quarter-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME
BASE=ROOT/'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json';PREV=ROOT/'Results/fullscope-private-b-r01/finite-level060-remaining-blocked-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level062-r02/implementation.jsonl'
FOLD=ROOT/'Tools/fullscope-private-b-r01/finite_level062_both_start_duty_r01.py';VALIDATOR=ROOT/'Tools/fullscope-private-b-r01/finite_level051_manual_scans_r01.py';ADOPTION=ROOT/'Results/primary/20260927T1509Z-level062-source-duty-correction-private-adoption.md'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(PREV,'6a881584fa805a7bbb01188ec9d7ebe5483aeccccef19399f5874f515fdd4083'),(PACKET,'38a89b4de50251a8b2d974ca61c853e70615305ebfd971dff95953fa9c79890b'),(FOLD,'f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa'),(ADOPTION,'72b82b777ddf6becdfe605bc932881aab779a3228d7aecfaccefce008a63c2e2')]
SESSION='Choose one diagonal fragment, one string-skip or shift cell, and one progression route. Begin at quarter-note speed. After every long shift, pause the exercise rather than the pulse: the hand relocates during the written duration, and the next note must arrive on time.'
PICK='Strict alternate picking is the default. Economy motion may connect adjacent strings; it may not brush a skipped string.'
SHIFT=['Hear and name the target.','Look at the target fret.','Release excess pressure.','Move thumb and hand together.','Land from the bass side or treble side as printed.','Re-articulate cleanly; no scrape unless / or \\ is marked.']
MAJOR='The master C-major route is transposed on the same string path. The progression begins low, crosses the middle strings on V, and resolves in a higher register on I.'
MINOR='The A-minor master route is transposed on the same string path. Preserve theoretical spellings such as E# in F# minor and B# in C# minor when naming the dominant third.'
MASTERY='Perform all six major and six minor diagonal progression routes.'
CLOCK='Selected introductory source-quarter slots; printed session page 1; no meter or acoustic gate inferred.'
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rh(x):return hashlib.sha256(compact(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def checkpin(r):assert pin(ROOT/r['path'])=={k:r[k] for k in ['path','bytes','sha256']},'INPUT_DRIFT'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(x):return re.sub(r'\s+',' ',x).strip()
def module(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def selection(c,r):
 assert type(r) is dict and set(r)=={'package_key','contract_sha256','start_stroke'},'SELECTION_FIELDS'
 assert r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'SELECTION_IDENTITY'
 assert type(r['start_stroke']) is str and r['start_stroke'] in ['D','U'],'EXPLICIT_START'
 first=r['start_stroke'];return {'package_key':c['package_key'],'contract_sha256':rh(c),'event_picks':[first,'U' if first=='D' else 'D']*6,'repeat_count':1,'runtime_admitted':False,'grants_credit':False}
def contract(old):
 ev=old['implementation']['events'];page=old['implementation']['source_scope']['locator']['physical_page'];major='major:' in old['source_payload']['label'];local=MAJOR if major else MINOR
 key,chords=old['source_payload']['label'].split(': ');chords=chords.split(' -> ');assert len(chords)==3
 groups=[{'order':j+1,'chord':ch,'function':['ii','V','I'][j] if major else ['ii-m7b5','V','i'][j],'event_orders':list(range(j*4+1,j*4+5)),'printed_roles':[e['role'] for e in ev[j*4:j*4+4]],'printed_notes':[e['printed_note'] for e in ev[j*4:j*4+4]]} for j,ch in enumerate(chords)]
 destinations=[]
 for n,e in enumerate(ev):
  prior=ev[n-1] if n else None
  destinations.append({'event_order':n+1,'destination':{k:e[k] for k in ['printed_note','role','string','fret']},'preview':['hear_and_name_note_role_string_fret','look_at_target_fret','locate_next_sounding_string'],'prepare_before':'current-note release' if prior else 'first attack','release_excess_pressure':True,'move_thumb_and_hand_together':True,'land_at_exact_printed_contact':True,'no_unmarked_scrape':True,'skipped_strings':[] if not prior else list(range(min(prior['string'],e['string'])+1,max(prior['string'],e['string']))),'skipped_strings_remain_silent':True,'source_pages':[1,2],'extra_attack_created':False})
 steps=[{'order':1,'action':'name_and_air_pick_complete_printed_progression','event_orders':list(range(1,13)),'key':key,'chord_groups':groups,'source':{'physical_pages':[2,page],'exact_preview':'Muted preview: air-pick the route before sounding it.'}}, {'order':2,'action':'choose_explicit_start_stroke','allowed':['D','U'],'meaning':'User selects the initial stroke to instantiate source default strict alternate. Available options are separate from whole-book required practice duties.'}, {'order':3,'action':'perform_one_introductory_quarter_progression','event_orders':list(range(1,13)),'destination_tasks':destinations,'preserve_pulse':True,'preserve_pick_cycle':True,'source':{'physical_pages':[1,2,page],'session':SESSION,'local':local},'printed_role_emphasis':{'event_orders':[1,5,9],'marker':'>','qualitative_only':True,'velocity':None},'chord_groups':groups,'preserve_theoretical_spelling':True}, {'order':4,'action':'self_report_destination_timing_silent_skips_and_chord_identity','automated_detection':False,'failure_source':{'physical_page':2,'exact_text':'FAILURE sweep noise, delayed landing, or a visible search for the next string'},'remediation_source':{'physical_page':20,'choices':[{'symptom':'skipped string rings','instruction':'Reduce pick depth and mute with both hands.'},{'symptom':'shift arrives late','instruction':'Preview target; move during previous duration.'},{'symptom':'chord identity lost','instruction':'Return to four chord tones in one position.'},{'symptom':'pick cycle resets','instruction':'Air-pick through the shift before sounding it.'}]}}]
 return {'schema':'fathom.private-selected-quarter-progression.v1','package_key':old['package_key'],'selection':'One introductory source-quarter pass of the exact printed12-contact route; strict alternate with an explicit chosen start.','metric_end_q':[12,1],'meter':None,'fixed_bpm':None,'acoustic_gate_q':None,'start_stroke_choices':['D','U'],'starting_stroke_source_requirement':'not established for these progression cards','both_starts_required_by_source':None,'both_starts_requirement_status':'not established for Module F/G; do not infer absence or extend Module A/B mastery clause','source_rules':{'session':{'physical_page':1,'exact_text':SESSION},'picking':{'physical_page':1,'exact_text':PICK},'shift_sequence':{'physical_page':2,'exact_steps':SHIFT},'local':{'physical_page':page,'exact_text':local}},'source_required_practice_duty':{'physical_page':20,'txt_line':868,'exact_pdf_text':MASTERY,'exact_txt_text':'- Perform all six major and all six minor diagonal progression routes.','scope':'All12 progression children, not this one selected pass alone.','completed':None},'steps':steps,'response_contract':{'validator':pin(VALIDATOR),'function':'response_state','allowed_responses':['acknowledged','needs_retry','stopped'],'meaning':'User-reported selected workflow only; never observed playing, correctness, mastery, credit or a saved Attempt.'},'unselected_source_obligations':[{'source_page':1,'instruction':'Whole session also chooses one diagonal fragment and one string-skip or shift cell.','status':'Separate children not selected/completed by this progression.'},{'source_page':1,'instruction':'Economy motion may connect adjacent strings without brushing a skipped string.','status':'Optional source alternative; selected mode here is strict alternate.'},{'source_page':20,'instruction':MASTERY,'status':'All12 route mastery duty remains unobserved; no full-workbook completion inferred.'},{'source_page':20,'instruction':'Remaining ten-phase progression, other mastery clauses, capstones and recovery/bridge duties.','status':'Whole source duties remain outside this single-route selected contract.'}],'automated_assessment':False,'grants_credit':False,'runtime_admitted':False}
def make(old,locator,txt_text):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=locator;new['source_payload']['txt_excerpt']=txt_text
 new['source_payload']['source_discrepancy']=[{'class':'historical_boundary_diagnostic_resolved','previous_diagnostic':old['source_payload']['source_discrepancy'],'resolution':'Exact standalone label and eight score rows exist in original TXT and match the original PDF grid.','txt_locator':locator,'remaining_format_difference':'PDF adds the local12-tone explanatory sentence; it is retained in PDF scope, not attributed to TXT.'}]
 new['implementation']['source_scope']['locator']['supplemental_txt_locator']=locator
 new['implementation']['kind']='selected_quarter_progression';new['implementation']['selected_quarter_contract']=contract(old)
 for n,e in enumerate(new['implementation']['events']):e.update(onset_q=[n,1],metric_slot_duration_q=[1,1])
 new['timing_authority']['relative_clock']=CLOCK
 return new
def verify(old,new,locator,txt_text):
 assert new==make(old,locator,txt_text),'EXACT_SCOPE_SOURCE_CONTRACT'
 ev=new['implementation']['events'];assert len(ev)==12 and [e['order'] for e in ev]==list(range(1,13))
 assert all(e['duration_q'] is None for e in ev) and new['timing_authority']['fixed_bpm'] is None and new['timing_authority']['acoustic_gate'] is None,'NO_INVENTED_CLOCK'
 assert [n+1 for n,e in enumerate(ev) if e['role'].startswith('>')]==[1,5,9],'PRINTED_EMPHASIS'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,s in PINS:assert sha(p)==s,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx=json.loads(BASE.read_text());prior=json.loads(PREV.read_text());rr=list(map(json.loads,PACKET.read_text().splitlines()));selected=[e for e in idx['children'] if e['level']==62 and 40<=e['line']<=51];assert len(selected)==12
 refs=rr[39]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());crops={}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  assert len(pdf.pages)==20;pages={n+1:p.extract_text(x_tolerance=1) for n,p in enumerate(pdf.pages)}
  for n,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n)),'WHOLE_BOOK_CONTEXT'
  for ent in selected:
   loc=rr[ent['line']-1]['implementation']['source_scope']['locator'];crops[ent['package_key']]=pdf.pages[loc['physical_page']-1].crop(loc['derived_bbox']).extract_text(x_tolerance=1)
 for rule in [SESSION,PICK]:assert norm(rule) in norm(pages[1])
 for rule in SHIFT+['Muted preview: air-pick the route before sounding it.','FAILURE sweep noise, delayed landing, or a visible search for the next string']:assert norm(rule) in norm(pages[2])
 for n in [11,12]:assert norm(MAJOR) in norm(pages[n])
 for n in [13,14]:assert norm(MINOR) in norm(pages[n])
 assert MASTERY in norm(pages[20]) and txt[867]=='- Perform all six major and all six minor diagonal progression routes.'
 assert 'Complete all eight diagonal triad fragments and six seventh-chord routes with both pick starts.' in norm(pages[20])
 manual=module(VALIDATOR,'manual');rows=[];olds=[];locators=[];texts=[];changes=[];source_checks=[];badselect=[];badresponse=[];choice_count=response_count=0
 for ent in selected:
  old=rr[ent['line']-1];assert rh(old)==ent['record_sha256'] and ent['category']=='implementation_or_interpretation_pending';crop=crops[ent['package_key']];scope=old['implementation']['source_scope'];assert norm(crop)==norm(scope['pdf_excerpt']),'PDF_CARD_CUSTODY'
  label=old['source_payload']['label'];found=[n for n,s in enumerate(txt) if s==label];assert len(found)==1;n=found[0];text='\n'.join(txt[n:n+9]);locator={'line_start':n+1,'line_end':n+9,'within_document_label':label};pg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',crop,re.M)};tg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',text,re.M)};assert len(pg)==8 and pg==tg,'ORIGINAL_TXT_PDF_SCORE'
  ev=old['implementation']['events'];assert len(ev)==12;sm={6:'E',5:'A',4:'D',3:'G',2:'B',1:'e'}
  for j,e in enumerate(ev):
   col=j*4;assert e['printed_column']==col and e['order']==j+1 and pg['Nte'][col:col+4].strip('-')==e['printed_note'] and pg['Rol'][col:col+4].strip('-')==e['role'] and int(re.match(r'\d+',pg[sm[e['string']]][col:])[0])==e['fret'],'EXACT_CONTACT'
   contacts=[(smkey,int(m[0])) for smkey in ['e','B','G','D','A','E'] if (m:=re.match(r'\d+',pg[smkey][col:col+4]))];assert contacts==[(sm[e['string']],e['fret'])],'EXACT_ONE_CONTACT'
  expected_roles=['>b3','5','b7','R','>3','5','b7','R','>3','5','7','R'] if 'major:' in label else ['>b3','b5','b7','R','>3','5','b7','R','>b3','5','b7','R'];assert [e['role'] for e in ev]==expected_roles,'CHORD_ROLE_SCHEDULE'
  if label.startswith('F# minor:'):assert ev[4]['printed_note']=='E#'
  if label.startswith('C# minor:'):assert ev[4]['printed_note']=='B#'
  new=make(old,locator,text);verify(old,new,locator,text);c=new['implementation']['selected_quarter_contract']
  for stroke in ['D','U']:assert selection(c,{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':stroke})['event_picks']==[stroke,'U' if stroke=='D' else 'D']*6;choice_count+=1
  good={'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'D'}
  for name,request in [('missing',{}),('wrong_key',{**good,'package_key':'other'}),('wrong_hash',{**good,'contract_sha256':'0'*64}),('unset',{**good,'start_stroke':None}),('economy',{**good,'start_stroke':'economy'}),('extra',{**good,'repeat':2})]:
   try:selection(c,request)
   except AssertionError:badselect.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('INVALID_SELECTION_ACCEPTED')
  for answers,status in [([],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED'),([{'step':j+1,'response':'acknowledged'} for j in range(4)],'USER_REPORTED_STEPS_FINISHED')]:assert manual.response_state(c,answers)==status;response_count+=1
  for name,answers in [('unknown',[{'step':1,'response':'passed'}]),('wrong_order',[{'step':2,'response':'acknowledged'}]),('bool_step',[{'step':True,'response':'acknowledged'}]),('after_stop',[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
   try:manual.response_state(c,answers)
   except AssertionError:badresponse.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('INVALID_RESPONSE_ACCEPTED')
  rows.append(new);olds.append(old);locators.append(locator);texts.append(text);source_checks.append({'package_key':old['package_key'],'txt_locator':locator,'pdf_page':scope['locator']['physical_page'],'bbox':scope['locator']['derived_bbox'],'preserved_contacts':12});changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':ent['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':ent['category'],'new_category':'timed_source_event_contract'})
 corruption=[]
 for index in [0,9,10]:
  for name,mut in [('wrong_fret',lambda r:r['implementation']['events'][0].update(fret=99)),('lost_note',lambda r:r['implementation']['events'].pop()),('wrong_slot',lambda r:r['implementation']['events'][1].update(onset_q=[1,2])),('acoustic_gate',lambda r:r['implementation']['events'][0].update(duration_q=[1,1])),('invent_BPM',lambda r:r['timing_authority'].update(fixed_bpm=60)),('lost_destination',lambda r:r['implementation']['selected_quarter_contract']['steps'][2]['destination_tasks'].pop()),('lost_emphasis',lambda r:r['implementation']['selected_quarter_contract']['steps'][2]['printed_role_emphasis'].update(event_orders=[])),('source_absence_claim',lambda r:r['implementation']['selected_quarter_contract'].update(both_starts_required_by_source=False)),('source_complete_claim',lambda r:r['implementation']['selected_quarter_contract']['source_required_practice_duty'].update(completed=True)),('wrong_TXT_line',lambda r:r['source_refs'][0]['locator'].update(line_start=1)),('theoretical_respelling',lambda r:r['implementation']['events'][4].update(printed_note='F')),('R_as_rest',lambda r:r['implementation']['events'][3].update(kind='rest'))]:
   bad=copy.deepcopy(rows[index]);mut(bad)
   try:verify(olds[index],bad,locators[index],texts[index])
   except AssertionError:corruption.append({'package_key':bad['package_key'],'reason':name})
   else:raise AssertionError('CORRUPTION_ACCEPTED '+name)
 fold=module(FOLD,'fold');_,_,effective,catmap,used,ops=fold.fold_chain(BASE,PREV);assert len(used)==341 and ops==379;assert dict(Counter(catmap.values()))==prior['effective_categories']
 keys={x['package_key'] for x in selected};other=lambda:rh([[x['package_key'],rh(effective[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,row in zip(changes,rows):key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];effective[key]=row;catmap[key]=d['new_category'];used.add(key)
 assert other()==before and len(used)==353
 identity=[[x['package_key'],effective[x['package_key']]['source_identity']] for x in idx['children']];assert len(effective)==2133 and rh(identity)==idx['ordered_identity_sha256'];cats=dict(Counter(catmap.values()));assert cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':472,'implementation_or_interpretation_pending':1023,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 for p,s in PINS:assert sha(p)==s
 for ref in refs:checkpin(ref)
 save(RES/'targeted-validation.json',{'result':'PASS','exact_routes':12,'preserved_contacts':144,'chord_groups':36,'all20_pdf_pages_match_context':True,'source_checks':source_checks,'valid_selections':choice_count,'selection_refusals':badselect,'response_checks':response_count,'response_refusals':badresponse,'content_refusals':corruption,'unchanged_other_rows':2121,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'Twelve selected introductory quarter progression contracts complete privately; full session/mastery unobserved; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'strict_semantics':'Fold guarded prior producer chain341 unique/379 operations (including adopted final38 Level62 duty correction, excluding intermediate14), then12 disjoint exact-key replacements; enforce every identity and preimage hash.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':353,'unique_replaced_children':353,'total_replacement_operations':391,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'prior_source_duty_private_adoption':pin(ADOPTION),'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'valid_selections':choice_count,'response_checks':response_count,'content_refusals':len(corruption)}))
if __name__=='__main__':main()
