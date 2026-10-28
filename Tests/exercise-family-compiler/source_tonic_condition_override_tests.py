#!/usr/bin/env python3
"""Exact one-key DATA reachability/guard proof; native owner release is C's gate."""
import hashlib,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'Build/manager-resume-r03/source-tonic-condition-correction-r01'
checks=0;blocked=0

def check(v,why):
 global checks
 checks+=1
 if not v:raise AssertionError(why)
def compact(x):return json.dumps(x,separators=(',',':'),ensure_ascii=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def schema_ok(schema,payload):
 if type(payload) is not dict or set(payload)!=set(schema['required']):return False
 for key,spec in schema['properties'].items():
  x=payload[key];types=spec['type'];types=[types] if type(types) is str else types
  if not any((t=='null' and x is None) or (t=='string' and type(x) is str) or (t=='boolean' and type(x) is bool) for t in types):return False
  if 'enum' in spec and not any(type(x) is type(v) and x==v for v in spec['enum']):return False
  if type(x) is str and (len(x)<spec.get('minLength',0) or len(x)>spec.get('maxLength',99999)):return False
 return True
def report_ok(node,payload):
 if not schema_ok(node['schema'],payload):return False
 if any(k not in payload or type(payload[k]) is not type(v) or payload[k]!=v for k,v in node['expected'].items()):return False
 for c in node['constraints']:
  if c['kind']=='nonempty_trimmed_text':
   x=payload[c['field']]
   if type(x) is not str or not x.strip() or len(x)>c['maximum']:return False
 return True
def reject(node,payload):
 global blocked
 check(not report_ok(node,payload),'negative/unknown must block DATA report transition');blocked+=1

def main():
 global blocked
 t=time.perf_counter();row=json.loads((OUT/'definition-override.jsonl').read_bytes());old=json.loads((OUT/'definition-preimage.jsonl').read_bytes());binding=json.loads((OUT/'override-binding.json').read_bytes());nodes=row['program']['graph']['nodes'];g=row['program']['graph']
 check(row['source_key']==binding['source_key']==old['source_key'],'exact one key')
 check(row['contract_sha256']==sha(compact(row['program']))==binding['corrected_program_contract_sha256'],'correct program hash')
 check(old['contract_sha256']==binding['source_definition_preimage']['contract_sha256'] and sha((OUT/'definition-preimage.jsonl').read_bytes().splitlines()[0])==binding['source_definition_preimage']['raw_line_sha256'],'exact preimage program and raw line')
 for key,value in old.items():
  if key not in ('program','contract_sha256'):check(row[key]==value,'raw record/identity/locators/span/pins unchanged')
 check(row['program']['source_criteria']==old['program']['source_criteria'] and row['program']['source_literal_sha256']==old['program']['source_literal_sha256'],'all exact source clauses retained')
 check(row['program']['source_metadata']==old['program']['source_metadata'] and row['program']['source_obligations_ref']==old['program']['source_obligations_ref'],'source context and broader obligations unchanged')
 check(set(old['program']['graph']['nodes'])-set(nodes)=={'criterion_002','criterion_003'},'remove only conditional declarations from execution')
 check(nodes['criterion_001']['next']=='end_unit' and nodes['tonic_choice']==old['program']['graph']['nodes']['tonic_choice'] and nodes['tonic_repair']==old['program']['graph']['nodes']['tonic_repair'],'minimal success link and same owned physical repair')
 check(nodes['repair_bind']['schema']['properties']['failed_criterion']['enum']==['source_extent','criterion_001'],'no stale conditional failed pass choices')
 # Specific finite paths inspect the actual emitted arcs and schema guards.
 extent={'source_extent_evidence':'synthetic full four-bar phrase report','unresolved_source_issue':'none_reported'}
 success={'reported_outcome':'reported_met','manual_evidence':'synthetic bar4 muted and tonic F# sung report'}
 repair={'low_F_sharp_drone_used':True,'density_reduced':True,'repair_evidence':'synthetic low F# drone and reduced-density retake report'}
 check(report_ok(nodes['source_extent'],extent) and report_ok(nodes['criterion_001'],success),'valid unconditional source reports')
 fpath=[g['entry'],nodes['source_extent']['next'],nodes['tonic_choice']['routes']['F#']['next'],nodes['criterion_001']['next']]
 check(fpath==['source_extent','tonic_choice','criterion_001','end_unit'],'F# requires only unconditional tonic report after complete source extent')
 check(all(k not in fpath for k in ('tonic_repair','criterion_002','criterion_003')) and 'low_F_sharp_drone_used' not in nodes['criterion_001']['schema']['properties'],'F# success never declares A-only repair')
 check(report_ok(nodes['tonic_repair'],repair),'valid A repair report')
 apath=[g['entry'],nodes['source_extent']['next'],nodes['tonic_choice']['routes']['A']['next'],'owned_release',nodes['tonic_repair']['next'],nodes['tonic_choice']['routes']['F#']['next'],nodes['criterion_001']['next']]
 check(apath==['source_extent','tonic_choice','tonic_repair','owned_release','tonic_choice','criterion_001','end_unit'] and nodes['tonic_repair']['physical'] is True,'A repair retains native owned release then retake')
 check(nodes['tonic_repair']['next']=='tonic_choice' and nodes['tonic_choice']['routes']['A']['next']=='tonic_repair','repeated sung A repeats repair/owned release; no automatic pass')
 for field in ('low_F_sharp_drone_used','density_reduced'):
  for v in (False,None,0,1,'true'):
   x=dict(repair);x[field]=v;reject(nodes['tonic_repair'],x)
 for node,payload,field in ((nodes['source_extent'],extent,'source_extent_evidence'),(nodes['criterion_001'],success,'manual_evidence'),(nodes['tonic_repair'],repair,'repair_evidence')):
  for v in ('',' \t\n',None,'x'*4097):x=dict(payload);x[field]=v;reject(node,x)
  x=dict(payload);x['undeclared']=True;reject(node,x)
 for v in ('reported_not_met','unknown',None,True):x=dict(success);x['reported_outcome']=v;reject(nodes['criterion_001'],x)
 for v in ('unresolved_issue_reported','unknown',None):x=dict(extent);x['unresolved_source_issue']=v;reject(nodes['source_extent'],x)
 for tonic in ('other','unknown'):
  next_node=nodes['tonic_choice']['routes'][tonic]['next'];check(next_node=='unresolved_tonic','non-F#/A enters unresolved terminal pass')
  for v in ('reported_not_met','unknown',None,'reported_met'):
   reject(nodes[next_node],{'reported_outcome':v,'manual_evidence':'synthetic unresolved tonic'})
 for value in ('F#','A','other','unknown'):check(schema_ok(nodes['tonic_choice']['schema'],{'reported_tonic':value}),'exact permitted source report menu')
 for value in ('C#','',None,True):check(not schema_ok(nodes['tonic_choice']['schema'],{'reported_tonic':value}),'unsupported tonic not synthesized');blocked+=1
 for n in nodes.values():
  if n['kind']=='end':check(n['grants_credit'] is False,'end never grants credit')
  if 'next' in n:check(n['next'] in nodes,'closed next-node reference')
  for route in n.get('routes',{}).values():check(route['next'] in nodes,'closed source route')
 check(row['program']['source_clock'] is None and row['program']['sounding_span'] is None and row['program']['fixed_bpm'] is None and row['program']['performance_observed'] is False and row['program']['automatic_mastery'] is False,'unknown clocks and manual-only limits preserved')
 result={'result':'PASS_ONE_KEY_DATA_BRANCH_CORRECTION','source_key':row['source_key'],'assertions':checks,'blocked_negative_unknown_fixtures':blocked,'correct_F_sharp_path':fpath,'correct_A_repair_path':apath,'original_source_record_changed':False,'original_literal_clauses_preserved':True,'native_owner_runs':0,'native_owned_release_retest_required':True,'run_seconds':time.perf_counter()-t,'official_acceptance_increment':0}
 (OUT/'data-validation.json').open('x').write(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(result))
if __name__=='__main__':main()
