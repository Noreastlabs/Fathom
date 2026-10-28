"""Five written zones plus a separately selected adjacent-zone response."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,itertools,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level059_c_root_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'
s=importlib.util.spec_from_file_location('helpers',HELPER);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
compact,rh,sha,pin,checkpin,save,norm,module=h.compact,h.rh,h.sha,h.pin,h.checkpin,h.save,h.norm,h.module
BASE,FOLD,VALIDATOR=h.BASE,h.FOLD,h.VALIDATOR
NAME='finite-level061-zones-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level061-motif-manual-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level061-r02/implementation.jsonl'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(FOLD,'f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa'),(PREV,'4189cb73f5fbbe692d7ceaf3423ef2facb72011ce90cafe9f200023df81cce17'),(PACKET,'c13b9ad0a1b3779166e324fb2c3cfbf70a72c4185cca8af6ae61d5bd0b0561ab')]
RULE='The seed moves through G7 to Cmaj7. Each transformation preserves at least one identity: pitch order, contour, rhythm, register, or target schedule. Recovery cards train the nearest secure resolution after an unstable note.'
SESSION='Choose one target quality, one approach type, and one progression phrase. Play the target alone first. Sing the target. Add the approach at half speed. Preserve the barline and leave at least one complete beat of space after every two-bar statement.'
GATE='Complete all sixteen chord-tone target rotations and all twenty-four approach cells. Play all five C-major zone phrases and create one response in an adjacent zone. Play all sixteen enclosure cells and twelve delayed resolutions without losing the subdivision. Transform the seed motif in six ways and use all twelve recovery cards without stopping the form. Perform six major and six minor progression phrases in their printed registers. Perform both twelve-bar model solos and both sixteen-bar capstones on two separate days.'
SM={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6};TUNING={1:64,2:59,3:55,4:50,5:45,6:40}
ZONE_RULE='The first three bars establish the cadence; bar 4 closes with 7-5-3-R. Keep the same role schedule in both zones. The fretboard route changes, but the harmonic sentence remains identical.'
RESPONSE_RULE='After the written phrases, create a response in the next zone. Preserve the beat-one role and the four-note rhythm, but change the remaining three notes.'
EXPECTED_ROLES=['b3','5','b7','R','3','b7','5','3','3','5','7','R','7','5','3','R'];BOUNDS=[[0,5],[4,8],[7,12],[10,15],[12,17]]
def steps_for(old):
 ev=old['implementation']['events'];return [{'order':1,'action':'name_Dm7_G7_Cmaj7_Cmaj7_functions_play_and_sing_beat_one_targets','target_event_orders':[1,5,9,13],'target_notes':[ev[i-1]['printed_note'] for i in [1,5,9,13]],'target_preparation_outside_printed16':True,'source_page':1},{'order':2,'action':'perform_source_four_bar_sixteen_note_phrase_in_printed_zone','event_orders':list(range(1,17)),'bar_event_orders':[list(range(4*n+1,4*n+5)) for n in range(4)],'beat_one_roles':['b3','3','3','7'],'bar4_roles':['7','5','3','R'],'picks':None,'numeric_clock':None,'no_invented_midphrase_rest':True},{'order':3,'action':'user_report_fixed_role_schedule_and_changed_register_route','automatic_detection':False}]
def family_contract(olds):
 cases=[];steps=[]
 for n,old in enumerate(olds,1):
  case={'zone':n,'bounds':BOUNDS[n-1],'package_key':old['package_key'],'source_identity':old['source_identity'],'source_record':{**pin(PACKET),'line':81+n,'record_sha256':rh(old)},'response_source_events':old['implementation']['events']};cases.append(case)
  for st in steps_for(old):steps.append({**copy.deepcopy(st),'order':len(steps)+1,'source_case_key':old['package_key'],'zone':n})
 steps += [{'order':16,'action':'perform_selected_next_zone_response_after_all_five_written_phrases','response_events_from_selection':True,'preserve_first_beat_role_and_four_note_rhythm':True,'numeric_rhythm':None,'picks':None},{'order':17,'action':'user_report_all_written_zones_and_one_adjacent_response_finished','automatic_detection':False}]
 return {'schema':'fathom.private-manual-five-zone-family.v1','source_cases':cases,'steps':steps,'source_response_rule':{'physical_page':15,'exact_text':RESPONSE_RULE},'source_mastery_subset':{'physical_page':20,'exact_text':'Play all five C-major zone phrases and create one response in an adjacent zone.'},'selected_response_policy':'Select one forward-adjacent zone pair Z1→Z2 through Z4→Z5. Keep the target-zone first note of each bar and choose a three-cycle of its remaining printed chord tones. This finite option set is a private realization of the open source composition instruction, not an exhaustive source restriction or printed response.','printed_attacks':80,'selected_response_attacks':16,'response_not_printed_inventory':True,'all_source_mastery_claimed':False,'runtime_admitted':False,'grants_credit':False}
def validate_response(c,r,events):
 z=r['target_zone'];case=c['source_cases'][z-1];src=case['response_source_events'];assert len(events)==16
 for bar in range(4):
  a=src[4*bar:4*bar+4];b=events[4*bar:4*bar+4];fields=['string','fret','printed_note','role','tag'];sig=lambda x:tuple(x[k] for k in fields)
  assert sig(a[0])==sig(b[0]);assert sorted(sig(x) for x in a[1:])==sorted(sig(x) for x in b[1:]);assert all(x['printed_note']!=y['printed_note'] for x,y in zip(a[1:],b[1:]));assert all(case['bounds'][0]<=x['fret']<=case['bounds'][1] and x['onset_q'] is None and x['duration_q'] is None and x['pick'] is None for x in b);assert [x['slot'] for x in b]==[1,2,3,4] and all(x['bar']==bar+1 for x in b)
def family_selection(c,r):
 assert type(r) is dict and set(r)=={'contract_sha256','source_zone','target_zone','bar_cycles'},'SELECTION_FIELDS';assert r['contract_sha256']==rh(c),'STALE_CONTRACT';assert type(r['source_zone']) is int and 1<=r['source_zone']<=4,'SOURCE_ZONE';assert type(r['target_zone']) is int and r['target_zone']==r['source_zone']+1,'NEXT_ZONE';assert type(r['bar_cycles']) is list and len(r['bar_cycles'])==4 and all(x in ['left','right'] for x in r['bar_cycles']),'BAR_CYCLES';case=c['source_cases'][r['target_zone']-1];seq=[]
 for bar,cycle in enumerate(r['bar_cycles']):
  for slot,pos in enumerate([0,2,3,1] if cycle=='left' else [0,3,1,2],1):
   source=case['response_source_events'][4*bar+pos];seq.append({'order':len(seq)+1,'bar':bar+1,'slot':slot,**{k:source[k] for k in ['string','fret','printed_note','role','tag']},'onset_q':None,'duration_q':None,'pick':None,'source_event_order':source['order'],'source_case_key':case['package_key']})
 validate_response(c,r,seq);return {'source_zone':r['source_zone'],'target_zone':r['target_zone'],'bar_cycles':r['bar_cycles'],'selected_response_events':seq,'grants_credit':False}
def family_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','next_step':None}
 chosen=family_selection(c,r);state=module(VALIDATOR,'v').response_state(c,responses);step=copy.deepcopy(c['steps'][len(responses)]) if state=='IN_PROGRESS' else None
 if step and step['order']==16:step['selected_response_events']=chosen['selected_response_events']
 return {'state':state,'next_step':step,'selection':chosen,'performance_observed':False,'grants_credit':False}
def contract(old,familyref):
 return {'schema':'fathom.private-manual-zone-phrase.v1','package_key':old['package_key'],'steps':steps_for(old),'family_response_contract':familyref,'family_response_not_completed_by_single_child':True,'source_session_duties':{'physical_page':1,'exact_text':SESSION,'conditional_space_after_two_bar_statement_beats':1,'no_added_rest_in_this_four_bar_phrase':True,'other_session_duties_observed':False},'source_required_practice_duty':{'physical_page':20,'exact_text':GATE,'completed':None},'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'User report only, no physical/hearing/mastery/Attempt/credit inference.'},'printed_attacks':16,'printed_memberships':16,'fixed_bpm':None,'picks':None,'both_starts_required':None,'runtime_admitted':False,'grants_credit':False}
def selection(c,r):assert type(r) is dict and set(r)=={'package_key','contract_sha256'} and r['package_key']==c['package_key'] and r['contract_sha256']==rh(c),'EXACT_CHILD_SELECTION';return {'package_key':c['package_key'],'grants_credit':False}
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','next_step':None}
 selection(c,r);state=module(VALIDATOR,'v').response_state(c,responses);return {'state':state,'next_step':c['steps'][len(responses)] if state=='IN_PROGRESS' else None,'performance_observed':False,'grants_credit':False}
def make(old,data,familyref):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_source_zone_phrase';new['implementation']['manual_execution_contract']=contract(old,familyref);return new
def verify(old,new,data,familyref):assert new==make(old,data,familyref),'EXACT_CONTRACT';assert old['implementation']['events']==new['implementation']['events'] and old['timing_authority']==new['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not any(p.exists() for p in [RES/'handoff.json',OUT/'implementation-overlay.jsonl',OUT/'family-response-contract.json']),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==535 and ops==629;entries=[x for x in idx['children'] if x['level']==61 and 82<=x['line']<=86];olds=[eff[x['package_key']] for x in entries];assert len(olds)==5 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={i+1:p.extract_text(x_tolerance=1) for i,p in enumerate(pdf.pages)};assert len(pages)==20
  for n,t in pages.items():assert norm(t)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n))
  assert ZONE_RULE in norm(pages[14]) and RESPONSE_RULE in norm(pages[15]) and SESSION in norm(pages[1]) and GATE in norm(pages[20])
  for n,old in enumerate(olds,1):
   sc=old['implementation']['source_scope'];pnum=sc['locator']['physical_page'];crop=pdf.pages[pnum-1].crop(sc['locator']['derived_bbox']);raw=crop.extract_text(x_tolerance=1);assert raw==sc['pdf_excerpt'];score=crop.filter(lambda o:o.get('object_type')!='char' or 'Courier' in o.get('fontname','')).extract_text(x_tolerance=1);header=old['source_payload']['label'];assert header==f'Z{n} - frets {BOUNDS[n-1][0]}-{BOUNDS[n-1][1]}';hits=[i for i,t in enumerate(txt) if 952<=i+1<1012 and t==header];assert len(hits)==1;line=hits[0];literal='\n'.join(txt[line:line+10]);assert '\n'.join(t.lstrip() for t in txt[line+1:line+10])==score;rows={k:''.join(v.split('|')) for k,v in re.findall(r'^\s*(Nte|Rol|Tag|e|B|G|D|A|E)\|(.*)$',score,re.M)};assert set(rows)=={'Nte','Rol','Tag','e','B','G','D','A','E'} and all(len(v)==64 for v in rows.values());ev=old['implementation']['events'];assert len(ev)==16
   for j,e in enumerate(ev):
    vals={k:v[4*j:4*j+4].strip('-') for k,v in rows.items()};cs=[(SM[k],int(v)) for k,v in vals.items() if k in SM and v];assert len(cs)==1 and (e['string'],e['fret'])==cs[0] and e['printed_note']==vals['Nte'] and e['role']==vals['Rol']==EXPECTED_ROLES[j] and e['tag']==vals['Tag'] and e['order']==j+1 and e['printed_column']==4*j and 'pick' not in e and e['onset_q'] is None and e['duration_q'] is None and BOUNDS[n-1][0]<=e['fret']<=BOUNDS[n-1][1]
   d={'locator':{'line_start':line+1,'line_end':line+10},'literal':literal};data.append(d);checks.append({'key':old['package_key'],'zone':n,'bounds':BOUNDS[n-1],'PDF_page':pnum,'PDF_bbox':sc['locator']['derived_bbox'],'TXT_locator':d['locator']})
 fam=family_contract(olds);fbytes=(json.dumps(fam,ensure_ascii=False,indent=2)+'\n').encode();fp=OUT/'family-response-contract.json';fr={'path':str(fp.relative_to(ROOT)),'bytes':len(fbytes),'sha256':hashlib.sha256(fbytes).hexdigest()};source_records=list(map(json.loads,PACKET.read_text().splitlines()))
 for case in fam['source_cases']:assert rh(source_records[case['source_record']['line']-1])==case['source_record']['record_sha256']
 plans=[];frefusals=[]
 for z in range(1,5):
  for cycles in itertools.product(['left','right'],repeat=4):
   req={'contract_sha256':rh(fam),'source_zone':z,'target_zone':z+1,'bar_cycles':list(cycles)};plan=family_selection(fam,req);plans.append({'request':req,'selected_response_sha256':rh(plan['selected_response_events'])})
 goodfam=plans[0]['request'];complete=[{'step':i+1,'response':'acknowledged'} for i in range(17)];assert family_state(fam,goodfam,complete)['state']=='USER_REPORTED_STEPS_FINISHED' and len(family_state(fam,goodfam,complete[:15])['next_step']['selected_response_events'])==16
 for label,req,a in [('stale',dict(goodfam,contract_sha256='0'*64),[]),('Z6',dict(goodfam,source_zone=5,target_zone=6),[]),('nonadjacent',dict(goodfam,target_zone=3),[]),('bool_zone',dict(goodfam,source_zone=True),[]),('wrong_cycle',dict(goodfam,bar_cycles=['same']*4),[]),('skip_written',goodfam,[{'step':16,'response':'acknowledged'}]),('after_stop',goodfam,[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
  try:family_state(fam,req,a)
  except AssertionError:frefusals.append(label)
  else:raise AssertionError('FAMILY_REFUSAL_FAILED')
 for label,mut in [('changed_first_beat',lambda es:es[0].update(role='R')),('out_of_zone',lambda es:es[2].update(fret=24)),('invented_clock',lambda es:es[3].update(duration_q=[1,1])),('unchanged_others',lambda es:es.__setitem__(slice(1,4),[{**es[i],**{k:fam['source_cases'][1]['response_source_events'][i][k] for k in ['string','fret','printed_note','role','tag']}} for i in range(1,4)]))]:
  bad=family_selection(fam,goodfam)['selected_response_events'];mut(bad)
  try:validate_response(fam,goodfam,bad)
  except AssertionError:frefusals.append(label)
  else:raise AssertionError('BAD_RESPONSE_ACCEPTED')
 rows=[];changes=[];refusals=[];states=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d,fr);verify(old,new,d,fr);ct=new['implementation']['manual_execution_contract'];good={'package_key':old['package_key'],'contract_sha256':rh(ct)};completechild=[{'step':i+1,'response':'acknowledged'} for i in range(3)]
  for a,state in [([],'IN_PROGRESS'),(completechild,'USER_REPORTED_STEPS_FINISHED'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED')]:assert workflow_state(ct,good,a)['state']==state;states+=1
  assert workflow_state(ct,None,[])['state']=='AWAITING_SELECTION';states+=1
  for label,r,a in [('stale',dict(good,contract_sha256='0'*64),[]),('wrong_key',dict(good,package_key='x'),[]),('extra_pick',dict(good,start_stroke='D'),[]),('skip_phrase',good,[completechild[0],completechild[2]]),('after_retry',good,[{'step':1,'response':'needs_retry'},completechild[1]])]:
   try:workflow_state(ct,r,a)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for n in range(5):
  for label,mut in [('wrong_role',lambda x:x['implementation']['events'][0].update(role='R')),('wrong_fret',lambda x:x['implementation']['events'][0].update(fret=24)),('invent_pick',lambda x:x['implementation']['events'][0].update(pick='D')),('invent_time',lambda x:x['implementation']['events'][0].update(duration_q=[1,1])),('wrong_family',lambda x:x['implementation']['manual_execution_contract']['family_response_contract'].update(sha256='0'*64)),('claim_mastery',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True))]:
   bad=copy.deepcopy(rows[n]);mut(bad)
   try:verify(olds[n],bad,data[n],fr)
   except AssertionError:corruptions.append({'key':bad['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,row in zip(changes,rows):key=d['package_key'];eff[key]=row;cat[key]=d['new_category'];used.add(key)
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];assert len(eff)==2133 and len(used)==540 and rh(identity)==idx['ordered_identity_sha256'] and other()==before;cats=dict(Counter(cat.values()));assert cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':713,'implementation_or_interpretation_pending':782,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for r in refs:checkpin(r)
 fp.write_bytes(fbytes);checkpin(fr);packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'all20_pages_match_context':True,'preserved_attacks_memberships':80,'family_response_plans':plans,'family_response_refusals':frefusals,'child_workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2128,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'5 complete selected written-zone contracts and source-bound family response; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'family_response_contract':fr,'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':540,'unique_replaced_children':540,'total_replacement_operations':634,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'family':fr,'categories':cats,'response_plans':len(plans),'family_refusals':len(frefusals),'child_states':states,'workflow_refusals':len(refusals),'content_refusals':len(corruptions)}))
if __name__=='__main__':main()
