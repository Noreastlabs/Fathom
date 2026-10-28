"""Two source-exact manual sixteen-bar capstone workflows; no inferred audio clock."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
from collections import Counter
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];HELPER=ROOT/'Tools/fullscope-private-b-r01/finite_level062_bridge_manual_r01.py';assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='38530b64c9ac9ba1011bf825d389375fffbaa29d79aef0ee5103a1265ed3cda8'
s=importlib.util.spec_from_file_location('bridge',HELPER);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
compact,rh,sha,pin,checkpin,save,norm,module=b.compact,b.rh,b.sha,b.pin,b.checkpin,b.save,b.norm,b.module
BASE,PACKET,FOLD,VALIDATOR=b.BASE,b.PACKET,b.FOLD,b.VALIDATOR
NAME='finite-level062-capstone-manual-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME;PREV=ROOT/'Results/fullscope-private-b-r01/finite-level062-approach-role-fields-r01/handoff.json'
PINS=[(p,d) for p,d in b.PINS if p!=b.PREV]+[(HELPER,'38530b64c9ac9ba1011bf825d389375fffbaa29d79aef0ee5103a1265ed3cda8'),(PREV,'0638f1e6714cfdd011eedd38b730ba187aa0d7a184c7e94bd71a65566b3a03e1')]
RULES={17:'Each four-bar block uses the three-bar diagonal route followed by a descending tonic arpeggio. Do not reset the pick cycle or hand position between keys. Announce the next key during beat 4 of the final tonic bar.',18:'The dominant third must remain theoretically and aurally clear. Use strict alternate picking first; economy motion may be added only across adjacent strings after every note is clean.'}
GATE='Complete both sixteen-bar capstones without resetting the pick cycle or losing the key sequence.'
def contract(old,blocks):
 page=old['implementation']['source_scope']['locator']['physical_page'];groups=[bar for key in blocks for bar in key['bars']];c=b.contract(old,groups,RULES[page]);c.update(schema='fathom.private-manual-sixteen-bar-capstone.v1',selection='One exact64-contact/16-bar/four-key capstone in manual practice; numeric timing remains unspecified.',start_scope_status='Both-start requirement not established for Module I; explicit choice is separate from source duty.')
 c['steps'][0].update(action='name_four_key_order_and_air_pick_all64_contacts',key_blocks=blocks,source={'physical_page':page,'exact_governing_paragraph':RULES[page]})
 c['steps'][2].update(action='perform_one_complete_manual_sixteen_bar_capstone',event_orders=list(range(1,65)),key_blocks=blocks,preserve_key_sequence=True,preserve_pick_cycle_across_key_boundaries=True,printed_role_emphasis={'event_orders':list(range(1,65,4)),'marker':'>','qualitative_only':True,'velocity':None},source_contact_authority='Original TXT four-key scores matched to four individual original PDF score blocks.',selected_pass_count=1,automatic_loop_or_wrap=False)
 if page==17:
  c['steps'][2]['key_transition_tasks']=[{'after_key_block':n+1,'during_source_bar':4*(n+1),'source_beat_label':4,'action':'announce_next_printed_key','next_key':blocks[n+1]['key'],'numeric_onset':None,'source_page':17} for n in range(3)];c['steps'][2]['do_not_reset_hand_position_between_keys']=True;c['steps'][2]['end_boundary']='One selected printed pass ends after the fourth key; no unprinted next key or loop is generated.'
 else:
  c['steps'][2]['dominant_third_tasks']=[{'key':block['key'],'chord':block['bars'][1]['chord'],'event_order':n*16+5,'printed_note':old['implementation']['events'][n*16+4]['printed_note'],'role':'3','action':'name_theoretical_dominant_third_and_keep_it_clear','automated_aural_assessment':False,'source_page':18} for n,block in enumerate(blocks)]
 c['steps'][3]['action']='self_report_full_key_sequence_shift_and_pick_continuity'
 c['source_required_practice_duty']={'physical_page':20,'txt_line':870,'exact_text':GATE,'required_capstones':2,'scope':'Both source capstones, beyond this one selected pass.','completed':None}
 c['unselected_source_obligations']=[{'physical_page':20,'instruction':GATE,'status':'Both-capstone uninterrupted key/pick duty remains unobserved.'},{'physical_page':1,'instruction':b.h.SESSION,'status':'Other selected session children remain separate.'},{'physical_page':18 if page==18 else 1,'instruction':RULES[18] if page==18 else b.h.PICK,'status':'Economy alternative unselected; only strict alternate chosen here, no cleanliness measurement claimed.'},{'physical_page':20,'instruction':'Remaining full-book mastery and ten-phase practice duties.','status':'Unselected/unobserved; no whole-book claim.'}]
 return c
def selection(c,r):
 result=b.selection(c,r);first=r['start_stroke'];result['event_picks']=[first,'U' if first=='D' else 'D']*32;return result
def workflow_state(c,r,responses):
 if r is None:assert responses==[],'RESPONSES_BEFORE_SELECTION';return {'state':'AWAITING_SELECTION','grants_credit':False}
 chosen=selection(c,r);v=module(VALIDATOR,'responses');return {'state':v.response_state(c,responses),'selection':chosen,'performance_observed':False,'grants_credit':False}
def make(old,blocks,loc,text):
 new=copy.deepcopy(old);new['source_refs'][0]['locator']=loc;new['source_payload']['txt_excerpt']=text;new['source_payload']['source_discrepancy']=[{'class':'historical_capstone_txt_boundary_diagnostic_resolved','previous_diagnostic':old['source_payload']['source_discrepancy'],'resolution':'Four exact original TXT key blocks match all original PDF musical grids; source headings/layout differ.','txt_locator':loc,'remaining_format_difference':'PDF-only governing paragraph remains in PDF context and explicit manual tasks; not attributed to TXT.'}];new['implementation']['kind']='manual_capstone_workflow';new['implementation']['manual_execution_contract']=contract(old,blocks);return new
def verify(old,new,blocks,loc,text):assert new==make(old,blocks,loc,text),'EXACT_CAPSTONE_CONTRACT';assert new['implementation']['events']==old['implementation']['events'] and new['timing_authority']==old['timing_authority'],'MUSIC_CLOCK_UNCHANGED'
def main():
 timer=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
 for p,d in PINS:assert sha(p)==d,'PIN'
 assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 idx=json.loads(BASE.read_text());rr=list(map(json.loads,PACKET.read_text().splitlines()));selected=[x for x in idx['children'] if x['level']==62 and x['line'] in [60,61]];assert len(selected)==2;refs=rr[59]['source_refs']
 for ref in refs:checkpin(ref)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();ctx=json.loads((ROOT/refs[2]['path']).read_text());source_blocks={};page_scope={17:(687,727,['C','G','D','A'],'major'),18:(731,771,['A','E','B','D'],'minor')}
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  pages={n:pdf.pages[n-1].extract_text(x_tolerance=1) for n in [1,2,17,18,20]}
  for n,text in pages.items():assert norm(text)==norm(next(x['text'] for x in ctx['pdf_pages'] if x['physical_page']==n)),'SOURCE_CONTEXT'
  for page,(start,end,keys,mode) in page_scope.items():
   assert RULES[page] in norm(pages[page]);found=[]
   for key in keys:
    matches=[(n,t) for n,t in enumerate(txt[start-1:end],start-1) if t.startswith(key+' '+mode+': ')];assert len(matches)==1;n,label=matches[0];head=label.replace(': ',' - ',1);hits=pdf.pages[page-1].search(re.escape(head));assert len(hits)==1;found.append((n,label,hits[0]))
   blocks=[]
   for n,label,hit in found:
    left=hit['x0']<400;below=[x['top'] for _,_,x in found if (x['x0']<400)==left and x['top']>hit['top']];bbox=[45.0 if left else 411.0,hit['top']-3,406.0 if left else 760.0,min(below)-2 if below else 577];crop=pdf.pages[page-1].crop(bbox).extract_text(x_tolerance=1);text='\n'.join(txt[n:n+9]);tg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',text,re.M)};pg={k:v.replace('|','') for k,v in re.findall(r'^\s*(Nte|Rol|[eBGDAE])\|(.*)$',crop,re.M)};assert len(pg)==8 and pg==tg,'ORIGINAL_KEY_GRID';assert label.replace(': ',' - ',1) in crop;blocks.append({'txt_line_start':n+1,'txt_line_end':n+9,'label':label,'grid':tg,'pdf_bbox':bbox})
   source_blocks[page]=blocks
 assert GATE in norm(pages[20]) and txt[869]=='- '+GATE
 for rule in [b.h.SESSION,b.h.PICK]:assert norm(rule) in norm(pages[1])
 for rule in b.h.SHIFT:assert norm(rule) in norm(pages[2])
 rows=[];olds=[];contexts=[];changes=[];checks=[];valid_choices=state_checks=0;refusals=[]
 for ent in selected:
  old=rr[ent['line']-1];assert rh(old)==ent['record_sha256'] and ent['category']=='implementation_or_interpretation_pending';page=old['implementation']['source_scope']['locator']['physical_page'];assert norm(pages[page])==norm(old['implementation']['source_scope']['pdf_excerpt']);start,end,keys,mode=page_scope[page];loc={'line_start':start,'line_end':end,'within_document_label':txt[start-1]};text='\n'.join(txt[start-1:end]);ev=old['implementation']['events'];assert len(ev)==64;blocks=[];sm={6:'E',5:'A',4:'D',3:'G',2:'B',1:'e'}
  for j,block in enumerate(source_blocks[page]):
   grid=block['grid'];key,chordtext=block['label'].split(': ');chords=chordtext.split(' | ');assert len(chords)==4;bars=[]
   for n,event in enumerate(ev[j*16:j*16+16]):
    col=n*4;assert event['order']==j*16+n+1 and event['printed_column']==col and grid['Nte'][col:col+4].strip('-')==event['printed_note'] and grid['Rol'][col:col+4].strip('-')==event['role'],'NOTE_ROLE';contacts=[(k,int(mt[0])) for k in ['e','B','G','D','A','E'] if (mt:=re.match(r'\d+',grid[k][col:col+4]))];assert contacts==[(sm[event['string']],event['fret'])],'CONTACT'
   for bar,chord in enumerate(chords):bars.append({'source_bar':j*4+bar+1,'chord':chord,'event_orders':list(range(j*16+bar*4+1,j*16+bar*4+5)),'printed_notes':[e['printed_note'] for e in ev[j*16+bar*4:j*16+bar*4+4]],'roles':[e['role'] for e in ev[j*16+bar*4:j*16+bar*4+4]]})
   blocks.append({'key_block':j+1,'key':key,'event_orders':list(range(j*16+1,j*16+17)),'bars':bars,'source':{'physical_page':page,'txt_lines':[block['txt_line_start'],block['txt_line_end']],'pdf_bbox':block['pdf_bbox']}})
  assert [x['key'].split()[0] for x in blocks]==keys and [n+1 for n,e in enumerate(ev) if e['role'].startswith('>')]==list(range(1,65,4));new=make(old,blocks,loc,text);verify(old,new,blocks,loc,text);c=new['implementation']['manual_execution_contract'];good={'package_key':old['package_key'],'contract_sha256':rh(c),'start_stroke':'D'}
  for stroke in ['D','U']:picks=selection(c,{**good,'start_stroke':stroke})['event_picks'];assert picks==[stroke,'U' if stroke=='D' else 'D']*32 and all(picks[x]==stroke for x in [0,16,32,48]);valid_choices+=1
  assert workflow_state(c,None,[])['state']=='AWAITING_SELECTION';state_checks+=1
  for answers,status in [([],'IN_PROGRESS'),([{'step':1,'response':'needs_retry'}],'NEEDS_RETRY'),([{'step':1,'response':'stopped'}],'STOPPED'),([{'step':n+1,'response':'acknowledged'} for n in range(4)],'USER_REPORTED_STEPS_FINISHED')]:assert workflow_state(c,good,answers)['state']==status;state_checks+=1
  for name,request,answers in [('missing',{},[]),('wrong_key',{**good,'package_key':'other'},[]),('stale',{**good,'contract_sha256':'0'*64},[]),('unset',{**good,'start_stroke':None},[]),('economy',{**good,'start_stroke':'economy'},[]),('loop',{**good,'repeat':2},[]),('responses_before_choice',None,[{'step':1,'response':'acknowledged'}]),('bad_response',good,[{'step':1,'response':'passed'}]),('wrong_order',good,[{'step':2,'response':'acknowledged'}]),('bool_step',good,[{'step':True,'response':'acknowledged'}]),('after_stop',good,[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:
   try:workflow_state(c,request,answers)
   except AssertionError:refusals.append({'key':old['package_key'],'reason':name})
   else:raise AssertionError('INVALID_WORKFLOW_ACCEPTED')
  rows.append(new);olds.append(old);contexts.append((blocks,loc,text));checks.append({'key':old['package_key'],'txt_locator':loc,'pdf_page':page,'key_blocks':blocks,'preserved_contacts':64});changes.append({'package_key':old['package_key'],'source_identity':old['source_identity'],'base_record_sha256':ent['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':ent['category'],'new_category':'complete_manual_nonplayback_contract'})
 corruptions=[]
 for n in range(2):
  for name,mut in [('wrong_contact',lambda r:r['implementation']['events'][0].update(fret=99)),('root_silence',lambda r:r['implementation']['events'][3].update(kind='rest')),('clock',lambda r:r['implementation']['events'][0].update(onset_q=[0,1])),('lost_key',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['key_blocks'].pop()),('reset_cycle',lambda r:r['implementation']['manual_execution_contract']['steps'][2].update(preserve_pick_cycle_across_key_boundaries=False)),('mastery_claim',lambda r:r['implementation']['manual_execution_contract']['source_required_practice_duty'].update(completed=True)),('start_absence',lambda r:r['implementation']['manual_execution_contract'].update(both_starts_required_by_source=False))]:
   bad=copy.deepcopy(rows[n]);mut(bad)
   try:verify(olds[n],bad,*contexts[n])
   except AssertionError:corruptions.append({'key':bad['package_key'],'reason':name})
   else:raise AssertionError('CORRUPTION_ACCEPTED')
 for n,name,mut in [(0,'omit_announcement',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['key_transition_tasks'].pop()),(0,'wrong_beat',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['key_transition_tasks'][0].update(source_beat_label=1)),(1,'lost_dominant_third',lambda r:r['implementation']['manual_execution_contract']['steps'][2]['dominant_third_tasks'].pop())]:
  bad=copy.deepcopy(rows[n]);mut(bad)
  try:verify(olds[n],bad,*contexts[n])
  except AssertionError:corruptions.append({'key':bad['package_key'],'reason':name})
  else:raise AssertionError('CORRUPTION_ACCEPTED')
 fold=module(FOLD,'fold');_,prior,effective,catmap,used,ops=fold.fold_chain(BASE,PREV);assert len(used)==372 and ops==410;keys={x['package_key'] for x in selected};other=lambda:rh([[x['package_key'],rh(effective[x['package_key']])] for x in idx['children'] if x['package_key'] not in keys]);before=other()
 for d,row in zip(changes,rows):key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'];effective[key]=row;catmap[key]=d['new_category'];used.add(key)
 identity=[[x['package_key'],effective[x['package_key']]['source_identity']] for x in idx['children']];assert len(effective)==2133 and len(used)==374 and rh(identity)==idx['ordered_identity_sha256'] and other()==before;cats=dict(Counter(catmap.values()));assert cats=={'timed_source_event_contract':507,'complete_manual_nonplayback_contract':491,'implementation_or_interpretation_pending':1004,'performer_choice_missing_fixed_realization':125,'demonstrated_source_conflict':6}
 packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 for p,d in PINS:assert sha(p)==d
 for ref in refs:checkpin(ref)
 save(RES/'targeted-validation.json',{'result':'PASS','capstones':2,'key_blocks':8,'source_bars':32,'preserved_contacts':128,'source_checks':checks,'valid_selections':valid_choices,'workflow_states':state_checks,'workflow_refusals':refusals,'content_refusals':corruptions,'even_boundary_limitation':'Each key block has16 notes. Resetting to the same initial stroke at an even boundary is observationally identical in stroke output; the preserved source no-reset duty is not a physical-reset detector.','unchanged_other_rows':2131,'unchanged_other_records_sha256':before,'final_input_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 save(RES/'handoff.json',{'schema_version':2,'status':'Two complete selected manual capstone contracts; whole-book mastery unobserved; B IN_PROGRESS','start_utc':utc,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'strict_semantics':'Fold guarded372 unique/410 operation prior chain then2 disjoint exact-key replacements; all record/source/identity pins required.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':374,'unique_replaced_children':374,'total_replacement_operations':412,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0})
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'valid_choices':valid_choices,'workflow_refusals':len(refusals),'content_refusals':len(corruptions)}))
if __name__=='__main__':main()
