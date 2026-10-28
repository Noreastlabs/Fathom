"""Eight selected introductory quarter-note triad fragments; private producer only."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];NAME='finite-level062-triad-quarter-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME
BASE=ROOT/'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json';PREV=ROOT/'Results/fullscope-private-b-r01/finite-level061-delayed-fields-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level062-r02/implementation.jsonl'
VALIDATOR=ROOT/'Tools/fullscope-private-b-r01/finite_level051_manual_scans_r01.py'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(PREV,'16571648f682531f87400b68a8e44e9ea9726a352ffcd9d125252dfdcf3f2026'),(PACKET,'38a89b4de50251a8b2d974ca61c853e70615305ebfd971dff95953fa9c79890b'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa')]
SESSION='Choose one diagonal fragment, one string-skip or shift cell, and one progression route. Begin at quarter-note speed. After every long shift, pause the exercise rather than the pulse: the hand relocates during the written duration, and the next note must arrive on time.'
PICK='Strict alternate picking is the default. Economy motion may connect adjacent strings; it may not brush a skipped string.'
LOCAL='The four-note ascent spells root-third-fifth-root. The repeated highest note keeps the mirror even. Do not let the position change interrupt the pick cycle or the note duration.'
SHIFT=['Hear and name the target.','Look at the target fret.','Release excess pressure.','Move thumb and hand together.','Land from the bass side or treble side as printed.','Re-articulate cleanly; no scrape unless / or \\ is marked.']
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rh(x):return hashlib.sha256(compact(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def checkpin(r):assert pin(ROOT/r['path'])=={k:r[k] for k in ['path','bytes','sha256']},'INPUT_DRIFT'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(x):return re.sub(r'\s+',' ',x).strip()
def selection(contract,request):
 assert isinstance(request,dict) and set(request)=={'package_key','contract_sha256','start_stroke'},'SELECTION_FIELDS'
 assert request['package_key']==contract['package_key'] and request['contract_sha256']==rh(contract),'SELECTION_IDENTITY'
 assert type(request['start_stroke']) is str and request['start_stroke'] in ['D','U'],'EXPLICIT_START_REQUIRED'
 first=request['start_stroke'];second='U' if first=='D' else 'D'
 return {'package_key':contract['package_key'],'contract_sha256':rh(contract),'event_picks':[first if i%2==0 else second for i in range(8)],'repeat_count':1,'runtime_admitted':False,'grants_credit':False}
def contract_for(old):
 ev=old['implementation']['events'];page=old['implementation']['source_scope']['locator']['physical_page'];dest=[]
 for i,e in enumerate(ev):
  prior=ev[i-1] if i else None
  dest.append({'event_order':i+1,'destination':{k:e[k] for k in ['printed_note','role','string','fret']},'prepare_before':'current-note release' if i else 'first attack','source':{'physical_pages':[1,2],'txt_rule':'Name the destination note, role, string, and fret before moving.'},'preview':['hear_and_name','look_at_target_fret','locate_sounding_string'],'relocation_required':None if not prior else (prior['string'],prior['fret'])!=(e['string'],e['fret']),'relocation_actions':['release_excess_pressure','move_thumb_and_hand_together','land_at_exact_destination','rearticulate_without_unmarked_scrape'],'entry_side':'not additionally specified; use printed contact route','skipped_strings':[] if not prior else list(range(min(e['string'],prior['string'])+1,max(e['string'],prior['string']))),'silent_skipped_strings_required':True,'extra_attack_created':False})
 steps=[{'order':1,'action':'name_and_air_pick_printed_route','event_orders':list(range(1,9)),'source':{'physical_page':2,'exact_text':'Muted preview: air-pick the route before sounding it.'}}, {'order':2,'action':'choose_explicit_start_stroke','allowed':['D','U'],'meaning':'Producer choice to instantiate source default alternate cycle; neither start is printed as mandatory.'}, {'order':3,'action':'perform_one_selected_quarter_fragment','event_orders':list(range(1,9)),'destination_tasks':dest,'source':{'physical_pages':[1,2,page],'exact_session_rule':SESSION,'exact_local_rule':LOCAL},'preserve_pulse':True,'preserve_pick_cycle':True,'repeat_highest_event_orders':[4,5]}, {'order':4,'action':'self_report_shift_and_pick_continuity','source':{'physical_page':2,'exact_text':'FAILURE sweep noise, delayed landing, or a visible search for the next string'},'automated_detection':False}]
 return {'schema':'fathom.private-selected-quarter-fragment.v1','package_key':old['package_key'],'selection':'Introductory quarter-note fragment, source default strict alternate; one explicit producer-selected start stroke and one pass.','metric_end_q':[8,1],'meter':None,'fixed_bpm':None,'acoustic_gate_q':None,'start_stroke_choices':['D','U'],'starting_stroke_is_printed':False,'both_starts_required_by_source':False,'source_rules':{'session':{'physical_page':1,'exact_text':SESSION},'picking':{'physical_page':1,'exact_text':PICK},'shift_sequence':{'physical_page':2,'exact_steps':SHIFT},'local':{'physical_page':page,'exact_text':LOCAL}},'steps':steps,'response_contract':{'validator':pin(VALIDATOR),'function':'response_state','allowed_responses':['acknowledged','needs_retry','stopped'],'meaning':'User-reported workflow only; not observed playing, correctness, mastery, credit or a saved Attempt.'},'unselected_source_obligations':[{'source_page':1,'instruction':'Choose one string-skip or shift cell and one progression route for the whole session.','status':'Separate children not selected or completed by this fragment.'},{'source_page':1,'instruction':'Economy motion may connect adjacent strings; it may not brush a skipped string.','status':'Optional alternative not selected; strict alternate only.'}], 'automated_assessment':False,'grants_credit':False,'runtime_admitted':False}
def verify(old,new):
 stripped=copy.deepcopy(new);contract=stripped['implementation'].pop('selected_quarter_contract');assert contract==contract_for(old),'COMPLETE_CONTRACT'
 stripped['implementation']['kind']=old['implementation']['kind'];stripped['timing_authority']=old['timing_authority']
 ev=stripped['implementation']['events'];assert len(ev)==8,'COUNT'
 for i,e in enumerate(ev):
  assert e['onset_q']==[i,1] and e.pop('metric_slot_duration_q')==[1,1] and e['duration_q'] is None,'QUARTER_SLOT'
  e['onset_q']=old['implementation']['events'][i]['onset_q']
 assert stripped==old,'OTHER_FACT_MUTATION'
 t=new['timing_authority'];assert t['fixed_bpm'] is None and t['acoustic_gate'] is None and t['relative_clock']=='Selected introductory source-quarter slots; printed session page 1; no meter or acoustic gate inferred.','CLOCK_AUTHORITY'
def main():
 start=datetime.now(timezone.utc).isoformat();timer=time.monotonic()
 for p,h in PINS:assert sha(p)==h,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS'
 OUT.mkdir(parents=True,exist_ok=True);RES.mkdir(parents=True,exist_ok=True)
 index=json.loads(BASE.read_text());prior=json.loads(PREV.read_text());rr=list(map(json.loads,PACKET.read_text().splitlines()));selected=[e for e in index['children'] if e['level']==62 and '/modulea/' in e['source_identity']];assert len(selected)==8 and [e['line'] for e in selected]==list(range(2,10));refs=rr[1]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());crops={}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={n:pdf.pages[n-1].extract_text(x_tolerance=1) for n in [1,2,3,4]}
  for n,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n)),'PAGE_CONTEXT'
  for e in selected:
   loc=rr[e['line']-1]['implementation']['source_scope']['locator'];crops[e['package_key']]=pdf.pages[loc['physical_page']-1].crop(loc['derived_bbox']).extract_text(x_tolerance=1)
 assert norm(SESSION) in norm(pages[1]) and norm(PICK) in norm(pages[1])
 for rule in SHIFT+['Muted preview: air-pick the route before sounding it.','FAILURE sweep noise, delayed landing, or a visible search for the next string']:assert norm(rule) in norm(pages[2]),'SHIFT_RULE'
 for p in [3,4]:assert norm(LOCAL) in norm(pages[p])
 assert '1. Name the destination note, role, string, and fret before moving.' in txt
 spec=importlib.util.spec_from_file_location('manual',VALIDATOR);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 rows=[];olds=[];changes=[];locators=[];selection_checks=0;response_checks=0;bad_select=[];bad_response=[]
 for entry in selected:
  old=rr[entry['line']-1];assert rh(old)==entry['record_sha256'] and entry['category']=='implementation_or_interpretation_pending';scope=old['implementation']['source_scope'];crop=crops[entry['package_key']];assert norm(crop)==norm(scope['pdf_excerpt']),'CARD_CUSTODY';label=old['source_payload']['label'];lines=[i for i,s in enumerate(txt) if s==label];assert len(lines)==1;n=lines[0];tg={k:v.replace('|','') for s in txt[n+1:n+11] for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',s)};pg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',crop,re.M)};assert tg==pg,'TXT_PDF_GRID'
  ev=old['implementation']['events'];assert len(ev)==8;sm={6:'E',5:'A',4:'D',3:'G',2:'B',1:'e'}
  for i,e in enumerate(ev):
   col=i*5;assert e['order']==i+1 and e['printed_column']==col and pg['Nte'][col:col+5].strip('-')==e['printed_note'] and pg['Rol'][col:col+5].strip('-')==e['role'] and int(re.match(r'\d+',pg[sm[e['string']]][col:])[0])==e['fret'],'CONTACT'
  contact=lambda e:tuple(e[k] for k in ['printed_note','role','string','fret']);assert list(map(contact,ev[:4]))==list(map(contact,ev[4:]))[::-1],'MIRROR'
  new=copy.deepcopy(old);new['implementation']['kind']='selected_quarter_fragment';c=contract_for(old);new['implementation']['selected_quarter_contract']=c
  for i,e in enumerate(new['implementation']['events']):e.update(onset_q=[i,1],metric_slot_duration_q=[1,1])
  new['timing_authority']['relative_clock']='Selected introductory source-quarter slots; printed session page 1; no meter or acoustic gate inferred.'
  verify(old,new)
  for stroke in ['D','U']:
   req={'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':stroke};result=selection(c,req);assert result['event_picks']==([stroke,'U' if stroke=='D' else 'D']*4);selection_checks+=1
  for name,req in [('missing',{}),('wrong_key',{'package_key':'other','contract_sha256':rh(c),'start_stroke':'D'}),('drift',{'package_key':old['package_key'],'contract_sha256':'0'*64,'start_stroke':'D'}),('unset',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':None}),('economy',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'economy'}),('extra',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'D','repeat':2})]:
   try:selection(c,req)
   except AssertionError:bad_select.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('BAD_SELECTION_ACCEPTED')
  for answers,expected in [([],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED'),([{'step':i+1,'response':'acknowledged'} for i in range(4)],'USER_REPORTED_STEPS_FINISHED')]:assert mod.response_state(c,answers)==expected;response_checks+=1
  for name,answers in [('unknown_response',[{'step':1,'response':'passed'}]),('wrong_order',[{'step':2,'response':'acknowledged'}]),('bool_step',[{'step':True,'response':'acknowledged'}]),('after_stop',[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
   try:mod.response_state(c,answers)
   except AssertionError:bad_response.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('BAD_RESPONSE_ACCEPTED')
  rows.append(new);olds.append(old);locators.append({'key':old['package_key'],'txt_lines':[n+1,n+10],'pdf_page':scope['locator']['physical_page'],'bbox':scope['locator']['derived_bbox']});changes.append({'package_key':new['package_key'],'source_identity':new['source_identity'],'base_record_sha256':entry['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':entry['category'],'new_category':'timed_source_event_contract'})
 corruptions=[]
 for name,mut in [('wrong_fret',lambda r:r['implementation']['events'][0].update(fret=99)),('lost_repeat',lambda r:r['implementation']['events'].pop(4)),('eighth_clock',lambda r:r['implementation']['events'][1].update(onset_q=[1,2])),('acoustic_duration',lambda r:r['implementation']['events'][0].update(duration_q=[1,1])),('invent_tempo',lambda r:r['timing_authority'].update(fixed_bpm=60)),('lost_destination',lambda r:r['implementation']['selected_quarter_contract']['steps'][2]['destination_tasks'].pop()),('whole_session_claim',lambda r:r['implementation']['selected_quarter_contract'].update(unselected_source_obligations=[])),('printed_start_claim',lambda r:r['implementation']['selected_quarter_contract'].update(starting_stroke_is_printed=True))]:
  bad=copy.deepcopy(rows[0]);mut(bad)
  try:verify(olds[0],bad)
  except AssertionError:corruptions.append(name)
  else:raise AssertionError('CORRUPTION_ACCEPTED '+name)
 effective={};used=set()
 for ref in index['packets']:
  checkpin(ref)
  for row in map(json.loads,(ROOT/ref['path']).read_text().splitlines()):assert row['package_key'] not in effective;effective[row['package_key']]=row
 chain=[];h=prior
 while True:
  chain.append(h)
  if 'prior_overlay_handoff' not in h:break
  checkpin(h['prior_overlay_handoff']);h=json.loads((ROOT/h['prior_overlay_handoff']['path']).read_text())
 for h in reversed(chain):
  checkpin(h['overlay']);oo=list(map(json.loads,(ROOT/h['overlay']['path']).read_text().splitlines()))
  for d in h['changes']:
   key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];row=oo[d['overlay_line']-1];assert rh(row)==d['overlay_record_sha256'] and row['package_key']==key;effective[key]=row;used.add(key)
 assert len(used)==254
 for d,row in zip(changes,rows):key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];effective[key]=row;used.add(key)
 identity=[[e['package_key'],effective[e['package_key']]['source_identity']] for e in index['children']];assert len(effective)==2133 and len(used)==262 and rh(identity)==index['ordered_identity_sha256'];cats=copy.deepcopy(prior['effective_categories']);cats['implementation_or_interpretation_pending']-=8;cats['timed_source_event_contract']+=8;assert sum(cats.values())==2133
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 for p,h in PINS:assert sha(p)==h
 for ref in refs:checkpin(ref)
 save(RES/'targeted-validation.json',{'result':'PASS','source_cards':8,'preserved_contacts':64,'original_txt_pdf_checks':locators,'explicit_start_selection_checks':selection_checks,'selection_refusals':bad_select,'response_checks':response_checks,'response_refusals':bad_response,'content_refusals':corruptions,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':1,'status':'Eight selected introductory quarter fragments complete privately; full session obligations separate; B IN_PROGRESS','start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'strict_semantics':'Follow verified prior handoff chain; fold254 existing replacements then8 disjoint replacements; check all input and record hashes; refuse missing/duplicate keys.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':262,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:ref[k] for k in ['path','bytes','sha256']} for ref in refs],'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'total_replacements':262}))
if __name__=='__main__':main()
