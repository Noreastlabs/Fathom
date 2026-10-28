"""Four source circuits with explicit manual timed-block and recording-audit progression."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,math,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,PACKET=b.BASE,b.FOLD,b.PACKET
NAME='finite-level063-endurance-manual-r02';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-cadences-manual-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'b2e558b37ac62abce347a3f2ffece0cfd7d6436b0180f236460142a6bdd0b70b')]
LOCAL='Begin with one written circuit. When it is clean, repeat continuously for 15 seconds, then rest 15 seconds. Progress to 30 and 60 seconds only when the final repetition matches the first.'
AUDIT='Record the first and final ten seconds of a timed set. Compare note length, pick noise, finger volume, skipped-string muting, tempo, and chord identity. If the end is worse, the current duration is above the usable endurance limit.'
ADVANCE='Add time before tempo. Add tempo only after the longest current block is clean on two days.'
RESET='Each stage keeps one full-beat rest or full hand release per four bars.'
SAFETY='Sweep and hybrid practice uses minimum pick depth and relaxed finger extension. Stop for pain or persistent tension.'
DIMENSIONS=['note_length','pick_noise','finger_volume','skipped_string_muting','tempo','chord_identity']
REPAIRS={'pick_grip_tightens':'stop; reset thumb/index contact','finger_plucks_snap':'lower pick volume; reduce finger extension','sweep_notes_overlap':'shorten fret duration; one-way burst only','tempo_wavers':'return to one written circuit','muting_degrades':'reduce work interval before tempo'}
STAGES=[(1,15,1,'1 clean set'),(2,15,3,'3 clean sets'),(3,30,2,'2 clean sets'),(4,45,2,'2 clean sets'),(5,60,1,'same tone start to finish')]
def contacts(old):return [{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in old['implementation']['events']]
def contract(old,d):
 cs=contacts(old);num=d['circuit'];opp=num!=3;has_hybrid=num in [2,4];has_sweep=num in [3,4]
 setup={'order':1,'kind':'setup','action':'set_source_muting_stop_work_rest_recording_and_quality_duties','muting':b.MUTING,'stop_immediately':b.STOP,'manual_timer_required':True,'no_automatic_audio_or_elapsed_time_observation':True}
 if has_hybrid or has_sweep:setup['source_safety_setup']={'physical_page':1,'exact_text':SAFETY,'minimum_pick_depth_required':True,'relaxed_finger_extension_required':True}
 if has_hybrid:setup['volume_setup']={'physical_page':2,'instruction':'Reduce pick volume until m and a can match comfortably; never snap or tense to compensate.'}
 if has_sweep:setup['source_sweep_release_setup']={'physical_page':2,'exact_text':'no held mini-barre unless printed','release_before_next_attack':True}
 steps=[setup,{'order':2,'kind':'written','action':'perform_one_written_circuit_and_report_clean','contacts_from':'printed','source_page':15}]
 if opp:steps.append({'order':3,'kind':'written','action':'perform_opposite_start_circuit_as_separate_global_practice','contacts_from':'opposite','source_page':20,'source_rule':b.BOTH})
 for stage,seconds,sets,standard in STAGES:
  for set_index in range(1,sets+1):
   common={'stage':stage,'set':set_index,'source_standard':standard}
   steps += [{'order':len(steps)+1,'kind':'work','action':'repeat_written_circuit_for_manual_work_target','contacts_from':'printed','target_seconds':seconds,'numeric_contact_schedule':None,'number_of_repetitions_or_last_contact_at_deadline':None,'source_page':16,'boundary_action':{'every_four_bars':'full hand release','source_page':16,'exact_text':RESET,'no_fixed_release_duration':True},'recording_target_windows':[[0,10],[seconds-10,seconds]],**common},{'order':len(steps)+2,'kind':'rest','action':'rest_at_least_as_long_as_reported_work','minimum_source_seconds':seconds,'source_pages':[1,15,16],**common},{'order':len(steps)+3,'kind':'audit','action':'compare_first_and_final_ten_seconds_and_report_quality','dimensions':DIMENSIONS,'require_explicit_clean_set_report':True,'source_page':16,'exact_text':AUDIT,**common}]
 steps.append({'order':len(steps)+1,'kind':'finish','action':'acknowledge_selected_duration_ladder_only_no_tempo_or_mastery_promotion'})
 repair_segments=[]
 if has_sweep:
  for offset in (range(0,32,4) if num==3 else range(16,32,4)):
   piece=cs[offset:offset+4];assert len({e['pick'] for e in piece})==1;repair_segments.append({'event_orders':[e['order'] for e in piece],'ordered_contacts':piece,'duration':None})
 return {'schema':'fathom.private-manual-endurance-ladder.v1','package_key':old['package_key'],'circuit':num,'chords':d['chords'],'source_contacts':cs,'source_system_blocks':d['systems'],'steps':steps,'source_rule':LOCAL,'source_stages':[{'stage':s,'work_seconds':sec,'minimum_rest_seconds':sec,'selected_set_count':n,'standard':st,'last_stage_one_set_is_selected_minimum_not_printed_count':s==5} for s,sec,n,st in STAGES],'initial_written_attacks':32,'additional_opposite_practice_attacks':32 if opp else 0,'timed_contact_count':None,'timed_repetition_count':None,'manual_cutoff_note_phase':None,'source_fatigue_repairs':{'physical_page':16,'instructions':REPAIRS,'sweep_one_way_source_segments':repair_segments,'tempo_wavers_reference':'source_contacts: exact one written32-note circuit','reduced_work_interval_seconds':None},'tempo_advance_gate':{'physical_page':16,'exact_text':ADVANCE,'two_clean_days_observed':False,'tempo_advance_authorized':False},'source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'completed':None},'source_required_practice_duty':{'physical_page':20,'full_gate_text':d['gate'],'completed':None},'P_direction_policy':'First P is selected D in printed practice and U in opposite practice. Later P directions are explicit learner choices. Fixed sweep/reverse strokes are preserved; only cross/hybrid starts change in I4.','note_onsets_durations_q':None,'fixed_bpm':None,'grants_credit':False,'runtime_admitted':False}
def selection(c,r):
 hasp=any(e['pick']=='P' for e in c['source_contacts']);fields={'package_key','contract_sha256'}|({'printed_P','opposite_P'} if hasp else set());assert type(r) is dict and set(r)==fields and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION';a=copy.deepcopy(c['source_contacts']);z=copy.deepcopy(a) if c['additional_opposite_practice_attacks'] else None
 if hasp:
  orders=[e['order'] for e in a if e['pick']=='P']
  for label,seq,start in [('printed_P',a,'D'),('opposite_P',z,'U')]:
   ds=r[label];assert type(ds) is list and len(ds)==len(orders) and ds[0]==start and all(type(x) is str and x in ['D','U'] for x in ds),'P_DIRECTIONS';mapping=dict(zip(orders,ds))
   for e in seq:e['pick_direction']=mapping[e['order']] if e['pick']=='P' else None
 if c['circuit']==1:
  for e in z:e['pick']='U' if e['pick']=='D' else 'D'
 elif c['circuit']==4:
  for e in z[:8]:e['pick']='U' if e['pick']=='D' else 'D'
 return {'printed':a,'opposite':z,'grants_credit':False}
def seconds(v):return type(v) in [int,float] and math.isfinite(v) and v>=0

def workflow_state(c,r,answers):
 assert type(answers) is list,'ANSWER_LIST'
 if r is None:assert answers==[],'ANSWERS_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 chosen=selection(c,r);state='IN_PROGRESS';last_work=None;sets=0;records=[];repair=None
 for n,a in enumerate(answers,1):
  assert state=='IN_PROGRESS' and n<=len(c['steps']),'AFTER_TERMINAL';step=c['steps'][n-1];assert type(a) is dict and type(a.get('step')) is int and a['step']==n,'STEP_ORDER'
  if a.get('response')=='stopped':assert set(a)=={'step','response'};state='STOPPED';continue
  kind=step['kind']
  if kind in ['setup','finish']:assert a=={'step':n,'response':'acknowledged'},'ACK_REQUIRED'
  elif kind=='written':
   assert set(a)=={'step','response'} and a['response'] in ['clean','degraded'],'WRITTEN_QUALITY'
   if a['response']=='degraded':state='NEEDS_RETRY';repair=c['source_fatigue_repairs']
  elif kind=='work':
   assert set(a)=={'step','response','reported_seconds','first_recording','final_recording','boundary_release_reported'} and a['response']=='work_reported','WORK_SCHEMA';assert seconds(a['reported_seconds']) and a['reported_seconds']>=step['target_seconds'],'WORK_TARGET';assert a['boundary_release_reported'] is True,'FULL_RELEASE_REQUIRED'
   assert all(type(a[k]) is str and a[k].strip() for k in ['first_recording','final_recording']),'RECORDING_LOCATORS';last_work=a['reported_seconds'];records.append({'stage':step['stage'],'set':step['set'],'user_reported_work_seconds':last_work,'first_window':[0,10],'last_window':[last_work-10,last_work],'overlap_seconds':max(0,20-last_work),'first_locator':a['first_recording'],'final_locator':a['final_recording']})
  elif kind=='rest':assert set(a)=={'step','response','reported_seconds'} and a['response']=='rest_reported' and last_work is not None and seconds(a['reported_seconds']) and a['reported_seconds']>=last_work,'EQUAL_REST_REQUIRED'
  else:
   assert kind=='audit' and set(a)=={'step','response','comparisons','clean_set_reported'} and a['response']=='manual_audit','AUDIT_SCHEMA';assert type(a['comparisons']) is dict and set(a['comparisons'])==set(DIMENSIONS) and all(x in ['same','worse'] for x in a['comparisons'].values()),'QUALITY_DIMENSIONS'
   assert type(a['clean_set_reported']) is bool,'EXPLICIT_CLEAN_SET_REPORT'
   if not a['clean_set_reported'] or 'worse' in a['comparisons'].values():state='NEEDS_RETRY';repair=c['source_fatigue_repairs']
   else:sets+=1
  if n==len(c['steps']) and state=='IN_PROGRESS':state='USER_REPORTED_SELECTED_LADDER_FINISHED'
 next_step=copy.deepcopy(c['steps'][len(answers)]) if state=='IN_PROGRESS' else None
 if next_step and 'contacts_from' in next_step:next_step['selected_contacts']=chosen[next_step['contacts_from']]
 return {'state':state,'next_step':next_step,'reported_clean_timed_sets':sets,'recording_windows':records,'fatigue_repair_guidance':repair,'recordings_or_elapsed_time_observed':False,'performance_observed':False,'grants_credit':False}
def make(old,d):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=d['locator'];new['source_payload']['txt_excerpt']=d['literal'];new['implementation']['kind']='manual_endurance_circuit_ladder';new['implementation']['manual_execution_contract']=contract(old,d);return new
def verify(old,new,d):assert new==make(old,d),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'SOURCE_FIELDS_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==612 and ops==750
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 74<=x['line']<=77];olds=[eff[x['package_key']] for x in entries];assert len(olds)==4 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={pn:pdf.pages[pn-1].extract_text(x_tolerance=1) for pn in [15,16]}
  for pn,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn))
  assert LOCAL in norm(pages[15]) and AUDIT in norm(pages[16]) and ADVANCE in norm(pages[16]) and RESET in norm(pages[16])
  for stage,sec,n,standard in STAGES:assert f'{stage} {sec} sec {sec} sec {standard}' in norm(pages[16]),'SOURCE_STAGE'
  for text in REPAIRS.values():assert text in norm(pages[16]),'REPAIR_SOURCE'
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE I -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE J -'))
  for num,old in enumerate(olds,1):
   sc=old['implementation']['source_scope'];raw=pdf.pages[14].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'];label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+12]);assert txt[n+1].startswith('Chord route: ');chords=txt[n+1][len('Chord route: '):].split(' -> ');assert len(chords)==4 and ' -> '.join(chords) in raw
   tg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9 and all(len(v)==96 for v in tg.values())
   ev=old['implementation']['events'];assert len(ev)==32;patterns={1:[list('DUDUDUDU')]*4,2:[list('PPmamPPa')]*4,3:[list('DDDDUUUU')]*4,4:[list('DUDUDUDU'),list('PPmamPPa'),list('DDDDUUUU'),list('UUUUDDDD')]};assert [e['pick'] for e in ev]==sum(patterns[num],[])
   for j,e in enumerate(ev):
    vals={k:v[3*j:3*j+3].strip('-') for k,v in tg.items()};cs=[(b.SM[k],int(x)) for k,x in vals.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[vals[k] for k in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   d={'locator':{'line_start':n+1,'line_end':n+12,'module':'I'},'literal':literal,'circuit':num,'chords':chords,'systems':patterns[num],'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':15,'PDF_bbox':sc['locator']['derived_bbox'],'chords':chords})
 rows=[];changes=[];refusals=[];corruptions=[];states=0;plans=[]
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];r={'package_key':old['package_key'],'contract_sha256':rh(c)};np=sum(e['pick']=='P' for e in old['implementation']['events'])
  if np:r.update(printed_P=['D']*np,opposite_P=['U']*np)
  plan=selection(c,r);plans.append({'key':old['package_key'],'selection':r,'plan_sha256':rh(plan)})
  if np:
   mixed={**r,'printed_P':['D']+['U' if j%2 else 'D' for j in range(1,np)],'opposite_P':['U']+['D' if j%2 else 'U' for j in range(1,np)]};plans.append({'key':old['package_key'],'selection':mixed,'plan_sha256':rh(selection(c,mixed))})
  if d['circuit']==4:assert plan['printed'][16:]==plan['opposite'][16:],'FIXED_SWEEPS_UNCHANGED'
  done=[]
  for st in c['steps']:
   k=st['kind'];a={'step':st['order']}
   if k in ['setup','finish']:a['response']='acknowledged'
   elif k=='written':a['response']='clean'
   elif k=='work':a.update(response='work_reported',reported_seconds=st['target_seconds'],first_recording='user supplied first-ten segment',final_recording='user supplied final-ten segment',boundary_release_reported=True)
   elif k=='rest':a.update(response='rest_reported',reported_seconds=st['minimum_source_seconds'])
   else:a.update(response='manual_audit',comparisons={k:'same' for k in DIMENSIONS},clean_set_reported=True)
   done.append(a)
  final=workflow_state(c,r,done);assert final['state']=='USER_REPORTED_SELECTED_LADDER_FINISHED' and final['reported_clean_timed_sets']==9 and len(final['recording_windows'])==9 and final['recording_windows'][0]['overlap_seconds']==5;states+=1
  assert workflow_state(c,r,[])['state']=='IN_PROGRESS' and workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=2
  ai=next(i for i,st in enumerate(c['steps']) if st['kind']=='audit');bad=copy.deepcopy(done[:ai+1]);bad[-1]['comparisons']['tempo']='worse';assert workflow_state(c,r,bad)['state']=='NEEDS_RETRY' and workflow_state(c,r,bad)['fatigue_repair_guidance']['instructions']==REPAIRS;states+=1
  assert workflow_state(c,r,[{'step':1,'response':'stopped'}])['state']=='STOPPED';states+=1
  wi=next(i for i,st in enumerate(c['steps']) if st['kind']=='work');ri=wi+1
  unclean=copy.deepcopy(done[:ai+1]);unclean[-1]['clean_set_reported']=False;assert workflow_state(c,r,unclean)['state']=='NEEDS_RETRY' and workflow_state(c,r,unclean)['reported_clean_timed_sets']==0;states+=1
  overrun=copy.deepcopy(done);overrun[wi]['reported_seconds']=16;overrun[ri]['reported_seconds']=16;overrun_state=workflow_state(c,r,overrun);assert overrun_state['state']=='USER_REPORTED_SELECTED_LADDER_FINISHED' and overrun_state['recording_windows'][0]['last_window']==[6,16] and overrun_state['recording_windows'][0]['overlap_seconds']==4;states+=1
  cases=[]
  for label,mut in [('missing_clean_report',lambda a:a[ai].pop('clean_set_reported')),('integer_clean_report',lambda a:a[ai].update(clean_set_reported=1)),('after_unclean',lambda a:a[ai].update(clean_set_reported=False)),('overrun_short_rest',lambda a:a[wi].update(reported_seconds=16)),('short_work',lambda a:a[wi].update(reported_seconds=14)),('short_rest',lambda a:a[ri].update(reported_seconds=14)),('missing_recording',lambda a:a[wi].update(first_recording='')),('missing_release',lambda a:a[wi].update(boundary_release_reported=False)),('bool_seconds',lambda a:a[wi].update(reported_seconds=True)),('nan_seconds',lambda a:a[wi].update(reported_seconds=float('nan'))),('missing_dimension',lambda a:a[ai]['comparisons'].pop('tempo')),('after_degraded',lambda a:a[ai]['comparisons'].update(tempo='worse'))]:
   aa=copy.deepcopy(done);mut(aa);cases.append((label,r,aa))
  cases += [('stale',dict(r,contract_sha256='0'*64),[]),('skip_initial',r,[done[1]]),('invent_note_count',dict(r,timed_notes=128),[]),('after_stop',r,[{'step':1,'response':'stopped'},done[1]])]
  if np:cases += [('wrong_P_count',dict(r,printed_P=['D']*(np-1)),[]),('wrong_start',dict(r,opposite_P=['D']*np),[])]
  for label,sr,aa in cases:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('REFUSAL_FAILED')
  for label,mut in [('fret',lambda x:x['implementation']['events'][0].update(fret=99)),('stage45lost',lambda x:x['implementation']['manual_execution_contract']['source_stages'][3].update(work_seconds=30)),('invent_timed_count',lambda x:x['implementation']['manual_execution_contract'].update(timed_contact_count=64)),('tempo_promotion',lambda x:x['implementation']['manual_execution_contract']['tempo_advance_gate'].update(tempo_advance_authorized=True)),('source_set_count',lambda x:x['implementation']['manual_execution_contract']['source_stages'][4].update(last_stage_one_set_is_selected_minimum_not_printed_count=False)),('mastery',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   aa=copy.deepcopy(new);mut(aa)
   try:verify(old,aa,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==616 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':789,'implementation_or_interpretation_pending':706,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':128,'additional_opposite_practice_contacts':96,'timed_contact_count':None,'selected_timed_sets_per_case':9,'plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2129,'unchanged_other_records_sha256':before,'explicit_clean_set_and_overrun_controls':True,'r01_draft_not_effective':True,'final_input_drift':0,'actual_recording_elapsed_time_audio_quality':'NOT_RUN','native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'4 complete selected manual endurance ladder contracts; numeric note scheduling and actual observations absent; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':616,'unique_replaced_children':616,'total_replacement_operations':754,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
