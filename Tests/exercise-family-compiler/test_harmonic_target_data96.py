#!/usr/bin/env python3
"""Cheap all-row exact binding/type/order/source-extent guards; no native behavior."""
import copy,importlib.util,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('c',ROOT/'Tools/exercise-family-compiler/compile_harmonic_target_data96.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
checks=refusals=0
def need(v,why):
 global checks
 checks+=1
 if not v:raise ValueError(why)
def reject(fn):
 global refusals
 try:fn()
 except ValueError:refusals+=1;return
 raise ValueError('MALFORMED_SOURCE_MUST_REFUSE')
def main():
 start=time.perf_counter();cache=C.I.Cache(ROOT);closure=cache.json(str((C.OUT/'family-closure.json').relative_to(ROOT)));contexts=json.loads((C.OUT/'contexts.json').read_text());index=cache.json(str(C.INDEX.relative_to(ROOT)));entries={r['package_key']:r for r in index['rows']};rows=[C.I.strict_json(x) for x in (C.OUT/'definitions.jsonl').read_bytes().splitlines()];ex=json.loads((C.OUT/'source-binding-exceptions.json').read_text());ps={r['payload_ref']['path']:cache.read(r['payload_ref']).splitlines() for r in rows};profiles=json.loads((C.OUT/'source-workflow-blueprints.json').read_text());need(len(rows)==len({r['source_key'] for r in rows})==91 and len(ex['isolated_rows'])==5,'91constructed5isolated');count=0
 for r in rows:
  e=entries[r['source_key']];p=r['payload_ref'];line=ps[p['path']][p['jsonl_line']-1];original=C.I.strict_json(line);ctx=contexts[str(r['level'])]['source_context'];need(r['definition_sha256']==C.sha(C.raw({k:v for k,v in r.items() if k!='definition_sha256'}))==closure['definition_hashes'][r['source_key']],'closed row hash');need(C.sha(line)==r['original_row_sha256'] and C.sha(C.raw(original))==r['source_record_canonical_sha256'],'whole original row pin');need(r['source_contracts']==original['implementation'] and r['source_timing_authority']==original['timing_authority'] and r['literal_source_payload']==original['source_payload'],'entire source contract/timing/literal source untouched');need(r['contract_sha256']==C.sha(C.raw(original['implementation'])),'source canonical contract');need(C.guard(original,e,ctx)==r['source_policy_tag'],'real source guard');need(profiles[r['source_policy_tag']]==C.blueprints(r['source_policy_tag'],original),'exact common blueprint');need(not r['native_owner_implemented'] and not r['runtime_admitted'],'DATA no native claim')
  for atom,source in zip(r['source_contracts']['ordered_contacts'],original['implementation']['ordered_contacts']):
   for name,value in source.items():need(atom[name]==value,'every field/order/null/source annotation');count+=name=='ordinal'
  for field,value in [('ordinal',2),('finger',True),('midi',128),('acoustic_gate_q',[1,1]),('duration_q',[-1,1]),('string_low_to_high',7)]:
   bad=copy.deepcopy(original);bad['implementation']['ordered_contacts'][0][field]=value;reject(lambda:C.guard(bad,e,ctx))
  bad=copy.deepcopy(original);bad['timing_authority']['fixed_bpm']=120;reject(lambda:C.guard(bad,e,ctx))
 for x in ex['isolated_rows']:
  p=x['payload_ref'];original=C.I.strict_json(ps[p['path']][p['jsonl_line']-1]);entry=entries[x['source_key']];reject(lambda:C.guard(original,entry,contexts[str(original['level'])]['source_context']));need(x['cached_Nte_contact_binding_differences'] and original['implementation']['source_family']=='target_phrase','exact cached binding exception, no manufactured repair')
 need(count==802 and sum(len(x['cached_Nte_contact_binding_differences']) for x in ex['isolated_rows'])==69,'exact safe/source-conflict field extent');need(len(profiles)==11 and all(p['native_owner_implemented'] is False and p['behavior_equivalence_claimed'] is False for p in profiles.values()),'blueprints not behavior proof');result={'result':'PASS_DATA91_ISOLATED5','rows':91,'source_contacts':count,'source_dispatch_tags':11,'assertions':checks,'type_order_source_scope_refusals':refusals,'cached_source_binding_exception_rows':5,'cached_source_binding_differences':69,'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache.files),'source_PDF_TXT_reads':0,'native_behavior_tests':0,'official_acceptance_increment':0};C.save(C.OUT/'cheap-source-proof.json',result);print(json.dumps(result))
if __name__=='__main__':main()
