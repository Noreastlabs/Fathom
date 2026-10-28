"""Eight seventh sweep bursts: full release, one breath, and gated manual repetition."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('b',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-seventh-sweeps-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level063-triad-sweeps-manual-r01/handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'26c42a5701b590bd3f8c6eb8618c357c049f288244e0ad5f72cf1580a75f3ac2')]
LOCAL='The four-string mirror comes directly from Level 60, but this level treats it as a short burst with a complete reset between repetitions. Do not turn the exercise into a continuous rake before muting is stable.'
PROTOCOL='Burst protocol: one mirror, full hand release, one breath, repeat. Increase repetitions only after the final note remains as clean as the first.'
SAFETY='Sweep and hybrid practice uses minimum pick depth and relaxed finger extension. Stop for pain or persistent tension.'
def contract(old,data):
 contacts=[{k:e[k] for k in ['order','printed_note','role','string','fret','pick']} for e in old['implementation']['events']]
 return {'schema':'fathom.private-manual-seventh-sweep-cycle.v1','package_key':old['package_key'],'actions':{
 'setup':{'instruction':'Set minimum pick depth, relaxed finger extension, muting and fret/attack/release/next-string sequence.','safety':SAFETY,'stop_immediately':b.STOP,'muting':b.MUTING,'accepted_responses':['acknowledged','stopped']},
 'mirror':{'instruction':'Perform one exact eight-note directional mirror with each note separated.','ordered_contacts':contacts,'source_rule':LOCAL,'physical_page':10,'repeat_highest_event_orders':[4,5],'release_before_next_attack':True,'accepted_responses':['acknowledged','stopped']},
 'full_hand_release':{'instruction':'Fully release the hand before the next repetition.','source_page':10,'accepted_responses':['acknowledged','stopped']},
 'one_breath':{'instruction':'Take one breath before repeating.','breath_duration_seconds':None,'source_page':10,'accepted_responses':['acknowledged','stopped']},
 'compare':{'instruction':'Report whether the final note remained as clean as the first before adding a repetition.','accepted_responses':['clean_match_repeat','clean_match_finish','not_clean','stopped'],'automatic_assessment':False}},
 'source_protocol':{'physical_page':10,'exact_text':PROTOCOL},'minimum_selected_repetitions':2,'minimum_selection_policy':'Two is the minimum private realization of repeat, not a printed repetition count; additional repetitions require explicit clean-match report.','source_fixed_repetition_count':None,
 'source_session_duties':{'physical_page':1,'exact_text':b.SESSION,'whole_session_observed':False},'source_required_practice_duty':{'physical_page':20,'full_gate_text':data['gate'],'completed':None},
 'selected_stroke_map':'DDDDUUUU','additional_opposite_start_pass':None,'both_starts_requirement_for_sweeps':None,
 'response_contract':{'function':'workflow_state','input':'exact key/hash and contiguous numbered action/response list','meaning':'Only user-reported repetitions; no physical/aural quality, mastery, Attempt or credit inference.'},
 'printed_attacks':8,'printed_memberships':8,'fixed_bpm':None,'onsets_q':None,'durations_q':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):assert type(r) is dict and set(r)=={'package_key','contract_sha256'} and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_SELECTION'
def workflow_state(c,r,answers):
 assert type(answers) is list,'RESPONSE_LIST'
 if r is None:assert answers==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 selection(c,r);state='IN_PROGRESS';action='setup';repetitions=0;clean_reports=0
 for n,a in enumerate(answers,1):
  assert state=='IN_PROGRESS','TERMINAL_RESPONSE';assert type(a) is dict and set(a)=={'sequence','action','response'},'RESPONSE_FIELDS';assert type(a['sequence']) is int and a['sequence']==n,'RESPONSE_ORDER';assert a['action']==action and a['response'] in c['actions'][action]['accepted_responses'],'EXPECTED_ACTION_RESPONSE'
  response=a['response']
  if response=='stopped':state='STOPPED';action=None
  elif action=='setup':action='mirror'
  elif action=='mirror':repetitions+=1;action='full_hand_release'
  elif action=='full_hand_release':action='one_breath'
  elif action=='one_breath':action='compare'
  elif response=='not_clean':state='NEEDS_RETRY';action=None
  elif response=='clean_match_repeat':clean_reports+=1;action='mirror'
  else:
   assert repetitions>=c['minimum_selected_repetitions'],'REPEAT_REQUIRED';clean_reports+=1;state='USER_REPORTED_SELECTED_REPETITIONS_FINISHED';action=None
 return {'state':state,'next_action':None if action is None else {'action':action,**c['actions'][action]},'learner_reported_repetitions':repetitions,'learner_reported_clean_matches':clean_reports,'additional_practice_attacks_outside_printed_inventory':max(0,repetitions-1)*8,'performance_observed':False,'grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_seventh_sweep_release_breath_repeat';new['implementation']['manual_execution_contract']=contract(old,data);return new
def verify(old,new,data):assert new==make(old,data),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==584 and ops==690
 proof=next(x for x in json.loads((b.RES/'artifact-manifest.json').read_text())['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context']
 entries=[x for x in idx['children'] if x['level']==63 and 46<=x['line']<=53];olds=[eff[x['package_key']] for x in entries];assert len(olds)==8 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 assert SAFETY in norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==1))
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  for pn in [10]:
   page=pdf.pages[pn-1].extract_text(x_tolerance=1);assert norm(page)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==pn)) and LOCAL in norm(page) and PROTOCOL in norm(page)
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE F -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE G -'))
  for old in olds:
   sc=old['implementation']['source_scope'];page=sc['locator']['physical_page'];assert page==10;raw=pdf.pages[page-1].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'];label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9
   ev=old['implementation']['events'];assert len(ev)==8 and [e['pick'] for e in ev]==list('DDDDUUUU')
   for j,e in enumerate(ev):
    vals={k:s[j*4:j*4+4].strip('-') for k,s in tg.items()};cs=[(b.SM[k],int(x)) for k,x in vals.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[vals[k] for k in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   sig=lambda x:tuple(x[k] for k in ['string','fret','printed_note','role']);assert list(map(sig,ev[:4]))==list(map(sig,ev[4:]))[::-1] and [e['string'] for e in ev]==[ev[0]['string'],ev[0]['string']-1,ev[0]['string']-2,ev[0]['string']-3,ev[0]['string']-3,ev[0]['string']-2,ev[0]['string']-1,ev[0]['string']]
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'F'},'literal':literal,'page':page,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_page':page,'PDF_bbox':sc['locator']['derived_bbox'],'highest_repeated_contact':sig(ev[3])})
 rows=[];changes=[];refusals=[];corruptions=[];states=0
 def sequence(items):return [{'sequence':i+1,'action':a,'response':r} for i,(a,r) in enumerate(items)]
 setup=[('setup','acknowledged')];cycle=[('mirror','acknowledged'),('full_hand_release','acknowledged'),('one_breath','acknowledged')]
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);c=new['implementation']['manual_execution_contract'];r={'package_key':old['package_key'],'contract_sha256':rh(c)}
  twice=sequence(setup+cycle+[('compare','clean_match_repeat')]+cycle+[('compare','clean_match_finish')]);thrice=sequence(setup+cycle+[('compare','clean_match_repeat')]+cycle+[('compare','clean_match_repeat')]+cycle+[('compare','clean_match_finish')])
  samples=[([],'IN_PROGRESS'),(sequence(setup),'IN_PROGRESS'),(sequence(setup+cycle),'IN_PROGRESS'),(twice,'USER_REPORTED_SELECTED_REPETITIONS_FINISHED'),(thrice,'USER_REPORTED_SELECTED_REPETITIONS_FINISHED'),(sequence(setup+cycle+[('compare','not_clean')]),'NEEDS_RETRY'),(sequence(setup+[('mirror','stopped')]),'STOPPED')]
  for aa,state in samples:assert workflow_state(c,r,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  assert workflow_state(c,r,twice)['learner_reported_repetitions']==2 and workflow_state(c,r,thrice)['learner_reported_repetitions']==3 and workflow_state(c,r,thrice)['additional_practice_attacks_outside_printed_inventory']==16
  for label,sr,aa in [('stale',dict(r,contract_sha256='0'*64),[]),('wrong_key',dict(r,package_key='wrong'),[]),('finish_first',r,sequence(setup+cycle+[('compare','clean_match_finish')])),('skip_release',r,sequence(setup+[cycle[0],cycle[2]])),('skip_breath',r,sequence(setup+cycle[:2]+[('compare','clean_match_repeat')])),('unconditional_repeat',r,sequence(setup+cycle+[('compare','repeat')])),('dirty_repeat',r,sequence(setup+cycle+[('compare','not_clean')]+cycle)),('after_finish',r,twice+[{'sequence':10,'action':'mirror','response':'acknowledged'}]),('extra_clock',dict(r,breath_seconds=2),[]),('opposite_start',dict(r,start='U'),[]),('bool_sequence',r,[{'sequence':True,'action':'setup','response':'acknowledged'}]),('after_stop',r,sequence([('setup','stopped'),('mirror','acknowledged')]))]:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('REFUSAL_FAILED')
  for label,mut in [('lost_high_repeat',lambda x:x['implementation']['events'][4].update(fret=99)),('alternate_pick',lambda x:x['implementation']['events'][1].update(pick='U')),('invent_breath',lambda x:x['implementation']['manual_execution_contract']['actions']['one_breath'].update(breath_duration_seconds=2)),('lost_release',lambda x:x['implementation']['manual_execution_contract']['actions']['mirror'].update(release_before_next_attack=False)),('invent_source_count',lambda x:x['implementation']['manual_execution_contract'].update(source_fixed_repetition_count=2)),('whole_mastery',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   bad=copy.deepcopy(new);mut(bad)
   try:verify(old,bad,d)
   except AssertionError:corruptions.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==592 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':765,'implementation_or_interpretation_pending':730,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':64,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2125,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'8 selected seventh sweep release/breath/clean-repeat contracts; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':592,'unique_replaced_children':592,'total_replacement_operations':698,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'states':states,'refusals':len(refusals),'corruptions':len(corruptions)}))
if __name__=='__main__':main()
