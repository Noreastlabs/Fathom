from pathlib import Path
import importlib.util,json,time,hashlib
ROOT=Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('reference_support',ROOT/'Tools/exercise-family-compiler/manual_procedure_reference_support.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
count=0;refusals=0

def check(b):
 global count
 count+=1;assert b

def refuse(fn,kind=m.BindingError):
 global refusals
 try:fn()
 except kind:refusals+=1;return
 raise AssertionError('NO_REFUSAL')

def main():
 start=time.monotonic();base=ROOT/'Build/manager-resume-r03/manual-procedure-level060-harmonic-r01/generated-r02';raw=(base/'definitions.jsonl').read_bytes();check(hashlib.sha256(raw).hexdigest()=='4e755362609a40c3103848e57472c3060aef6ba4cd8280ead0f4121e277575ad');rows=[json.loads(x) for x in raw.splitlines()];check(len(rows)==44)
 cache=m.CachedWitnesses(ROOT);programs=set();bound=0;projections=0;sustains=0
 for row in rows:
  original,contract=cache.resolve(row);programs.add(row['program']['name']);check(original['package_key']==row['source_key']);check(m.sha(m.compact(row['program']))==row['contract_sha256'])
  for node in row['program']['graph']['nodes'].values():
   b=m.resolve_node_bindings(contract,node);bound+=len(b)
   if 'release_source_action_ref' in b:check(b['release_source_action_ref']['action']=='explicit_learner_release_of_final_tonic_sustain');check(b['release_source_action_ref']['duration_q'] is None and b['release_source_action_ref']['automatically_timed'] is False);sustains+=1
   if 'computed_expected' in node:
    op=node['computed_expected'];domain=row['program']['graph']['domains'][op['domain']]
    for entry in domain:
     values=m.selected_domain_reports(op,entry['selection'],domain);check(set(values)==set(op['fields']));check(all(len(x)==len(entry['contacts']) for x in values.values()));projections+=1
    unknown={k:None for k in op['selection']};refuse(lambda:m.selected_domain_reports(op,unknown,domain),m.UnresolvedReport)
    bad={k:True for k in op['selection']};refuse(lambda:m.selected_domain_reports(op,bad,domain));refuse(lambda:m.selected_domain_reports(op,domain[0]['selection'],domain+[domain[0]]))
  refuse(lambda:cache.resolve(row))
 check(len(programs)==7 and sustains==8);check(cache.files_hashed==len({r['payload_ref']['path'] for r in rows}))
 reference=rows[0]['payload_ref'].copy();reference['jsonl_line']=True;refuse(lambda:cache.payload(reference));reference=rows[0]['payload_ref'].copy();reference['path']='../escape';refuse(lambda:cache.payload(reference));reference=rows[0]['payload_ref'].copy();reference['sha256']='0'*64;refuse(lambda:cache.payload(reference));refuse(lambda:m.source_step(contract,{'original_contract_path':['steps',True]}));refuse(lambda:m.source_step(contract,{'original_contract_path':['steps',99999]}))
 result=dict(outcome='PASS',rows=44,source_programs=7,cached_payload_files_hashed_once=cache.files_hashed,source_step_bindings=bound,explicit_sustain_release_witnesses=sustains,closed_domain_profiles_projected=projections,assertions=count,expected_refusals=refusals,seconds=time.monotonic()-start,current224_mutated=False,native_admitted=False,source_rereads=0,credit=False)
 p=ROOT/'Build/manager-resume-r03/manual-procedure-reference-support-r01/proof-r02.json'
 with p.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(result))
if __name__=='__main__':main()
