#!/usr/bin/env python3
"""Compile one closed118 contact family from the sealed69/49 DATA, no source research."""
import collections, copy, hashlib, importlib.util, json, pathlib, re, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT='Build/manager-resume-r03/harmonic-contact-family118-r01'
INPUTS=[('Build/manager-resume-r03/color-contact-data69-r01/definitions.jsonl',833551,'62c67da244833c93de16c9b77fbb2c4b92955050b59eb382ec33632313bc8c17'),('Build/manager-resume-r03/harmonic-contact-data49-r01/definitions.jsonl',796085,'3fc6cea11a625a7eaba180a05b51d2a5ed474f6f43be9cc043eb8f324d746dab')]
CTX=[('Build/manager-resume-r03/color-contact-data69-r01/shared-contexts.json',8167,None),('Build/manager-resume-r03/harmonic-contact-data49-r01/shared-contexts.json',26774,None)]
SPEC=importlib.util.spec_from_file_location('inventory',pathlib.Path(__file__).with_name('build_family_inventory.py'));I=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(I)
def need(v,s):
 if not v:raise ValueError(s)
def raw(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def native_raw(x):
 """Match StrictJson.stringify, including every control character's hex escape."""
 if isinstance(x,str):return ('"'+''.join('\\"' if c=='"' else '\\\\' if c=='\\' else '\\u%04x'%ord(c) if ord(c)<32 else c for c in x)+'"').encode()
 if isinstance(x,list):return b'['+b','.join(native_raw(v) for v in x)+b']'
 if isinstance(x,dict):return b'{'+b','.join(native_raw(k)+b':'+native_raw(x[k]) for k in sorted(x))+b'}'
 return raw(x)
def sha(x):return hashlib.sha256(x).hexdigest()
def save(p,x):p.open('xb').write(raw(x)+b'\n')
def ref(p):
 b=p.read_bytes();return {'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':sha(b)}
def outcome(label):return {'type':['string','null'],'enum':['reported_met','reported_not_met','unknown',None],'learner_label':label.replace('_',' ')}
def phase(name,after,fields,instructions,refs,manual=False,extent=None):
 props={f:outcome(f) for f in fields};props['evidence']={'type':['string','null'],'maxLength':4096,'learner_label':'My manual source evidence'}
 return {'id':name,'after_source_ordinal':after,'source_extent':extent or [1,after],'manual_material_separate_from_displayed_contacts':manual,'instructions':instructions,'source_refs':refs,'report_schema':{'type':'object','properties':props,'required':fields+['evidence'],'additionalProperties':False},'guards':[{'kind':'manual_reported_met','field':f} for f in fields]+[{'kind':'nonempty_trimmed_text','field':'evidence','minimum':1,'maximum':4096}]}
def repairs(context):
 level=context['level']
 if level==40: text=context['complete_source_instructions']['practice_mastery_text'];pointer=['context','complete_source_instructions','practice_mastery_text']
 elif level==46:text='\n'.join(context['complete_instructions']['error_diagnosis']);pointer=['context','complete_instructions','error_diagnosis']
 else:text=context['source_guidance']['practice_mastery_text'];pointer=['context','source_guidance','practice_mastery_text']
 section=text.split('ERROR DIAGNOSIS',1)[-1].split('MASTERY',1)[0];rows=[]
 for line in section.splitlines():
  match=re.fullmatch(r'([A-Z][A-Z /#-]+): (.+)',line.strip())
  if not match:continue
  label,action=match.groups();code=re.sub('[^a-z0-9]+','_',label.lower()).strip('_')
  fields=['literal_source_repair_reported','manual_alternative_material_reported'];p=phase(code,0,fields,[line.strip(),'Use the original source repair manually; unchanged displayed contacts are not a generated alternative.'],[pointer],True,[None,None]);p['label']=label;p['requires_owned_release_before_repair']=True
  if level==40 and label=='A SOUNDS LIKE HOME':
   p['report_schema']['properties']['phrases_ended_on_F_sharp']={'type':['integer','null'],'minimum':0,'maximum':100000,'learner_label':'Complete phrases I ended on F#'};p['report_schema']['required'].append('phrases_ended_on_F_sharp');p['guards'].append({'kind':'minimum','field':'phrases_ended_on_F_sharp','value':3})
  rows.append(p)
 need(len(rows)==(6 if level in (40,47) else 7),'EXACT_SOURCE_DIAGNOSES');return rows
def program(row,context):
 cs=row['source_contracts'];n=len(row['source_atoms']);level=row['level'];module=row['source_module'];phases=[]
 ptr=['source_contracts'];instruction=[s['text'] for s in row['unit']['source_actions'] if s.get('role')!='printed_notational_table_row' and set(s['text'].strip())!={'='}]
 if level==40 and module=='D':
  r=cs['source_response_relationship']
  phases=[phase('A_call',6,['six_original_call_contacts','A_center_call','printed_call_endings'],['Play the six printed A-call contacts in their exact order. Name their active-chord roles.'],[ptr+['source_response_relationship','phrases',0]],extent=[1,6]),phase('F_sharp_answer',12,['six_original_answer_contacts','four_shared_opening_joins','changed_active_chord_roles','printed_F_sharp_ending','related_but_differently_centered'],[r['source_task_duty']],[ptr+['source_response_relationship']],extent=[7,12])]
 elif level==40 and module=='E':
  c=cs['source_completion_cadence'];phases=[phase('direct_completion_cadence',n,['all_original_contacts','direct_fretted_D_and_G_sharp','written_beat_one_targets','immediate_pool_returns','final_F_sharp_root'],[cs['source_specific_rule'],c['intonation_duty']],[ptr+['source_completion_cadence']])]
  if c['later_source_pass'] is not None:phases.append(phase('later_manual_slide_pass',n,['one_completion_tone_approached_by_slide','written_beat_one_arrival_preserved'],[c['later_source_pass']['required_source_duty'],'The approach origin, finger, curve and start time remain your manual choices; this display supplies no slide realization.'],[ptr+['source_completion_cadence','later_source_pass']],True))
 elif level==40 and module=='F':
  phases=[phase('eight_bar_center_shift',n,['eight_original_chords','A_center_first_four_bars','F_sharp_center_last_four_bars','final_F_sharp_more_final_than_bar_four_A'],[context['pdf_guidance']['module_f_center_text']],[['context','pdf_guidance','module_f_center_text']]),phase('manual_drone_and_no_drone_passes',n,['complete_A_then_F_sharp_drone_pass','complete_no_drone_pass','center_shift_preserved_without_drone'],['Perform the complete written eight-bar study with the specified A/F# drones, then without drones. Accompaniment is supplied manually; no drone events are generated.'],[['context','pdf_guidance','module_f_center_text']],True)]
 elif level==40 and module=='G':phases=[phase('controlled_model',n,['all_original_contacts','original_harmony_schedule','literal_model_rule','printed_phrase_endings','beat_one_targets_secure_before_replacement'],[cs['source_specific_rule']],[ptr+['source_specific_rule'],['context','complete_source_instructions','module_g_text']])]
 elif module=='A' and level in (40,46):
  rule=cs['source_specific_rule'] if level==40 else cs['source_rule'];fields=['all_original_contacts','only_printed_chord_targets','every_printed_chord_role_named']
  phases=[phase('target_cell',n,fields,[rule],[ptr+['source_specific_rule' if level==40 else 'source_rule']])]
 elif level==47:
  if 'switch_contract' in cs:
   phases=[phase('source_pool_switch',n,['all_original_contacts','first_source_pool','second_source_pool','same_manual_subdivision','original_contour'],['Preserve the printed two-bar pitch-pool order and contour. Pool labels are not backing chords; no numeric subdivision is supplied.'],[ptr+['switch_contract']])]
  elif 'question_answer_contract' in cs:
   phases=[phase('source_question',4,['four_original_question_contacts','printed_question_color'],['Play the four printed question contacts before changing color.'],[ptr+['question_answer_contract']],extent=[1,4]),phase('source_answer',n,['four_original_answer_contacts','color_changed_after_four','same_original_neck_area'],['Play the original four-note answer in the same neck area and retain the after-contact4 color boundary.'],[ptr+['question_answer_contract']],extent=[5,8])]
  elif 'chorus_contract' in cs:
   phases=[phase('twelve_bar_chorus',n,['all_original_contacts','twelve_original_chord_position_bars','first_note_identifies_or_prepares_chord','original_color_membership','barline_form'],['Preserve all twelve source chord/position bars and four printed contacts per bar. The one selected model keeps its original quarter slots; other routes remain unclocked.'],[ptr+['chorus_contract']])]
  else:
   fields=['all_original_contacts','printed_color_membership','original_source_phrase_order']
   if module=='G':fields.append('printed_active_chord_roles')
   if cs['route_contract']['silent_shifts']:fields.append('all_written_silent_shifts_reported')
   phases=[phase('source_color_phrase',n,fields,['Keep every original source atom, color and applicable chord role. Source-null fingers and spans remain unspecified.'],[ptr+['route_contract']])]
 else:raise ValueError('CLOSED118_POLICY_TAG')
 variants=cs.get('variants',[])
 if level==40:broader=[context['complete_source_instructions']['practice_mastery_text']]
 elif level==46:broader=context['complete_instructions']['practice']+context['complete_instructions']['mastery_gate']
 else:broader=[context['source_guidance']['practice_mastery_text']]
 return {'schema':'fathom.harmonic-contact-source-program.1','policy_tag':f'L{level}:{module}','instruction_blocks':instruction,'broader_manual_source_instructions':broader,'broader_instructions_are_not_this_row_completion_or_observed_mastery':True,'original_contact_ordinals':list(range(1,n+1)),'saved_pick_starts':[v['pick_start'] for v in variants],'unspecified_pick_is_only_available_when_no_saved_variants':True,'requires_both_saved_starts':bool(variants),'report_phases':phases,'repair_options':repairs(context),'external_source_context_ref':row['context_ref'],'unknown_numeric_metric_is_not_a_rhythm_choice':True,'inherits_physical_tempo_rule':False,'inherits_physical_frame_or_pick_debt':False,'generated_alternative_contacts':False,'native_music_model':False,'source_clock':None,'source_acoustic_gates':None}
def generate():
 t=time.perf_counter();cache=I.Cache(ROOT);defs=[];refs=[]
 for path,size,digest in INPUTS:
  pin={'path':path,'bytes':size,'sha256':digest};lines=cache.read(pin).splitlines()
  for index,line in enumerate(lines,1):
   row=I.strict_json(line);need(row['definition_sha256']==sha(raw({k:v for k,v in row.items() if k!='definition_sha256'})),'SEALED_DATA_ROW_HASH');defs.append(row);refs.append(dict(pin,jsonl_line=index))
 contexts={}
 for label,closeout_sha in [('color-contact-data69-r01','b44c7a48343a0c6ad89481616a411f7e88d7fae94096892d0a782d5b76f1ee26'),('harmonic-contact-data49-r01','e8f5d3669e3a439f4be199eb2f1c3494339276f482d42f3c3908f324913e1e94')]:
  seal=cache.json({'path':f'Build/manager-resume-r03/{label}/frozen-closeout.json','sha256':closeout_sha});manifest=cache.json(seal['artifact_manifest']);pin=next(p for p in manifest['artifacts'] if p['path'].endswith('/shared-contexts.json'));obj=cache.json(pin)
  if 'contexts' in obj:
   for level,x in obj['contexts'].items():contexts[level]={'context_ref':x['context_ref'],'source_context':x['context']}
  else:contexts[str(obj['context']['level'])]={'context_ref':obj['context_ref'],'source_context':obj['context']}
 need(len(defs)==len({r['source_key'] for r in defs})==len({r['source_identity'] for r in defs})==118 and set(contexts)=={'40','46','47'},'CLOSED118_3_CONTEXTS')
 compiled=[]
 for row,pin in zip(defs,refs):
  ctx=contexts[str(row['level'])];need(row['context_ref']==ctx['context_ref'],'CONTEXT_BOUND_ROW');x=copy.deepcopy(row);x['original_data_definition_sha256']=x.pop('definition_sha256');x['original_data_ref']=pin;x['schema']='fathom.compiled-harmonic-contact-definition.1';x['contract_sha256']=sha(raw(x['source_contracts']));x['program']=program(row,ctx['source_context']);x['compiled_definition_sha256']=sha(native_raw(x));compiled.append(x)
 need(sum(len(x['source_atoms']) for x in compiled)==1510,'SOURCE1510');out=ROOT/OUT;need(not out.exists(),'NEW118_OUTPUT');out.mkdir(parents=True)
 (out/'definitions.jsonl').open('xb').write(b''.join(raw(x)+b'\n' for x in compiled));save(out/'contexts.json',contexts)
 closure={'schema':'fathom.harmonic-contact-source-closure.1','rows':118,'contacts':1510,'source_contexts':3,'data_input_refs':[cache.reference(p) for p in sorted(cache.files)],'row_hashes':{x['source_key']:x['compiled_definition_sha256'] for x in compiled},'policy_tag_counts':dict(collections.Counter(x['program']['policy_tag'] for x in compiled)),'phases':sum(len(x['program']['report_phases']) for x in compiled),'source_metrics':{'rows':1,'contacts':48},'unknown_fingers':1070,'saved_pick_variants':70,'rows_without_saved_pick_variants':83,'native_music_model':False,'source_clock':None,'source_acoustic_gates':None,'official_acceptance_increment':0};save(out/'family-closure.json',closure)
 header=['#pragma once','#include <array>','namespace fathom::tasks::harmonic_contacts::compiled {','struct Row { const char* key; const char* json; };','inline const std::array<Row,118> rows={{']+['{'+json.dumps(x['source_key'])+','+json.dumps(raw(x).decode(),ensure_ascii=False)+'},' for x in compiled]+['}};','inline const char* contextsJson='+json.dumps(raw(contexts).decode(),ensure_ascii=False)+';','inline const char* closureSha='+json.dumps(sha(raw(closure)))+';','}'];(out/'GeneratedHarmonicContactFamilyData.hpp').open('x').write('\n'.join(header)+'\n')
 receipt={'result':'CLOSED118_SOURCE_FAMILY_GENERATED_NATIVE_CHECKS_PENDING','seconds':time.perf_counter()-t,'cached_files_hashed_once':len(cache.files),'source_pdf_txt_reads':0,'native_owner_models':0,'official_acceptance_increment':0};save(out/'generation-receipt.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':generate()
