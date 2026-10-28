#!/usr/bin/env python3
"""Reference-bound A69 color-contact DATA, using cached sources only.

This compiles closed data and future shared-operator descriptors. It creates no
owner, native model, installed route, performance observation or acceptance.
"""
import argparse,collections,copy,hashlib,importlib.util,json,pathlib,time
from fractions import Fraction
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT_REL='Build/manager-resume-r03/color-contact-data69-r01'
LEDGER={'path':'Build/manager-resume-r03/family-inventory-r01/family-ledger.jsonl','bytes':20737074,'sha256':'ce8ad63e95cf1670804f058833ec43538d42a611f260d5d1711ee17fc5925d4b'}
KINDS={'color_harmony_contract_metric_pending','timed_color_harmony_contract'}
CORE_SPEC=importlib.util.spec_from_file_location('inventory_core',pathlib.Path(__file__).with_name('build_family_inventory.py'));I=importlib.util.module_from_spec(CORE_SPEC);CORE_SPEC.loader.exec_module(I)
def need(v,why):
 if not v:raise ValueError(why)
def compact(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def insertion(x):return json.dumps(x,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def strict(b):return I.strict_json(b)
def pin(cache,path):cache.read(path);return cache.reference(path)
def save(path,x):path.open('xb').write(compact(x)+b'\n')
def schema_object(fields,required):return {'type':'object','properties':fields,'required':required,'additionalProperties':False}
def nullable_bool(label):return {'type':['boolean','null'],'learner_label':label}
def outcome(label):return {'type':['string','null'],'enum':['reported_met','reported_not_met','unknown',None],'learner_label':label}
def exact_shape(row):
 contracts=row['source_contracts']
 if 'chorus_contract' in contracts:return 'twelve_bar_source_chorus'
 if 'switch_contract' in contracts:return 'two_bar_pool_switch'
 if 'question_answer_contract' in contracts:return 'four_note_question_answer'
 return 'ordered_source_color_phrase'
def source_guard(o,entry,ctx):
 need(o['package_key']==entry['package_key'] and o['source_identity']==entry['source_identity'] and o['level']==47,'SOURCE_IDENTITY')
 i=o['implementation'];need(i['kind'] in KINDS and i['runtime_eligible'] is False and i['canonical_ids_allocated'] is False and i['mastery_or_credit'] is False,'SOURCE_KIND_NONADMISSION')
 need(o['timing_authority']['fixed_bpm'] is None and o['timing_authority']['ascii_spacing_is_duration'] is False and i['ordered_rest_locations']==[],'CLOCK_REST_AUTHORITY')
 need(not o['source_payload']['source_discrepancy'],'LOCAL_SOURCE_DISCREPANCY')
 need(i['color_legend']==ctx['color_legend'] and i['route_contract']['G_sharp_policy']=='marked E7 completion tone only' and i['route_contract']['source_phrase_order_preserved'] is True,'EXACT_COLOR_SOURCE_POLICY')
 cs=i['ordered_contacts'];need(len(cs) in (8,12,16,48),'SOURCE_EXTENT_COUNT')
 next_slot=Fraction(0)
 for n,c in enumerate(cs):
  need(type(c['ordinal']) is int and c['ordinal']==n+1,'ORDINAL')
  need(type(c['string_low_to_high']) is int and c['string_low_to_high'] in range(1,7) and c['string_label']==['E','A','D','G','B','e'][c['string_low_to_high']-1],'STRING_CONVENTION')
  need(type(c['fret']) is int and c['fret']>=0 and c['finger'] is None and type(c['midi']) is int and 0<=c['midi']<=127,'SOURCE_PHYSICAL_UNKNOWN_FINGER')
  need(c['acoustic_gate_q'] is None and c['pick_attack'] is True and c['attack']=='picked','SOURCE_ATTACK_UNKNOWN_SOUNDING')
  need(c['color']==ctx['color_legend'][c['note_spelling']],'SOURCE_COLOR_LEGEND')
  if c['harmony'] is not None:need(c['harmony'] in ctx['role_matrix'] and ctx['role_matrix'][c['harmony']][c['note_spelling']]==c['harmonic_role'],'SOURCE_HARMONY_ROLE')
  need(type(c['source_line']) is int and c['source_line']>0 and type(c['source_column_1based']) is int and c['source_column_1based']>0,'SOURCE_LOCATOR')
  if i['kind']=='color_harmony_contract_metric_pending':need(c['onset_q'] is None and c['duration_q'] is None,'UNSELECTED_METRIC_STAYS_NULL')
  else:
   need(c['onset_q']==[n,1] and c['duration_q']==[1,1],'SAVED_MODEL_QUARTERS');next_slot+=Fraction(1)
 if i['kind']=='timed_color_harmony_contract':need(len(cs)==48 and o['timing_authority']['end_q']==[48,1] and i['practice_options']['selected']=='PDF19 first written chorus as quarter notes','MODEL_SCOPE')
 else:need(o['timing_authority']['end_q'] is None and o['timing_authority']['selected_projection'] is None,'UNSELECTED_SCOPE')
 need('variants' not in i,'DO_NOT_INVENT_PICK_START_VARIANTS')
 if 'switch_contract' in i:
  need(len(cs)==16 and i['switch_contract']['numeric_subdivision_unselected'] is True and i['switch_contract']['pool_label_is_not_backing_chord'] is True,'SWITCH_SCOPE')
  for n,c in enumerate(cs):need(c['source_pitch_pool']==i['switch_contract']['bar1_pool' if n<8 else 'bar2_pool'],'SOURCE_POOL_SWITCH')
 if 'question_answer_contract' in i:need(len(cs)==8 and i['question_answer_contract']['change_color_after_contact']==4 and i['question_answer_contract']['same_neck_area'] is True,'QUESTION_ANSWER_BOUNDARY')
 if 'chorus_contract' in i:
  cc=i['chorus_contract'];need(len(cs)==48 and len(cc['chords'])==len(cc['positions'])==12 and cc['four_contacts_per_bar'] is True,'CHORUS_FORM')
  for n,c in enumerate(cs):need(c['harmony']==cc['chords'][n//4] and c['position']==cc['positions'][n//4],'EXACT_SOURCE_BAR_HARMONY_POSITION')
 return 16*len(cs)+12

def row_for(o,e,raw,context_ref):
 i=o['implementation'];contracts={k:v for k,v in i.items() if k not in ('ordered_contacts','task_steps','ordered_rest_locations','kind')}
 body={'schema':'fathom.reference-bound-color-contact-definition.1','source_key':o['package_key'],'source_identity':o['source_identity'],'level':47,'existing_parent_id':o['existing_parent_id'],'implementation_kind':i['kind'],'source_category':e['current_payload']['category'],'source_module':i['source_module'],'original_row_sha256':sha(raw),'source_record_canonical_sha256':sha(compact(o)),'source_record_compact_sha256':sha(insertion(o)),'payload_ref':e['current_payload']['ref'],'retained_contract_path':['implementation'],'context_ref':context_ref,'source_pins':e['source_pins'],'unit':{'heading_path':o['source_payload']['parent_path'],'printed_label':o['source_payload']['printed_label'],'source_actions':i['task_steps'],'source_action_refs':[['implementation','task_steps',n] for n in range(len(i['task_steps']))],'complete_notation_witness':['source_payload','exact_unit_lines']},'source_atoms':copy.deepcopy(i['ordered_contacts']),'source_contracts':copy.deepcopy(contracts),'timing_authority':copy.deepcopy(o['timing_authority']),'unresolved_reasons':copy.deepcopy(o['unresolved_reasons']),'ordered_rest_locations':[],'source_unknowns':{'printed_finger':None,'source_clock':None,'source_acoustic_gate':None,'saved_pick_direction_variants':None,'performer_choices_are_not_source_facts':True},'boundaries':{'native_model_created':False,'runtime_admitted':False,'observed_performance':False,'whole_child_accepted':False,'grants_credit':False}}
 body['shared_program']=exact_shape(body);body['source_atoms_sha256']=sha(compact(body['source_atoms']));body['definition_sha256']=sha(compact(body));return body

def operator_blueprints():
 evidence={'type':['string','null'],'maxLength':4096,'learner_label':'My manual evidence; blank or unknown remains unresolved'}
 phases={
 'ordered_source_color_phrase':{'source_parameters':['source_atoms','source_contracts.route_contract','unit.source_actions'],'required_reports':['all_source_atoms_reported','color_membership_reported','source_phrase_order_reported'],'semantics':'Every original contact, color and applicable harmonic role remains bound. No finger or pulse is fabricated.'},
 'two_bar_pool_switch':{'source_parameters':['source_atoms','source_contracts.switch_contract','source_contracts.route_contract'],'required_reports':['all_source_atoms_reported','bar1_pool_reported','bar2_pool_reported','same_subdivision_reported','contour_preserved_reported'],'semantics':'Use the original16 contacts and distinct MIN/MAJ or MAJ/MIN pools; pool labels are not backing chords. Numeric subdivision remains unselected.'},
 'four_note_question_answer':{'source_parameters':['source_atoms','source_contracts.question_answer_contract'],'required_reports':['all_source_atoms_reported','question_reported','answer_reported','color_change_after_four_reported','same_neck_area_reported'],'semantics':'Preserve both original four-note clauses, the after-contact4 boundary and the original neck area.'},
 'twelve_bar_source_chorus':{'source_parameters':['source_atoms','source_contracts.chorus_contract','timing_authority'],'required_reports':['all_source_atoms_reported','all_twelve_bars_reported','original_chord_sequence_reported','first_note_target_reported','barline_form_reported'],'semantics':'Preserve12 exact chord/position bars, four contacts per bar and the first-note identifies-or-prepares rule. Only the one model retains its selected quarter slots; shuffle remains a separate ungenerated later option.'}}
 for p in phases.values():
  p['report_schema']=schema_object({k:outcome(k.replace('_',' ')) for k in p['required_reports']}|{'evidence':evidence},p['required_reports']+['evidence'])
  p['guards']=[{'kind':'manual_reported_met','field':k} for k in p['required_reports']]+[{'kind':'nonempty_trimmed_text','field':'evidence'}]
  p['negative_or_unknown']='Retain raw manual outcome/evidence, block completion, use explicit source repair/retry; no inferred performance.'
 return {'schema':'fathom.color-contact-operator-blueprints.1','native_supported':False,'source_kind_tags':sorted(KINDS),'shared_programs':phases,'common_source_semantics':{'color_legend_ref':['context','color_legend'],'role_matrix_ref':['context','role_matrix'],'G_sharp_row_policy_ref':['source_contracts','route_contract','G_sharp_policy'],'root_R_is_not_rest':True,'source_ordinal_and_annotation_integrity':'Closed source atoms retain every original field. A chosen finger or pulse belongs to a separate learner report; source nulls stay null.','source_overlaps':'Only rows with literal route_contract.silent_shifts true require source-guided silent shift reports. Exact fret/frame release boundaries are not inferred from absent fingering/position facts.','manual_release':'An eventual shared owner must own cancellation/release/retry/navigation/history; this DATA supplies no owner or release proof.'},'future_operator_requirements':['Reference-bound original implementation kind and closed source-atom witness bridge.','Shared ordered source-atom owner with optional printed finger, optional metric spans and optional saved pick direction; no MusicModel/acoustic or clock fallback.','Source color/role/pool/question/chorus typed manual reports and explicit nonempty evidence, preserving negative/unknown outcomes.','Source-supported manual overlap/repair/release routes, retaining source debt and history through restart/cancel/navigation.'],'source_repair_instruction_ref':['context','source_guidance','practice_mastery_text'],'repair_routes_are_separate_manual_realizations':True,'external_source_boundary':'ModuleB third-control sites and12 open recovery cards are outside69. Source mastery/recording/drone/ear/separate-day and full872-workload conditions remain broader manual obligations; selected776 cannot certify them.','official_acceptance_increment':0}

def build(root):
 t=time.perf_counter();cache=I.Cache(root);ledger=[strict(x) for x in cache.read(LEDGER).splitlines()];need(len(ledger)==7271,'LEDGER7271')
 by={r['package_key']:r for r in ledger};need(len(by)==7271 and len({r['source_identity'] for r in ledger})==7271,'LEDGER_IDENTITIES')
 descriptor_path='Planning/Fathom-Exercise-WBS-Annex-v1.json';d=cache.json(descriptor_path);dp=cache.reference(descriptor_path);need(d['base']['sha256']=='dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c','SAME_IMMUTABLE_OFFICIAL_BASE')
 accepted=set()
 for op in d['current_status_resolution']['operations']:
  s=op['selection'];k=s['package_key'];need(k in by and k not in accepted and s['source_identity']==by[k]['source_identity'] and s['existing_parent_id']==by[k]['existing_parent_id'],'CURRENT_STATUS_IDENTITY')
  need(op['current_overlay']['status']=='Accepted' and op['current_overlay'].get('source_key',k)==k,'CLOSED_CURRENT_ACCEPTED_OPERATIONS');accepted.add(k)
 need(len(accepted)==2325 and d['current_view']['children']['child_status_counts']=={'Accepted':2325,'Pending':4946},'ADOPTED2325')
 excluded={};owned67=cache.json({'path':'Build/manager-resume-r03/manual-source-assessments67-r01/generated-r03/family-closure.json','bytes':541776,'sha256':'552ebbe02073d087c59a692bb09bb4a37080faa2a92a70896f9f0e1bdb031616'});excluded['source67']=set(owned67['keys'])
 owned17=cache.json({'path':'Build/manager-resume-r03/piecewise-contact-family-r01/cohort.json','bytes':374745,'sha256':'68a09de3c6db0ce94774fb7aa91900ee07dd678b0702dfbc76440e17f680f40a'});excluded['piecewise17']={x['source_key'] for x in owned17['rows']}
 native=cache.json({'path':'Build/manager-resume-r03/family-inventory-r01/native-projection-cohort.json','bytes':5380406,'sha256':'a6e3c5166d5fa4d2f1a282830cfca994ba93616088939704b0b5c18cb6e11dc0'});excluded['ordered1401']={x['package_key'] for x in native['candidates']}
 physical=cache.json({'path':'Build/manager-resume-r03/unpitched-contact-preparation-r01/cohort.json','bytes':367986,'sha256':'88f2cdffda1516c15e1d9f6aab617519b7d0313be3d92348c265d64bab300998'});excluded['physical339']={x['key'] for x in physical['rows']};need({k:len(v) for k,v in excluded.items()}=={'source67':67,'piecewise17':17,'ordered1401':1401,'physical339':339},'CLOSED_OWNED_SCOPES')
 pendingA=[x for x in ledger if (x['current_payload'] or {}).get('owner')=='A' and not x['dispatch_ownership']['broad_lane_excluded'] and x['package_key'] not in accepted]
 remaining=[x for x in pendingA if x['package_key'] not in set.union(*excluded.values())];selected=[x for x in remaining if x['level']==47 and x['current_payload']['implementation_kind'] in KINDS];need(len(pendingA)==701 and len(remaining)==617 and len(selected)==69,'EXACT_SELECTION_DENOMINATOR')
 refs={e['current_payload']['ref']['path']:e['current_payload']['ref'] for e in selected};need(len(refs)==1,'ONE_PACKET');pr=next(iter(refs.values()));rawlines=cache.read(pr).splitlines();ctxpath=str(pathlib.Path(pr['path']).parent/'level-source-context.json');ctx=cache.json(ctxpath);ctxref=cache.reference(ctxpath);need(ctx['level']==47,'ONE_LEVEL_CONTEXT')
 rows=[];assertions=0
 for e in selected:
  cp=e['current_payload'];raw=rawlines[cp['ref']['jsonl_line']-1];o=strict(raw);need(sha(compact(o))==cp['record_canonical_sha256'] and sha(insertion(o))==cp['record_compact_order_sha256'],'ORIGINAL_ROW_PINS')
  for kind in ('txt','pdf'):need(ctx['originals'][kind]['sha256']==e['source_pins'][kind+'_sha256'],'CONTEXT_SOURCE_JOIN')
  assertions+=source_guard(o,e,ctx);rows.append(row_for(o,e,raw,ctxref))
 need(sum(len(x['source_atoms']) for x in rows)==776 and collections.Counter(x['implementation_kind'] for x in rows)=={'color_harmony_contract_metric_pending':68,'timed_color_harmony_contract':1},'CLOSED69_776')
 phases=operator_blueprints();selection={'schema':'fathom.color-contact-selection.1','ledger':LEDGER,'descriptor_snapshot':dp,'descriptor_preimage':OUT_REL+'/authority-descriptor-preimage.json','official_base_reused_by_saved_ledger_pin':d['base'],'official_children':7271,'current_accepted':2325,'current_pending':4946,'nontransferred_pending_A':701,'unowned_source_indexed_A':617,'selected_keys':69,'excluded_owned_counts':{k:len(v) for k,v in excluded.items()},'excluded_owned_keys':{k:sorted(v) for k,v in excluded.items()},'remaining_kind_counts':dict(collections.Counter(x['current_payload']['implementation_kind'] for x in remaining)),'keys':[r['source_key'] for r in rows],'source_identity':[r['source_identity'] for r in rows],'data_shape_counts':dict(collections.Counter(r['shared_program'] for r in rows)),'shape_counts_are_not_behavior_equivalence':True,'scope':'DATA_ONLY_NATIVE_OWNER_SHARED_BRIDGE_PENDING'}
 return cache,rows,ctx,ctxref,selection,phases,assertions,time.perf_counter()-t

def generate(root):
 cache,rows,ctx,ctxref,selection,phases,assertions,seconds=build(root);out=pathlib.Path(root)/OUT_REL;need(not out.exists(),'NEW_OUTPUT_ROOT');out.mkdir(parents=True)
 save(out/'selection.json',selection);(out/'authority-descriptor-preimage.json').open('xb').write(cache.files['Planning/Fathom-Exercise-WBS-Annex-v1.json']['raw'])
 (out/'definitions.jsonl').open('xb').write(b''.join(compact(x)+b'\n' for x in rows));save(out/'shared-contexts.json',{'schema':'fathom.color-contact-shared-contexts.1','context_ref':ctxref,'context':ctx,'full_context_is_trusted_source_metadata':True});save(out/'operator-blueprints.json',phases)
 closure={'schema':'fathom.color-contact-data-closure.1','keys':69,'source_contacts':776,'selected_metric_rows':1,'unselected_metric_rows':68,'printed_fingers_unknown':776,'saved_pick_variants':None,'clock':None,'source_sounding_gates':None,'native_models':0,'source_contexts':1,'source_input_refs':[cache.reference(p) for p in sorted(cache.files)],'definition_hashes':{x['source_key']:x['definition_sha256'] for x in rows},'source_kind_counts':dict(collections.Counter(x['implementation_kind'] for x in rows)),'module_counts':dict(collections.Counter(x['source_module'] for x in rows)),'data_shape_counts':selection['data_shape_counts'],'data_shapes_are_not_behavior_equivalence':True,'known_source_conflicts_outside_scope':ctx['demonstrated_source_conflicts'],'native_owner_pending':True,'runtime_admitted':False,'official_acceptance_increment':0};save(out/'family-closure.json',closure)
 header=['#pragma once','#include <array>','namespace fathom::tasks::color_contacts::data {','struct Row { const char* key; const char* json; };','inline const std::array<Row,69> rows = {{']+[ '{'+json.dumps(x['source_key'])+','+json.dumps(compact(x).decode(),ensure_ascii=False)+'},' for x in rows]+['}};','inline const char* sharedContextJson='+json.dumps(compact({'context_ref':ctxref,'context':ctx}).decode(),ensure_ascii=False)+';','inline const char* sourceClosureSha='+json.dumps(sha(compact(closure)))+';','}'];(out/'GeneratedColorContactData.hpp').open('x').write('\n'.join(header)+'\n')
 metrics={'schema':'fathom.color-contact-generation-receipt.1','result':'CLOSED69_SOURCE_DATA_GENERATED_CHECKS_PENDING','source_binding_assertions':assertions,'generation_seconds':seconds,'cached_files_hashed_once':len(cache.files),'original_source_pdf_txt_reads':0,'old_native_review_replays':0,'new_native_owner_models':0,'official_acceptance_increment':0};save(out/'generation-receipt.json',metrics);print(json.dumps(metrics))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',default=str(ROOT));x=a.parse_args();generate(x.root)
