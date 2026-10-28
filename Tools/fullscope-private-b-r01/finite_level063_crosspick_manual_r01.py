"""Eight source triad crosspicking contracts with mandatory opposite-start practice."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level059_c_root_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'
s=importlib.util.spec_from_file_location('helper',HELPER);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
compact,rh,sha,pin,checkpin,save,norm,module=h.compact,h.rh,h.sha,h.pin,h.checkpin,h.save,h.norm,h.module
BASE,FOLD,VALIDATOR=h.BASE,h.FOLD,h.VALIDATOR
NAME='finite-level063-crosspick-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level061-delayed-workflow-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level063-r02/implementation.jsonl'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(FOLD,'f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa'),(PACKET,'264b657b7993c2eb9417df3271732b7c097fa8605ff9f468840b990c2039adaf'),(PREV,'591d56dc79a924fe3de97b3f71abafa1ebbbae057ceed07e66796e0e02b59670')]
LOCAL='Use strict alternate picking. The pick follows a shallow curved path so both inside and outside string changes remain available. Stop each note when the next string sounds.'
CAPTION='8-note crosspick roll; repeat with the opposite starting stroke.'
SESSION='Choose one crosspicking cell, one hybrid cell, and one sweep burst. Stop before fatigue changes the attack. Rest at least as long as the work interval during endurance training. A faster phrase is not successful if notes overlap, skipped strings ring, or the chord identity disappears.'
MUTING='Fretting hand releases the completed string. Picking-hand palm or spare fingers silence lower strings. The active note should be the only sustained pitch unless a printed pedal tone is intentional.'
STOP='Pain, burning tension, uncontrolled string noise, or a collapsing pick grip ends the set immediately.'
BOTH='Complete all crosspicking and hybrid cells with equal tone and both pick starts.'
SM={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6}
def contract(old,data):
 ev=old['implementation']['events'];ordered=[{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in ev];opposite=[{**e,'pick':'U' if e['pick']=='D' else 'D'} for e in ordered]
 return {'schema':'fathom.private-manual-crosspick-roll.v1','package_key':old['package_key'],'steps':[
 {'order':1,'action':'set_source_muting_and_shallow_curved_alternate_path','source_page':2,'muting_instruction':MUTING,'safety_stop':STOP,'independent_attack_per_note':True,'previous_note_stops_at_next_string':True,'setup_not_extra_printed_attack':True},
 {'order':2,'action':'perform_printed_eight_note_D_start_roll','ordered_contacts':ordered,'source_pages':[data['PDF_page']],'source_rule':LOCAL,'onsets_and_durations_q':None},
 {'order':3,'action':'repeat_identical_contacts_with_U_start','ordered_contacts':opposite,'source_page':data['PDF_page'],'source_caption':CAPTION,'onsets_and_durations_q':None,'additional_practice_attacks_outside_printed_inventory':8},
 {'order':4,'action':'user_report_equal_tone_chord_identity_independent_attacks_and_muting_for_both_starts','automatic_assessment':False}],
 'source_session_duties':{'physical_page':1,'exact_text':SESSION,'other_systems_and_endurance_are_separate_unobserved_duties':True},
 'source_required_practice_duty':{'physical_page':20,'both_starts_exact_text':BOTH,'full_gate_text':data['gate'],'both_starts_required':True,'whole_gate_completed':None},
 'source_error_repair':{'physical_page':20,'symptom':'CROSSPICK STALLS','instruction':'isolate one inside/outside change','implementation':'retry_crossing_pair selects two adjacent contacts from the exact failed D or U pass; no invented loop count, period or measured recovery.'},
 'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'User report only; completion requires both source passes and confers no mastery, Attempt, credit or observed performance.'},
 'printed_attacks':8,'printed_memberships':8,'required_opposite_pass_attacks':8,'fixed_bpm':None,'acoustic_gate':None,'numeric_note_duration':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):
 assert type(r) is dict and set(r)=={'package_key','contract_sha256'} and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION'
 return {'package_key':c['package_key'],'required_passes':['D','U'],'grants_credit':False}
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 selection(c,r);state=module(VALIDATOR,'v').response_state(c,responses)
 return {'state':state,'next_step':c['steps'][len(responses)] if state=='IN_PROGRESS' else None,'stop_instruction':STOP,'performance_observed':False,'grants_credit':False}
def retry_crossing_pair(c,r,responses,pair_start):
 assert workflow_state(c,r,responses)['state']=='NEEDS_RETRY','RETRY_REQUIRED'
 assert responses[-1]['step'] in [2,3],'FAILED_PASS_REQUIRED'
 assert type(pair_start) is int and 1<=pair_start<=7,'PAIR_BOUNDARY'
 contacts=c['steps'][responses[-1]['step']-1]['ordered_contacts'][pair_start-1:pair_start+1]
 assert len(contacts)==2 and contacts[0]['string']!=contacts[1]['string'],'ACTUAL_CROSSING'
 return {'source_step':responses[-1]['step'],'source_event_orders':[pair_start,pair_start+1],'ordered_contacts':contacts,'loop_count':None,'loop_period':None,'numeric_clock':None,'next_user_action':'Practice the selected change or stop; restarting the full contract is an explicit separate selection.','grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['source_payload']['source_discrepancy']=[{'class':'historical_txt_boundary_diagnostic_resolved','previous_diagnostic':old['source_payload']['source_discrepancy'],'resolution':'Module A-qualified original TXT musical grid matches original PDF; PDF-only caption retains PDF attribution.'}];new['implementation']['kind']='manual_crosspick_both_start_roll';new['implementation']['manual_execution_contract']=contract(old,data);return new
def verify(old,new,data):assert new==make(old,data),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'fold').fold_chain(BASE,PREV);assert len(used)==540 and ops==646
 entries=[x for x in idx['children'] if x['level']==63 and 2<=x['line']<=9];olds=[eff[x['package_key']] for x in entries];assert len(olds)==8 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={i+1:p.extract_text(x_tolerance=1) for i,p in enumerate(pdf.pages)};assert len(pages)==20
  for n,t in pages.items():assert norm(t)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n))
  # The original PDF's two-column atlas interleaves text; isolate its muting paragraph by coordinates.
  muting=pdf.pages[1].crop((45,300,410,335)).extract_text(x_tolerance=1)
  assert SESSION in norm(pages[1]) and STOP in norm(pages[2]) and BOTH in norm(pages[20]) and LOCAL in norm(pages[3]) and LOCAL in norm(pages[4])
  assert MUTING in norm(muting),'MUTING_SOURCE'
  gate=norm(pages[20].split('Mastery gate before Level 64\n',1)[1].split('Completion audit and practice log',1)[0]);assert '30 clean seconds with equal rest.' in gate and 'both sixteen-bar capstones' in gate
  lo=txt.index('MODULE A - CROSSPICKED TRIAD ROLLS');hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE B'))
  for old in olds:
   sc=old['implementation']['source_scope'];page=sc['locator']['physical_page'];raw=pdf.pages[page-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'] and CAPTION in raw
   label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9
   ev=old['implementation']['events'];assert len(ev)==8;third='b3' if 'minor' in label else '3';assert [e['role'] for e in ev]==['R',third,'5',third]*2 and [e['pick'] for e in ev]==list('DUDUDUDU')
   for j,e in enumerate(ev):
    col=4*j;v={k:s[col:col+4].strip('-') for k,s in tg.items()};cs=[(SM[k],int(x)) for k,x in v.items() if k in SM and x]
    assert cs==[(e['string'],e['fret'])] and e['printed_note']==v['Nte'] and e['role']==v['Rol'] and e['pick']==v['Pck'] and e['order']==j+1 and e['printed_column']==col and e['onset_q'] is None and e['duration_q'] is None
   assert [e['string'] for e in ev]==[ev[0]['string'],ev[0]['string']-1,ev[0]['string']-2,ev[0]['string']-1]*2
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'A'},'literal':literal,'PDF_page':page,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':page,'PDF_bbox':sc['locator']['derived_bbox'],'printed_contacts':8,'opposite_practice_contacts':8})
 rows=[];changes=[];refusals=[];repairs=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];good={'package_key':old['package_key'],'contract_sha256':rh(c)};done=[{'step':i+1,'response':'acknowledged'} for i in range(4)]
  assert [e['pick'] for e in c['steps'][2]['ordered_contacts']]==list('UDUDUDUD')
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),(done[:2],'IN_PROGRESS'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,good,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  for phase in [2,3]:
   answers=done[:phase-1]+[{'step':phase,'response':'needs_retry'}]
   for boundary in range(1,8):repairs.append({'key':old['package_key'],'phase':phase,'pair_start':boundary,'repair_sha256':rh(retry_crossing_pair(c,good,answers,boundary))})
  for label,r,aa in [('stale',dict(good,contract_sha256='0'*64),[]),('wrong_key',dict(good,package_key='wrong'),[]),('omit_U',good,[*done[:2],done[3]]),('extra_clock',dict(good,bpm=120),[]),('skip_setup',good,[done[1]]),('after_stop',good,[{'step':1,'response':'stopped'},done[1]]),('after_retry',good,[done[0],{'step':2,'response':'needs_retry'},done[2]]),('before_selection',None,[done[0]])]:
   try:workflow_state(c,r,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  for label,aa,b in [('no_failure',done[:2],1),('not_pass_failure',[{'step':1,'response':'needs_retry'}],1),('nonadjacent_boundary',[done[0],{'step':2,'response':'needs_retry'}],8),('bool_boundary',[done[0],{'step':2,'response':'needs_retry'}],True)]:
   try:retry_crossing_pair(c,good,aa,b)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('REPAIR_REFUSAL_FAILED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for i in range(8):
  for label,mut in [('fret',lambda r:r['implementation']['events'][0].update(fret=99)),('opposite_pick',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['ordered_contacts'][0].update(pick='D')),('clock',lambda r:r['implementation']['events'][0].update(duration_q=[1,1])),('both_starts_false',lambda r:r['implementation']['manual_execution_contract']['source_required_practice_duty'].update(both_starts_required=False)),('lost_muting',lambda r:r['implementation']['manual_execution_contract']['steps'][0].update(previous_note_stops_at_next_string=False)),('whole_mastery',lambda r:r['implementation']['manual_execution_contract']['source_required_practice_duty'].update(whole_gate_completed=True))]:
   bad=copy.deepcopy(rows[i]);mut(bad)
   try:verify(olds[i],bad,data[i])
   except AssertionError:corruptions.append({'key':rows[i]['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={e['package_key'] for e in entries};other=lambda:rh([[e['package_key'],rh(eff[e['package_key']])] for e in idx['children'] if e['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[e['package_key'],eff[e['package_key']]['source_identity']] for e in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==548 and other()==before and rh(identity)==idx['ordered_identity_sha256'] and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':721,'implementation_or_interpretation_pending':774,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for r in refs:checkpin(r)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'all20_pages_match_context':True,'PDF_muting_crop':{'page':2,'bbox':[45,300,410,335],'text':muting},'printed_contacts':64,'additional_required_opposite_practice_contacts':64,'workflow_states':states,'crossing_repairs':repairs,'workflow_and_repair_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2125,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'8 complete selected both-start crosspick manual contracts; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':548,'unique_replaced_children':548,'total_replacement_operations':654,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'states':states,'repairs':len(repairs),'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
