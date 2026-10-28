"""Twelve source triad sweep bursts with required rest and source-bound slower repair."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-triad-sweeps-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-hybrid-sevenths-manual-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'d554393f0e66ddc2bd20eb57773409b85bdc68261077242865ecf60feea0f369')]
LOCAL='Use one continuous pick motion across the three strings, repeat the highest note with the first upstroke, and reverse. The fretting hand releases each completed string before the next attack.'
CAPTION='6-note mirror. Rest after every complete burst.'
FAILURE='Failure signs: the three notes sound together, the pick stops between strings, or the top turnaround is late. Repair with a slower one-way three-note sweep before restoring the mirror.'
SAFETY='Sweep and hybrid practice uses minimum pick depth and relaxed finger extension. Stop for pain or persistent tension.'
def contract(old,data):
 contacts=[{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in old['implementation']['events']]
 return {'schema':'fathom.private-manual-triad-sweep.v1','package_key':old['package_key'],'steps':[
 {'order':1,'action':'set_minimum_pick_depth_relaxed_extension_muting_and_release','physical_pages':[1,2],'safety':SAFETY,'stop_immediately':b.STOP,'muting':b.MUTING,'sequence':['fret','attack','release','next string'],'one_pitch_at_a_time':True,'no_held_mini_barre_unless_printed':True},
 {'order':2,'action':'perform_exact_six_note_continuous_directional_sweep_mirror','ordered_contacts':contacts,'source_rule':LOCAL,'physical_page':data['page'],'repeat_highest_event_orders':[3,4],'release_before_next_attack':True,'numeric_onsets_or_durations':None},
 {'order':3,'action':'rest_after_complete_burst','source_caption':CAPTION,'physical_page':data['page'],'duration':None,'next_requires_manual_acknowledgement':True},
 {'order':4,'action':'user_report_separate_notes_continuous_pick_and_timely_top_turn','failure_rule':FAILURE,'physical_page':data['page'],'automatic_assessment':False}],
 'source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'whole_session_observed':False},'source_required_practice_duty':{'physical_page':20,'full_gate_text':data['gate'],'completed':None},
 'selected_stroke_map':'DDDUUU','additional_opposite_start_pass':None,'both_starts_requirement_for_sweeps':None,
 'response_contract':{'function':'workflow_state','recovery_function':'recovery_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'User reports only, no listening/timing/mastery/credit inference.'},
 'printed_attacks':6,'printed_memberships':6,'fixed_bpm':None,'onsets_q':None,'durations_q':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):assert type(r) is dict and set(r)=={'package_key','contract_sha256'} and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION'
def workflow_state(c,r,answers):
 if r is None:assert answers==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 selection(c,r);state=module(VALIDATOR,'v').response_state(c,answers);return {'state':state,'next_step':c['steps'][len(answers)] if state=='IN_PROGRESS' else None,'performance_observed':False,'grants_credit':False}
def recovery_plan(c,r,answers,direction):
 assert workflow_state(c,r,answers)['state']=='NEEDS_RETRY' and answers[-1]['step']==4,'POST_REST_FAILURE_REQUIRED';assert direction in ['D','U'],'ONE_WAY_DIRECTION';source=c['steps'][1]['ordered_contacts'];piece=source[:3] if direction=='D' else source[3:];assert len(piece)==3 and all(x['pick']==direction for x in piece)
 return {'schema':'fathom.private-triad-sweep-recovery.v1','package_key':c['package_key'],'source_contract_sha256':rh(c),'direction':direction,'steps':[
 {'order':1,'action':'perform_slower_one_way_three_note_sweep','ordered_contacts':piece,'relative_tempo':'slower than the failed mirror practice tempo','numeric_tempo_ratio':None,'release_before_next_attack':True,'source_rule':FAILURE},
 {'order':2,'action':'rest_after_one_way_repair_burst','duration':None,'policy':'Conservative explicit recovery pause; no source-fixed rest length.'},
 {'order':3,'action':'restore_exact_six_note_mirror','ordered_contacts':source,'numeric_clock':None,'release_before_next_attack':True},
 {'order':4,'action':'rest_after_restored_mirror','duration':None,'source_caption':CAPTION},
 {'order':5,'action':'user_report_recovery_without_automatic_measurement','automatic_assessment':False}],
 'repair_attacks_outside_printed_inventory':3,'restored_mirror_practice_attacks_outside_printed_inventory':6,'grants_credit':False}
def recovery_state(c,r,answers,choice,replies):
 assert type(choice) is dict and set(choice)=={'source_contract_sha256','direction'} and choice['source_contract_sha256']==rh(c),'RECOVERY_SELECTION'
 plan=recovery_plan(c,r,answers,choice['direction']);state=module(VALIDATOR,'v').response_state(plan,replies);return {'state':state,'plan':plan,'next_step':plan['steps'][len(replies)] if state=='IN_PROGRESS' else None,'performance_observed':False,'grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_sweep_burst_rest_and_repair';new['implementation']['manual_execution_contract']=contract(old,data);return new
def verify(old,new,data):assert new==make(old,data),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==572 and ops==678
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 34<=x['line']<=45];olds=[eff[x['package_key']] for x in entries];assert len(olds)==12 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 assert SAFETY in norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==1))
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  for pn in [8,9]:
   page=pdf.pages[pn-1].extract_text(x_tolerance=1);assert norm(page)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn)) and LOCAL in norm(page) and FAILURE in norm(page)
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE E -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE F -'))
  for old in olds:
   sc=old['implementation']['source_scope'];page=sc['locator']['physical_page'];assert page in [8,9];raw=pdf.pages[page-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'] and CAPTION in raw;label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9
   ev=old['implementation']['events'];assert len(ev)==6 and [e['pick'] for e in ev]==list('DDDUUU')
   for j,e in enumerate(ev):
    vals={k:s[j*4:j*4+4].strip('-') for k,s in tg.items()};cs=[(b.SM[k],int(x)) for k,x in vals.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[vals[k] for k in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   sig=lambda x:tuple(x[k] for k in ['string','fret','printed_note','role']);assert list(map(sig,ev[:3]))==list(map(sig,ev[3:]))[::-1] and [e['string'] for e in ev]==[ev[0]['string'],ev[0]['string']-1,ev[0]['string']-2,ev[0]['string']-2,ev[0]['string']-1,ev[0]['string']]
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'E'},'literal':literal,'page':page,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':page,'PDF_bbox':sc['locator']['derived_bbox'],'highest_repeated_contact':sig(ev[2])})
 rows=[];changes=[];plans=[];refusals=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];r={'package_key':old['package_key'],'contract_sha256':rh(c)};done=[{'step':i+1,'response':'acknowledged'} for i in range(4)];failed=done[:3]+[{'step':4,'response':'needs_retry'}]
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),(done[:2],'IN_PROGRESS'),(failed,'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  for direction in ['D','U']:
   choice={'source_contract_sha256':rh(c),'direction':direction};rdone=[{'step':i+1,'response':'acknowledged'} for i in range(5)];st=recovery_state(c,r,failed,choice,rdone);assert st['state']=='USER_REPORTED_STEPS_FINISHED';plans.append({'key':old['package_key'],'direction':direction,'plan_sha256':rh(st['plan'])});assert recovery_state(c,r,failed,choice,[])['state']=='IN_PROGRESS';assert recovery_state(c,r,failed,choice,[{'step':1,'response':'stopped'}])['state']=='STOPPED';states+=3
  for label,sr,aa in [('stale',dict(r,contract_sha256='0'*64),[]),('wrong_key',dict(r,package_key='wrong'),[]),('skip_rest',r,[*done[:2],done[3]]),('opposite_start',dict(r,start='U'),[]),('extra_clock',dict(r,bpm=90),[]),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[*failed,{'step':5,'response':'acknowledged'}])]:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  for label,aa,ch,ans in [('no_failure',done,{'source_contract_sha256':rh(c),'direction':'D'},[]),('before_rest',done[:1]+[{'step':2,'response':'needs_retry'}],{'source_contract_sha256':rh(c),'direction':'D'},[]),('wrong_direction',failed,{'source_contract_sha256':rh(c),'direction':'ALT'},[]),('stale_recovery',failed,{'source_contract_sha256':'0'*64,'direction':'D'},[]),('skip_recovery_rest',failed,{'source_contract_sha256':rh(c),'direction':'D'},[{'step':1,'response':'acknowledged'},{'step':3,'response':'acknowledged'}]),('after_recovery_stop',failed,{'source_contract_sha256':rh(c),'direction':'D'},[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
   try:recovery_state(c,r,aa,ch,ans)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('RECOVERY_REFUSAL_FAILED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for i in range(12):
  for label,mut in [('lost_high_repeat',lambda r:r['implementation']['events'][3].update(fret=99)),('alternate_pick',lambda r:r['implementation']['events'][1].update(pick='U')),('invent_rest',lambda r:r['implementation']['manual_execution_contract']['steps'][2].update(duration=1)),('lost_release',lambda r:r['implementation']['manual_execution_contract']['steps'][1].update(release_before_next_attack=False)),('invent_clock',lambda r:r['implementation']['events'][0].update(onset_q=[0,1])),('whole_mastery',lambda r:r['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   bad=copy.deepcopy(rows[i]);mut(bad)
   try:verify(olds[i],bad,data[i])
   except AssertionError:corruptions.append({'key':rows[i]['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==584 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':757,'implementation_or_interpretation_pending':738,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':72,'one_way_repair_plans':plans,'workflow_and_recovery_states':states,'workflow_and_recovery_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2121,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'12 selected triad sweep burst/rest/recovery contracts; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':584,'unique_replaced_children':584,'total_replacement_operations':690,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'states':states,'repairs':len(plans),'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
