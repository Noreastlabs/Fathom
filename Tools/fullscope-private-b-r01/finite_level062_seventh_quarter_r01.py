"""Six exact seventh routes using the frozen source-quarter contract machinery."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];NAME='finite-level062-seventh-quarter-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME
HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level062_triad_quarter_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b61217a335339a9e37910c83231d84e83b8410a51633f2842035f13aa53669cf'
spec=importlib.util.spec_from_file_location('triad',HELPER);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
compact,rh,sha,pin,checkpin,save,norm=h.compact,h.rh,h.sha,h.pin,h.checkpin,h.save,h.norm
BASE=h.BASE;PACKET=h.PACKET;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level062-triad-quarter-r01/handoff.json';VALIDATOR=h.VALIDATOR
LOCAL='The route repeats the four-note seventh-chord spelling across two octaves. Name every role. The diagonal path may cross two positions, but no non-chord note is added.'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(PREV,'0859c02e53394d95dc16f71fbf605f7b5d156acfe19a3e918f21e18143af6b3d'),(PACKET,'38a89b4de50251a8b2d974ca61c853e70615305ebfd971dff95953fa9c79890b'),(HELPER,'b61217a335339a9e37910c83231d84e83b8410a51633f2842035f13aa53669cf'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa')]
def contract_for(old):
 c=h.contract_for(old);c['schema']='fathom.private-selected-quarter-seventh-route.v1';c['selection']='Introductory quarter-note seventh route, source default strict alternate; one explicit producer-selected start stroke and one pass.';c['metric_end_q']=[16,1];c['source_rules']['local']['exact_text']=LOCAL
 c['steps'][0]['event_orders']=list(range(1,17));s=c['steps'][2];s['action']='perform_one_selected_quarter_seventh_route';s['event_orders']=list(range(1,17));s['repeat_highest_event_orders']=[8,9];s['source']['exact_local_rule']=LOCAL;s['no_inserted_nonchord_notes']=True
 return c
def selection(c,request):
 assert isinstance(request,dict) and set(request)=={'package_key','contract_sha256','start_stroke'},'SELECTION_FIELDS'
 assert request['package_key']==c['package_key'] and request['contract_sha256']==rh(c),'SELECTION_IDENTITY'
 assert type(request['start_stroke']) is str and request['start_stroke'] in ['D','U'],'EXPLICIT_START_REQUIRED'
 first=request['start_stroke'];return {'package_key':c['package_key'],'contract_sha256':rh(c),'event_picks':[first,'U' if first=='D' else 'D']*8,'repeat_count':1,'runtime_admitted':False,'grants_credit':False}
def verify(old,new):
 stripped=copy.deepcopy(new);c=stripped['implementation'].pop('selected_quarter_contract');assert c==contract_for(old),'COMPLETE_CONTRACT';stripped['implementation']['kind']=old['implementation']['kind'];stripped['timing_authority']=old['timing_authority'];ev=stripped['implementation']['events'];assert len(ev)==16,'COUNT'
 for i,e in enumerate(ev):assert e['onset_q']==[i,1] and e.pop('metric_slot_duration_q')==[1,1] and e['duration_q'] is None,'QUARTER_SLOT';e['onset_q']=old['implementation']['events'][i]['onset_q']
 assert stripped==old,'OTHER_FACT_MUTATION'
 t=new['timing_authority'];assert t['fixed_bpm'] is None and t['acoustic_gate'] is None and t['relative_clock']=='Selected introductory source-quarter slots; printed session page 1; no meter or acoustic gate inferred.','CLOCK_AUTHORITY'
def main():
 start=datetime.now(timezone.utc).isoformat();timer=time.monotonic()
 for p,digest in PINS:assert sha(p)==digest,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';OUT.mkdir(parents=True,exist_ok=True);RES.mkdir(parents=True,exist_ok=True)
 index=json.loads(BASE.read_text());prior=json.loads(PREV.read_text());rr=list(map(json.loads,PACKET.read_text().splitlines()));selected=[e for e in index['children'] if e['level']==62 and '/moduleb/' in e['source_identity']];assert len(selected)==6 and [e['line'] for e in selected]==list(range(10,16));refs=rr[9]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());crops={}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={n:pdf.pages[n-1].extract_text(x_tolerance=1) for n in [1,2,5,6]}
  for n,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n)),'PAGE_CONTEXT'
  for e in selected:
   loc=rr[e['line']-1]['implementation']['source_scope']['locator'];crops[e['package_key']]=pdf.pages[loc['physical_page']-1].crop(loc['derived_bbox']).extract_text(x_tolerance=1)
 assert norm(h.SESSION) in norm(pages[1]) and norm(h.PICK) in norm(pages[1])
 for rule in h.SHIFT+['Muted preview: air-pick the route before sounding it.','FAILURE sweep noise, delayed landing, or a visible search for the next string']:assert norm(rule) in norm(pages[2])
 for page in [5,6]:assert norm(LOCAL) in norm(pages[page])
 spec=importlib.util.spec_from_file_location('manual',VALIDATOR);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 rows=[];olds=[];changes=[];locators=[];bad_selections=[];bad_responses=[];selection_count=response_count=0
 for entry in selected:
  old=rr[entry['line']-1];assert rh(old)==entry['record_sha256'] and entry['category']=='implementation_or_interpretation_pending';scope=old['implementation']['source_scope'];crop=crops[entry['package_key']];assert norm(crop)==norm(scope['pdf_excerpt']),'CARD_CUSTODY';label=old['source_payload']['label'];matches=[i for i,s in enumerate(txt) if s==label];assert len(matches)==1;n=matches[0];tg={k:v.replace('|','') for s in txt[n+1:n+11] for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',s)};pg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',crop,re.M)};assert tg==pg,'TXT_PDF_GRID'
  ev=old['implementation']['events'];assert len(ev)==16;sm={6:'E',5:'A',4:'D',3:'G',2:'B',1:'e'}
  for i,e in enumerate(ev):
   col=i*4;assert e['order']==i+1 and e['printed_column']==col and pg['Nte'][col:col+4].strip('-')==e['printed_note'] and pg['Rol'][col:col+4].strip('-')==e['role'] and int(re.match(r'\d+',pg[sm[e['string']]][col:])[0])==e['fret'],'CONTACT'
  contacts=lambda e:tuple(e[k] for k in ['printed_note','role','string','fret']);assert list(map(contacts,ev[:8]))==list(map(contacts,ev[8:]))[::-1],'MIRROR'
  new=copy.deepcopy(old);new['implementation']['kind']='selected_quarter_seventh_route';c=contract_for(old);new['implementation']['selected_quarter_contract']=c
  for i,e in enumerate(new['implementation']['events']):e.update(onset_q=[i,1],metric_slot_duration_q=[1,1])
  new['timing_authority']['relative_clock']='Selected introductory source-quarter slots; printed session page 1; no meter or acoustic gate inferred.';verify(old,new)
  for stroke in ['D','U']:
   req={'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':stroke};assert selection(c,req)['event_picks']==[stroke,'U' if stroke=='D' else 'D']*8;selection_count+=1
  for name,req in [('missing',{}),('wrong_key',{'package_key':'other','contract_sha256':rh(c),'start_stroke':'D'}),('drift',{'package_key':old['package_key'],'contract_sha256':'0'*64,'start_stroke':'D'}),('unset',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':None}),('economy',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'economy'}),('extra',{'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'D','repeat':2})]:
   try:selection(c,req)
   except AssertionError:bad_selections.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('BAD_SELECTION_ACCEPTED')
  for answers,expected in [([],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED'),([{'step':i+1,'response':'acknowledged'} for i in range(4)],'USER_REPORTED_STEPS_FINISHED')]:assert mod.response_state(c,answers)==expected;response_count+=1
  for name,answers in [('unknown_response',[{'step':1,'response':'passed'}]),('wrong_order',[{'step':2,'response':'acknowledged'}]),('bool_step',[{'step':True,'response':'acknowledged'}]),('after_stop',[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
   try:mod.response_state(c,answers)
   except AssertionError:bad_responses.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('BAD_RESPONSE_ACCEPTED')
  rows.append(new);olds.append(old);locators.append({'key':old['package_key'],'txt_lines':[n+1,n+10],'pdf_page':scope['locator']['physical_page'],'bbox':scope['locator']['derived_bbox']});changes.append({'package_key':new['package_key'],'source_identity':new['source_identity'],'base_record_sha256':entry['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':entry['category'],'new_category':'timed_source_event_contract'})
 refusals=[]
 for name,mut in [('wrong_fret',lambda r:r['implementation']['events'][0].update(fret=99)),('lost_repeat',lambda r:r['implementation']['events'].pop(8)),('eighth_clock',lambda r:r['implementation']['events'][1].update(onset_q=[1,2])),('acoustic_duration',lambda r:r['implementation']['events'][0].update(duration_q=[1,1])),('invent_tempo',lambda r:r['timing_authority'].update(fixed_bpm=60)),('lost_destination',lambda r:r['implementation']['selected_quarter_contract']['steps'][2]['destination_tasks'].pop()),('whole_session_claim',lambda r:r['implementation']['selected_quarter_contract'].update(unselected_source_obligations=[])),('triad_end',lambda r:r['implementation']['selected_quarter_contract'].update(metric_end_q=[8,1]))]:
  bad=copy.deepcopy(rows[0]);mut(bad)
  try:verify(olds[0],bad)
  except AssertionError:refusals.append(name)
  else:raise AssertionError('CORRUPTION_ACCEPTED '+name)
 effective={};used=set()
 for ref in index['packets']:
  checkpin(ref)
  for row in map(json.loads,(ROOT/ref['path']).read_text().splitlines()):assert row['package_key'] not in effective;effective[row['package_key']]=row
 chain=[];item=prior
 while True:
  chain.append(item)
  if 'prior_overlay_handoff' not in item:break
  checkpin(item['prior_overlay_handoff']);item=json.loads((ROOT/item['prior_overlay_handoff']['path']).read_text())
 for item in reversed(chain):
  checkpin(item['overlay']);oo=list(map(json.loads,(ROOT/item['overlay']['path']).read_text().splitlines()))
  for d in item['changes']:
   key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];row=oo[d['overlay_line']-1];assert rh(row)==d['overlay_record_sha256'] and row['package_key']==key;effective[key]=row;used.add(key)
 assert len(used)==262
 for d,row in zip(changes,rows):key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];effective[key]=row;used.add(key)
 identity=[[e['package_key'],effective[e['package_key']]['source_identity']] for e in index['children']];assert len(effective)==2133 and len(used)==268 and rh(identity)==index['ordered_identity_sha256'];cats=copy.deepcopy(prior['effective_categories']);cats['implementation_or_interpretation_pending']-=6;cats['timed_source_event_contract']+=6;assert sum(cats.values())==2133
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 for p,digest in PINS:assert sha(p)==digest
 for ref in refs:checkpin(ref)
 save(RES/'targeted-validation.json',{'result':'PASS','source_routes':6,'preserved_contacts':96,'original_txt_pdf_checks':locators,'valid_selections':selection_count,'selection_refusals':bad_selections,'response_checks':response_count,'response_refusals':bad_responses,'content_refusals':refusals,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':1,'status':'Six selected introductory quarter seventh routes complete privately; full session separate; B IN_PROGRESS','start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'strict_semantics':'Follow verified prior chain; fold262 replacements then these6 disjoint exact-key replacements with all input/record guards; refuse missing/duplicate keys.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':268,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:ref[k] for k in ['path','bytes','sha256']} for ref in refs],'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats}))
if __name__=='__main__':main()
