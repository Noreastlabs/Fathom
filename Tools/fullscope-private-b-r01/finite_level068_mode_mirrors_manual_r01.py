"""Five mode mirrors with three prescribed accent passes and explicit omission choices."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,itertools,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level068_tension_pairs_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='367103ce21e3b967f54c910258882f98c16840357d17d2e39b48a5958230925a'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level068-mode-mirrors-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level068-upper-structures-manual-r01/handoff.json';PROOF=b.RES/'targeted-validation.json'
PINS=[(p,h)for p,h in b.PINS if p!=b.PREV]+[(PREV,'59fb0efeb7d57de2120698d0e8b92a6e6c36e0c2f8733a5fc4113dd5bc0c31b7'),(PROOF,'3e15d81c605eec0c384bb9dd8aefb5d35faf9d1561cb11ee2d7cad70d423d0b4')]
LOCAL='Say the E-relative formula 1-b2-3-4-5-b6-b7-1. Accent G# on the first pass, F and C on the second, and only the E roots on the third.'
VARIATION='Improvisation variation: omit one non-chord tension on each repetition while keeping E, G#, B, and D unchanged.'
FORMULA=['1','b2','3','4','5','b6','b7','1'];NOTES=['E','F','G#','A','B','C','D','E','E','D','C','B','A','G#','F','E'];ROLES=['R','b9','3','11','5','b13','b7','R','R','b7','b13','5','11','3','b9','R'];ACCENTS=[['G#'],['F','C'],['E']];CORE=['E','G#','B','D']
def contract(old,d):
 ev=copy.deepcopy(old['implementation']['events']);passes=[{'pass':j+1,'accent_pitches':pitches,'accent_source_orders':[e['order']for e in ev if e['printed_note']in pitches],'ordered_contacts':copy.deepcopy(ev)}for j,pitches in enumerate(ACCENTS)]
 return {'schema':'fathom.private-manual-E-phrygian-dominant-three-accent-mirrors.v1','package_key':old['package_key'],'spoken_E_relative_formula':FORMULA,'accent_passes':passes,'core_pitches_preserved':CORE,'steps':[{'order':1,'action':'name_E7_function_and_say_E_relative_formula','ordered_names':['E7','E Phrygian dominant'],'E_relative_formula':FORMULA,'source_page':d['page'],'exact_context':LOCAL,'printed_A_harmonic_minor_degrees_are_distinct':True,'source_safety':b.SAFETY}]+[{'order':j+2,'action':'play_complete_mirror_with_prescribed_accent_pass','pass':j+1,'accent_pitches':a['accent_pitches'],'accent_source_orders':a['accent_source_orders'],'contacts_from_selection':'pass'+str(j+1),'source_page':d['page'],'exact_context':LOCAL,'top_E_reattack_source_orders':[8,9]}for j,a in enumerate(passes)]+[{'order':5,'action':'play_selected_nonchord_tension_omission_repetitions','source_page':4,'exact_text':VARIATION,'module_continuation_applies_to_all_five_positions':True,'chosen_policy':'Omit both occurrences of one selected nonchord pitch class F, A or C per repetition; retain all other contacts in their original order.','source_occurrence_policy_and_repetition_count':None,'interface_repetition_bound':[1,8],'selected_bound_not_source_prescription':True,'numeric_clock':None,'fixed_variation_accent':None},{'order':6,'action':'release_and_report_mode_formula_accents_omissions_and_safety','required_reports':['E_relative_formula_spoken_reported','three_required_accent_patterns_heard_reported','upper_E_root_reattacked_reported','selected_tension_omissions_preserved_all_core_contacts_reported','final_E_released_reported','safety_stop_instruction_followed_reported'],'automatic_assessment':False}],'printed_contacts':16,'additional_accent_pass_contacts':32,'variation_contacts_per_selected_repetition':14,'source_fixed_fingers':None,'numeric_clock':None,'fixed_bpm':None,'selected_picking':'D/U alternation is an implementation choice for each pass and repetition, not an added source mandate.','source_full_book_mastery':{'page':20,'exact_full_page':d['gate'],'completed':None,'two_clean_days_observed':None},'runtime_admitted':False,'grants_credit':False,'response_contract':{'function':'workflow_state','base_validator':pin(VALIDATOR),'meaning':'Accents, tension choice, playing, release and safety are manual reports, no observed mastery or credit.'}}
def selection(c,r):
 assert type(r)is dict and set(r)=={'package_key','contract_sha256','start_stroke','omitted_tension_by_repetition'}and r['package_key']==c['package_key']and r['contract_sha256']==rh(c),'EXACT_SELECTION';assert r['start_stroke']in['D','U'],'START';om=r['omitted_tension_by_repetition'];assert type(om)is list and 1<=len(om)<=8 and all(type(x)is str and x in['F','A','C']for x in om),'OMISSION_CHOICES';out={}
 for p in c['accent_passes']:
  cs=copy.deepcopy(p['ordered_contacts'])
  for e in cs:e['selected_accent']=e['order']in p['accent_source_orders']
  out['pass'+str(p['pass'])]=cs
 variations=[]
 for n,pitch in enumerate(om,1):
  cs=[copy.deepcopy(e)for e in c['accent_passes'][0]['ordered_contacts']if e['printed_note']!=pitch];variations.append({'repetition':n,'omitted_pitch_class':pitch,'source_orders':[e['order']for e in cs],'selected_contacts':cs,'selected_accent':None})
 for cs in[*out.values(),*[v['selected_contacts']for v in variations]]:
  for j,e in enumerate(cs):e['selected_pick']='D'if(j%2==0)==(r['start_stroke']=='D')else'U';e['selected_pass_order']=j+1
 out['variations']=variations;return out
def done_responses(c,r):return [{'step':1,'response':'acknowledged','ordered_names':['E7','E Phrygian dominant'],'E_relative_formula':FORMULA,'prepared_reported':True}]+[{'step':j+2,'response':'acknowledged','pass':j+1,'accent_source_orders':a['accent_source_orders'],'exact_mirror_and_accents_played_reported':True}for j,a in enumerate(c['accent_passes'])]+[{'step':5,'response':'acknowledged','omitted_tension_by_repetition':r['omitted_tension_by_repetition'],'selected_repetitions_played_with_core_unchanged_reported':True},{'step':6,'response':'acknowledged',**dict.fromkeys(c['steps'][5]['required_reports'],True)}]
def workflow_state(c,r,answers):
 if r is None:
  assert answers==[],'ANSWERS_BEFORE_SELECTION'
  return {'state':'AWAITING_SELECTION','grants_credit':False}
 plan=selection(c,r);assert type(answers)is list and len(answers)<=6,'ANSWERS';bare=[];failed=[];expected=done_responses(c,r)
 for n,a in enumerate(answers,1):
  assert type(a)is dict and type(a.get('step'))is int and a['step']==n and a.get('response')in ['acknowledged','needs_retry','stopped'],'ORDER'
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
 if step and 'contacts_from_selection'in step:step['selected_contacts']=plan[step['contacts_from_selection']]
 if step and step['order']==5:step['selected_variations']=plan['variations']
 return {'state':state,'next_step':step,'selection':plan,'performance_observed':False,'grants_credit':False}
def make(old,d):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=d['locator'];new['source_payload']['txt_excerpt']=d['literal'];new['source_payload']['source_discrepancy']=[{'class':'exact_mode_mirror_txt_pdf_reconciled','previous_diagnostic':old['source_payload'].get('source_discrepancy'),'resolution':'All sixteen original contacts/degrees/roles match. Three source accent passes implemented; continuation-page omission duty carries explicit choice policy and source unknowns.','TXT':d['locator']}];new['implementation']['kind']='manual_mode_mirror_accents_and_tension_omission';new['implementation']['manual_execution_contract']=contract(old,d);return new
def verify(old,new,d):assert new==make(old,d)and new['implementation']['events']==old['implementation']['events']and new['timing_authority']==old['timing_authority'],'EXACT_CONTRACT'
def main():
 start=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,h in PINS:assert sha(p)==h,'PIN'
 assert not OUT.exists()and not RES.exists(),'OUTPUT_EXISTS';idx,pr,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==791 and ops==929;entries=[x for x in idx['children']if x['level']==68 and 2<=x['line']<=6];olds=[eff[x['package_key']]for x in entries];assert len(olds)==5 and all(x['package_key']not in used and rh(r)==x['record_sha256']for x,r in zip(entries,olds));refs=olds[0]['source_refs'];assert json.loads(PROOF.read_text())['all20_original_pages_match_context']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());pages={x['physical_page']:x['text']for x in ctx['pdf_pages']};data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path'])as pdf:
  for pn in[3,4]:raw=pdf.pages[pn-1].extract_text(x_tolerance=1);assert norm(raw)==norm(pages[pn])and LOCAL in norm(raw)
  assert VARIATION in norm(pages[4]);lo=next(i for i,t in enumerate(txt)if t.startswith('MODULE A -'));hi=next(i for i,t in enumerate(txt)if t.startswith('MODULE B -'))
  for j,old in enumerate(olds):
   label=old['source_payload']['label'];n=next(n for n in range(lo,hi)if txt[n]==label);end=next(k for k in range(n+1,hi)if not txt[k].strip());literal='\n'.join(txt[n:end]);sc=old['implementation']['source_scope'];pn=3 if j<3 else 4;assert sc['locator']['physical_page']==pn;crop=pdf.pages[pn-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert crop==sc['pdf_excerpt'];tg=b.grid(literal);pg=b.grid(crop);assert tg==pg and all(len(v)==64 for v in tg.values());ev=old['implementation']['events'];assert len(ev)==16
   for z,e in enumerate(ev):
    vals={s:v[z*4:z*4+4].strip('-')for s,v in tg.items()};tab=[(b.SM[s],int(v))for s,v in vals.items()if s in b.SM and v];assert tab==[(e['string'],e['fret'])]and e['order']==z+1 and e['kind']=='note_contact'and e['printed_note']==vals['Nte']==NOTES[z]and e['degree']==vals['Deg']and e['role']==vals['Rol']==ROLES[z]and e['onset_q']is None and e['duration_q']is None and(b.TUNING[e['string']]+e['fret'])%12==b.PC[e['printed_note']]
   simp=lambda es:[(e['printed_note'],e['string'],e['fret'])for e in es];assert simp(ev[:8])==list(reversed(simp(ev[8:])));d={'locator':{'line_start':n+1,'line_end':end,'module':'A','label':label},'literal':literal,'gate':pages[20],'page':pn};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':pn,'PDF_bbox':sc['locator']['derived_bbox'],'all16_notes_degrees_roles_contacts_match':True,'mirror_top_root_reattack':True,'full_module_continuation_variation_page':4})
 rows=[];changes=[];states=0;plans=[];refusals=[];corruptions=[];choice_sets=[[x]for x in['F','A','C']]+[list(x)for x in itertools.product(['F','A','C'],repeat=2)]+[['F','A','C','F','A','C','F','A']]
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];rs=[{'package_key':c['package_key'],'contract_sha256':rh(c),'start_stroke':st,'omitted_tension_by_repetition':choice}for choice in choice_sets for st in['D','U']]
  for r in rs:
   p=selection(c,r)
   for j in range(3):es=p['pass'+str(j+1)];assert len(es)==16 and[e['order']for e in es if e['selected_accent']]==[[3,14],[2,6,11,15],[1,8,9,16]][j]and[e['selected_pick']for e in es]==list(('DU'if r['start_stroke']=='D'else'UD')*8)
   for var,pitch in zip(p['variations'],r['omitted_tension_by_repetition']):
    cs=var['selected_contacts'];assert len(cs)==14 and all(e['printed_note']!=pitch for e in cs)and[e['order']for e in cs]==[e['order']for e in old['implementation']['events']if e['printed_note']!=pitch]and[{k:e[k]for k in['order','printed_note','string','fret']}for e in cs if e['printed_note']in CORE]==[{k:e[k]for k in['order','printed_note','string','fret']}for e in old['implementation']['events']if e['printed_note']in CORE]
   assert workflow_state(c,r,done_responses(c,r))['state']=='USER_REPORTED_STEPS_FINISHED';plans.append({'key':c['package_key'],'request':r,'selection_sha256':rh(p)})
  r=rs[0];done=done_responses(c,r)
  for aa,state in[(done[:z],'IN_PROGRESS')for z in range(6)]+[(done,'USER_REPORTED_STEPS_FINISHED'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  fail=[]
  for num,a in enumerate(done,1):
   for f,v in a.items():
    if type(v)is bool:x=copy.deepcopy(done[:num]);x[-1][f]=False;fail.append((str(num)+f,x))
  for _,a in fail:assert workflow_state(c,r,a)['state']=='NEEDS_RETRY';states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  wrong=copy.deepcopy(done);wrong[2]['accent_source_orders']=[1,8,9,16];misreport=copy.deepcopy(done);misreport[4]['omitted_tension_by_repetition']=['C'];nonbool=copy.deepcopy(done);nonbool[4]['selected_repetitions_played_with_core_unchanged_reported']=1;combined=copy.deepcopy(done[:5]);combined[0]['prepared_reported']=False;combined[-1]['selected_repetitions_played_with_core_unchanged_reported']=False
  controls=[('stale',dict(r,contract_sha256='0'*64),[]),('wrong_key',dict(r,package_key='other'),[]),('invented_clock',dict(r,hold_q=4),[]),('omit_core',dict(r,omitted_tension_by_repetition=['G#']),[]),('omit_borrowed_unprinted_G',dict(r,omitted_tension_by_repetition=['G']),[]),('no_variation',dict(r,omitted_tension_by_repetition=[]),[]),('excess_repetition',dict(r,omitted_tension_by_repetition=['F']*9),[]),('wrong_accent',r,wrong),('different_omission_report',r,misreport),('nonbool',r,nonbool),('skip_variation',r,[*done[:4],done[5]]),('combined_failed_reports',r,combined),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[done[0],{'step':2,'response':'needs_retry'},done[2]])]+[('after_false_'+label,r,[*a,done[len(a)]])for label,a in fail if len(a)<6]
  for label,rr,aa in controls:
   try:workflow_state(c,rr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('REFUSAL_FAILED')
  muts=[('fret',lambda x:x['implementation']['events'][0].update(fret=99)),('clock',lambda x:x['implementation']['events'][0].update(duration_q=[1,1])),('lost_variation',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(4)),('wrong_accent',lambda x:x['implementation']['manual_execution_contract']['accent_passes'][0].update(accent_source_orders=[1])),('false_absence_other_positions',lambda x:x['implementation']['manual_execution_contract']['steps'][4].update(module_continuation_applies_to_all_five_positions=False)),('false_source_repeat_count',lambda x:x['implementation']['manual_execution_contract']['steps'][4].update(source_occurrence_policy_and_repetition_count=1)),('false_mastery',lambda x:x['implementation']['manual_execution_contract']['source_full_book_mastery'].update(completed=True))]
  for label,mut in muts:
   bad=copy.deepcopy(new);mut(bad)
   try:verify(old,bad,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key']for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])]for x in idx['children']if x['package_key']not in keys]);before=other()
 for d,row in zip(changes,rows):eff[d['package_key']]=row;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']]for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==796 and other()==before and rh(identity)==idx['ordered_identity_sha256']and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':967,'implementation_or_interpretation_pending':528,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,h in PINS:assert sha(p)==h
 for ref in refs:checkpin(ref)
 OUT.mkdir(parents=True);RES.mkdir(parents=True);packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(x)+'\n'for x in rows));save(RES/'targeted-validation.json',{'result':'PASS','full20page_original_context_proof':pin(PROOF),'source_checks':checks,'printed_contacts':80,'additional_accent_pass_contacts':160,'minimum_selected_variation_contacts':70,'maximum_interface_variation_contacts':560,'selection_plans':plans,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2128,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'Five manual mode mirrors, three accent passes and explicit omission choices; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-start,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':796,'unique_replaced_children':796,'total_replacement_operations':934,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k]for k in['path','bytes','sha256']}for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0});print(compact({'handoff':pin(RES/'handoff.json'),'packet':pin(packet),'categories':cats,'plans':len(plans),'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
