#!/usr/bin/env python3
"""Cached44 table/closed-operator checks. No source rereads or native admission."""
import collections,hashlib,json,pathlib,sys,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'Tools/exercise-family-compiler'))
from manual_procedure_reference_support import CachedWitnesses,BindingError,path_value,require

ROOT=pathlib.Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-procedure-level063-protocols-r01'
PINS={'generated-r01/definitions.jsonl':'29f8a751587482c0097105754572314101895899fad99f6bbcd57c66d02af219','generated-r01/family-closure.json':'ca7849378ae2f55ca73027ec30f267b92a34f21db7a00f5802dc7b1513c34431','operator-schema-r01.json':'ed9f857ac78ea49676781fceb737bca5cacdd0c8b8fa82f6841da26a521c4f64'}

def main():
 start=time.perf_counter();checks=0;bindings=0;constraints=collections.Counter();programs=collections.Counter();rows=[]
 for relative,digest in PINS.items():
  raw=(BASE/relative).read_bytes();require(hashlib.sha256(raw).hexdigest()==digest,'FROZEN_INPUT_DRIFT');checks+=1
 rows=[json.loads(line) for line in (BASE/'generated-r01/definitions.jsonl').read_bytes().splitlines()];require(len(rows)==44,'EXACT44');cache=CachedWitnesses(ROOT)
 for row in rows:
  original,contract=cache.resolve(row);programs[row['program']['name']]+=1;g=row['program']['graph'];checks+=1
  for name,node in g['nodes'].items():
   for field in ('source_action_ref','release_source_action_ref'):
    if field in node:
     ref=node[field];require(set(ref)=={'original_contract_path'},'SOURCE_REF_SHAPE');parts=ref['original_contract_path'];require(type(parts) is list and len(parts)==2,'BOUNDED_SOURCE_REF')
     if parts[0]=='steps':require(type(parts[1]) is int and parts[1]>=0,'SOURCE_STEP_INDEX')
     else:require(parts[0]=='actions' and parts[1] in {'setup','mirror','full_hand_release','one_breath','compare'},'CLOSED_SEVENTH_ACTION')
     value=path_value(contract,parts);require(value is not None,'SOURCE_ACTION_WITNESS');bindings+=1;checks+=1
   guards=list(node.get('constraints',[]))
   for route in node.get('routes',{}).values():guards+=route.get('guards',[])
   for guard in guards:
    kind=guard['kind'];constraints[kind]+=1
    if kind=='reported_seconds_at_least':
     require(set(guard)=={'kind','value_ref','lower_bound_ref'},'DURATION_SHAPE');lower=guard['lower_bound_ref'];require(set(lower)=={'scope','path'},'REFERENCE_SHAPE')
     if lower['scope']=='contract':
      require(len(lower['path'])==3 and lower['path'][0]=='steps' and type(lower['path'][1]) is int and lower['path'][2]=='target_seconds','SOURCE_DURATION_REFERENCE');value=path_value(contract,lower['path']);require(type(value) in (int,float) and value>=0,'SOURCE_DURATION_BOUND')
     else:require(lower['scope']=='saved' and lower['path'][-1]=='reported_seconds','PRIOR_MANUAL_DURATION')
    elif kind=='failed_node_is':require(set(guard)=={'kind','node'} and guard['node']=='self_report','CLOSED_FINAL_REPORT_REPAIR')
    elif kind=='nonempty_trimmed_text':require(set(guard)=={'kind','value_ref','minimum','maximum'} and guard['value_ref']['scope']=='payload' and guard['minimum']==1 and guard['maximum']==512,'CLOSED_TEXT_LIMIT')
    elif kind=='trimmed_text_exact':require(set(guard)=={'kind','value_ref'},'EXACT_TRIMMED_GUARD')
    elif kind=='equals_literal':require(set(guard)=={'kind','value_ref','literal'},'EXACT_LITERAL_GUARD')
    checks+=1
   if node.get('terminal_failure'):
    require(node['kind']=='end' and node['status']=='needs_retry','NO_TERMINAL_FAILURE_COMPLETION');checks+=1
   op=node.get('computed_expected')
   if op and op['kind']=='source_order_P_directions':
    require(set(op)=={'kind','source_contacts','directions_ref','protocol_start','include_first','first_P_order','source_P_orders','report_field','directions_value_kind'},'P_OPERATOR_SHAPE');actual=[x['order'] for x in op['source_contacts'] if x['pick']=='P'];require(actual==op['source_P_orders'] and actual[0]==op['first_P_order'] and len(actual)==len(set(actual)),'EXACT_SOURCE_P_ORDER');require(op['directions_value_kind'] in {'array','one_scalar'},'P_INPUT_KIND');require(op['protocol_start'] in {'D','U'} and type(op['include_first']) is bool,'P_PROTOCOL');checks+=1
  require(original['source_identity']==row['source_identity'],'EXACT_SOURCE_IDENTITY')
 require(len(cache.rows_bound)==44 and len(programs)==10 and cache.files_hashed==4 and bindings==459,'DENOMINATORS')
 return {'outcome':'PASS','rows':44,'programs':dict(programs),'cached_payload_files_hashed_once':cache.files_hashed,'source_bindings':bindings,'guard_counts':dict(constraints),'assertions':checks,'seconds':time.perf_counter()-start,'source_PDF_TXT_reads':0,'source_copies':0,'perrow_models':0,'native_owner_execution':False,'current224_mutated':False}

if __name__=='__main__':
 result=main();print(json.dumps(result,indent=2))
 if len(sys.argv)>1:pathlib.Path(sys.argv[1]).open('x').write(json.dumps(result,indent=2)+'\n')
