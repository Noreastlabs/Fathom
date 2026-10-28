#!/usr/bin/env python3
"""Closed flat installed package for the frozen ordered-contact manual owner."""
import argparse
import importlib.util
import json
import pathlib
import subprocess
import time

SPEC = importlib.util.spec_from_file_location('inventory', pathlib.Path(__file__).with_name('build_family_inventory.py'))
I = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(I)
OUT = 'Build/manager-resume-r03/ordered-contact-package-r01'
PACKAGE = 'Content/runtime/compiled-manual-families-v1/ordered-contact'
RESULT = 'Results/manager-resume-r03/ordered-contact-package-r01.json'
PROJECTION = {'path': 'Build/manager-resume-r03/ordered-contact-generation-r01/artifact-manifest.json', 'bytes': 3536,
              'sha256': '5d4240ec57ee559df2a77a0077f797c42fdebaaf7fa201bbd8dfbf6c2c6a9963'}
TASK = {'path': 'Build/manager-resume-r03/ordered-contact-task-ownership-correction-r02/artifact-manifest.json', 'bytes': 6923,
        'sha256': '033f05ab35a18a4d0256199a9c2ed6a897c4810b28ae2eac06efd078cd1c10cc'}
ASSETS = 'Build/manager-resume-r03/native-integration-r01/Fathom_artefacts/Debug/Fathom.app/Contents/Resources/source-library/bundle/assets'
NEW_CODE = ['Source/tasks/InstalledOrderedContactTaskRegistry.hpp','Source/tasks/InstalledOrderedContactTaskRegistry.cpp',
            'Source/tasks/OrderedContactTaskFormAdapter.hpp','Source/tasks/OrderedContactTaskFormAdapter.cpp',
            'Tests/exercise-family-compiler/ordered_contact_package_tests.cpp','Tools/exercise-family-compiler/package_ordered_contact_task.py']


def pin(cache, path):
    cache.read(path); return cache.reference(path)


def generate(root, refresh=False):
    start = time.perf_counter(); root = pathlib.Path(root).resolve(); cache = I.Cache(root)
    out = root / OUT; package = root / PACKAGE
    resumed=None
    if package.exists():
        I.require(refresh and not (out/'artifact-manifest.json').exists() and not (out/'native-validation.json').exists(),'FROZEN_PACKAGE_OR_REFRESH_NOT_ALLOWED')
        resumed=pin(cache,OUT+'/generation-receipt.json')
    else:I.require(out.is_dir() and not (out/'generation-receipt.json').exists(), 'NEW_PACKAGE_SCOPE')
    plan = cache.json({'path': OUT+'/package-plan.json','bytes':1619,'sha256':'bd2d2cc0ea615b8dd4bc99988fc0dd6858041a899be4bb29d9e5402cba2ec495'})
    I.require(plan['rows'] == 1401 and plan['no_App_CMake_Home_descriptor_or_frozen_source_changes'], 'PLAN_SCOPE')
    frozen = {}
    for manifest in [PROJECTION,TASK]:
        for ref in cache.json(manifest)['artifacts']:
            cache.read(ref); frozen[ref['path']] = ref
    table_path = 'Build/manager-resume-r03/ordered-contact-generation-r01/GeneratedOrderedContactData.hpp'
    table = cache.read(frozen[table_path]).decode()
    row_lines = table.split('inline const StoredRow rows[] = {\n',1)[1].split('\n};',1)[0].splitlines()
    rows = [I.strict_json('['+line.strip()[1:-2]+']') for line in row_lines]
    context_lines = table.split('inline constexpr const char* contexts[] = {\n',1)[1].split('\n};',1)[0].splitlines()
    native_contexts = [I.strict_json(json.loads(line.rstrip(','))) for line in context_lines]
    closure = cache.json(frozen['Build/manager-resume-r03/ordered-contact-generation-r01/family-closure.json'])
    oracle = cache.json(frozen['Build/manager-resume-r03/ordered-contact-task-r01/source-policy-oracle.json'])
    source_packets = [r for r in closure['input_pins'] if r['path'].startswith('Build/fullscope-private-a-r01/') and r['path'].endswith('/packet.jsonl')]
    I.require(len(rows)==1401 and len(native_contexts)==11 and len(source_packets)==10 and len(oracle['policies'])==10,'BULK_SHARED_COUNTS')
    source_packets.sort(key=lambda r:r['path']); packet_indices={r['path']:i for i,r in enumerate(source_packets)}
    policies = oracle['policies']; policy_sha = oracle['policy_closure_sha256']
    contract_context = {'schema':'fathom.ordered-contact-manual-definition.1',
        'native_row_closure_sha256':closure['row_closure_sha256'],'manual_policy_closure_sha256':policy_sha,
        'manual_owner_hpp_sha256':frozen['Source/tasks/OrderedContactTask.hpp']['sha256'],
        'manual_owner_cpp_sha256':frozen['Source/tasks/OrderedContactTask.cpp']['sha256']}
    versions = {'native_source_version':'fathom.private-selected-ordered-contact.1',
        'manual_source_version':'fathom.private-ordered-contact-manual-policy.1',
        'manual_owner_revision':2,
        'form_schema_version':'fathom.ordered-contact-manual-form.1',
        'native_row_closure_sha256':closure['row_closure_sha256'],'manual_policy_closure_sha256':policy_sha,
        'cohort_sha256':closure['cohort']['sha256'],'contract_context':contract_context,
        'frozen_projection_manifest_sha256':PROJECTION['sha256'],'frozen_task_manifest_sha256':TASK['sha256'],
        'code_pins':[frozen[p] for p in ['Source/tasks/OrderedContactFamily.hpp','Source/tasks/OrderedContactFamily.cpp',
            'Source/tasks/OrderedContactTask.hpp','Source/tasks/OrderedContactTask.cpp', table_path,
            'Build/manager-resume-r03/ordered-contact-task-r01/GeneratedOrderedContactPolicy.hpp']],
        'package_code_pins':[pin(cache,p) for p in NEW_CODE if not p.startswith('Tests/')]}
    source_assets = {}
    for p in policies:
        for kind in ['txt','pdf']:
            ref=p['source_context']['originals'][kind];source_assets[ref['path']]=ref
    # Integrity-only reuse of current host resources; no PDF/TXT extraction/copy.
    asset_root=root/ASSETS; I.require(asset_root.is_dir() and asset_root.resolve()==asset_root,'REAL_EXISTING_HOST_ASSET_ROOT')
    source_bytes=0
    for ref in source_assets.values():
        path=asset_root/ref['path'];cursor=asset_root
        for component in pathlib.Path(ref['path']).parts:
            I.require(component not in ['.','..'],'SAFE_SOURCE_ASSET_PATH');cursor/=component;I.require(not cursor.is_symlink(),'SOURCE_ASSET_SYMLINK')
        b=cache.read({'path':str(path.relative_to(root)),'bytes':ref['bytes'],'sha256':ref['sha256']});source_bytes+=len(b)
    I.require(len(source_assets)==20,'TWENTY_SOURCE_ASSETS')
    definitions=[];seen=set();offset=0
    for native,row_manifest in zip(rows,closure['rows_manifest']):
        key,sid,record,packet,packet_sha,line,level,begin,count,context,endN,endD,down,up,preserved=native
        I.require(key==row_manifest['key'] and sid==row_manifest['identity'] and record==row_manifest['source_record']
            and begin==row_manifest['contact_offset']==offset and count==row_manifest['contact_count']
            and key not in seen and len(down)==len(up)==count and I.digest(preserved.encode())==row_manifest['preserved_sha256'],'EVERY_CLOSED_NATIVE_ROW')
        I.require(source_packets[packet_indices[packet]]['sha256']==packet_sha and 0<=context<11 and 2<=level<=11,'ROW_SOURCE_POLICY_JOIN')
        body={'source_key':key,'source_identity':sid,'record_canonical_sha256':record,'source_packet':packet_indices[packet],
              'packet_line':line,'level':level,'native_contact_offset':begin,'contact_count':count,
              'metric_end_q':[endN,endD],'native_context':context,'source_policy':level-2}
        body['contract_sha256']=I.digest(I.compact({'row':body,'context':contract_context},True))
        definitions.append(body);seen.add(key);offset+=count
    I.require(offset==59528 and len(seen)==1401,'ALL_ROW_CONTACT_CLOSURE')
    package.mkdir(parents=True,exist_ok=True)
    raw=b''.join(I.compact(d,True)+b'\n' for d in definitions);(package/'definitions.jsonl').write_bytes(raw)
    def save(path,obj):
        ref=I.write_json(root/path,obj);ref['path']=path;return ref
    definitions_ref={'path':'definitions.jsonl','bytes':len(raw),'sha256':I.digest(raw)}
    context_ref=save(PACKAGE+'/contexts.json',{'schema':'fathom.ordered-contact-shared-contexts.1',
        'native_contexts':native_contexts,'source_policies':policies,'source_packets':source_packets})
    context_pin={**context_ref,'path':'contexts.json'}
    manifest={'schema':'fathom.ordered-contact-manual-package.1','family':'ordered-contact','scope':'manual-guidance-candidate',
        'rows':1401,'native_contexts':11,'source_policy_groups':10,'runtime_candidate':True,'runtime_admitted':False,
        'practice_admitted':False,'official_accepted':False,'grants_credit':False,'fixed_bpm':None,'source_acoustic_gates':None,
        'package_files':['manifest.json','definitions.jsonl','contexts.json'],'definitions':definitions_ref,'contexts':context_pin,
        'source_assets':[source_assets[p] for p in sorted(source_assets)],'version_bindings':versions,
        'resource_layout':{'package_subdirectory':'compiled-manual-families-v1/ordered-contact',
            'source_library_assets_subdirectory':'source-library/bundle/assets','two_explicit_real_roots_required':True}}
    manifest_ref=save(PACKAGE+'/manifest.json',manifest)
    binding='#pragma once\nnamespace fathom::tasks::ordered_contacts::package_binding {\n'
    binding+=f'inline constexpr const char* manifestSha="{manifest_ref["sha256"]}";\n'
    binding+='inline constexpr const char* versionsJson='+json.dumps(I.compact(versions,True).decode(),ensure_ascii=False)+';\n}\n'
    p=out/'GeneratedOrderedContactPackageBinding.hpp';p.write_text(binding)
    binding_ref=pin(cache,OUT+'/'+p.name)
    receipt={'result':'GENERATED_CLOSED_BULK_PACKAGE','rows':1401,'package_files':3,'shared_policies':10,'native_contexts':11,
        'source_assets_reused':20,'source_asset_bytes':source_bytes,'source_asset_copies':0,'original_source_research':0,
        'generation_seconds':round(time.perf_counter()-start,6),'package_bytes':len(raw)+context_ref['bytes']+manifest_ref['bytes'],
        'resumed_unsealed_receipt':resumed,
        'artifacts':{'manifest':manifest_ref,'definitions':{**definitions_ref,'path':PACKAGE+'/definitions.jsonl'},
            'contexts':context_ref,'native_binding':binding_ref},'versions':versions,'host_assets_root':ASSETS}
    save(OUT+'/generation-receipt.json',receipt);print(json.dumps(receipt))


def prove(root):
    root=pathlib.Path(root).resolve();cache=I.Cache(root);out=root/OUT
    receipt=cache.json(OUT+'/generation-receipt.json')
    for ref in receipt['artifacts'].values():cache.read(ref)
    for ref in receipt['versions']['package_code_pins']:cache.read(ref)
    for path in NEW_CODE:cache.read(path)
    for manifest in [PROJECTION,TASK]:
        for ref in cache.json(manifest)['artifacts']:
            if ref['path'].startswith('Source/') or ref['path'].endswith('.hpp'):cache.read(ref)
    executable=out/'ordered_contact_package_tests'
    command=['clang++','-std=c++17','-O0','-g0','-Wall','-Wextra','-Wpedantic','-Werror',
        '-I',str(root/'Source'),'-I',str(out),'-I',str(root/'Build/manager-resume-r03/ordered-contact-generation-r01'),
        '-I',str(root/'Build/manager-resume-r03/ordered-contact-task-r01'),
        *(str(root/p) for p in ['Source/tasks/OrderedContactFamily.cpp','Source/tasks/OrderedContactTask.cpp',
          'Source/tasks/OrderedContactTaskFormAdapter.cpp','Source/tasks/InstalledOrderedContactTaskRegistry.cpp',
          'Source/core/MusicModel.cpp','Source/core/Quantity.cpp','Source/content/StrictJson.cpp',
          'Tests/exercise-family-compiler/ordered_contact_package_tests.cpp']),'-o',str(executable)]
    start=time.perf_counter();result=subprocess.run(command,capture_output=True,text=True,cwd=root);compile_seconds=time.perf_counter()-start
    (out/'compile.log').write_text(result.stdout+result.stderr);I.require(result.returncode==0,'PACKAGE_COMPILE: see compile.log')
    start=time.perf_counter();result=subprocess.run([str(executable),str(root)],capture_output=True,text=True,cwd=root);run_seconds=time.perf_counter()-start
    (out/'native-validation.log').write_text(result.stderr);I.require(result.returncode==0,'PACKAGE_NATIVE_PROOF: '+result.stderr.strip())
    native=I.strict_json(result.stdout);I.require(native['result']=='PASS' and native['all_row_queries']==1401,'PROOF_DENOMINATOR')
    def save(path,obj):
        ref=I.write_json(root/path,obj);ref['path']=path;return ref
    proof=save(OUT+'/native-validation.json',native)
    build=save(OUT+'/standalone-build.json',{'command':command,'compile_seconds':round(compile_seconds,6),
        'proof_seconds':round(run_seconds,6),'input_code_pins':[pin(cache,p) for p in NEW_CODE],
        'App_build':False,'shared_CMake_Home_Content_descriptor_changed':False})
    report={'schema':'fathom.ordered-contact-package-result.1','result':'CLOSED_PACKAGE_NATIVE_PROOF_PASS','rows':1401,
        'native':native,'generation_seconds':receipt['generation_seconds'],'compile_seconds':round(compile_seconds,6),
        'proof_seconds':round(run_seconds,6),'package_files':3,'package_bytes':receipt['package_bytes'],
        'source_asset_copies':0,'source_original_research':0,'old_task_projection_proofs_replayed':False,
        'form_adapter':'Closed JSON Schema over one frozen native owner, no row logic or source metadata in learner forms',
        'layout':{'package':PACKAGE,'source_assets_root':ASSETS,'host_provides_two_explicit_real_roots':True},
        'source_clock':'Unselected manual passes unclocked; exact selected hand slots remain source-relative only',
        'sounding_gates':'unknown','official_runtime_acceptance_increments':0,
        'remaining_gates':['Distinct review and root App/resource/form integration','Broader external set/session/two-day reports',
            'No altered native realizations for optional mixed-mode/distance plans','Practice/acoustic/release authority unchanged'],
        'artifacts':{**receipt['artifacts'],'native_validation':proof,'standalone_build':build}}
    final=save(RESULT,report);refs=[final,proof,build,*receipt['artifacts'].values(),PROJECTION,TASK]
    for p in [*NEW_CODE,OUT+'/package-plan.json',OUT+'/generation-receipt.json',OUT+'/compile.log',OUT+'/native-validation.log',OUT+'/ordered_contact_package_tests']:
        refs.append(pin(cache,p))
    manifest=save(OUT+'/artifact-manifest.json',{'schema':'fathom.ordered-contact-package-artifacts.1','self_excluded':True,
        'artifacts':refs,'official_runtime_acceptance_increments':0})
    print(json.dumps({'result':final,'manifest':manifest,'native':native,'times':{'compile':round(compile_seconds,6),'proof':round(run_seconds,6)}}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default='.');parser.add_argument('--prove',action='store_true');parser.add_argument('--refresh-unsealed',action='store_true');args=parser.parse_args()
    try:prove(args.root) if args.prove else generate(args.root,args.refresh_unsealed)
    except (I.Refusal,OSError,KeyError,ValueError) as error:raise SystemExit('REFUSE: '+str(error))
