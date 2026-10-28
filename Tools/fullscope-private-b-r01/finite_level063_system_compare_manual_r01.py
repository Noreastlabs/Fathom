"""Eight same-shape system comparisons, with explicit global opposite-start practice."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,itertools,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-system-compare-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-seventh-sweeps-manual-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'6a866a4f7d89fd2ad3bda6776b3a05ca0c29d7f0a3a1411b678777bd2d442606')]
LOCAL='Each chord receives an eight-note crosspick roll, an eight-note hybrid roll, a six-note down-sweep mirror, and a six-note reverse-sweep mirror. Keep tempo, tone, and chord shape constant.'
CAPTION='28 attacks total; rest after each system.'
SYSTEMS=['CROSSPICK','HYBRID','DOWN SWEEP','UP SWEEP'];LENGTHS=[8,8,6,6];PICKS=[list('DUDUDUDU'),list('PmamPmam'),list('DDDUUU'),list('UUUDDD')]
ATLAS='Reduce pick volume until m and a can match it comfortably. Do not solve a weak finger-plucked note by snapping the string or tensing the hand.'
def contract(old,data):
 ev=old['implementation']['events'];segments=[];offset=0
 for label,n in zip(SYSTEMS,LENGTHS):segments.append({'system':label,'source_event_orders':list(range(offset+1,offset+n+1)),'contacts':[{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in ev[offset:offset+n]]});offset+=n
 steps=[{'order':1,'action':'choose_constant_practice_tempo_tone_and_printed_shape_then_apply_source_muting_volume_stop_duties','source_rule':LOCAL,'physical_pages':[1,2,data['page']],'muting':b.MUTING,'volume_rule':ATLAS,'stop_immediately':b.STOP}]
 for label in SYSTEMS+['CROSSPICK U START','HYBRID U START']:
  steps += [{'order':len(steps)+1,'action':'perform_selected_system','system':label,'contacts_from_selection':label,'constant_tempo_tone_shape':True},{'order':len(steps)+2,'action':'rest_after_system','system':label,'duration':None,'source_caption':CAPTION,'physical_page':data['page']}]
 steps.append({'order':14,'action':'write_manual_comparison_while_reporting_constant_tempo_tone_shape_and_separate_notes','automatic_assessment':False,'no_universal_superior_system_claim':True})
 return {'schema':'fathom.private-manual-four-system-comparison.v1','package_key':old['package_key'],'segments':segments,'steps':steps,'printed_system_order':SYSTEMS,'printed_attacks':28,'additional_global_practice_attacks':16,'global_opposite_start_policy':{'physical_page':20,'exact_text':b.BOTH,'selected_realization':'Append crosspick U-start and hybrid U-start after the four printed systems, with rests. Appended order is private implementation of global practice, not printed Module G order.'},'hybrid_pick_direction_policy':'Initial P uses selected D start in the printed comparison and U start in appended practice. Later P directions are explicit independent learner choices. Printed P/m/a agents remain unchanged.','source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'whole_session_observed':False},'source_required_practice_duty':{'physical_page':20,'full_gate_text':data['gate'],'completed':None},'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'comparison_note':'Nonempty learner-written text on final acknowledgement, not a measured result or grading.'},'note_onsets_durations_q':None,'rest_duration':None,'fixed_bpm':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):
 fields={'package_key','contract_sha256','tempo_label','tone_label','D_hybrid_later_P','U_hybrid_later_P'};assert type(r) is dict and set(r)==fields,'SELECTION_FIELDS';assert r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'SELECTION_IDENTITY'
 for k in ['tempo_label','tone_label']:assert type(r[k]) is str and r[k].strip()==r[k] and r[k],'CONSTANT_SETTING'
 assert r['D_hybrid_later_P'] in ['D','U'] and r['U_hybrid_later_P'] in ['D','U'],'LATER_P_CHOICE'
 plans={s['system']:copy.deepcopy(s['contacts']) for s in c['segments']};plans['CROSSPICK U START']=[{**e,'pick':'U' if e['pick']=='D' else 'D'} for e in plans['CROSSPICK']]
 hybrid=plans['HYBRID'];plans['HYBRID U START']=copy.deepcopy(hybrid)
 for label,start in [('HYBRID','D'),('HYBRID U START','U')]:
  for e in plans[label]:e['pick_direction']=(start if e['order']==9 else r[start+'_hybrid_later_P']) if e['pick']=='P' else None
 return {'plans':plans,'tempo_label':r['tempo_label'],'tone_label':r['tone_label'],'printed_shape_unchanged':True,'grants_credit':False}
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 chosen=selection(c,r);assert type(responses) is list;projected=[]
 for a in responses:
  assert type(a) is dict and {'step','response'}<=set(a),'RESPONSE_FIELDS';note=a['step']==14 and a['response']=='acknowledged';assert set(a)==({'step','response','comparison_note'} if note else {'step','response'}),'COMPARISON_FIELDS'
  if note:assert type(a['comparison_note']) is str and a['comparison_note'].strip(),'WRITTEN_COMPARISON'
  projected.append({k:a[k] for k in ['step','response']})
 state=module(VALIDATOR,'v').response_state(c,projected);step=copy.deepcopy(c['steps'][len(responses)]) if state=='IN_PROGRESS' else None
 if step and 'contacts_from_selection' in step:step['selected_contacts']=chosen['plans'][step['contacts_from_selection']];step['tempo_label']=chosen['tempo_label'];step['tone_label']=chosen['tone_label']
 return {'state':state,'next_step':step,'selection':chosen,'performance_observed':False,'grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_four_system_comparison';new['implementation']['manual_execution_contract']=contract(old,data);return new
def verify(old,new,data):assert new==make(old,data),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'SOURCE_FIELDS_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==592 and ops==698
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 54<=x['line']<=61];olds=[eff[x['package_key']] for x in entries];assert len(olds)==8 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] and cat[x['package_key']]=='implementation_or_interpretation_pending' for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  for pn in [11,12]:
   text=pdf.pages[pn-1].extract_text(x_tolerance=1);assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn)) and LOCAL in norm(text)
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE G -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE H -'));heads={r['source_payload']['label'] for r in olds}
  for old in olds:
   sc=old['implementation']['source_scope'];page=sc['locator']['physical_page'];assert page in [11,12];raw=pdf.pages[page-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'] and CAPTION in raw;label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];end=next((i for i in range(n+1,hi) if txt[i] in heads),hi);block=txt[n:end];assert [x for x in block if x in SYSTEMS]==SYSTEMS
   ev=old['implementation']['events'];assert len(ev)==28;offset=0;segments=[]
   for sys_name,count,expected_picks in zip(SYSTEMS,LENGTHS,PICKS):
    ti=block.index(sys_name);lines=block[ti+1:ti+10];tg={k:v for t in lines for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',t)};rl=raw.splitlines();pi=rl.index(sys_name);pg={k:v for t in rl[pi+1:pi+4] for k,v in re.findall(r'^(Nte|Rol|Pck)\|(.*)$',t)};assert len(tg)==9 and len(pg)==3 and all(tg[k]==v for k,v in pg.items());es=ev[offset:offset+count];assert [e['pick'] for e in es]==expected_picks
    for j,e in enumerate(es):
     vals={k:v[4*j:4*j+4].strip('-') for k,v in tg.items()};cs=[(b.SM[k],int(x)) for k,x in vals.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[vals[k] for k in ['Nte','Rol','Pck']] and e['order']==offset+j+1 and e['onset_q'] is None and e['duration_q'] is None
    segments.append({'system':sys_name,'TXT_line_start':n+ti+2,'contacts':count,'PDF_fields':['Nte','Rol','Pck'],'TXT_only_fields':['string','fret']});offset+=count
   sig=lambda e:tuple(e[k] for k in ['string','fret','printed_note','role']);assert list(map(sig,ev[:8]))==list(map(sig,ev[8:16]));assert list(map(sig,ev[16:19]))==list(map(sig,ev[19:22]))[::-1] and list(map(sig,ev[22:25]))==list(map(sig,ev[25:28]))[::-1];assert set(map(sig,ev[:8]))==set(map(sig,ev[16:]))
   d={'locator':{'line_start':n+1,'line_end':end,'module':'G'},'literal':'\n'.join(block),'page':page,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':page,'PDF_bbox':sc['locator']['derived_bbox'],'segments':segments})
 rows=[];changes=[];plans=[];refusals=[];corruptions=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];base={'package_key':old['package_key'],'contract_sha256':rh(c),'tempo_label':'learner-selected setting A','tone_label':'learner-selected tone A'};done=[{'step':n+1,'response':'acknowledged'} for n in range(14)];done[-1]['comparison_note']='manual comparison supplied by learner fixture; no observed sound'
  for a,z in itertools.product(['D','U'],repeat=2):
   r={**base,'D_hybrid_later_P':a,'U_hybrid_later_P':z};p=selection(c,r);ps=p['plans'];assert [e['pick'] for e in ps['CROSSPICK U START']]==list('UDUDUDUD') and [e['pick'] for e in ps['UP SWEEP']]==list('UUUDDD') and [e['pick_direction'] for e in ps['HYBRID'] if e['pick']=='P']==['D',a] and [e['pick_direction'] for e in ps['HYBRID U START'] if e['pick']=='P']==['U',z];plans.append({'key':old['package_key'],'choice':r,'plan_sha256':rh(p)})
  r={**base,'D_hybrid_later_P':'D','U_hybrid_later_P':'U'}
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),(done[:9],'IN_PROGRESS'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  for label,sr,aa in [('stale',dict(r,contract_sha256='0'*64),[]),('tempo_empty',dict(r,tempo_label=''),[]),('tone_empty',dict(r,tone_label=''),[]),('finger_substitution',dict(r,D_hybrid_later_P='a'),[]),('skip_rest',r,[*done[:2],done[3]]),('omit_opposites',r,[*done[:9],done[13]]),('no_comparison',r,[*done[:13],{'step':14,'response':'acknowledged'}]),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[done[0],{'step':2,'response':'needs_retry'},done[2]]),('invent_clock',dict(r,rest_seconds=1),[])]:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  for label,mut in [('wrong_up_sweep',lambda x:x['implementation']['events'][22].update(pick='D')),('fret',lambda x:x['implementation']['events'][0].update(fret=99)),('lost_rest',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(2)),('clock',lambda x:x['implementation']['manual_execution_contract']['steps'][2].update(duration=1)),('hybrid_agent',lambda x:x['implementation']['events'][9].update(pick='a')),('false_mastery',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   bad=copy.deepcopy(new);mut(bad)
   try:verify(old,bad,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==600 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':773,'implementation_or_interpretation_pending':722,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':224,'additional_global_opposite_contacts':128,'plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2125,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'8 complete selected four-system comparisons and separate global opposite-start practice; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':600,'unique_replaced_children':600,'total_replacement_operations':706,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
