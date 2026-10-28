#!/usr/bin/env python3
"""All-key original-witness parity and adversarial guards for emitted A69 DATA.

No native owner, performer observation or source research is exercised here.
"""
import copy,hashlib,importlib.util,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'Build/manager-resume-r03/color-contact-data69-r01'
SPEC=importlib.util.spec_from_file_location('color_compiler',ROOT/'Tools/exercise-family-compiler/compile_color_contact_family.py');C=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(C)
checks=0;refusals=0

def check(v,why):
 global checks
 checks+=1
 if not v:raise AssertionError(why)
def scalar_int(x):return type(x) is int

def validate(row,original,entry,context,context_ref):
 check(row['schema']=='fathom.reference-bound-color-contact-definition.1','closed definition schema')
 check(row['source_key']==entry['package_key']==original['package_key'] and row['source_identity']==entry['source_identity']==original['source_identity'] and row['level']==47 and row['existing_parent_id']==entry['existing_parent_id'],'source identity')
 check(row['payload_ref']==entry['current_payload']['ref'] and row['source_record_canonical_sha256']==entry['current_payload']['record_canonical_sha256']==C.sha(C.compact(original)) and row['source_record_compact_sha256']==entry['current_payload']['record_compact_order_sha256']==C.sha(C.insertion(original)),'source record hash and witness')
 check(row['retained_contract_path']==['implementation'] and row['context_ref']==context_ref and row['source_pins']==entry['source_pins'],'all original bindings')
 impl=original['implementation'];check(row['implementation_kind']==impl['kind'] and row['source_module']==impl['source_module'],'original kind and module')
 check(row['unit']['source_actions']==impl['task_steps'] and row['unit']['source_action_refs']==[['implementation','task_steps',n] for n in range(len(impl['task_steps']))] and row['unit']['complete_notation_witness']==['source_payload','exact_unit_lines'] and row['unit']['printed_label']==original['source_payload']['printed_label'] and row['unit']['heading_path']==original['source_payload']['parent_path'],'exact actions and complete musical extent witness')
 check(row['source_atoms']==impl['ordered_contacts'],'all original contact fields, annotations, locators, timing and attack')
 check(row['source_contracts']=={k:v for k,v in impl.items() if k not in ('ordered_contacts','task_steps','ordered_rest_locations','kind')},'complete original contract preservation')
 check(row['timing_authority']==original['timing_authority'] and row['unresolved_reasons']==original['unresolved_reasons'] and row['ordered_rest_locations']==[],'all timing and unresolved authority preserved')
 check(row['source_unknowns']=={'printed_finger':None,'source_clock':None,'source_acoustic_gate':None,'saved_pick_direction_variants':None,'performer_choices_are_not_source_facts':True},'all source unknowns')
 check(row['boundaries']=={'native_model_created':False,'runtime_admitted':False,'observed_performance':False,'whole_child_accepted':False,'grants_credit':False},'DATA is no native model or completion')
 shape='twelve_bar_source_chorus' if 'chorus_contract' in impl else 'two_bar_pool_switch' if 'switch_contract' in impl else 'four_note_question_answer' if 'question_answer_contract' in impl else 'ordered_source_color_phrase'
 check(row['shared_program']==shape,'shape selects actual source contract')
 check(row['source_atoms_sha256']==C.sha(C.compact(row['source_atoms'])),'atom digest')
 check(row['definition_sha256']==C.sha(C.compact({k:v for k,v in row.items() if k!='definition_sha256'})),'entire definition digest')
 for atom in row['source_atoms']:
  check(scalar_int(atom['ordinal']) and scalar_int(atom['midi']) and atom['finger'] is None and atom['acoustic_gate_q'] is None,'source unknown finger/gate and integer encoding')
  check(atom['color']==context['color_legend'][atom['note_spelling']],'exact color membership')
  if atom['harmonic_role']=='R':check(atom['pick_attack'] is True and atom['attack']=='picked','root role never converted into rest')
  if atom['harmony']:check(context['role_matrix'][atom['harmony']][atom['note_spelling']]==atom['harmonic_role'],'literal chord role matrix')
  if row['implementation_kind']=='color_harmony_contract_metric_pending':check(atom['onset_q'] is None and atom['duration_q'] is None,'unknown metric not chosen')
  else:check(atom['onset_q']==[atom['ordinal']-1,1] and atom['duration_q']==[1,1],'only original model quarter slots')

def rejection(fn):
 global refusals
 no=False
 try:fn()
 except (AssertionError,ValueError,KeyError,TypeError):no=True
 check(no,'malformed source-bound DATA must refuse');refusals+=1

def reports(blueprint):
 for name,p in blueprint['shared_programs'].items():
  schema=p['report_schema'];check(schema['additionalProperties'] is False and set(schema['required'])==set(schema['properties']),'closed typed phase report')
  check(len(p['required_reports'])>=3 and 'learner_done' not in schema['properties'] and 'done' not in schema['properties'],'material source constraints rather than generic done bit')
  check(set(p['required_reports'])=={g['field'] for g in p['guards'] if g['kind']=='manual_reported_met'} and {'kind':'nonempty_trimmed_text','field':'evidence'} in p['guards'],'all required source outcomes and nonblank evidence gate')
  for field in p['required_reports']:check(schema['properties'][field]['enum']==['reported_met','reported_not_met','unknown',None],'typed outcomes retain negative/unknown')
  # Pure prospective descriptor checks only; not current native execution.
  def passes(payload):
   return set(payload)==set(schema['required']) and all(payload[k]=='reported_met' for k in p['required_reports']) and type(payload['evidence']) is str and bool(payload['evidence'].strip()) and len(payload['evidence'])<=4096
  positive={k:'reported_met' for k in p['required_reports']}|{'evidence':'synthetic manual source criterion evidence'};check(passes(positive),'valid typed report descriptor')
  for field in p['required_reports']:
   for value in ('reported_not_met','unknown',None,True):
    x=copy.deepcopy(positive);x[field]=value;check(not passes(x),'negative/unknown/boolean outcome remains unresolved')
  for value in ('',' \t\r\n',None,'x'*4097):x=copy.deepcopy(positive);x['evidence']=value;check(not passes(x),'blank or excessive evidence remains unresolved')
  x=copy.deepcopy(positive);x['unexpected']=True;check(not passes(x),'extra report field refused')
 check(blueprint['native_supported'] is False and len(blueprint['shared_programs'])==4 and blueprint['common_source_semantics']['root_R_is_not_rest'] is True and blueprint['repair_routes_are_separate_manual_realizations'] is True,'native/future and external source boundaries')


def main():
 t=time.perf_counter();closure=C.strict((OUT/'family-closure.json').read_bytes());cache=C.I.Cache(ROOT)
 for ref in closure['source_input_refs']:cache.read(ref)
 selection=C.strict((OUT/'selection.json').read_bytes());ledger=[C.strict(x) for x in cache.read(selection['ledger']).splitlines()];by={x['package_key']:x for x in ledger};rows=[C.strict(x) for x in (OUT/'definitions.jsonl').read_bytes().splitlines()];shared=C.strict((OUT/'shared-contexts.json').read_bytes());context=shared['context'];context_ref=shared['context_ref'];check(context==cache.json(context_ref),'exact cached context')
 check(len(rows)==69 and len({x['source_key'] for x in rows})==len({x['source_identity'] for x in rows})==69 and selection['official_children']==7271 and selection['unowned_source_indexed_A']==617 and selection['current_accepted']==2325,'closed selection denominator and uniqueness')
 descriptor=C.strict((OUT/'authority-descriptor-preimage.json').read_bytes());check(C.sha((OUT/'authority-descriptor-preimage.json').read_bytes())==selection['descriptor_snapshot']['sha256'],'frozen current-status preimage')
 adopted={op['selection']['package_key'] for op in descriptor['current_status_resolution']['operations']};owned=set().union(*(set(v) for v in selection['excluded_owned_keys'].values()));check(set(selection['keys']).isdisjoint(adopted|owned),'no accepted/owned dispatch')
 packet_cache={};total=0;root_roles=0
 for row in rows:
  e=by[row['source_key']];p=row['payload_ref'];raw=cache.read(p).splitlines()[p['jsonl_line']-1];original=C.strict(raw);check(row['original_row_sha256']==C.sha(raw),'exact raw original line')
  validate(row,original,e,context,context_ref);total+=len(row['source_atoms']);root_roles+=sum(x['harmonic_role']=='R' for x in row['source_atoms']);check(closure['definition_hashes'][row['source_key']]==row['definition_sha256'],'closure all-row digest')
  # Mutations remain bound to independent original witnesses, even if a digest is reissued.
  mutations=[lambda x:x['source_atoms'][0].update(finger=1),lambda x:x['source_atoms'][0].update(midi=None),lambda x:x['source_atoms'][0].update(acoustic_gate_q=[1,1]),lambda x:x['source_atoms'][0].update(color='wrong'),lambda x:x['source_atoms'][0].update(harmonic_role='rest'),lambda x:x['source_atoms'][0].update(onset_q=[999,1]),lambda x:x['source_atoms'].reverse(),lambda x:x['payload_ref'].update(jsonl_line=x['payload_ref']['jsonl_line']+1),lambda x:x['context_ref'].update(sha256='0'*64),lambda x:x['source_contracts']['route_contract'].update(silent_shifts=not x['source_contracts']['route_contract']['silent_shifts']),lambda x:x['boundaries'].update(runtime_admitted=True),lambda x:x['source_unknowns'].update(saved_pick_direction_variants=['D','U'])]
  for mutate in mutations:
   x=copy.deepcopy(row);mutate(x);x['source_atoms_sha256']=C.sha(C.compact(x['source_atoms']));x['definition_sha256']=C.sha(C.compact({k:v for k,v in x.items() if k!='definition_sha256'}));rejection(lambda:validate(x,original,e,context,context_ref))
  source_mutations=[lambda x:x['implementation']['ordered_contacts'][0].update(ordinal=True),lambda x:x['implementation']['ordered_contacts'][0].update(midi=True),lambda x:x['implementation']['ordered_contacts'][0].update(finger=2),lambda x:x['timing_authority'].update(fixed_bpm=120),lambda x:x['implementation'].update(variants=['invented'])]
  for mutate in source_mutations:
   x=copy.deepcopy(original);mutate(x);rejection(lambda:C.source_guard(x,e,context))
 check(total==776 and root_roles>0,'exact776 and root correction cases')
 # Header rows are deep-equal to the actual emitted JSONL, rather than another compiler result.
 header=(OUT/'GeneratedColorContactData.hpp').read_text();lines=header.split('inline const std::array<Row,69> rows = {{\n',1)[1].split('\n}};',1)[0].splitlines();decoded=[json.loads('['+x[1:-2]+']') for x in lines];check([json.loads(x[1]) for x in decoded]==rows and [x[0] for x in decoded]==selection['keys'],'actual generated-header table exact equality')
 check(C.sha(C.compact(closure)) in header,'exact header source closure')
 reports(C.strict((OUT/'operator-blueprints.json').read_bytes()))
 result={'result':'PASS_DATA_ONLY','keys':69,'source_contacts':776,'source_root_roles_preserved_as_pitched':root_roles,'assertions':checks,'malformed_input_refusals':refusals,'source_contexts':1,'source_kinds':2,'data_shapes':4,'shape_count_is_not_behavior_equivalence':True,'run_seconds':time.perf_counter()-t,'cached_files_once':len(cache.files),'original_pdf_txt_research':0,'native_owner_runs':0,'official_acceptance_increment':0}
 (OUT/'data-validation.json').open('x').write(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(result))
if __name__=='__main__':main()
