"""Six single-string tension-resolution cells: isolated pairs then linked source route."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level059_c_root_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR=b.BASE,b.FOLD,b.VALIDATOR
NAME='finite-level068-tension-pairs-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PACKET=ROOT/'Build/fullscope-private-b-r01/level068-r02/implementation.jsonl';PREV=ROOT/'Results/fullscope-private-b-r01/finite-level067-function-core-manual-r01/handoff.json'
PINS=[(p,h) for p,h in b.PINS if p in [BASE,FOLD,VALIDATOR]]+[(PACKET,'a7f32287a83711b69c47a7dc249f231e47e30718784e6016651c5032de322e2b'),(PREV,'e23fcf3bbede63ab91a8c209f0c4d7cf7e8f1cd97241668ef4a61d1953713fb8')]
SM={'E':6,'A':5,'D':4,'G':3,'B':2,'e':1};TUNING={1:64,2:59,3:55,4:50,5:45,6:40};PC={'A':9,'B':11,'C':0,'D':2,'E':4,'F':5,'G':7,'G#':8}
LOCAL='Each eight-tone cell isolates four two-note resolutions. G natural is a borrowed #9 color; it is not part of A harmonic minor. Play every pair separately before linking the complete cell.'
SCOPE='Every non-chord tone must point to a named E7 or A-minor destination.'
SAFETY='Safety: use slides instead of forced bends on heavy strings; stop for pain or persistent tension.'
MODE='CHORD FIRST, MODE SECOND: THE TENSIONS ARE MEANINGFUL BECAUSE E7 RESOLVES TO A MINOR'
NOTES=['F','E','G','G#','A','G#','C','B'];ROLES=['b9','R','#9*','3','11','3','b13','5'];DEGREES=['b6','5','b7*','7','1','7','b3','2']
def grid(text):return {s:v.replace('|','') for s,v in re.findall(r'^\s*(Nte|Deg|Rol|e|B|G|D|A|E)\|(\S+)',text,re.M) if s not in SM or v.replace('|','').strip('-')}
def contract(old,d):
 ev=copy.deepcopy(old['implementation']['events']);pairs=[]
 for j in range(4):pairs.append({'pair':j+1,'source_orders':[2*j+1,2*j+2],'tension_note':NOTES[j*2],'tension_E7_role':ROLES[j*2],'destination_note':NOTES[j*2+1],'destination_E7_role':ROLES[j*2+1],'borrowed_color':j==1,'ordered_contacts':copy.deepcopy(ev[j*2:j*2+2]),'separation_duration':None})
 steps=[{'order':1,'action':'name_E7_then_mode_and_prepare_borrowed_color_boundary','ordered_naming':['E7','E Phrygian dominant'],'source_atlas_page':2,'source_rule':MODE,'borrowed_G_is_outside_A_harmonic_minor':True,'source_page':5,'exact_context':LOCAL,'source_scope_page':1,'source_scope':SCOPE,'source_safety':SAFETY}]
 for j,p in enumerate(pairs):steps.append({'order':j+2,'action':'name_tension_and_destination_then_play_pair_separately','pair':p['pair'],'tension_note':p['tension_note'],'tension_E7_role':p['tension_E7_role'],'destination_note':p['destination_note'],'destination_E7_role':p['destination_E7_role'],'ordered_contacts':p['ordered_contacts'],'contacts_from_selection':'pair'+str(j+1),'source_page':5,'numeric_gap':None})
 steps += [{'order':6,'action':'link_complete_eight_contact_source_cell','ordered_contacts':ev,'contacts_from_selection':'linked','source_page':5,'exact_context':LOCAL},{'order':7,'action':'report_resolution_hearing_borrowed_color_and_source_safety','required_reports':['four_pairs_practiced_separately_before_linking_reported','named_destinations_heard_reported','borrowed_G_distinguished_from_scale_Gsharp_reported','b9_sharp9_11_b13_distinguished_by_ear_reported','no_forced_bends_and_safety_stop_rule_followed_reported'],'automatic_assessment':False}]
 return {'schema':'fathom.private-manual-tension-pairs-then-linked.v1','package_key':old['package_key'],'single_string':ev[0]['string'],'pairs':pairs,'steps':steps,'printed_contacts':8,'additional_isolated_pair_practice_contacts':8,'source_R_role_means_root_not_rest':True,'selected_picking':'Alternation chosen by learner D/U; no local source picking mandate inferred.','source_fixed_fingers':None,'numeric_clock':None,'fixed_bpm':None,'source_full_book_mastery':{'page':20,'exact_full_page':d['gate'],'completed':None,'two_clean_days_observed':None},'runtime_admitted':False,'grants_credit':False,'response_contract':{'function':'workflow_state','base_validator':pin(VALIDATOR),'meaning':'Names, sound, safety and playing are manual declarations; no acoustic/physical certification or credit.'}}
def selection(c,r):
 assert type(r)is dict and set(r)=={'package_key','contract_sha256','start_stroke'} and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION';assert r['start_stroke'] in ['D','U'],'START';out={}
 for j,p in enumerate(c['pairs']):out['pair'+str(j+1)]=copy.deepcopy(p['ordered_contacts'])
 out['linked']=copy.deepcopy(c['steps'][5]['ordered_contacts'])
 for cs in out.values():
  for j,e in enumerate(cs):e['selected_pick']='D' if (j%2==0)==(r['start_stroke']=='D') else 'U'
 return out
def done_responses(c):return [{'step':1,'response':'acknowledged','ordered_naming':['E7','E Phrygian dominant'],'G_natural_is_borrowed_reported':True,'source_safety_prepared_reported':True}]+[{'step':j+2,'response':'acknowledged','pair':p['pair'],'tension_note':p['tension_note'],'tension_E7_role':p['tension_E7_role'],'destination_note':p['destination_note'],'destination_E7_role':p['destination_E7_role'],'named_then_played_separately_reported':True} for j,p in enumerate(c['pairs'])]+[{'step':6,'response':'acknowledged','linked_cell_played_reported':True},{'step':7,'response':'acknowledged',**dict.fromkeys(c['steps'][6]['required_reports'],True)}]
def workflow_state(c,r,answers):
 if r is None:
  assert answers==[],'ANSWERS_BEFORE_SELECTION'
  return {'state':'AWAITING_SELECTION','grants_credit':False}
 plan=selection(c,r);assert type(answers)is list and len(answers)<=7,'ANSWERS';bare=[];failed=[];expected=done_responses(c)
 for n,a in enumerate(answers,1):
  assert type(a)is dict and type(a.get('step'))is int and a['step']==n and a.get('response') in ['acknowledged','needs_retry','stopped'],'ORDER'
  if a['response']=='acknowledged':
   want=expected[n-1];assert set(a)==set(want),'RESPONSE_FIELDS'
   for k,v in want.items():
    if type(v)is bool:
     assert type(a[k])is bool,'BOOLEAN'
     if not a[k]:failed.append(n)
    else:assert type(a[k])is type(v) and a[k]==v,'EXACT_RESPONSE_VALUE'
  else:assert set(a)=={'step','response'},'TERMINAL_FIELDS'
  bare.append({k:a[k] for k in ['step','response']})
 state=module(VALIDATOR,'v').response_state(c,bare)
 if failed:assert len(answers)==min(failed),'AFTER_FAILED_REPORT';state='NEEDS_RETRY'
 step=copy.deepcopy(c['steps'][len(answers)]) if state=='IN_PROGRESS' else None
 if step and 'contacts_from_selection' in step:step['selected_contacts']=plan[step['contacts_from_selection']]
 return {'state':state,'next_step':step,'selection':plan,'performance_observed':False,'grants_credit':False}
def make(old,d):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=d['locator'];new['source_payload']['txt_excerpt']=d['literal'];new['source_payload']['source_discrepancy']=[{'class':'exact_txt_pdf_pair_cell_reconciled','previous_diagnostic':old['source_payload'].get('source_discrepancy'),'resolution':'Original PDF5/TXT semantic grid equality; empty string rows/outer barline only normalized. RoleR is sounded E root, not a rest.','TXT':d['locator']}];new['implementation']['kind']='manual_tension_pairs_separately_then_linked';new['implementation']['manual_execution_contract']=contract(old,d);return new
def verify(old,new,d):assert new==make(old,d) and new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'EXACT_CONTRACT'
def main():
 start=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,h in PINS:assert sha(p)==h,'PIN'
 assert not OUT.exists() and not RES.exists(),'OUTPUT_EXISTS';idx,pr,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==761 and ops==899;entries=[x for x in idx['children'] if x['level']==68 and 7<=x['line']<=12];olds=[eff[x['package_key']] for x in entries];assert len(olds)==6 and all(x['package_key']not in used and rh(r)==x['record_sha256'] for x,r in zip(entries,olds));refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  assert len(pdf.pages)==20;pages={n+1:p.extract_text(x_tolerance=1) for n,p in enumerate(pdf.pages)}
  for pn,raw in pages.items():assert norm(raw)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn)),'FULL_BOOK_CONTEXT'
  assert LOCAL in norm(pages[5]) and SCOPE in norm(pages[1]) and SAFETY in norm(pages[1]) and MODE in norm(pages[2]);lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE B -'));hi=next(i for i,t in enumerate(txt) if t.startswith('MODULE C -'))
  for j,old in enumerate(olds):
   label=old['source_payload']['label'];n=next(n for n in range(lo,hi) if txt[n]==label);end=next(k for k in range(n+1,hi) if not txt[k].strip());literal='\n'.join(txt[n:end]);sc=old['implementation']['source_scope'];assert sc['locator']['physical_page']==5;crop=pdf.pages[4].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert crop==sc['pdf_excerpt'];tg=grid(literal);pg=grid(crop);assert tg==pg and len(tg)==4 and all(len(v)==40 for v in tg.values());ev=old['implementation']['events'];assert len(ev)==8
   for z,e in enumerate(ev):
    vals={s:v[z*5:z*5+5].strip('-') for s,v in tg.items()};tab=[(SM[s],int(v)) for s,v in vals.items() if s in SM and v];assert tab==[(e['string'],e['fret'])] and e['string']==[6,4,5,2,3,1][j] and e['order']==z+1 and e['kind']=='note_contact' and e['printed_note']==vals['Nte']==NOTES[z] and e['degree']==vals['Deg']==DEGREES[z] and e['role']==vals['Rol']==ROLES[z] and e['onset_q']is None and e['duration_q']is None and (TUNING[e['string']]+e['fret'])%12==PC[e['printed_note']]
   assert ev[1]['role']=='R' and ev[1]['printed_note']=='E' and ev[1]['kind']=='note_contact';d={'locator':{'line_start':n+1,'line_end':end,'module':'B','label':label},'literal':literal,'gate':pages[20]};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':5,'PDF_bbox':sc['locator']['derived_bbox'],'all8_notes_degrees_E7_roles_contacts_match':True,'R_root_not_rest':True,'borrowed_G_outside_harmonic_minor':True})
 rows=[];changes=[];states=0;plans=[];refusals=[];corruptions=[]
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];done=done_responses(c);rs=[{'package_key':c['package_key'],'contract_sha256':rh(c),'start_stroke':st} for st in ['D','U']]
  for r in rs:
   p=selection(c,r);pairs=[e for k,es in p.items() if k!='linked' for e in es];assert len(pairs)==len(p['linked'])==8 and [e['order'] for e in pairs]==list(range(1,9)) and [e['selected_pick'] for e in p['linked']]==list(('DU' if r['start_stroke']=='D' else 'UD')*4) and [e['selected_pick'] for e in pairs]==[e['selected_pick'] for e in p['linked']];plans.append({'key':c['package_key'],'request':r,'selection_sha256':rh(p)})
  r=rs[0]
  for aa,state in [(done[:z],'IN_PROGRESS') for z in range(7)]+[(done,'USER_REPORTED_STEPS_FINISHED'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  fail=[]
  for n,a in enumerate(done,1):
   for f,v in a.items():
    if type(v)is bool:x=copy.deepcopy(done[:n]);x[-1][f]=False;fail.append((str(n)+f,x))
  for label,a in fail:assert workflow_state(c,r,a)['state']=='NEEDS_RETRY';states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  wrong=copy.deepcopy(done);wrong[0]['ordered_naming'].reverse();role=copy.deepcopy(done);role[1]['destination_E7_role']='rest';borrow=copy.deepcopy(done);borrow[2]['tension_E7_role']='3';nonbool=copy.deepcopy(done);nonbool[1]['pair']=True;combined=copy.deepcopy(done[:6]);combined[0]['source_safety_prepared_reported']=False;combined[-1]['linked_cell_played_reported']=False
  controls=[('stale',dict(r,contract_sha256='0'*64),[]),('wrong_key',dict(r,package_key='other'),[]),('clock',dict(r,bpm=90),[]),('mode_before_chord',r,wrong),('root_as_rest',r,role),('borrowed_color_as_major3',r,borrow),('bool_pair',r,nonbool),('skip_isolated_pairs',r,[done[0],done[5]]),('combined_failed_reports',r,combined),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[done[0],{'step':2,'response':'needs_retry'},done[2]])]+[('after_false_'+label,r,[*a,done[len(a)]]) for label,a in fail if len(a)<7]
  for label,rr,aa in controls:
   try:workflow_state(c,rr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('REFUSAL_FAILED')
  muts=[('fret',lambda x:x['implementation']['events'][0].update(fret=99)),('clock',lambda x:x['implementation']['events'][0].update(duration_q=[1,1])),('root_as_rest',lambda x:x['implementation']['events'][1].update(kind='rest')),('borrowed_G_changed_to_Gsharp',lambda x:x['implementation']['events'][2].update(printed_note='G#')),('lost_isolated_pair',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(2)),('false_source_picking_mandate',lambda x:x['implementation']['manual_execution_contract'].update(selected_picking='Source requires alternate picking')),('false_mastery',lambda x:x['implementation']['manual_execution_contract']['source_full_book_mastery'].update(completed=True))]
  for label,mut in muts:
   bad=copy.deepcopy(new);mut(bad)
   try:verify(old,bad,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key']not in keys]);before=other()
 for d,row in zip(changes,rows):eff[d['package_key']]=row;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==767 and other()==before and rh(identity)==idx['ordered_identity_sha256'] and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':938,'implementation_or_interpretation_pending':557,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,h in PINS:assert sha(p)==h
 for ref in refs:checkpin(ref)
 OUT.mkdir(parents=True);RES.mkdir(parents=True);packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(x)+'\n' for x in rows));save(RES/'targeted-validation.json',{'result':'PASS','all20_original_pages_match_context':True,'page_text_sha256':[{'page':n,'sha256':hashlib.sha256(t.encode()).hexdigest()} for n,t in pages.items()],'source_checks':checks,'printed_contacts':48,'additional_isolated_practice_contacts':48,'selection_plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2127,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'Six manual tension-resolution cells with isolated-pair then linked practice; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-start,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':767,'unique_replaced_children':767,'total_replacement_operations':905,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0});print(compact({'handoff':pin(RES/'handoff.json'),'packet':pin(packet),'categories':cats,'plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
