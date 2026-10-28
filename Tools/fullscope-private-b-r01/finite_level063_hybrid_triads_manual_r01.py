"""Eight hybrid triad contracts: source P/m/a, explicit later-P choices, and both starts."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,itertools,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('prior',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-hybrid-triads-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-direction-manual-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'189f5de97fee88ae9996b443d38df35ca80be63b767db3db708bcf4e766e6953')]
LOCAL='The note order matches Module A, but the lower voice belongs to the pick and the upper two voices belong to m and a. Keep the hand close to the strings and match every attack in volume.'
VOLUME='Volume test: play P alone, m alone, and a alone. Reduce the strongest attack until all three can produce the same dynamic without strain.'
ATLAS='Reduce pick volume until m and a can match it comfortably. Do not solve a weak finger-plucked note by snapping the string or tensing the hand.'
SYMBOLS={'P':'pick','m':'middle finger','a':'ring finger'}
def source_contacts(old):return [{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in old['implementation']['events']]
def contract(old,data):
 contacts=source_contacts(old)
 return {'schema':'fathom.private-manual-hybrid-triad.v1','package_key':old['package_key'],'steps':[
 {'order':1,'action':'isolate_P_then_m_then_a_and_balance_volume_without_strain','representative_source_contacts':contacts[:3],'minimum_setup_attacks_outside_printed_eight':3,'P_setup_direction':None,'repeat_count':None,'local_volume_rule':{'physical_page':6,'exact_text':VOLUME},'atlas_volume_rule':{'physical_page':2,'exact_text':ATLAS},'muting':b.MUTING,'stop_immediately':b.STOP,'automatic_assessment':False},
 {'order':2,'action':'perform_eight_note_hybrid_roll_with_first_P_D','source_contacts':contacts,'selected_contacts_from':'D_start_plan','source_rule':LOCAL,'physical_page':6},
 {'order':3,'action':'perform_same_hybrid_roll_with_first_P_U','source_contacts':contacts,'selected_contacts_from':'U_start_plan','source_rule':LOCAL,'physical_page':6,'additional_required_practice_attacks_outside_inventory':8},
 {'order':4,'action':'user_report_balanced_pick_fingers_chord_identity_muting_and_both_starts','automatic_assessment':False}],
 'source_symbol_map':SYMBOLS,'both_starts_source':{'physical_page':20,'exact_text':b.BOTH,'required':True},
 'later_P_direction_policy':'The source prints P, not a stroke direction. Event5 direction is an explicit independent learner choice D/U in each pass. Those choices are a private realization, not printed directions or an alternate-picking claim.','source_later_P_direction':None,
 'source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'whole_session_observed':False},'source_required_practice_duty':{'physical_page':20,'full_gate_text':data['gate'],'completed':None},
 'source_error_repair':{'physical_page':20,'symptom':'HYBRID IMBALANCE','instruction':'reduce pick volume; shorten finger motion','action_on_needs_retry':'Stop this selected pass and return to the three-agent volume calibration on an explicit restart; no automatic recovery.'},
 'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'User reports only; no recording, physical performance, mastery or credit inferred.'},
 'printed_attacks':8,'required_second_pass_attacks':8,'minimum_calibration_attacks':3,'fixed_bpm':None,'onsets_q':None,'durations_q':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):
 assert type(r) is dict and set(r)=={'package_key','contract_sha256','D_pass_second_P','U_pass_second_P'},'SELECTION_FIELDS'
 assert r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'SELECTION_IDENTITY'
 assert r['D_pass_second_P'] in ['D','U'] and r['U_pass_second_P'] in ['D','U'],'LATER_P_DIRECTION'
 plans={}
 for start,n in [('D',1),('U',2)]:
  cs=copy.deepcopy(c['steps'][n]['source_contacts'])
  for e in cs:
   e['attack_agent']=SYMBOLS[e['pick']];e['pick_direction']=(start if e['order']==1 else r[start+'_pass_second_P']) if e['pick']=='P' else None
  assert [x['order'] for x in cs if x['pick']=='P']==[1,5]
  plans[start+'_start_plan']=cs
 return {**plans,'directions_are_explicit_learner_choices':True,'grants_credit':False}
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 chosen=selection(c,r);state=module(VALIDATOR,'v').response_state(c,responses);step=copy.deepcopy(c['steps'][len(responses)]) if state=='IN_PROGRESS' else None
 if step and 'selected_contacts_from' in step:step['selected_contacts']=chosen[step['selected_contacts_from']]
 return {'state':state,'next_step':step,'selection':chosen,'performance_observed':False,'grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_hybrid_triad_both_start_choice';new['implementation']['manual_execution_contract']=contract(old,data);return new
def verify(old,new,data):assert new==make(old,data),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'SOURCE_FIELDS_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==556 and ops==662
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 18<=x['line']<=25];olds=[eff[x['package_key']] for x in entries];assert len(olds)==8 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  page=pdf.pages[5].extract_text(x_tolerance=1);assert norm(page)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==6)) and LOCAL in norm(page) and VOLUME in norm(page) and 'P = PICK | m = MIDDLE FINGER | a = RING FINGER' in page
  volume=pdf.pages[1].crop((415,300,750,335)).extract_text(x_tolerance=1);assert ATLAS in norm(volume)
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE C -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE D -'))
  for old in olds:
   sc=old['implementation']['source_scope'];assert sc['locator']['physical_page']==6;raw=pdf.pages[5].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'];label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9
   ev=old['implementation']['events'];assert len(ev)==8 and [e['pick'] for e in ev]==list('PmamPmam')
   for j,e in enumerate(ev):
    v={k:s[j*4:j*4+4].strip('-') for k,s in tg.items()};cs=[(b.SM[k],int(x)) for k,x in v.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[v[k] for k in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   assert [e['string'] for e in ev]==[ev[0]['string'],ev[0]['string']-1,ev[0]['string']-2,ev[0]['string']-1]*2
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'C'},'literal':literal,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_bbox':sc['locator']['derived_bbox'],'printed_agents':[e['pick'] for e in ev]})
 rows=[];changes=[];plans=[];refusals=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];base={'package_key':old['package_key'],'contract_sha256':rh(c)};done=[{'step':i+1,'response':'acknowledged'} for i in range(4)]
  for a,z in itertools.product(['D','U'],repeat=2):
   req={**base,'D_pass_second_P':a,'U_pass_second_P':z};p=selection(c,req)
   for start in ['D','U']:
    cs=p[start+'_start_plan'];assert cs[0]['pick_direction']==start and cs[4]['pick_direction']==req[start+'_pass_second_P'] and all(e['pick_direction'] is None and e['attack_agent']==SYMBOLS[e['pick']] for e in cs if e['pick']!='P') and [e['pick'] for e in cs]==list('PmamPmam')
   plans.append({'key':old['package_key'],'choice':req,'plans_sha256':rh(p)})
  good={**base,'D_pass_second_P':'D','U_pass_second_P':'U'}
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),(done[:2],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED')]:assert workflow_state(c,good,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  assert workflow_state(c,good,done[:1])['next_step']['selected_contacts'][0]['pick_direction']=='D'
  for label,r,aa in [('stale',dict(good,contract_sha256='0'*64),[]),('wrong_key',dict(good,package_key='wrong'),[]),('unresolved_direction',dict(good,D_pass_second_P='P'),[]),('finger_substitution',dict(good,U_pass_second_P='m'),[]),('extra_agent',dict(good,finger='thumb'),[]),('extra_clock',dict(good,bpm=90),[]),('omit_U',good,[*done[:2],done[3]]),('skip_calibration',good,[done[1]]),('after_stop',good,[{'step':1,'response':'stopped'},done[1]]),('after_retry',good,[{'step':1,'response':'needs_retry'},done[1]])]:
   try:workflow_state(c,r,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for i in range(8):
  for label,mut in [('fret',lambda r:r['implementation']['events'][0].update(fret=99)),('source_P_to_D',lambda r:r['implementation']['events'][0].update(pick='D')),('m_to_a',lambda r:r['implementation']['manual_execution_contract']['steps'][1]['source_contacts'][1].update(pick='a')),('false_source_direction',lambda r:r['implementation']['manual_execution_contract'].update(source_later_P_direction='D')),('lost_volume',lambda r:r['implementation']['manual_execution_contract']['steps'][0].pop('atlas_volume_rule')),('false_mastery',lambda r:r['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   bad=copy.deepcopy(rows[i]);mut(bad)
   try:verify(olds[i],bad,data[i])
   except AssertionError:corruptions.append({'key':rows[i]['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==564 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':737,'implementation_or_interpretation_pending':758,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'volume_PDF_crop':{'page':2,'bbox':[415,300,750,335],'text':volume},'printed_contacts':64,'required_U_practice_contacts':64,'minimum_volume_calibration_contacts':24,'plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2125,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'8 selected hybrid triad manual contracts with disclosed later-P learner choices; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':564,'unique_replaced_children':564,'total_replacement_operations':670,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
