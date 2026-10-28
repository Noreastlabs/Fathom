from pathlib import Path
import json,hashlib,copy,importlib.util,sys,time,resource,datetime,os
R=Path(__file__).resolve().parents[3]; B=R/'Build/fullscope-private-c-r01/two-pilot-exporter-review-r01/adversarial-r01'; O=R/'Results/fullscope-private-c-r01/two-pilot-exporter-review-r01'
B.mkdir(exist_ok=False); WORK=B/'fixture';WORK.mkdir();tool=R/'Tools/manager-resume-r01/two-pilot-admission-exporter-r01/export_descriptor.py'
assert hashlib.sha256(tool.read_bytes()).hexdigest()=='a31cfeb2a2b11308074b3e2d2ed6bc2a99821e95aa96bf89d79e7b695ff1a1a3'
s=importlib.util.spec_from_file_location('frozen_review_target',tool);ex=importlib.util.module_from_spec(s);s.loader.exec_module(ex)
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic();inputs={};checks=0;outcomes=[];findings=[]
def pin(p):
 b=p.read_bytes();return {'path':str(p.relative_to(R)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):
 inputs[str(p.relative_to(R))]=pin(p);return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n');return pin(p)
def check(c,msg):
 global checks
 checks+=1
 if not c:raise AssertionError(msg)
base=R/'Results/primary/20260912T204759Z-2.3.1.1.1-r14-evidence'
parts={'registry':read(base/'allocation01/cumulative-registry.json'),'allocation':read(base/'allocation01/cumulative-allocation.json'),'lineage':read(base/'handoff01/lineage-baseline.json'),'source_bindings':{'entries':[]},'reservations':{'entries':[]}}
specs={}
for case in ('l003-modeb001','l004-ex002'):
 spec=read(R/ex.CASE_ROOT/(case+'-input.json'));specs[case]=spec;parts['source_bindings']['entries'].append({'source_identity':spec['source_identity'],'item':spec['item'],'record_sha256':spec['canonical_record_sha256']})
check(len(parts['allocation']['records'])==551,'historical551')

def fixture(p,folder=WORK,authchange=None):
 folder.mkdir(exist_ok=True)
 components={k:write(folder/(k+'.json'),v) for k,v in p.items()}
 u={'schema':'fathom-cumulative-identity-union.1','generation':'C-INDEPENDENT-SYNTHETIC-001','classification':'TEST_FIXTURE','components':components}
 a={'schema':'fathom-controller-current-union-authority.1','generation':u['generation'],'classification':'TEST_FIXTURE','coverage':{'all_current_components':True,'all_held_and_permanent_reservations':True},'union':write(folder/'union.json',u),'live_anchors':[{'role':k,'ref':write(folder/('anchor-'+k+'.json'),{'role':k,'TEST_FIXTURE_ONLY':True})} for k in ('installed_registry','allocation','lineage','source_bindings','reservations')],'evidence':[write(folder/'fixture-evidence.json',{'synthetic':True,'current_global_state_proved':False})]}
 if authchange:authchange(a)
 return write(folder/'authority.json',a)
def protected_snapshot():
 return {p['path']:pin(R/p['path'])['sha256'] for p in inputs.values()}
def invoke(name,p=None,case='l003-modeb001',expected='REFUSE',authchange=None,optionchange=None,hook=None):
 p=parts if p is None else p;a=fixture(p,authchange=authchange);out=B/(name+'.json');before=protected_snapshot();argv={'root':R,'case':case,'output':str(out.relative_to(R)),'authority':a['path'],'authority_sha256':a['sha256'],'synthetic':True}
 if optionchange:argv.update(optionchange)
 restore=lambda:None
 if hook:restore=hook(a,out)
 error=None;descriptor=None
 try:descriptor=ex.export(**argv)
 except Exception as e:error=type(e).__name__+': '+str(e)
 finally:restore()
 accepted=descriptor is not None;actual='ACCEPT' if accepted else 'REFUSE';check(before==protected_snapshot(),name+' immutable fixture inputs changed')
 check(not list(WORK.glob('.descriptor-*')) and not list(B.glob('.descriptor-*')),name+' staging leak')
 if not accepted:check(not out.exists(),name+' unexpected output')
 outcome={'id':name,'case':case,'expected':expected,'actual':actual,'error':error,'authority':a,'no_staging':True,'protected_inputs_unchanged':True,'output':pin(out) if out.exists() else None}
 outcomes.append(outcome)
 if actual!=expected:
  proof=B/('finding-'+name);proof.mkdir();proofref=fixture(p,proof,authchange=authchange)
  finding=dict(outcome,repro_authority=proofref,repro_output=str((proof/'repro-output.json').relative_to(R)))
  findings.append(finding)
 if descriptor:
  spec=specs[case];check(descriptor['retained_present_variant_ids']==spec['retained_variant_ids'],name+' full12');check(descriptor['selected_runtime_variant_ids']==[x['id'] for x in spec['selected_variants']],name+' selected2')
  check(descriptor['retained_event_ids']==spec['event_ids'],name+' events');check(descriptor['retained_memberships']==len(spec['event_ids'])*12,name+' memberships');check(descriptor['selected_memberships']==len(spec['event_ids'])*2,name+' selected memberships')
  for f in ('new_ids','native_validated','runtime_admitted','queue_reserved','installed','learner_performance_observed','credit_awarded'):check(descriptor[f] in (False,0),name+' no authority')
 return descriptor

def mutation(fn):p=copy.deepcopy(parts);fn(p);return p
# Independent output comparison with original fixed adoptions and frozen drafts.
for case in specs:
 d=invoke('positive-'+case,case=case,expected='ACCEPT');r=invoke('repeat-'+case,case=case,expected='ACCEPT');check(d==r,'deterministic '+case)
 draftout=B/(case+'-draft.json');draft=ex.export(R,case,str(draftout.relative_to(R)),draft=True);check(draftout.read_bytes()==(R/ex.CASE_ROOT/(case+'-draft.json')).read_bytes(),'byte identical frozen draft')
 check(d['canonical_record_sha256']==specs[case]['canonical_record_sha256'],'fixed record digest')
 check(d['status']=='SYNTHETIC_GUARD_PASS_NOT_ADMITTED' and d['current_identity_closure']['native_or_admission_authority'] is False,'test boundary')
 check(d['fixed_bpm'] is None and d['acoustic_gate_q'] is None,'unknown performance')
# Cumulative identity counterexamples: keep both source/record/variant sets intact, change only unrelated registry fact.
invoke('unrelated-existing-item-reparent',mutation(lambda p:next(e for e in p['registry']['entities'] if e['id']=='fg:item:000445').update(parent='fg:module:000240')))
invoke('unrelated-existing-module-reparent',mutation(lambda p:next(e for e in p['registry']['entities'] if e['id']=='fg:module:000445').update(parent='fg:workbook:000003')))
invoke('registry-item-without-allocation-head',mutation(lambda p:p['registry']['entities'].append({'id':'fg:item:999999','kind':'item','parent':'fg:module:000445','label':'TEST_FIXTURE_ORPHAN'})))
invoke('unrelated-allocation-removed',mutation(lambda p:(p['allocation']['records'].pop('fg:item:000551'),p['lineage']['records'].pop('fg:item:000551'))))
invoke('unrelated-original-occurrence-remap',mutation(lambda p:p['allocation']['records']['fg:item:000551']['occurrences'].update({'ascending:1':'fg:item:000551:event:9999'})))
invoke('unselected-variant-map-loss',mutation(lambda p:p['allocation']['records']['fg:item:000240']['variants'].pop('quintuplets-up_and_down-U-even')))
invoke('foreign-source-same-item',mutation(lambda p:p['source_bindings']['entries'].append({'source_identity':'TEST_FIXTURE_OTHER_SOURCE','item':'fg:item:000240','record_sha256':specs['l003-modeb001']['canonical_record_sha256']})))
invoke('later-current-predecessor',mutation(lambda p:p['lineage']['records']['fg:item:000240'].update(content_revision=2)))
invoke('nonselected-reservation-conflict',mutation(lambda p:p['reservations']['entries'].append({'reservation_id':'C-R1','status':'HELD','source_identity':'TEST_FIXTURE_OTHER_SOURCE','ids':['fg:variant:000837']})))
invoke('unrelated-module-reservation-conflict',mutation(lambda p:p['reservations']['entries'].append({'reservation_id':'C-R2','status':'PERMANENT','source_identity':'TEST_FIXTURE_OTHER_SOURCE','ids':['fg:module:000445']})))
invoke('same-owner-reservation',mutation(lambda p:p['reservations']['entries'].append({'reservation_id':'C-EXISTING','status':'PERMANENT','source_identity':specs['l003-modeb001']['source_identity'],'ids':['fg:item:000240','fg:variant:000837']})),expected='ACCEPT')
invoke('missing-authority',optionchange={'authority':None,'authority_sha256':None})
invoke('wrong-authority-digest',optionchange={'authority_sha256':'0'*64})
invoke('synthetic-as-current',optionchange={'synthetic':False})
invoke('self-current-no-census',authchange=lambda a:a.update(live_anchors=[],current=True,timestamp='2099-01-01T00:00:00Z'))
for selector in ('l003-modea001','l004-ex001','fg:item:004901','l003-modeb002'):
 invoke('unsupported-'+selector.replace(':','-'),case=selector)
# Actual read/check logic runs unchanged; review hook mutates only its private anchor immediately before the original final recheck.
def late_anchor(a,out):
 old=ex.Reader.recheck;anchor=WORK/'anchor-reservations.json'
 def wrapped(reader):anchor.write_bytes(b'C private late-anchor drift');return old(reader)
 ex.Reader.recheck=wrapped
 return lambda:setattr(ex.Reader,'recheck',old)
invoke('final-live-anchor-drift',hook=late_anchor)
# Collision created after initial output checks must remain untouched and no stage leak.
def race_out(a,out):
 old=ex.Reader.recheck;target=out
 def wrapped(reader):old(reader);target.write_bytes(b'concurrent private sentinel')
 ex.Reader.recheck=wrapped
 def restore():
  setattr(ex.Reader,'recheck',old);check(target.read_bytes()==b'concurrent private sentinel','race sentinel survived');identity=pin(target);target.rename(B/'race-preserved-sentinel.txt');outcomes.append({'id':'race-sentinel-preservation','original_pin':identity,'preserved_as':str((B/'race-preserved-sentinel.txt').relative_to(R))})
 return restore
invoke('exclusive-publication-collision',hook=race_out)
# Protected output shapes, all possible destinations private-owned.
invoke('nonbuild-output',optionchange={'output':'Tests/fullscope-private-c-r01/two-pilot-exporter-review-r01/must-not-write.json'})
invoke('traversal-output',optionchange={'output':str(B.relative_to(R))+'/../must-not-write.json'})
symlink=B/'symlink-parent';symlink.symlink_to(WORK,target_is_directory=True)
invoke('symlink-parent-output',optionchange={'output':str(symlink.relative_to(R))+'/must-not-write.json'})
# Direct strict JSON entry points; no alternative validator or acceptance patch.
for text,name in [('{"schema":1,"schema":2}','duplicate-key'),('{"value":NaN}','nonfinite')]:
 try:ex.decode(text)
 except ex.Refusal as e:outcomes.append({'id':name,'actual':'REFUSE','error':str(e)});check(True,name)
 else:check(False,name)
for p in inputs.values():check(pin(R/p['path'])==p,'input final rehash')
report={'schema':'fathom-independent-two-pilot-review-execution.1','start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.monotonic()-tick,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'checks':checks,'classification':'TEST_FIXTURE_ONLY','current_live_global_union_proved':False,'native_runs':0,'tool':pin(tool),'inputs':list(inputs.values()),'outcomes':outcomes,'unexpected_acceptances':findings,'finding_count':len(findings),'verdict':'REVISE' if findings else 'PASS_EXECUTED_CHECKS_ONLY'}
write(O/'independent-results-r01.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','outcomes','unexpected_acceptances')},indent=2));print(json.dumps(findings,indent=2))
