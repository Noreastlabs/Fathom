"""Sixteen source enclosure cells and guarded explicit manual follow-up choices."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];NAME='finite-level061-enclosure-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME
BASE=ROOT/'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json';PREV=ROOT/'Results/fullscope-private-b-r01/finite-level061-diatonic-manual-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level061-r02/implementation.jsonl';HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level051_manual_scans_r01.py'
STRINGS={'E':6,'A':5,'D':4,'G':3,'B':2,'e':1};OPEN={6:40,5:45,4:50,3:55,2:59,1:64};PCS={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
RULE='The first two notes are motion. The third and fourth notes are the destination. Practice above-below and below-above orders separately before alternating them.'
SESSION='Choose one target quality, one approach type, and one progression phrase. Play the target alone first. Sing the target. Add the approach at half speed. Preserve the barline and leave at least one complete beat of space after every two-bar statement.'
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rh(x):return hashlib.sha256(compact(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def checkpin(r):assert pin(ROOT/r['path'])=={k:r[k] for k in ['path','bytes','sha256']},'INPUT_DRIFT'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(x):return re.sub(r'\s+',' ',x).strip()
def followup(contract,choice,separate_practice_reports):
 """Producer-authored manual routing; self reports never count as performance proof."""
 own=contract['source_cell']['package_key'];mate=contract['paired_cell']['package_key']
 if type(choice)is not str or choice not in ['repeat_current','practice_other_order','alternate_one_pair','stop']:raise ValueError('CHOICE')
 if type(separate_practice_reports)is not dict or set(separate_practice_reports)!={own,mate} or any(type(v)is not bool for v in separate_practice_reports.values()):raise ValueError('EXACT_BOOLEAN_UNIT_REPORTS')
 if choice=='alternate_one_pair' and not all(separate_practice_reports.values()):raise ValueError('SEPARATE_PRACTICE_REQUIRED')
 route={'repeat_current':[own],'practice_other_order':[mate],'alternate_one_pair':[own,mate],'stop':[]}[choice]
 return {'choice':choice,'ordered_source_keys':route,'scope':'One explicitly selected manual route; no automatic repetition.','report_basis':'learner self-report only','performed':False,'assessment':None,'credit_awarded':False}
def verify(old,new,mate):
 stripped=copy.deepcopy(new);stripped['implementation'].pop('manual_execution_contract');stripped['implementation']['kind']=old['implementation']['kind'];assert stripped==old,'OTHER_MUTATION'
 c=new['implementation']['manual_execution_contract'];ev=old['implementation']['events'];steps=c['steps'];assert c['mode']=='manual_nonplayback' and c['automated_assessment'] is False and c['grants_credit'] is False,'AUTHORITY'
 assert c['clock']==dict.fromkeys(['onset_q','duration_q','fixed_bpm','acoustic_gate_q','numeric_velocity']),'CLOCK'
 assert all(e['onset_q'] is None and e['duration_q'] is None for e in ev) and c['printed_cell_contact_count']==4 and c['separate_preparatory_target_count']==1,'SOURCE_COUNT'
 assert [s['order'] for s in steps]==list(range(1,len(steps)+1)),'STEP_ORDER'
 assert [s['action'] for s in steps]==['name_destination_and_enclosure_order','establish_personal_reference_pace','play_reference_target_before_cell','sing_target','prepare_enclosure_half_reference_speed','play_source_contact','play_source_contact','play_source_contact','play_source_contact','self_report_separate_practice'],'STEPS'
 assert steps[0]['printed_target']==ev[2]['printed_note'] and steps[0]['target_role']==ev[2]['role'],'TARGET'
 assert steps[2]['source_event_sha256']==rh(ev[2]) and steps[2]['counted_in_printed_four'] is False,'PREPARATION_SOURCE'
 plays=[s for s in steps if s['action']=='play_source_contact'];assert [s['event_order'] for s in plays]==[1,2,3,4] and [s['event_sha256'] for s in plays]==[rh(e) for e in ev],'SOURCE_EVENTS'
 assert [s['phrase_role'] for s in plays]==['temporary approach','temporary approach','destination','repeated destination'],'PHRASE_ROLE'
 for ref,row in [(c['source_cell'],old),(c['paired_cell'],mate)]:assert ref['package_key']==row['package_key'] and ref['source_identity']==row['source_identity'] and ref['base_record_sha256']==rh(row),'PAIR_IDENTITY'
 assert c['source_context']=={'governing':RULE,'session':SESSION,'pages':[1,old['implementation']['source_scope']['locator']['physical_page']]},'FULL_CONTEXT'
 assert c['followup_choice']['allowed']==['repeat_current','practice_other_order','alternate_one_pair','stop'] and c['followup_choice']['alternation_requires_both_exact_units_reported_separately_practiced'] is True,'CHOICE_GUARD'
 assert c['scope']['whole_session_completed'] is False and c['scope']['automatic_repetition'] is False,'NO_COMPLETION'

def main():
 t=time.monotonic();utc=datetime.now(timezone.utc).isoformat();frozen=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(PREV,'f0a6a186fe4a90cce04bfbcc01d66cdb6f9a1f47061a44e84cae2ce5733fe372'),(PACKET,'c13b9ad0a1b3779166e324fb2c3cfbf70a72c4185cca8af6ae61d5bd0b0561ab'),(HELPER,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa')]
 for p,h in frozen:assert sha(p)==h
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS'
 spec=importlib.util.spec_from_file_location('manual_response_reference',HELPER);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 index=json.loads(BASE.read_text());prior=json.loads(PREV.read_text());rr=list(map(json.loads,PACKET.read_text().splitlines()));selected=[e for e in index['children'] if e['level']==61 and '/modulec/' in e['source_identity']];assert len(selected)==16 and [e['line'] for e in selected]==list(range(42,58));refs=rr[41]['source_refs']
 for ref in refs:checkpin(ref)
 txt=[s.strip() for s in (ROOT/refs[0]['path']).read_text().splitlines()];ctx=json.loads((ROOT/refs[2]['path']).read_text());pages={};crops={}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  for p in [1,7,8]:pages[p]=pdf.pages[p-1].extract_text(x_tolerance=1)
  for e in selected:loc=rr[e['line']-1]['implementation']['source_scope']['locator'];crops[e['package_key']]=pdf.pages[loc['physical_page']-1].crop(loc['derived_bbox']).extract_text(x_tolerance=1)
 for p,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==p)),'PAGE_CUSTODY'
 assert all(norm(RULE) in norm(pages[p]) for p in [7,8]) and norm(SESSION) in norm(pages[1]),'FULL_CONTEXT'
 response={'author':'B producer-authored manual interaction; source facts separately located.','fields':{'step':'integer, 1-based contiguous prefix of steps','response':['acknowledged','needs_retry','stopped']},'additional_fields':False,'initial_responses':[],'advance':'Explicit acknowledged advances; retry or stop ends this sequence. Retry starts fresh.','completion':'USER_REPORTED_STEPS_FINISHED only; external self-reported separate-practice state is never automatic performance evidence.','meaning':'No measured correctness, mastery, learner credit or saved Session/Attempt.'}
 rows=[];olds=[];mates=[];changes=[];locators=[];followup_passes=0;followup_refusals=0
 for i,entry in enumerate(selected):
  old=rr[entry['line']-1];mate=rr[selected[i^1]['line']-1];assert rh(old)==entry['record_sha256'] and entry['category']=='implementation_or_interpretation_pending';scope=old['implementation']['source_scope'];page=scope['locator']['physical_page'];crop=crops[entry['package_key']];assert norm(crop)==norm(scope['pdf_excerpt']),'CARD_CUSTODY'
  label=old['source_payload']['label'];score=[line.strip() for line in crop.splitlines() if re.match(r'^\s*(Nte|Rol|Tag|[eBGDAE])\|',line)];assert len(score)==9;starts=[j for j,s in enumerate(txt) if s==label and txt[j+1:j+10]==score];assert len(starts)==1,'TXT_CARD';n=starts[0]+1
  ev=old['implementation']['events'];mev=mate['implementation']['events'];assert len(ev)==4 and len({e['string'] for e in ev})==1 and [e['tag'] for e in ev]==['CHR','CHR','T','T'];target=ev[2]['fret'];order=label.rsplit(' - ',1)[1];expected=[target+1,target-1,target,target] if order=='above-below' else [target-1,target+1,target,target];assert [e['fret'] for e in ev]==expected,'SOURCE_APPROACH_ORDER'
  assert mate['source_payload']['label'].rsplit(' - ',1)[0]==label.rsplit(' - ',1)[0] and mate['source_payload']['label'].rsplit(' - ',1)[1]!=order and [e['fret'] for e in mev]==[ev[1]['fret'],ev[0]['fret'],target,target] and [e['string'] for e in mev]==[ev[0]['string']]*4,'EXACT_PAIR'
  grid=dict(line.split('|',1) for line in score)
  for e in ev:
   col=e['printed_column'];s=next(k for k,v in STRINGS.items() if v==e['string']);m=re.match(r'\d+',grid[s][col:]);assert m and int(m[0])==e['fret']
   for key,field in [('Nte','printed_note'),('Rol','role'),('Tag','tag')]:assert grid[key][col:].split('-',1)[0]==e[field]
   note=e['printed_note'];assert (OPEN[e['string']]+e['fret'])%12==(PCS[note[0]]+note.count('#')-note.count('b'))%12,'PITCH'
  assert [e['role'] for e in ev]==['app','app',ev[2]['role'],ev[2]['role']] and ev[2]['printed_note']==ev[3]['printed_note'],'REPEATED_TARGET'
  source={'physical_page':page,'bbox':scope['locator']['derived_bbox'],'label':label,'txt_lines':[n,n+9]};steps=[]
  def add(action,**kw):steps.append({'order':len(steps)+1,'action':action,**kw})
  add('name_destination_and_enclosure_order',printed_target=ev[2]['printed_note'],target_role=ev[2]['role'],enclosure_order=order,source=source)
  add('establish_personal_reference_pace',fixed_bpm=None,meaning='Personal manual reference pace; source supplies no fixed numeric tempo.')
  add('play_reference_target_before_cell',source_event_sha256=rh(ev[2]),string=ev[2]['string'],fret=target,printed_note=ev[2]['printed_note'],counted_in_printed_four=False,source={'physical_page':1,'exact_text':'Play the target alone first.'})
  add('sing_target',printed_note=ev[2]['printed_note'],assessment=None,source={'physical_page':1,'exact_text':'Sing the target.'})
  add('prepare_enclosure_half_reference_speed',speed_relation='half of learner-selected reference pace',fixed_bpm=None,source={'physical_page':1,'exact_text':'Add the approach at half speed.'})
  for j,e in enumerate(ev):add('play_source_contact',event_order=e['order'],event_sha256=rh(e),phrase_role=['temporary approach','temporary approach','destination','repeated destination'][j],source=source)
  add('self_report_separate_practice',source={'physical_page':page,'exact_text':RULE},meaning='Explicit report that this source order was practiced separately; no measured correctness or completed counterpart inferred.')
  sr=lambda r:{'package_key':r['package_key'],'source_identity':r['source_identity'],'base_packet':str(PACKET.relative_to(ROOT)),'base_packet_sha256':sha(PACKET),'base_record_sha256':rh(r)}
  c={'schema':'fathom.private-manual-enclosure.v1','mode':'manual_nonplayback','steps':steps,'source_cell':sr(old),'paired_cell':sr(mate),'printed_cell_contact_count':4,'separate_preparatory_target_count':1,'clock':dict.fromkeys(['onset_q','duration_q','fixed_bpm','acoustic_gate_q','numeric_velocity']),'source_context':{'governing':RULE,'session':SESSION,'pages':[1,page]},'followup_choice':{'author':'Producer-authored finite manual interaction for the source separate-before-alternate rule.','allowed':['repeat_current','practice_other_order','alternate_one_pair','stop'],'alternation_requires_both_exact_units_reported_separately_practiced':True,'readiness_schema':'Exact dict of own and paired package keys to strict booleans; supplied only from explicit learner reports, never inferred from timing or correctness.','one_pair_semantics':'Current four-contact cell then paired four-contact cell once; another pair requires another explicit choice. No printed repetition-count claim.'},'scope':{'selected':'Exact individual enclosure order plus source-faithful optional finite follow-up route.','whole_session_completed':False,'automatic_repetition':False,'unselected_session_duties':['Choose a progression phrase; preserve its barline and leave at least one full beat after each two-bar statement.'],'aggregate_workbook_count_reinterpreted':False},'response_contract':copy.deepcopy(response),'automated_assessment':False,'grants_credit':False};new=copy.deepcopy(old);new['implementation']['kind']='manual_enclosure_contract';new['implementation']['manual_execution_contract']=c;verify(old,new,mate)
  seq=[{'step':j+1,'response':'acknowledged'} for j in range(len(steps))];assert helper.response_state(c,seq)=='USER_REPORTED_STEPS_FINISHED' and helper.response_state(c,seq[:-1])=='IN_PROGRESS';assert helper.response_state(c,[{'step':1,'response':'needs_retry'}])=='NEEDS_RETRY' and helper.response_state(c,[{'step':1,'response':'stopped'}])=='STOPPED'
  own=old['package_key'];other=mate['package_key'];ready={own:True,other:True}
  for choice,want in [('repeat_current',[own]),('practice_other_order',[other]),('alternate_one_pair',[own,other]),('stop',[])]:assert followup(c,choice,ready)['ordered_source_keys']==want;followup_passes+=1
  for choice,reports in [('alternate_one_pair',{own:True,other:False}),('alternate_one_pair',{own:False,other:True}),('alternate_one_pair',{own:True,other:1}),('repeat_current',{own:True}),('unknown',ready),('alternate_one_pair',{own:True,other:True,'wrong-unit':True})]:
   try:followup(c,choice,reports)
   except ValueError:followup_refusals+=1
   else:raise AssertionError('FOLLOWUP_REFUSAL_MISSED')
  rows.append(new);olds.append(old);mates.append(mate);locators.append({'source_identity':old['source_identity'],'paired_source_identity':mate['source_identity'],'txt_lines':[n,n+9],'pdf_page':page,'contacts':4});changes.append({'package_key':new['package_key'],'source_identity':new['source_identity'],'base_record_sha256':entry['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':entry['category'],'new_category':'complete_manual_nonplayback_contract'})
 refused=[]
 for name,mut in [('wrong_pair',lambda r:r['implementation']['manual_execution_contract']['paired_cell'].update(source_identity='wrong')),('omit_repeat',lambda r:r['implementation']['events'].pop()),('invert_approach',lambda r:r['implementation']['events'][0].update(fret=99)),('invent_timing',lambda r:r['implementation']['manual_execution_contract']['clock'].update(duration_q=1)),('skip_separate_guard',lambda r:r['implementation']['manual_execution_contract']['followup_choice'].update(alternation_requires_both_exact_units_reported_separately_practiced=False)),('prep_count_inflation',lambda r:r['implementation']['manual_execution_contract'].update(printed_cell_contact_count=5)),('credit',lambda r:r['implementation']['manual_execution_contract'].update(grants_credit=True))]:
  bad=copy.deepcopy(rows[0]);mut(bad)
  try:verify(olds[0],bad,mates[0])
  except AssertionError:refused.append(name)
  else:raise AssertionError('CORRUPTION_ACCEPTED '+name)
 effective={};used=set()
 for ref in index['packets']:
  checkpin(ref)
  for row in map(json.loads,(ROOT/ref['path']).read_text().splitlines()):assert row['package_key'] not in effective;effective[row['package_key']]=row
 chain=[];h=prior
 while True:
  chain.append(h)
  if 'prior_overlay_handoff' not in h:break
  checkpin(h['prior_overlay_handoff']);h=json.loads((ROOT/h['prior_overlay_handoff']['path']).read_text())
 for h in reversed(chain):
  checkpin(h['overlay']);oo=list(map(json.loads,(ROOT/h['overlay']['path']).read_text().splitlines()))
  for d in h['changes']:
   key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];row=oo[d['overlay_line']-1];assert rh(row)==d['overlay_record_sha256'] and row['package_key']==key;effective[key]=row;used.add(key)
 assert len(used)==226
 for d,row in zip(changes,rows):key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];effective[key]=row;used.add(key)
 identity=[[e['package_key'],effective[e['package_key']]['source_identity']] for e in index['children']];assert len(effective)==2133 and len(used)==242 and rh(identity)==index['ordered_identity_sha256']
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));cats=copy.deepcopy(prior['effective_categories']);cats['implementation_or_interpretation_pending']-=16;cats['complete_manual_nonplayback_contract']+=16
 for p,h in frozen:assert sha(p)==h
 for ref in refs:checkpin(ref)
 save(RES/'targeted-validation.json',{'result':'PASS','exact_cards':16,'unchanged_source_contacts':64,'separate_preparatory_target_tasks':16,'original_txt_pdf_checks':locators,'valid_response_cases':64,'valid_followup_cases':followup_passes,'causal_followup_refusals':followup_refusals,'causal_content_refusals':refused,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':1,'status':'Sixteen enclosure manual and guarded choice contracts; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-t,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'strict_semantics':'Follow verified prior handoff links to checkpoint-r03; fold226 replacements before these16 disjoint replacements; check all whole-file and record hashes; refuse missing/duplicate keys.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':242,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:ref[k] for k in ['path','bytes','sha256']} for ref in refs],'reused_response_validator':pin(HELPER),'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'followup_refusals':followup_refusals,'content_refusals':len(refused)}))
if __name__=='__main__':main()
