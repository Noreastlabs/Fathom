"""Thirty-five revised quality-specific seventh contracts and a source-bound family audit, private manual only."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level059_c_root_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'
s=importlib.util.spec_from_file_location('helpers',HELPER);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
compact,rh,sha,pin,checkpin,save,norm,module=h.compact,h.rh,h.sha,h.pin,h.checkpin,h.save,h.norm,h.module
BASE,FOLD,VALIDATOR=h.BASE,h.FOLD,h.VALIDATOR
NAME='finite-level060-remaining-families-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level060-low-e-m7-manual-r01/handoff.json';PACKET=ROOT/'Build/fullscope-private-b-r01/level060-r02/implementation.jsonl';PREIMAGE=ROOT/'Build/fullscope-private-b-r01/finite-level060-remaining-blocked-r01/implementation-overlay.jsonl'
PINS=[(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(FOLD,'f182c4c6a48140d0c7dc7a0a370e96ac862965f6859f0b6c5234137d85479d9d'),(VALIDATOR,'eaf1c992bd43ebe597ee77af9a42f708356c720cec57a9dcf7759581bf8166fa'),(HELPER,'b617c7a18a44f2a097afcba061d207c60366251a51b957960970699192c5c61b'),(PREV,'3e624d7316c1fec7afa58b1781f7de7de0d0d0be3707da62acb975a19d6f4759'),(PACKET,'adb0ca4e0a02e07832772bbb4180c7e1a57888076fde3e9d619f3224581d0794'),(PREIMAGE,'dcf05b92882df0d3a218afa4ccdb7fb6cc31b1000ca2e6c1f5ae68f94a34cc2b')]
AUDIT='Play roots in ascending order, then reverse the root order. Say the chord spelling before the blocked attack. If two strings ring together during economy picking, stop and repair the release before adding tempo.'
BOUNDARY='Use clean tone. Begin with one blocked chord, then the eight-note arpeggio mirror. Sweep only after alternate-picking note separation is reliable. Stop immediately if the hand grips, if adjacent notes ring together, or if the pick accelerates through the string crossing.'
GATE='Form and spell all 56 root/quality/family commands without sounding them. Perform all 56 blocked-plus-arpeggiated natural-root shapes. Use alternate and economy picking without overlapping strings. Maintain the stroke cycle through all eight seven-note loop cells. Accent guide tones and complete both same-root quality ladders. Track six major ii-V-I and six minor iiø-V-i progressions. Complete all six arpeggio-to-scale links and eight call/answer pairs. Perform both sixteen-bar capstones on two separate days.'
ALT=list('DUDUDUDU');ECO=list('DDDDUUUU');SM={'E':6,'A':5,'D':4,'G':3,'B':2}
CONFIG={6:('LOW-E-ROOT',[6,5,4,3],['R','b5','b7','b3'],[1,2,1,1],'minor-seven-flat-five'),7:('A-STRING-ROOT',[5,4,3,2],['R','5','7','3'],[1,3,2,4],'major-seven'),8:('A-STRING-ROOT',[5,4,3,2],['R','5','b7','3'],[1,3,1,4],'dominant-seven'),9:('A-STRING-ROOT',[5,4,3,2],['R','5','b7','b3'],[1,4,1,2],'minor-seven'),10:('A-STRING-ROOT',[5,4,3,2],['R','b5','b7','b3'],[1,2,1,3],'minor-seven-flat-five')}
def page(old):return old['implementation']['source_scope']['locator']['physical_page']
def guides(old):
 roles=CONFIG[page(old)][2];return [roles[3],roles[2]]
def rule(old):
 cfg=CONFIG[page(old)];strings='E-A-D-G' if cfg[0]=='LOW-E-ROOT' else 'A-D-G-B';return f'Active strings: {strings}. Role order from low to high: {"-".join(cfg[2])}. Practice the blocked voicing first, then the strict-alternate mirror. A second pass uses economy picking without allowing adjacent strings to overlap.'
def parse_grid(text):
 rows={k:v for k,v in re.findall(r'^\s*(Nte|Rol|Pck|B|G|D|A|E)\|(.*)$',text,re.M)};assert {'Nte','Rol','Pck'}.issubset(rows) and len(set(rows)&set(SM))==4 and all(len(v)==32 for v in rows.values()),'GRID_WIDTH';out=[]
 for n in range(8):
  vals={k:v[n*4:n*4+4].strip('-') for k,v in rows.items()};cs=[(SM[k],int(v)) for k,v in vals.items() if k in SM and v];assert len(cs)==1;out.append({'string':cs[0][0],'fret':cs[0][1],'printed_note':vals['Nte'],'role':vals['Rol'],'pick':vals['Pck']})
 return out

def steps_for(old,spelling):
 ev=old['implementation']['events'];guide={m['role']:m for m in ev[0]['members'] if m['role'] in guides(old)};assert set(guide)==set(guides(old))
 return [{'order':1,'action':'name_root_quality_spelling_active_zone_and_rehearse_accented_guide_tones','chord':ev[0]['chord'],'spelling':spelling,'active_strings':CONFIG[page(old)][1],'guide_tone_members':guide,'guide_order_from_explicit_selection':True,'guide_preparation_outside_printed9':True,'numeric_accent_strength':None,'source':{'physical_pages':[1,2],'guide_rule_bbox_pdf1':[552,162,748,183],'guide_rule':'The third and seventh carry function. Accent them before adding roots, fifths, scales, or speed.'}},{'order':2,'action':'perform_one_blocked_chord_then_eight_alternate_notes','event_orders':list(range(1,10)),'blocked_attack_count':1,'mirror_event_orders':list(range(2,10)),'mirror_picks':ALT,'source_page':page(old),'complete_spelling_before_blocked_attack':True},{'order':3,'action':'user_report_alternate_note_separation_reliable_before_economy','acknowledged_means_user_reports_reliable_separation':True,'needs_retry_or_stopped_ends_workflow':True,'automatic_detection':False,'source':{'physical_page':1,'exact_text':BOUNDARY}},{'order':4,'action':'perform_economy_eight_note_mirror_replay','event_orders':list(range(2,10)),'pick_override':ECO,'new_blocked_attack_selected':False,'release_each_string_before_next_begins':True,'source':{'physical_page':page(old),'exact_text':rule(old),'picking_page2':'ECO mirror: D D D D | U U U U'},'stop_and_repair_if_adjacent_strings_ring':True},{'order':5,'action':'self_report_quality_and_controlled_separation','automatic_detection':False}]
def family_contract(olds,parsed):
 cases=[];route=[];steps=[]
 for n,(old,data) in enumerate(zip(olds,parsed),1):cases.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'source_record':{**pin(PREIMAGE),'line':old['implementation']['events'][0]['source']['physical_page']*7-35+n,'record_sha256':rh(old)},'root_fret':old['implementation']['events'][0]['members'][0]['fret'],'chord':old['implementation']['events'][0]['chord'],'spelling':data['spelling'],'steps':steps_for(old,data['spelling'])})
 for direction,seq in [('ascending',cases),('descending',cases[::-1])]:
  for case in seq:
   route.append({'direction':direction,'package_key':case['package_key'],'source_record_sha256':case['source_record']['record_sha256']})
   for local in case['steps']:steps.append({**copy.deepcopy(local),'order':len(steps)+1,'source_case_key':case['package_key'],'source_case_record_sha256':case['source_record']['record_sha256'],'direction':direction})
 return {'schema':'fathom.private-manual-source-family-audit.v1','source_scope':f'Level60 PDF{page(old)} {CONFIG[page(old)][0]} {CONFIG[page(old)][4]} seven-root family audit','source_rule':{'physical_page':page(old),'exact_text':AUDIT},'source_cases':cases,'route':route,'steps':steps,'required_silent_work':{'source_page':1,'formations':56,'attestation_only':True},'guide_roles':guides(old),'performed':False,'print_inventory_changed':False,'runtime_admitted':False,'grants_credit':False,'fixed_bpm':None}
def contract(old,parsed,familyref):
 return {'schema':'fathom.private-manual-blocked-seventh-mirror.v1','package_key':old['package_key'],'selection':'Single nine-attack printed cell plus eight-note economy mirror; family audit is separately executable and unperformed.','steps':steps_for(old,parsed['spelling']),'required_silent_work':{'source_page':1,'formations':56,'required_user_report':'user_reports_complete','automatic_assessment':False},'guide_roles':guides(old),'family_audit_contract':familyref,'family_audit_required_by_source_but_not_completed_by_single_cell':True,'printed_attacks':9,'printed_memberships':12,'economy_replay_attacks':8,'guide_preparation_attacks':2,'unknown_additional_blocked_repetition_not_invented':True,'physical_boundary':{'source_page':1,'exact_text':BOUNDARY,'clean_tone_required':True,'user_reported_stop_is_terminal':True,'automated_detection':False},'response_contract':{'function':'workflow_state','validator':pin(VALIDATOR),'responses':['acknowledged','needs_retry','stopped'],'meaning':'Manual user report, no measured acoustic/physical performance, Attempt, mastery or credit.'},'source_required_practice_duty':{'physical_page':20,'exact_text':GATE,'completed':None},'broader_both_starts_required_by_source':None,'fixed_bpm':None,'acoustic_gate':None,'runtime_admitted':False,'grants_credit':False,'automated_assessment':False}
def choose_common(c,r,child):
 fields={'contract_sha256','silent56_report','guide_role_order'}|({'package_key'} if child else set());assert type(r) is dict and set(r)==fields,'SELECTION_FIELDS';assert r['contract_sha256']==rh(c),'STALE_CONTRACT'
 if child:assert r['package_key']==c['package_key'],'WRONG_CHILD'
 assert type(r['silent56_report']) is str and r['silent56_report']=='user_reports_complete','SILENT_PREREQUISITE';assert type(r['guide_role_order']) is list and r['guide_role_order'] in [c['guide_roles'],list(reversed(c['guide_roles']))],'GUIDE_SELECTION';return {'contract_sha256':rh(c),'silent56_prerequisite':'user_reports_complete_not_observed','guide_role_order':r['guide_role_order'],'runtime_admitted':False,'grants_credit':False}
def selection(c,r):return choose_common(c,r,True)
def family_selection(c,r):return choose_common(c,r,False)
def state_for(c,r,responses,child):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','next_step':None,'grants_credit':False}
 chosen=choose_common(c,r,child);state=module(VALIDATOR,'v').response_state(c,responses);return {'state':state,'next_step':c['steps'][len(responses)] if state=='IN_PROGRESS' else None,'selection':chosen,'performance_observed':False,'grants_credit':False}
def workflow_state(c,r,responses):return state_for(c,r,responses,True)
def family_workflow_state(c,r,responses):return state_for(c,r,responses,False)
def make(old,parsed,familyref):
 n=copy.deepcopy(old);n['source_refs'][0]['locator']=parsed['locator'];n['source_payload']['txt_excerpt']=parsed['literal'];n['source_payload']['source_discrepancy']=[{'class':'exact_txt_header_and_grid_verified','prior_diagnostic':old['source_payload']['source_discrepancy'],'decision':'Unique original TXT card agrees with original PDF spelling/frets/fingers and all mirror contacts.'}];n['implementation']['kind']='manual_blocked_seventh_mirror_workflow';del n['implementation']['pending_contract_scope'];n['implementation']['manual_execution_contract']=contract(old,parsed,familyref);n['implementation']['context_tasks'][2]['instruction']=rule(old);return n
def verify(old,new,parsed,familyref):assert new==make(old,parsed,familyref),'EXACT_SOURCE_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'PREDECESSOR_MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not any(p.exists() for p in [RES/'handoff.json',OUT/'implementation-overlay.jsonl',*[OUT/f'family-p{n:03}.json' for n in CONFIG]]),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx,prior,effective,catmap,used,ops=module(FOLD,'fold').fold_chain(BASE,PREV);assert len(used)==486 and ops==545
 selected=[x for x in idx['children'] if x['level']==60 and 23<=x['line']<=57];preimages=list(map(json.loads,PREIMAGE.read_text().splitlines()));assert len(preimages)==42;olds=preimages[7:];assert len(selected)==len(olds)==35
 for ent,old in zip(selected,olds):assert ent['package_key']==old['package_key'] and rh(effective[ent['package_key']])==rh(old) and catmap[ent['package_key']]=='implementation_or_interpretation_pending'
 refs=olds[0]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());crops={}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  assert len(pdf.pages)==20;pages={n+1:p.extract_text(x_tolerance=1) for n,p in enumerate(pdf.pages)}
  guide_bbox=[552,162,748,183];guide_excerpt=pdf.pages[0].crop(guide_bbox).extract_text(x_tolerance=1)
  for n,t in pages.items():assert norm(t)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n)),'FULL_BOOK_CONTEXT'
  for old in olds:crops[old['package_key']]=pdf.pages[page(old)-1].crop(old['implementation']['source_scope']['locator']['derived_bbox']).extract_text(x_tolerance=1)
 assert BOUNDARY in norm(pages[1]) and GATE in norm(pages[20]) and '56 root/quality/family formations are performed before the sounded exercises.' in norm(pages[1]) and 'ECO mirror: D D D D | U U U U' in norm(pages[2]) and 'The third and seventh carry function. Accent them before adding roots, fifths, scales, or speed.' == norm(guide_excerpt)
 parsed=[];checks=[]
 for n,old in enumerate(olds):
  cfg=CONFIG[page(old)];assert rule(old) in norm(pages[page(old)]) and AUDIT in norm(pages[page(old)]);crop=crops[old['package_key']];assert norm(crop)==norm(old['implementation']['source_scope']['pdf_excerpt']);lines=crop.splitlines();ev=old['implementation']['events'];chord=ev[0]['chord'];rootfret=ev[0]['members'][0]['fret'];assert lines[0]==f'{chord} - {cfg[0]} fret {rootfret}'+(' Family audit' if n%7==6 else '')
  m=re.fullmatch(r'Chord (.+) \| Frets ([0-9-]+) \| Fingers ([0-9-]+) \| 9 attacks',lines[1]);assert m;spelling=m[1].split('-');frets=list(map(int,m[2].split('-')));fingers=list(map(int,m[3].split('-')));hits=[i for i,t in enumerate(txt) if t==f'{chord} | root fret {rootfret} | spelling {m[1]} | frets {m[2]} | fingers {m[3]} | 1 blocked + 8 mirror = 9 attacks'];assert len(hits)==1;line=hits[0];literal='\n'.join(txt[line:line+8]);source=parse_grid(crop);assert source==parse_grid(literal) and [x['pick'] for x in source]==ALT
  assert len(ev)==9 and len(ev[0]['members'])==4 and [x['fret'] for x in ev[0]['members']]==frets and [x['finger'] for x in ev[0]['members']]==fingers==cfg[3] and [x['string'] for x in ev[0]['members']]==cfg[1] and [x['role'] for x in ev[0]['members']]==cfg[2] and set(spelling)=={x['printed_note'] for x in ev[0]['members']}
  for j,(e,x) in enumerate(zip(ev[1:],source)):assert {k:e[k] for k in x}==x and e['order']==j+2 and e['printed_column']==j*4 and e['onset_q'] is None and e['duration_q'] is None
  for memb,x in zip(ev[0]['members'],source[:4]):assert {k:memb[k] for k in ['string','fret','printed_note','role']}=={k:x[k] for k in ['string','fret','printed_note','role']}
  parsed.append({'spelling':spelling,'locator':{'line_start':line+1,'line_end':line+8},'literal':literal});checks.append({'key':old['package_key'],'physical_page':page(old),'PDF_bbox':old['implementation']['source_scope']['locator']['derived_bbox'],'TXT_locator':parsed[-1]['locator'],'chord':chord,'root_fret':rootfret,'spelling':spelling,'frets':frets,'fingers':fingers,'guide_roles':guides(old)})
 families={};familyrefs={};familybytes={}
 for start in range(0,35,7):
  group=olds[start:start+7];fam=family_contract(group,parsed[start:start+7]);p=page(group[0]);data=(json.dumps(fam,ensure_ascii=False,indent=2)+'\n').encode();path=OUT/f'family-p{p:03}.json';ref={'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()};families[p]=fam;familyrefs[p]=ref;familybytes[p]=data
  assert len(fam['steps'])==70 and len(fam['route'])==14 and [x['root_fret'] for x in fam['source_cases']]==([1,3,5,7,8,10,12] if p==6 else [2,3,5,7,8,10,12])
  for case in fam['source_cases']:assert rh(preimages[case['source_record']['line']-1])==case['source_record']['record_sha256']
 rows=[];changes=[];refusals=[];states=choices=0
 def refuse(label,fn,key):
  try:fn()
  except AssertionError:refusals.append({'key':key,'reason':label})
  else:raise AssertionError('INVALID_ACCEPTED:'+label)
 for ent,old,data in zip(selected,olds,parsed):
  fr=familyrefs[page(old)];new=make(old,data,fr);verify(old,new,data,fr);c=new['implementation']['manual_execution_contract'];good={'package_key':old['package_key'],'contract_sha256':rh(c),'silent56_report':'user_reports_complete','guide_role_order':guides(old)}
  for order in [guides(old),guides(old)[::-1]]:assert selection(c,dict(good,guide_role_order=order))['guide_role_order']==order;choices+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';states+=1
  for a,state in [([],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED'),([{'step':n+1,'response':'acknowledged'} for n in range(5)],'USER_REPORTED_STEPS_FINISHED')]:assert workflow_state(c,good,a)['state']==state;states+=1
  before=[{'step':1,'response':'acknowledged'},{'step':2,'response':'acknowledged'}];assert workflow_state(c,good,before)['next_step']['action']=='user_report_alternate_note_separation_reliable_before_economy';assert workflow_state(c,good,before+[{'step':3,'response':'acknowledged'}])['next_step']['action']=='perform_economy_eight_note_mirror_replay';assert workflow_state(c,good,before+[{'step':3,'response':'needs_retry'}])['next_step'] is None;states+=3
  wrongguide=['3','7'] if guides(old)!=['3','7'] else ['b3','b7']
  for label,r,a in [('wrong_key',dict(good,package_key='other'),[]),('stale',dict(good,contract_sha256='0'*64),[]),('no_silent',dict(good,silent56_report='not_yet'),[]),('bool_silent',dict(good,silent56_report=True),[]),('wrong_quality',dict(good,guide_role_order=wrongguide),[]),('duplicate_guide',dict(good,guide_role_order=[guides(old)[0]]*2),[]),('other_start',dict(good,start_stroke='U'),[]),('skip_gate',good,before+[{'step':4,'response':'acknowledged'}]),('retry_then_economy',good,before+[{'step':3,'response':'needs_retry'},{'step':4,'response':'acknowledged'}]),('before_choice',None,[{'step':1,'response':'acknowledged'}])]:refuse(label,lambda:workflow_state(c,r,a),old['package_key'])
  rows.append(new);changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':rh(old),'previous_effective_record_sha256':rh(old),'original_base_record_sha256':ent['record_sha256'],'replacement_basis':'previous_effective_record','overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':catmap[old['package_key']],'new_category':'complete_manual_nonplayback_contract'})
 familychecks=[]
 for p,fam in families.items():
  fg={'contract_sha256':rh(fam),'silent56_report':'user_reports_complete','guide_role_order':fam['guide_roles']};complete=[{'step':i+1,'response':'acknowledged'} for i in range(70)]
  for order in [fam['guide_roles'],fam['guide_roles'][::-1]]:assert family_selection(fam,dict(fg,guide_role_order=order))['guide_role_order']==order
  assert family_workflow_state(fam,fg,complete)['state']=='USER_REPORTED_STEPS_FINISHED' and family_workflow_state(fam,fg,complete[:35])['state']=='IN_PROGRESS' and fam['steps'][35]['direction']=='descending'
  assert [x['package_key'] for x in fam['route'][7:]]==list(reversed([x['package_key'] for x in fam['route'][:7]]))
  for prefix in range(2,70,5):assert family_workflow_state(fam,fg,complete[:prefix])['next_step']['action']=='user_report_alternate_note_separation_reliable_before_economy' and family_workflow_state(fam,fg,complete[:prefix]+[{'step':prefix+1,'response':'stopped'}])['next_step'] is None
  familychecks.append({'page':p,'full_completion':True,'reverse_route':True,'terminal_gate_positions':list(range(3,71,5)),'source_preimages':7})
  for label,req,a in [('stale',dict(fg,contract_sha256='0'*64),[]),('without_prerequisite',dict(fg,silent56_report='unknown'),[]),('skip_reverse',fg,complete[:35]+[{'step':70,'response':'acknowledged'}]),('after_stop',fg,[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:refuse(label,lambda:family_workflow_state(fam,req,a),f'family_p{p}')
 corruptions=[]
 for n in [0,3,6,7,10,13,14,17,20,21,24,27,28,31,34]:
  for label,mut in [('lost_block',lambda x:x['implementation']['events'].pop(0)),('role_R_as_rest',lambda x:x['implementation']['events'][1].update(kind='rest')),('wrong_finger',lambda x:x['implementation']['events'][0]['members'][0].update(finger=4)),('lost_gate',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(2)),('economy_as_alternate',lambda x:x['implementation']['manual_execution_contract']['steps'][3].update(pick_override=ALT)),('wrong_family_ref',lambda x:x['implementation']['manual_execution_contract']['family_audit_contract'].update(sha256='0'*64)),('invent_clock',lambda x:x['implementation']['events'][0].update(duration_q=[1,1])),('false_mastery',lambda x:x['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True)),('wrong_string_family',lambda x:x['implementation']['manual_execution_contract']['steps'][0].update(active_strings=[1,2,3,4]))]:
   bad=copy.deepcopy(rows[n]);mut(bad)
   try:verify(olds[n],bad,parsed[n],familyrefs[page(olds[n])])
   except AssertionError:corruptions.append({'key':bad['package_key'],'reason':label})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 keys={x['package_key'] for x in selected};other=lambda:rh([[x['package_key'],rh(effective[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,row in zip(changes,rows):key=d['package_key'];assert key in used and rh(effective[key])==d['previous_effective_record_sha256'];effective[key]=row;catmap[key]=d['new_category']
 identity=[[x['package_key'],effective[x['package_key']]['source_identity']] for x in idx['children']];assert len(effective)==2133 and len(used)==486 and rh(identity)==idx['ordered_identity_sha256'] and other()==before;cats=dict(Counter(catmap.values()));assert cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':659,'implementation_or_interpretation_pending':836,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 for p,data in familybytes.items():path=ROOT/familyrefs[p]['path'];path.write_bytes(data);checkpin(familyrefs[p])
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 save(RES/'targeted-validation.json',{'result':'PASS','exact_cards':35,'preserved_printed_attacks':315,'preserved_memberships':420,'all20_pages_match_context':True,'guide_source':{'physical_page':1,'bbox':guide_bbox,'exact_text':guide_excerpt},'source_checks':checks,'valid_guide_order_choices':choices,'workflow_states':states,'family_checks':familychecks,'workflow_refusals':refusals,'content_refusals':corruptions,'unchanged_other_rows':2098,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'35 existing corrected seventh cells now complete manual contracts with five source-bound family audits; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'family_audit_contracts':list(familyrefs.values()),'changes':changes,'revision_of_existing_overlay':True,'changed_existing_overlay_keys':35,'newly_replaced_keys':0,'strict_semantics':'Replace exactly35 prior effective records using previous_effective_record preimages, never append.315 source attacks420 memberships unchanged. Five family audits reference immutable source preimages lines8–42, not output self-references. Manual prerequisites, reliability and completion are user reports only.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':486,'unique_replaced_children':486,'total_replacement_operations':580,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'families':list(familyrefs.values()),'categories':cats,'workflow_states':states,'workflow_refusals':len(refusals),'content_refusals':len(corruptions)}))
if __name__=='__main__':main()
