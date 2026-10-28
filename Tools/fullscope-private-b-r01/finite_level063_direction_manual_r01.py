"""Eight direction rolls, recording locators and explicit manual same-tempo family audit."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level063_crosspick_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='a98423b44b9ec23ecee217605418990c9f34030ba364776fdb34aeca30c87b17'
s=importlib.util.spec_from_file_location('previous',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,FOLD,VALIDATOR,PACKET=b.BASE,b.FOLD,b.VALIDATOR,b.PACKET
NAME='finite-level063-direction-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=b.RES/'handoff.json';CONTEXT_PROOF=b.RES/'targeted-validation.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(PREV,'70d0c81c66af74b9ac0b8bbf162a557c65f2e93d9912dc455104ab633f75d733')]
RULE='Practice all four string orders on C major and A minor. Accent event 1 only. The outside-skip and inside-skip rolls cross a nonadjacent string; mute the skipped string completely.'
AUDIT='Audit: record the rolls at the same tempo. If one direction is louder or later, isolate only that string-change pair instead of repeating the complete cell.'
def family(olds,entries):
 return {'schema':'fathom.private-direction-recording-family.v1','source_page':5,'rule':RULE,'audit':AUDIT,'source_cases':[{'package_key':old['package_key'],'source_identity':old['source_identity'],'source_record':{**pin(PACKET),'line':ent['line'],'record_sha256':rh(old)}} for old,ent in zip(olds,entries)],'required_case_passes':16,'passes':['D','U'],'U_authority':{'page':20,'text':b.BOTH},'tempo_binding':'One explicit nonempty learner-selected tempo label applies to every recorded pass; it is not a printed BPM or a note schedule.','recording_locator_semantics':'User-supplied file/take/segment locator; file existence and audible quality are not observed by this private contract.','no_recording_created_here':True,'grants_credit':False}
def selected_contacts(events,start):
 return [{**{k:e[k] for k in ['order','printed_note','role','string','fret']},'pick':e['pick'] if start=='D' else ('U' if e['pick']=='D' else 'D'),'accent':e['order']==1} for e in events]
def crossings(events):return [{'event_orders':[j+1,j+2],'skipped_strings':list(range(min(a['string'],c['string'])+1,max(a['string'],c['string'])))} for j,(a,c) in enumerate(zip(events,events[1:]))]
def contract(old,data,fr):
 c=b.contract(old,data);c['schema']='fathom.private-manual-direction-roll.v1';c['family_audit']=fr;c['individual_completion_not_family_completion']=True
 for n,start in [(1,'D'),(2,'U')]:
  step=c['steps'][n];step['ordered_contacts']=selected_contacts(old['implementation']['events'],start);step['action']=f'record_eight_note_{start}_start_direction_roll_at_selected_family_tempo';step['accent_event_orders']=[1];step['mute_skipped_strings_by_transition']=crossings(old['implementation']['events']);step['recording_locator_required']=True
  step.pop('source_caption',None);step['source_rule']=RULE;step['both_starts_authority']={'page':20,'text':b.BOTH}
 c['steps'][3]['action']='user_report_completed_both_recorded_passes_and_submit_to_family_comparison';c['source_error_repair']={'physical_page':5,'exact_text':AUDIT,'implementation':'family_audit returns only the exact selected adjacent source pair for a learner-reported louder/later direction.'}
 return c
def select(c,r):
 assert type(r) is dict and set(r)=={'package_key','contract_sha256','family_sha256','tempo_label'},'SELECTION_FIELDS'
 assert r['package_key']==c['package_key'] and r['contract_sha256']==rh(c) and r['family_sha256']==c['family_audit']['sha256'],'SELECTION_IDENTITY'
 assert type(r['tempo_label']) is str and r['tempo_label'].strip()==r['tempo_label'] and r['tempo_label'],'TEMPO_LABEL'
def workflow_state(c,r,responses):
 assert type(responses) is list,'RESPONSE_LIST'
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 select(c,r);projected=[]
 for a in responses:
  assert type(a) is dict and {'step','response'}<=set(a),'RESPONSE_FIELDS'
  needs_record=a['step'] in [2,3] and a['response']=='acknowledged'
  assert set(a)==({'step','response','recording_locator'} if needs_record else {'step','response'}),'RECORDING_FIELDS'
  if needs_record:assert type(a['recording_locator']) is str and a['recording_locator'].strip(),'RECORDING_LOCATOR'
  projected.append({k:a[k] for k in ['step','response']})
 state=module(VALIDATOR,'v').response_state(c,projected)
 return {'state':state,'next_step':c['steps'][len(responses)] if state=='IN_PROGRESS' else None,'tempo_label':r['tempo_label'],'recordings':{('D' if a['step']==2 else 'U'):a['recording_locator'] for a in responses if 'recording_locator' in a},'performance_observed':False,'grants_credit':False}
def family_audit(f,fr,contracts,r,submissions):
 assert type(r) is dict and set(r)=={'family_sha256','tempo_label'} and r['family_sha256']==fr['sha256'],'FAMILY_IDENTITY'
 assert type(r['tempo_label']) is str and r['tempo_label'].strip()==r['tempo_label'] and r['tempo_label'],'FAMILY_TEMPO'
 assert type(submissions) is list and len(submissions)==8,'ALL_EIGHT_REQUIRED';expected=[x['package_key'] for x in f['source_cases']];seen=set();repairs=[];recordings=[]
 for sub in submissions:
  assert type(sub) is dict and set(sub)=={'selection','responses','judgments'},'SUBMISSION_FIELDS';sr=sub['selection'];k=sr['package_key'];assert k in expected and k not in seen,'EXACT_UNIQUE_CASE';seen.add(k);c=contracts[k]
  assert sr['tempo_label']==r['tempo_label'] and sr['family_sha256']==r['family_sha256'],'SAME_TEMPO'
  state=workflow_state(c,sr,sub['responses']);assert state['state']=='USER_REPORTED_STEPS_FINISHED','CHILD_UNFINISHED';assert type(sub['judgments']) is dict and set(sub['judgments'])=={'D','U'},'BOTH_JUDGMENTS'
  for start in ['D','U']:
   j=sub['judgments'][start];assert type(j) is dict and set(j)=={'result','pair_start'} and j['result'] in ['consistent','louder','later'],'JUDGMENT'
   if j['result']=='consistent':assert j['pair_start'] is None,'UNNEEDED_PAIR'
   else:
    n=j['pair_start'];assert type(n) is int and 1<=n<=7,'PAIR_BOUNDARY';step=c['steps'][1 if start=='D' else 2];pair=step['ordered_contacts'][n-1:n+1];assert pair[0]['string']!=pair[1]['string'],'ACTUAL_CROSSING';repairs.append({'package_key':k,'pass':start,'reported_issue':j['result'],'ordered_contacts':pair,'mute_skipped_strings':crossings(pair)[0]['skipped_strings'],'only_this_pair_not_full_cell':True,'loop_count':None,'loop_period':None})
   recordings.append({'package_key':k,'pass':start,'recording_locator':state['recordings'][start]})
 assert seen==set(expected)
 return {'state':'USER_REPORTED_REPAIR_REQUIRED' if repairs else 'USER_REPORTED_FAMILY_AUDIT_FINISHED','tempo_label':r['tempo_label'],'recordings':recordings,'selected_pair_repairs':repairs,'recording_or_audio_verified':False,'grants_credit':False}
def make(old,data,fr):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_recorded_direction_roll';new['implementation']['manual_execution_contract']=contract(old,data,fr);return new
def verify(old,new,data,fr):assert new==make(old,data,fr),'EXACT_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==548 and ops==654
 prior_manifest=json.loads((b.RES/'artifact-manifest.json').read_text());proof=next(x for x in prior_manifest['artifacts'] if x['path']==str(CONTEXT_PROOF.relative_to(ROOT)));checkpin(proof);assert json.loads(CONTEXT_PROOF.read_text())['all20_pages_match_context'] is True
 entries=[x for x in idx['children'] if x['level']==63 and 10<=x['line']<=17];olds=[eff[x['package_key']] for x in entries];assert len(olds)==8 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());gate=eff[next(x['package_key'] for x in idx['children'] if x['level']==63 and x['line']==2)]['implementation']['manual_execution_contract']['source_required_practice_duty']['full_gate_text'];data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  page=pdf.pages[4].extract_text(x_tolerance=1);assert norm(page)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==5)) and RULE in norm(page) and AUDIT in norm(page)
  lo=next(i for i,t in enumerate(txt) if t.startswith('MODULE B -'));hi=next(i for i in range(lo+1,len(txt)) if txt[i].startswith('MODULE C -'))
  for old in olds:
   sc=old['implementation']['source_scope'];assert sc['locator']['physical_page']==5;raw=pdf.pages[4].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'];label=old['source_payload']['label'];hits=[i for i in range(lo,hi) if txt[i]==label];assert len(hits)==1;n=hits[0];literal='\n'.join(txt[n:n+10]);tg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',literal,re.M)};pg={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|e|B|G|D|A|E)\|(.*)$',raw,re.M)};assert tg==pg and len(tg)==9
   ev=old['implementation']['events'];assert len(ev)==8 and [e['pick'] for e in ev]==list('DUDUDUDU')
   for j,e in enumerate(ev):
    v={k:s[j*4:j*4+4].strip('-') for k,s in tg.items()};cs=[(b.SM[k],int(x)) for k,x in v.items() if k in b.SM and x];assert cs==[(e['string'],e['fret'])] and [e[k] for k in ['printed_note','role','pick']]==[v[k] for k in ['Nte','Rol','Pck']] and e['order']==j+1 and e['onset_q'] is None and e['duration_q'] is None
   d={'locator':{'line_start':n+1,'line_end':n+10,'module':'B'},'literal':literal,'PDF_page':5,'gate':gate};data.append(d);checks.append({'key':old['package_key'],'TXT':d['locator'],'PDF_bbox':sc['locator']['derived_bbox'],'crossings':crossings(ev)})
 fam=family(olds,entries);fp=OUT/'family-recording-audit.json';fb=(json.dumps(fam,ensure_ascii=False,indent=2)+'\n').encode();fr={'path':str(fp.relative_to(ROOT)),'bytes':len(fb),'sha256':hashlib.sha256(fb).hexdigest()};rows=[];changes=[];contracts={};subs=[];refusals=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d,fr);verify(old,new,d,fr);c=new['implementation']['manual_execution_contract'];k=old['package_key'];contracts[k]=c;r={'package_key':k,'contract_sha256':rh(c),'family_sha256':fr['sha256'],'tempo_label':'learner-selected metronome setting A'};done=[{'step':1,'response':'acknowledged'},{'step':2,'response':'acknowledged','recording_locator':'manual take: '+k+' D'},{'step':3,'response':'acknowledged','recording_locator':'manual take: '+k+' U'},{'step':4,'response':'acknowledged'}]
  assert sum(x['accent'] for x in c['steps'][1]['ordered_contacts'])==1 and sum(x['accent'] for x in c['steps'][2]['ordered_contacts'])==1
  for aa,state in [([],'IN_PROGRESS'),(done,'USER_REPORTED_STEPS_FINISHED'),(done[:2],'IN_PROGRESS'),([{'step':1,'response':'stopped'}],'STOPPED'),([done[0],{'step':2,'response':'needs_retry'}],'NEEDS_RETRY')]:assert workflow_state(c,r,aa)['state']==state;states+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  for label,sr,aa in [('stale',dict(r,contract_sha256='0'*64),[]),('wrong_family',dict(r,family_sha256='0'*64),[]),('blank_tempo',dict(r,tempo_label=''),[]),('omit_U',r,[*done[:2],done[3]]),('missing_recording',r,[done[0],{'step':2,'response':'acknowledged'}]),('after_stop',r,[{'step':1,'response':'stopped'},done[1]]),('after_retry',r,[done[0],{'step':2,'response':'needs_retry'},done[2]]),('extra_clock',dict(r,bpm=90),[])]:
   try:workflow_state(c,sr,aa)
   except AssertionError:refusals.append({'key':k,'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  subs.append({'selection':r,'responses':done,'judgments':{p:{'result':'consistent','pair_start':None} for p in ['D','U']}});rows.append(new);changes.append({'package_key':k,'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[k],'new_category':'complete_manual_nonplayback_contract'})
 req={'family_sha256':fr['sha256'],'tempo_label':'learner-selected metronome setting A'};assert family_audit(fam,fr,contracts,req,subs)['state']=='USER_REPORTED_FAMILY_AUDIT_FINISHED';repair_checks=[]
 for i in range(8):
  for start in ['D','U']:
   for j in range(1,8):
    ss=copy.deepcopy(subs);ss[i]['judgments'][start]={'result':'louder' if j%2 else 'later','pair_start':j};result=family_audit(fam,fr,contracts,req,ss);assert result['state']=='USER_REPORTED_REPAIR_REQUIRED' and len(result['selected_pair_repairs'])==1 and len(result['selected_pair_repairs'][0]['ordered_contacts'])==2;repair_checks.append({'key':ss[i]['selection']['package_key'],'pass':start,'pair':j,'repair_sha256':rh(result['selected_pair_repairs'][0])})
 family_refusals=[]
 for label,mut in [('missing',lambda ss:ss.pop()),('duplicate',lambda ss:ss.__setitem__(1,copy.deepcopy(ss[0]))),('different_tempo',lambda ss:ss[0]['selection'].update(tempo_label='different setting')),('missing_U',lambda ss:ss[0]['judgments'].pop('U')),('bool_pair',lambda ss:ss[0]['judgments']['D'].update(result='later',pair_start=True)),('bad_pair',lambda ss:ss[0]['judgments']['D'].update(result='later',pair_start=8)),('unfinished',lambda ss:ss[0]['responses'].pop()),('automatic_result',lambda ss:ss[0]['judgments']['D'].update(result='detected_clean'))]:
  ss=copy.deepcopy(subs);mut(ss)
  try:family_audit(fam,fr,contracts,req,ss)
  except AssertionError:family_refusals.append(label)
  else:raise AssertionError('FAMILY_REFUSAL_FAILED')
 corruptions=[]
 for i in range(8):
  for label,mut in [('fret',lambda r:r['implementation']['events'][0].update(fret=99)),('accent5',lambda r:r['implementation']['manual_execution_contract']['steps'][1]['ordered_contacts'][4].update(accent=True)),('omit_skip_muting',lambda r:r['implementation']['manual_execution_contract']['steps'][1].update(mute_skipped_strings_by_transition=[])),('opposite_pick',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['ordered_contacts'][0].update(pick='D')),('clock',lambda r:r['implementation']['events'][0].update(onset_q=[0,1]))]:
   bad=copy.deepcopy(rows[i]);mut(bad)
   try:verify(olds[i],bad,data[i],fr)
   except AssertionError:corruptions.append({'key':rows[i]['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,r in zip(changes,rows):eff[d['package_key']]=r;cat[d['package_key']]=d['new_category'];used.add(d['package_key'])
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];cats=dict(Counter(cat.values()));assert len(eff)==2133 and len(used)==556 and rh(identity)==idx['ordered_identity_sha256'] and other()==before and cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':729,'implementation_or_interpretation_pending':766,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 fp.write_bytes(fb);packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'full_book_context_reused_by_reference':proof,'printed_contacts':64,'required_U_practice_contacts':64,'workflow_states':states,'workflow_refusals':refusals,'manual_family_audit_all16_case_passes':True,'family_pair_repairs':repair_checks,'family_refusals':family_refusals,'content_refusals':corruptions,'unchanged_other_rows':2125,'unchanged_other_records_sha256':before,'final_input_drift':0,'actual_recording_or_audio_assessment':'NOT_RUN','native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'8 selected direction-roll contracts plus manual family recording audit; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'family_recording_audit':fr,'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':556,'unique_replaced_children':556,'total_replacement_operations':662,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'family':fr,'categories':cats,'states':states,'family_pair_repairs':len(repair_checks),'workflow_refusals':len(refusals),'family_refusals':len(family_refusals),'content_refusals':len(corruptions)}))
if __name__=='__main__':main()
