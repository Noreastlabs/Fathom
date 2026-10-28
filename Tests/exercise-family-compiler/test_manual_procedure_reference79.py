from pathlib import Path
import importlib.util,json,time,hashlib,copy
ROOT=Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('support',ROOT/'Tools/exercise-family-compiler/manual_procedure_reference_support.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assertions=0;refusals=0

def check(value):
 global assertions
 assertions+=1;assert value

def refuse(fn,kind=m.BindingError):
 global refusals
 try:fn()
 except kind:refusals+=1;return
 raise AssertionError('NO_REFUSAL')

def main():
 start=time.monotonic();files=[('manual-procedure-level060-harmonic-r01','4e755362609a40c3103848e57472c3060aef6ba4cd8280ead0f4121e277575ad',44),('manual-procedure-source-targets-r01','2d763f64e47ccaa93b787267311f4661352674bf576d33865b918df21f869969',35)];cache=m.CachedWitnesses(ROOT);rows=[];programs=set();bindings=profiles=sustains=units=guards=0
 for family,digest,count in files:
  raw=(ROOT/'Build/manager-resume-r03'/family/'generated-r02/definitions.jsonl').read_bytes();check(m.sha(raw)==digest);selected=[json.loads(x) for x in raw.splitlines()];check(len(selected)==count);rows+=selected
 for row in rows:
  original,contract=cache.resolve(row);programs.add(row['program']['name']);check(original['package_key']==row['source_key'])
  for node in row['program']['graph']['nodes'].values():
   bound=m.resolve_node_bindings(contract,node);bindings+=len(bound.get('source_action_refs',[]))+('source_action_ref' in bound)+('release_source_action_ref' in bound)
   if 'release_source_action_ref' in bound:check(bound['release_source_action_ref']['action']=='explicit_learner_release_of_final_tonic_sustain');sustains+=1
   if len(bound.get('source_action_refs',[]))==2:
    check(node['physical'] is True and [x['original_contract_path'] for x in node['source_action_refs']]==[['steps',3],['steps',4]]);units+=1
    bad=copy.deepcopy(node);bad['source_action_refs'].reverse();refuse(lambda:m.resolve_node_bindings(contract,bad));bad=copy.deepcopy(node);bad['physical']=False;refuse(lambda:m.resolve_node_bindings(contract,bad))
   for guard in node.get('constraints',[]):
    if guard['kind']=='nonempty_trimmed_text':
     guards+=1;check(m.nonempty_trimmed_text(guard,' x '));check(m.nonempty_trimmed_text(guard,'x'*512));check(not m.nonempty_trimmed_text(guard,'x'*513));check(not m.nonempty_trimmed_text(guard,'\u3000\u00a0\t '));check(m.nonempty_trimmed_text(guard,'\u3000é\u00a0'));refuse(lambda:m.nonempty_trimmed_text(guard,True));bad=copy.deepcopy(guard);bad['extra']=True;refuse(lambda:m.nonempty_trimmed_text(bad,'plan'))
   if 'computed_expected' in node:
    op=node['computed_expected'];domain=row['program']['graph']['domains'][op['domain']]
    for entry in domain:
     actual=m.selected_domain_reports(op,entry['selection'],domain);check(set(actual)==set(op['fields']) and all(len(x)==len(entry['contacts']) for x in actual.values()));profiles+=1
     if 'chosen_pick_sequence' in actual:check(actual['chosen_pick_sequence']==[x['chosen_pick'] for x in entry['contacts']])
    unknown={x:None for x in op['selection']};refuse(lambda:m.selected_domain_reports(op,unknown,domain),m.UnresolvedReport);bad={x:True for x in op['selection']};refuse(lambda:m.selected_domain_reports(op,bad,domain));refuse(lambda:m.selected_domain_reports(op,domain[0]['selection'],domain+[domain[0]]))
  refuse(lambda:cache.resolve(row))
 check(len(rows)==79 and len(programs)==15 and units==guards and units>0 and sustains==8);check(cache.files_hashed==len({r['payload_ref']['path'] for r in rows}))
 proof=dict(outcome='PASS',rows=79,source_programs=15,cached_payloads_hashed_once=cache.files_hashed,exact_source_action_bindings=bindings,closed_domain_profiles=profiles,source_sustain_witnesses=sustains,uninterrupted_recovery_units=units,trimmed_plan_guards=guards,assertions=assertions,refusals=refusals,seconds=time.monotonic()-start,current224_mutated=False,owner_execution=False,source_PDF_TXT_reads=0,credit=False)
 out=ROOT/'Build/manager-resume-r03/manual-procedure-future79-r02/reference-proof-r01.json'
 with out.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
 print(json.dumps(proof))
if __name__=='__main__':main()
