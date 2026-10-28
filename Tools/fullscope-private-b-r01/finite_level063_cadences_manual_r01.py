"""Twelve assigned-system cadence contracts, with exact source bars and spellings."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-cadences-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-source-setup-correction-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'b65e03632f2225fe73f56a37c38ab5effd48dc2258c34b00395d1d7219be6764')]
MAJOR='Each key uses three four-note arpeggio bars. The system changes by key, not inside the cadence. Preserve the chord spelling and beat-one target while the right-hand method changes.'
MINOR='The assigned systems follow the same two-key rotation as the major page. Do not allow the sweep or hybrid mechanics to obscure the raised dominant third in F# and C# minor.'
QUALITY='MAKE THE b5 OF ii-m7b5, THE 3 OF V7, AND THE b3 OF i AUDIBLE'
SAFETY='Sweep and hybrid practice uses minimum pick depth and relaxed finger extension. Stop for pain or persistent tension.'
ATLAS='Reduce pick volume until m and a can match it comfortably. Do not solve a weak finger-plucked note by snapping the string or tensing the hand.'
def contract(old,d):
 ev=old['implementation']['events'];cs=[{**{k:e[k] for k in ['order','printed_note','role','string','fret','pick']},'normalized_role':e['role'].lstrip('>'),'accent':e['role'].startswith('>'),'bar':(e['order']-1)//4+1} for e in ev]
 setup={'order':1,'action':'name_chords_roles_beat_one_targets_and_prepare_assigned_system','chords':d['chords'],'assigned_system':d['system'],'bar_event_orders':[[1,2,3,4],[5,6,7,8],[9,10,11,12]],'beat_one_target_orders':[1,5,9],'beat_one_target_notes':[ev[i-1]['printed_note'] for i in [1,5,9]],'muting':b.MUTING,'stop_immediately':b.STOP,'source_rule':MAJOR,'source_page':13}
 if d['minor']:setup['minor_quality_duties']={'source_page':14,'heading':QUALITY,'rule':MINOR,'audible_quality_orders':[2,5,9],'audible_quality_roles':['b5','3','b3'],'audible_quality_notes':[ev[i-1]['printed_note'] for i in [2,5,9]],'additional_accents_invented':False}
 if d['system'] in ['hybrid','sweep']:setup['source_safety_setup']={'physical_page':1,'exact_text':SAFETY,'minimum_pick_depth_required':True,'relaxed_finger_extension_required':True}
 if d['system']=='hybrid':setup['source_volume_setup']={'physical_page':2,'exact_text':ATLAS}
 if d['system']=='sweep':setup['source_sweep_release_setup']={'physical_page':2,'exact_text':'no held mini-barre unless printed','do_not_hold_mini_barre_unless_printed':True,'release_before_next_attack':True,'same_string_reattacks':[[a['order'],z['order']] for a,z in zip(ev,ev[1:]) if a['string']==z['string']],'interpretation':'Each printed same-string D is a distinct reattack; do not silently replace with legato or assert one unbroken motion through all four contacts. No physical motion timing is specified.'}
 steps=[setup,{'order':2,'action':'perform_printed_twelve_contact_three_bar_cadence','contacts_from_selection':'printed','ordered_source_contacts':cs,'assigned_system':d['system'],'no_intraphrase_added_rest':True}]
 if d['system']!='sweep':steps.append({'order':3,'action':'perform_global_opposite_start_practice','contacts_from_selection':'opposite','ordered_source_contacts':cs,'source_page':20,'source_rule':b.BOTH,'practice_attacks_outside_printed_inventory':12})
 steps.append({'order':len(steps)+1,'action':'user_report_chord_spelling_targets_quality_and_unchanged_system_through_cadence','automatic_assessment':False})
 return {'schema':'fathom.private-manual-assigned-cadence.v1','package_key':old['package_key'],'steps':steps,'assigned_system':d['system'],'printed_attacks':12,'additional_opposite_practice_attacks':0 if d['system']=='sweep' else 12,'hybrid_direction_policy':'Source P has no printed stroke direction. First P is D then U across the selected passes; each later P direction is an explicit learner choice, not a printed alternation claim.','source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'whole_session_observed':False},'source_required_practice_duty':{'physical_page':20,'full_gate_text':d['gate'],'completed':None},'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'User report only, no detected performance/mastery/credit.'},'onsets_q':None,'durations_q':None,'fixed_bpm':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):
 hybrid=c['assigned_system']=='hybrid';fields={'package_key','contract_sha256'}|({'D_later_P','U_later_P'} if hybrid else set());assert type(r) is dict and set(r)==fields and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION';cs=c['steps'][1]['ordered_source_contacts'];printed=copy.deepcopy(cs);opposite=copy.deepcopy(cs) if c['assigned_system']!='sweep' else None
 if hybrid:
  later=[e['order'] for e in cs if e['pick']=='P' and e['order']!=1];assert later==[2,5,6,9,10]
  for start,seq in [('D',printed),('U',opposite)]:
   ds=r[start+'_later_P'];assert type(ds) is list and len(ds)==5 and all(type(v) is str and v in ['D','U'] for v in ds),'LATER_P_SCHEMA';mapping={1:start,**dict(zip(later,ds))}
   for e in seq:e['pick_direction']=mapping[e['order']] if e['pick']=='P' else None
 elif c['assigned_system']=='cross':
  for e in opposite:e['pick']='U' if e['pick']=='D' else 'D'
 return {'printed':printed,'opposite':opposite,'grants_credit':False}
def workflow_state(c,r,answers):
 if r is None:assert answers==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 chosen=selection(c,r);state=module(VALIDATOR,'v').response_state(c,answers);step=copy.deepcopy(c['steps'][len(answers)]) if state=='IN_PROGRESS' else None
 if step and 'contacts_from_selection' in step:step['selected_contacts']=chosen[step['contacts_from_selection']]
 return {'state':state,'next_step':step,'selection':chosen,'performance_observed':False,'grants_credit':False}
def make(old,d):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=d['locator'];new['source_payload']['txt_excerpt']=d['literal'];new['implementation']['kind']='manual_assigned_system_cadence';new['implementation']['manual_execution_contract']=contract(old,d);return new
def verify(old,new,d):assert new==make(old,d),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'SOURCE_FIELDS_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==600 and ops==738
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 62<=x['line']<=73];olds=[eff[x['package_key']] for x in entries];assert len(olds)==12 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={pn:pdf.pages[pn-1].extract_text(x_tolerance=1) for pn in [13,14]}
  for pn,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn))
  assert MAJOR in norm(pages[13]) and MINOR in norm(pages[14]) and QUALITY in pages[14]
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE H -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE I -'))
  for k,old in enumerate(olds):
   system=['cross','cross','hybrid','hybrid','sweep','sweep'][k%6];minor=k>=6;sc=old['implementation']['source_scope'];pn=sc['locator']['physical_page'];assert pn==(14 if minor else 13);raw=pdf.pages[pn-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'] and f'Assigned system: {system}. 12 tones.' in raw
   key,chords=old['source_payload']['label'].split(' - ',1);head=f'{key} - system {system}: {chords}';hits=[i for i in range(lo,hi) if txt[i]==head];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={s:v.replace('|','') for s,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={s:v.replace('|','') for s,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9 and all(len(v)==48 for v in tg.values())
   ev=old['implementation']['events'];assert len(ev)==12;expected=(list('DUDU') if system=='cross' else list('PPma') if system=='hybrid' else list('DDDD'))*3;assert [e['pick'] for e in ev]==expected
   for j,e in enumerate(ev):
    vals={s:v[4*j:4*j+4].strip('-') for s,v in tg.items()};cs=[(b.SM[s],int(x)) for s,x in vals.items() if s in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[f] for f in ['printed_note','role','pick']]==[vals[f] for f in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   assert [e['order'] for e in ev if e['role'].startswith('>')]==[1,5,9]
   if minor:assert [ev[i-1]['role'].lstrip('>') for i in [2,5,9]]==['b5','3','b3']
   if key=='F# minor':assert ev[4]['printed_note']=='E#'
   if key=='C# minor':assert ev[4]['printed_note']=='B#'
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'H'},'literal':literal,'page':pn,'minor':minor,'chords':chords.split(' -> '),'system':system,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':pn,'PDF_bbox':sc['locator']['derived_bbox'],'assigned_system':system,'chords':d['chords'],'first_beats':[ev[i-1]['printed_note'] for i in [1,5,9]]})
 rows=[];changes=[];plans=[];refusals=[];corruptions=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];base={'package_key':old['package_key'],'contract_sha256':rh(c)}
  requests=[base] if d['system']!='hybrid' else [{**base,'D_later_P':a,'U_later_P':z} for a,z in [(['D']*5,['U']*5),(['U']*5,['D']*5),(list('DUDUD'),list('UDUDU')),(list('UDUDU'),list('DUDUD'))]]
  for r in requests:
   p=selection(c,r);assert len(p['printed'])==12 and [e['order'] for e in p['printed'] if e['accent']]==[1,5,9]
   if d['system']=='hybrid':assert p['printed'][0]['pick_direction']=='D' and p['opposite'][0]['pick_direction']=='U' and all(e['pick_direction'] is None for e in p['printed'] if e['pick']!='P')
   elif d['system']=='cross':assert [e['pick'] for e in p['opposite']]==list('UDUDUDUDUDUD')
   else:assert p['opposite'] is None and [e['pick'] for e in p['printed']]==['D']*12
   plans.append({'key':old['package_key'],'request':r,'plan_sha256':rh(p)})
  r=requests[0];done=[{'step':i+1,'response':'acknowledged'} for i in range(len(c['steps']))]
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  negatives=[('stale',dict(r,contract_sha256='0'*64),[]),('wrong_key',dict(r,package_key='wrong'),[]),('skip_setup',r,[done[1]]),('extra_clock',dict(r,bpm=90),[]),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[done[0],{'step':2,'response':'needs_retry'},done[2]])]
  if d['system']=='hybrid':negatives += [('short_directions',dict(r,D_later_P=['D']*4),[]),('finger_substitute',dict(r,U_later_P=['m']*5),[]),('omit_opposite',r,[*done[:2],done[3]])]
  if d['system']=='cross':negatives += [('omit_opposite',r,[*done[:2],done[3]])]
  for label,sr,aa in negatives:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  muts=[('fret',lambda x:x['implementation']['events'][0].update(fret=99)),('printed_accidental',lambda x:x['implementation']['events'][4].update(printed_note='C')),('lost_accent',lambda x:x['implementation']['manual_execution_contract']['steps'][1]['ordered_source_contacts'][0].update(accent=False)),('wrong_system',lambda x:x['implementation']['manual_execution_contract'].update(assigned_system='other')),('clock',lambda x:x['implementation']['events'][0].update(duration_q=[1,1]))]
  if d['minor']:muts.append(('lost_minor_quality',lambda x:x['implementation']['manual_execution_contract']['steps'][0].pop('minor_quality_duties')))
  if d['system']!='cross':muts.append(('lost_safety',lambda x:x['implementation']['manual_execution_contract']['steps'][0].pop('source_safety_setup')))
  for label,mut in muts:
   bad=copy.deepcopy(new);mut(bad)
   try:verify(old,bad,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==612 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':785,'implementation_or_interpretation_pending':710,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':144,'additional_global_opposite_contacts':96,'representative_plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2121,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'12 selected assigned-system three-bar cadence contracts; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':612,'unique_replaced_children':612,'total_replacement_operations':750,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'representative_plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
