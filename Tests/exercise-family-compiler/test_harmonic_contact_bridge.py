#!/usr/bin/env python3
"""All-row source binding from exact sealed cached DATA; original assets unread."""
import copy,hashlib,importlib.util,json,pathlib,time
ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'Build/manager-resume-r03/harmonic-contact-family118-r01'
spec=importlib.util.spec_from_file_location('compiler',ROOT/'Tools/exercise-family-compiler/compile_harmonic_contact_bridge.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
checks=0
def need(v,why):
 global checks
 checks+=1
 if not v:raise ValueError(why)
def walk(x,path):
 for component in path:x=x[component]
 return x
def main():
 t=time.perf_counter();cache=C.I.Cache(ROOT);original=[];pins=[]
 for path,size,digest in C.INPUTS:
  pin={'path':path,'bytes':size,'sha256':digest}
  for n,line in enumerate(cache.read(pin).splitlines(),1):original.append(C.I.strict_json(line));pins.append(dict(pin,jsonl_line=n))
 compiled=[C.I.strict_json(line) for line in (OUT/'definitions.jsonl').read_bytes().splitlines()];contexts=C.I.strict_json((OUT/'contexts.json').read_bytes());closure=C.I.strict_json((OUT/'family-closure.json').read_bytes());manifest=C.I.strict_json((ROOT/'Content/runtime/compiled-manual-families-v1/harmonic-contact/manifest.json').read_bytes());package=[C.I.strict_json(line) for line in (ROOT/'Content/runtime/compiled-manual-families-v1/harmonic-contact/definitions.jsonl').read_bytes().splitlines()]
 need(len(original)==len(compiled)==len(package)==118,'exact118');need(len({r['source_key'] for r in compiled})==len({r['source_identity'] for r in compiled})==118,'unique scope');count=refs=0
 for old,new,pin,pkg in zip(original,compiled,pins,package):
  restored=copy.deepcopy(new)
  for k in ('original_data_ref','program','contract_sha256','compiled_definition_sha256'):restored.pop(k)
  restored['definition_sha256']=restored.pop('original_data_definition_sha256');restored['schema']=old['schema'];need(restored==old,'entire original DATA deep equality');need(new['original_data_ref']==pin,'original row file/line pin');need(new['original_data_definition_sha256']==C.sha(C.raw({k:v for k,v in old.items() if k!='definition_sha256'})),'original canonical source data hash')
  need(new['compiled_definition_sha256']==C.sha(C.native_raw({k:v for k,v in new.items() if k!='compiled_definition_sha256'}))==closure['row_hashes'][new['source_key']],'native row closed hash');need(new['contract_sha256']==C.sha(C.raw(old['source_contracts']))==C.sha(C.native_raw(old['source_contracts']))==pkg['contract_sha256'],'canonical original source contract join');need(pkg['source_program_sha256']==C.sha(C.native_raw(new['program'])),'closed native program hash');need(pkg['package_binding_sha256']==C.sha(C.native_raw({'row':{k:v for k,v in pkg.items() if k!='package_binding_sha256'},'versions':manifest['versions']})),'separate exact package/version binding')
  context=contexts[str(new['level'])];need(new['context_ref']==context['context_ref'],'exact context witness');need(new['program']==C.program(old,context['source_context']),'deterministic tagged policy construction');need(new['program']['generated_alternative_contacts'] is False and new['program']['native_music_model'] is False and new['program']['source_clock'] is None and new['program']['source_acoustic_gates'] is None,'explicit no inferred acoustic or alternative realization');need(new['program']['original_contact_ordinals']==list(range(1,len(old['source_atoms'])+1)),'source ordering');
  for a,b in zip(old['source_atoms'],new['source_atoms']):
   for key in a:need(a[key]==b[key],'every exact atom property including null/role/pick/span/locator')
   count+=1
  for phase in new['program']['report_phases']+new['program']['repair_options']:
   for pointer in phase['source_refs']:
    if pointer[0]=='context':value=walk(context['source_context'],pointer[1:])
    else:value=walk(old,pointer)
    need(value is not None,'actual cached source reference');refs+=1
   need(set(phase['report_schema']['required'])==set(phase['report_schema']['properties']) and phase['report_schema']['additionalProperties'] is False,'closed typed criteria');need(phase['instructions'] and phase['guards'],'source duty/evidence criteria, no done bit')
 need(count==1510 and closure['phases']==137,'exact source contact/phase totals');need(manifest['rows']==118 and not manifest['runtime_admitted'] and not manifest['practice_admitted'] and not manifest['official_accepted'],'no release/acceptance claim')
 # Check exact current native/program helper pins once; assets are hash-only checked by native registry.
 for pin in manifest['versions']['code_pins']:need(C.ref(ROOT/pin['path'])==pin,'native shared code identity')
 result={'result':'PASS','rows':118,'source_atoms':count,'literal_source_refs':refs,'assertions':checks,'cached_original_data_files_hashed_once':len(cache.files),'original_PDF_TXT_reads':0,'seconds':time.perf_counter()-t,'official_acceptance_increment':0};C.save(OUT/'all-row-source-binding-proof.json',result);print(json.dumps(result))
if __name__=='__main__':main()
