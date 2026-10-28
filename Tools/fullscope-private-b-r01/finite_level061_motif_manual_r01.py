"""Five source-defined motifs, exact harmonic-tag repair and manual target workflow."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level059_c_root_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'
s=importlib.util.spec_from_file_location('helpers',HELPER);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
compact,rh,sha,pin,checkpin,save,norm,module=h.compact,h.rh,h.sha,h.pin,h.checkpin,h.save,h.norm,h.module
BASE,FOLD,VALIDATOR=h.BASE,h.FOLD,h.VALIDATOR
NAME='finite-level061-motif-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level060-framing-manual-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level061-r02/implementation.jsonl'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(FOLD,'f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa'),(PREV,'aff55aa109be45338369f6c570ea0600c9c97dd9063add6a32dc41178a7f57cb'),(PACKET,'c13b9ad0a1b3779166e324fb2c3cfbf70a72c4185cca8af6ae61d5bd0b0561ab')]
RULE='The seed moves through G7 to Cmaj7. Each transformation preserves at least one identity: pitch order, contour, rhythm, register, or target schedule. Recovery cards train the nearest secure resolution after an unstable note.'
SESSION='Choose one target quality, one approach type, and one progression phrase. Play the target alone first. Sing the target. Add the approach at half speed. Preserve the barline and leave at least one complete beat of space after every two-bar statement.'
GATE='Complete all sixteen chord-tone target rotations and all twenty-four approach cells. Play all five C-major zone phrases and create one response in an adjacent zone. Play all sixteen enclosure cells and twelve delayed resolutions without losing the subdivision. Transform the seed motif in six ways and use all twelve recovery cards without stopping the form. Perform six major and six minor progression phrases in their printed registers. Perform both twelve-bar model solos and both sixteen-bar capstones on two separate days.'
SM={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6};TUNING={1:64,2:59,3:55,4:50,5:45,6:40}
def corrected_events(old):
 ev=copy.deepcopy(old['implementation']['events'])
 for i,e in enumerate(ev):e['tag']='G7' if i<4 else 'Cmaj';e['harmonic_context_chord']='G7' if i<4 else 'Cmaj7'
 return ev

def contract(old,data):
 ev=corrected_events(old);code=data['code'];fixed={'H5':[2,4,6,8],'H6':[3,7]}.get(code);approach={'H5':[{'approach_orders':[i-1],'target_order':i} for i in [2,4,6,8]],'H6':[{'approach_orders':[1,2],'target_order':3},{'approach_orders':[5,6],'target_order':7}]}.get(code,[])
 identity={'H1':{'preserved':'Source seed order','reference':'self'},'H3':{'preserved':'G7 then Cmaj7 functions; each four-note pitch-class group reverses the seed','reference':'H1','strict_monotonic_pitch_contour_claimed':False},'H4':{'preserved':'Seed pitch-class and role order','reference':'H1','semitone_offsets_from_source_seed':[12,12,12,12,12,12,0,0],'uniform_octave_shift_claimed':False},'H5':{'preserved':'G7/Cmaj7 target schedule','chromatic_below_target_pairs':approach},'H6':{'preserved':'G7/Cmaj7 target schedule','above_below_target_enclosures':approach,'fill_orders':[4,8]}}[code]
 return {'schema':'fathom.private-manual-chord-tone-motif.v1','package_key':old['package_key'],'motif_code':code,'allowed_target_orders_by_chord':[[1,2,3,4],[5,6,7,8]] if fixed is None else None,'required_target_orders':fixed,'steps':[{'order':1,'action':'name_G7_Cmaj7_target_functions_play_selected_targets_alone_then_sing','selected_target_events_from_selection':True,'target_attack_and_singing_outside_printed8':True,'source':{'physical_page':1,'exact_text':SESSION}},{'order':2,'action':'practice_source_approach_target_patterns_at_relative_half_speed' if approach else 'name_identity_preserved_or_changed_from_source_seed','approach_target_patterns':approach,'relative_speed_ratio_to_learner_reference':[1,2] if approach else None,'numeric_bpm':None,'identity_contract':identity,'no_source_approach_claim_for_target_only_card':not bool(approach)},{'order':3,'action':'perform_exact_eight_note_motif_across_G7_Cmaj7','event_orders':list(range(1,9)),'chord_groups':[{'chord':'G7','event_orders':[1,2,3,4]},{'chord':'Cmaj7','event_orders':[5,6,7,8]}],'picks':None,'temporary_approach_orders':[e['order'] for e in ev if e['role']=='app'],'target_orders_from_selection':True,'target_receives_harmonic_weight':True,'avoid_stopping_after_first_group':True},{'order':4,'action':'leave_at_least_one_source_beat_of_space_after_two_bar_statement','minimum_source_beats':1,'quarter_note_duration_q':None,'beat_duration_seconds':None,'manual_user_report_only':True,'source':{'physical_page':1,'exact_text':SESSION}},{'order':5,'action':'user_report_target_remains_clear_and_motif_identity_preserved','automatic_detection':False}],'source_rule':{'physical_page':16,'exact_text':RULE},'source_required_practice_duty':{'physical_page':20,'exact_text':GATE,'completed':None,'all_six_transformations_claimed':False,'H2_source_ambiguity_unresolved':True},'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'Manual user report only; no observed hearing, performance, mastery, Attempt or credit.'},'printed_attacks':8,'printed_memberships':8,'source_picking':None,'both_starts_required':None,'fixed_bpm':None,'runtime_admitted':False,'grants_credit':False,'automated_assessment':False}
def selection(c,r):
 assert type(r) is dict and set(r)=={'package_key','contract_sha256','target_orders'},'SELECTION_FIELDS';assert r['package_key']==c['package_key'],'WRONG_KEY';assert r['contract_sha256']==rh(c),'STALE_CONTRACT';orders=r['target_orders'];assert type(orders) is list and all(type(x) is int for x in orders),'TARGET_TYPE'
 if c['required_target_orders'] is not None:assert orders==c['required_target_orders'],'FIXED_SOURCE_TARGETS'
 else:assert len(orders)==2 and all(x in group for x,group in zip(orders,c['allowed_target_orders_by_chord'])),'TARGET_CHORD_SCOPE'
 return {'target_orders':orders,'runtime_admitted':False,'grants_credit':False}
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','next_step':None,'grants_credit':False}
 chosen=selection(c,r);state=module(VALIDATOR,'v').response_state(c,responses);step=copy.deepcopy(c['steps'][len(responses)]) if state=='IN_PROGRESS' else None
 if step:step['selected_target_orders']=chosen['target_orders']
 return {'state':state,'next_step':step,'selection':chosen,'performance_observed':False,'grants_credit':False}
def make(old,data):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=data['locator'];new['source_payload']['txt_excerpt']=data['literal'];new['implementation']['kind']='manual_source_motif_target_workflow';new['implementation']['events']=corrected_events(old);new['implementation']['manual_execution_contract']=contract(old,data);new['implementation']['harmonic_tag_correction']={'printed_Tag_grid':data['printed_tag'],'four_column_cells':['G7']*4+['Cmaj']*4,'normalized_chords':['G7']*4+['Cmaj7']*4,'normalization_authority':{'physical_page':16,'exact_text':RULE},'prior_tags':[e.get('tag') for e in old['implementation']['events']]};return new
def verify(old,new,data):
 assert new==make(old,data),'EXACT_CONTRACT';strip=lambda e:{k:v for k,v in e.items() if k not in ['tag','harmonic_context_chord']};assert [strip(e) for e in old['implementation']['events']]==[strip(e) for e in new['implementation']['events']] and old['timing_authority']==new['timing_authority'],'MUSICAL_FIELDS_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,eff,cat,used,ops=module(FOLD,'f').fold_chain(BASE,PREV);assert len(used)==530 and ops==624;entries=[x for x in idx['children'] if x['level']==61 and 99<=x['line']<=103];olds=[eff[x['package_key']] for x in entries];assert len(olds)==5 and all(x['package_key'] not in used and rh(eff[x['package_key']])==x['record_sha256'] for x in entries)
 refs=olds[0]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());data=[];checks=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={i+1:p.extract_text(x_tolerance=1) for i,p in enumerate(pdf.pages)};assert len(pages)==20
  for n,t in pages.items():assert norm(t)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n))
  assert RULE in norm(pages[16]) and SESSION in norm(pages[1]) and GATE in norm(pages[20])
  for old in olds:
   sc=old['implementation']['source_scope'];crop=pdf.pages[15].crop(sc['locator']['derived_bbox']).extract_text(x_tolerance=1);assert crop==sc['pdf_excerpt'];header=old['source_payload']['label'];assert header in crop;code=header[:2];assert code in ['H1','H3','H4','H5','H6'];hits=[i for i,t in enumerate(txt) if 1012<=i+1<=1078 and t==header];assert len(hits)==1;line=hits[0];literal='\n'.join(txt[line:line+10]);rows={k:''.join(v.split('|')) for k,v in re.findall(r'^\s*(Nte|Rol|Tag|e|B|G|D|A|E)\|(.*)$',literal,re.M)};assert set(rows)=={'Nte','Rol','Tag','e','B','G','D','A','E'} and all(len(v)==32 for v in rows.values())
   for label in ['Nte','Rol']:
    value=re.search(label+r'\|([^\n]+)',crop)[1].replace('|','');assert value==rows[label]
   ev=old['implementation']['events'];assert len(ev)==8
   for j,e in enumerate(ev):
    vals={k:v[4*j:4*j+4].strip('-') for k,v in rows.items()};cs=[(SM[k],int(v)) for k,v in vals.items() if k in SM and v];assert len(cs)==1 and (e['string'],e['fret'])==cs[0] and e['printed_note']==vals['Nte'] and e['role']==vals['Rol'] and e['order']==j+1 and e['printed_column']==j*4 and 'pick' not in e and e['onset_q'] is None and e['duration_q'] is None;assert vals['Tag']==('G7' if j<4 else 'Cmaj')
   d={'code':code,'locator':{'line_start':line+1,'line_end':line+10},'literal':literal,'printed_tag':rows['Tag']};data.append(d);checks.append({'key':old['package_key'],'code':code,'original_PDF16_bbox':sc['locator']['derived_bbox'],'TXT_contact_locator':d['locator'],'PDF_note_role_match':True,'TXT_only_string_fret_authority':True,'old_tags':[e.get('tag') for e in ev],'parsed_printed_tags':['G7']*4+['Cmaj']*4})
 seed=olds[0]['implementation']['events'];rev=olds[1]['implementation']['events'];shift=olds[2]['implementation']['events'];assert [e['printed_note'] for e in rev]==[e['printed_note'] for e in reversed(seed[:4])]+[e['printed_note'] for e in reversed(seed[4:])];offsets=[TUNING[b['string']]+b['fret']-TUNING[a['string']]-a['fret'] for a,b in zip(seed,shift)];assert offsets==[12]*6+[0]*2
 for n,patterns in [(3,[([1],2),([3],4),([5],6),([7],8)]),(4,[([1,2],3),([5,6],7)])]:
  ev=olds[n]['implementation']['events']
  for approaches,target in patterns:
   target_pitch=TUNING[ev[target-1]['string']]+ev[target-1]['fret'];diff=[TUNING[ev[i-1]['string']]+ev[i-1]['fret']-target_pitch for i in approaches];assert diff==([-1] if n==3 else [1,-1])
 rows=[];changes=[];refusals=[];states=choices=0
 for ent,old,d in zip(entries,olds,data):
  new=make(old,d);verify(old,new,d);ct=new['implementation']['manual_execution_contract'];targetsets=[ct['required_target_orders']] if ct['required_target_orders'] is not None else [[a,b] for a in range(1,5) for b in range(5,9)];good={'package_key':old['package_key'],'contract_sha256':rh(ct),'target_orders':targetsets[0]}
  for targets in targetsets:assert selection(ct,dict(good,target_orders=targets))['target_orders']==targets;choices+=1
  complete=[{'step':i+1,'response':'acknowledged'} for i in range(5)]
  for a,state in [([],'IN_PROGRESS'),(complete,'USER_REPORTED_STEPS_FINISHED'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED')]:assert workflow_state(ct,good,a)['state']==state;states+=1
  assert workflow_state(ct,None,[])['state']=='AWAITING_SELECTION' and workflow_state(ct,good,complete[:3])['next_step']['minimum_source_beats']==1;states+=2
  for label,r,a in [('stale',dict(good,contract_sha256='0'*64),[]),('wrong_key',dict(good,package_key='x'),[]),('wrong_target_scope',dict(good,target_orders=[1,2]),[]),('boolean_target',dict(good,target_orders=[True,5]),[]),('extra_pick',dict(good,start_stroke='D'),[]),('skip_space',good,complete[:3]+[complete[4]]),('continue_after_retry',good,[{'step':1,'response':'needs_retry'},complete[1]]),('before_choice',None,complete[:1])]:
   try:workflow_state(ct,r,a)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':label})
   else:raise AssertionError('WORKFLOW_REFUSAL_FAILED')
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':cat[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for n in range(5):
  for label,mut in [('merged_tag',lambda x:x['implementation']['events'][4].update(tag='CmajCmajCmajCmaj')),('wrong_chord',lambda x:x['implementation']['events'][7].update(harmonic_context_chord='G7')),('wrong_fret',lambda x:x['implementation']['events'][0].update(fret=0)),('invent_pick',lambda x:x['implementation']['events'][0].update(pick='D')),('invent_time',lambda x:x['implementation']['events'][0].update(duration_q=[1,1])),('lost_space',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(3)),('claim_six_transformations',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(all_six_transformations_claimed=True))]:
   bad=copy.deepcopy(rows[n]);mut(bad)
   try:verify(olds[n],bad,data[n])
   except AssertionError:corruptions.append({'key':bad['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in entries};other=lambda:rh([[x['package_key'],rh(eff[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,row in zip(changes,rows):key=d['package_key'];eff[key]=row;cat[key]=d['new_category'];used.add(key)
 identity=[[x['package_key'],eff[x['package_key']]['source_identity']] for x in idx['children']];assert len(eff)==2133 and len(used)==535 and rh(identity)==idx['ordered_identity_sha256'] and other()==before;cats=dict(Counter(cat.values()));assert cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':708,'implementation_or_interpretation_pending':787,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for r in refs:checkpin(r)
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows));save(RES/'targeted-validation.json',{'result':'PASS','source_checks':checks,'all20_pages_match_context':True,'preserved_musical_attacks_memberships':40,'tag_cells_corrected':20,'normalized_harmonic_contexts_added':40,'register_shift_semitones':offsets,'source_approach_offsets_verified':True,'target_choices':choices,'workflow_states':states,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2128,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'5 complete selected motif manual contracts and exact harmonic-tag repair; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':535,'unique_replaced_children':535,'total_replacement_operations':629,'ordered_identity_sha256':rh(identity),'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'target_choices':choices,'states':states,'workflow_refusals':len(refusals),'content_refusals':len(corruptions)}))
if __name__=='__main__':main()
