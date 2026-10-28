from pathlib import Path
import json,hashlib,subprocess,sys,copy,datetime,time,resource
R=Path(__file__).resolve().parents[3];lane='fullscope-private-c-r01/two-pilot-exporter-review-r02';B=R/'Build'/lane/'targeted-r01';O=R/'Results'/lane;B.mkdir(exist_ok=False)
tool=R/'Tools/manager-resume-r01/two-pilot-admission-exporter-r02/export_descriptor.py';cases=('l003-modeb001','l004-ex002');inputs={};checks=0;results=[];tick=time.monotonic()
def check(v,msg):
 global checks
 checks+=1
 if not v:raise AssertionError(msg)
def pin(p):
 b=p.read_bytes();return {'path':str(p.relative_to(R)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):inputs[str(p.relative_to(R))]=pin(p);return json.loads(p.read_text())
def verify(ref):check(pin(R/ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')},'input pin '+ref['path']);inputs[ref['path']]={k:ref[k] for k in ('path','bytes','sha256')}
def write(p,x):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n');return pin(p)
check(pin(tool)['sha256']=='d50b9c6a7db6803d5ecbfacdee8c0d8126c3384fb88f91a7e71f96cd5abeeafd','frozen tool');inputs[str(tool.relative_to(R))]=pin(tool)
previous=read(R/'Results/fullscope-private-c-r01/two-pilot-exporter-review-r01/counterexample-cli-replays-r01.json')

def closure_refs(authref):
 verify(authref);a=read(R/authref['path']);verify(a['union']);u=read(R/a['union']['path'])
 for ref in list(u['components'].values())+[x['ref'] for x in a['live_anchors']]+a['evidence']:verify(ref)
 return a,u

def cli(name,authref,expect,reason=None):
 a,u=closure_refs(authref);out=B/(name+'.json');before={k:pin(R/k) for k in inputs}
 argv=[sys.executable,'-B',str(tool),'--root',str(R),'--case','l003-modeb001','--synthetic','--authority',authref['path'],'--authority-sha256',authref['sha256'],'--output',str(out.relative_to(R))]
 p=subprocess.run(argv,text=True,capture_output=True)
 check(p.returncode==(0 if expect=='ACCEPT' else 2),name+' exit '+p.stderr)
 if expect=='REFUSE':check(reason in p.stderr,name+' causal refusal');check(not out.exists(),name+' no output')
 else:
  d=json.loads(out.read_text());check(d['status']=='SYNTHETIC_GUARD_PASS_NOT_ADMITTED',name+' test boundary');check(d['item']=='fg:item:000240' and len(d['retained_present_variant_ids'])==12 and d['selected_runtime_variant_ids']==['fg:variant:000827','fg:variant:000829'],name+' finite binding')
 check(not list(B.glob('.descriptor-*')),name+' no staging');check(before=={k:pin(R/k) for k in before},name+' readonly inputs')
 results.append({'id':name,'expected':expect,'argv':argv,'authority':authref,'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'no_staging':True,'input_pins_unchanged':True,'output':pin(out) if out.exists() else None})
 return a,u
for f in previous['replays']:
 verify(f['output']);reason='CUMULATIVE_ITEM_SET' if 'without-allocation' in f['id'] else 'PRIOR_REGISTRY_REMAPPED'
 cli('old-'+f['id'],f['authority'],'REFUSE',reason)
# Minimal new fixtures: unchanged components referenced directly, only mutated registry/allocation emitted privately.
a0,u0=closure_refs(previous['replays'][0]['authority']);base=R/'Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence'
registry=read(base/'allocation01/cumulative-registry.json');allocation=read(base/'allocation01/cumulative-allocation.json');lineage=read(base/'handoff01/lineage-baseline.json')
check(len(registry['entities'])==5687,'all historical5687');check(len(allocation['records'])==551,'all historical551')

def fixture(name,variant=False,allocated=False):
 folder=B/name;folder.mkdir();u=copy.deepcopy(u0);a=copy.deepcopy(a0)
 u['components']['registry']=pin(base/'allocation01/cumulative-registry.json');u['components']['allocation']=pin(base/'allocation01/cumulative-allocation.json');u['components']['lineage']=pin(base/'handoff01/lineage-baseline.json')
 if variant:
  r=copy.deepcopy(registry);r['entities'].append({'id':'fg:variant:999998','kind':'variant','parent':'fg:item:000551','label':'C_SYNTHETIC_APPENDED_VARIANT'});u['components']['registry']=write(folder/'registry.json',r)
 if allocated:
  al=copy.deepcopy(allocation);al['records']['fg:item:000551']['variants']['C_SYNTHETIC_APPENDED_VARIANT']='fg:variant:999998';u['components']['allocation']=write(folder/'allocation.json',al)
  h=copy.deepcopy(lineage);h['records']['fg:item:000551']={'content_revision':2,'record_sha256':'a'*64};u['components']['lineage']=write(folder/'lineage.json',h)
 a['union']=write(folder/'union.json',u);return write(folder/'authority.json',a)
cli('unchanged-historical-positive',fixture('base'),'ACCEPT')
cli('new-orphan-registered-variant',fixture('orphan',variant=True),'REFUSE','CUMULATIVE_VARIANT_REVERSE_COVERAGE')
cli('coherent-later-variant-append',fixture('append',variant=True,allocated=True),'ACCEPT')
# Exact change analysis: no semantic draft change outside the explicitly allowed input_refs field.
comparisons=[]
for case in cases:
 b1=R/'Build/manager-resume-r01/two-pilot-admission-exporter-r01';b2=R/'Build/manager-resume-r01/two-pilot-admission-exporter-r02'
 s1=read(b1/(case+'-input.json'));s2=read(b2/(case+'-input.json'))
 check(set(s2)-set(s1)=={'historical_registry_ref'} and not(set(s1)-set(s2)),'only new registry input field')
 check({k:v for k,v in s2.items() if k!='historical_registry_ref'}==s1,'all old input facts exact');verify(s2['historical_registry_ref'])
 d1=read(b1/(case+'-draft.json'));d2=read(b2/(case+'-draft.json'));check(set(d1)==set(d2),'draft fields stable')
 changed=[k for k in d1 if d1[k]!=d2[k]];check(changed==['input_refs'],'only input references differ: '+repr(changed))
 refs1={r['path']:r for r in d1['input_refs']};refs2={r['path']:r for r in d2['input_refs']};removed=set(refs1)-set(refs2);added=set(refs2)-set(refs1)
 check(removed=={str((b1/(case+'-input.json')).relative_to(R))},'only old case input removed')
 check(added=={str((b2/(case+'-input.json')).relative_to(R)),s2['historical_registry_ref']['path']},'new input and registry ref only')
 check(all(refs1[k]==refs2[k] for k in set(refs1)&set(refs2)),'all common refs exact')
 comparisons.append({'case':case,'changed_top_level_fields':changed,'removed_reference_paths':sorted(removed),'added_reference_paths':sorted(added),'all_other_semantics_identical':True})
for ref in list(inputs.values()):verify(ref)
report={'schema':'fathom-two-pilot-targeted-rereview.1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','checks':checks,'elapsed_seconds':time.monotonic()-tick,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'classification':'TEST_FIXTURE_ONLY','live_current_union_proved':False,'native_runs':0,'results':results,'draft_comparisons':comparisons,'inputs':list(inputs.values())}
write(O/'targeted-results-r01.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('results','draft_comparisons','inputs')},indent=2));print(json.dumps([{'id':r['id'],'exit':r['exit_code'],'error':r['stderr'].strip()} for r in results],indent=2))
