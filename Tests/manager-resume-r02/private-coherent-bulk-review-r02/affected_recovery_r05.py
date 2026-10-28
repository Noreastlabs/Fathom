"""Independent exact full-voicing loss / unusable register / retained-debt QA."""
from copy import deepcopy
import datetime, importlib.util, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LANE=Path('manager-resume-r02/private-coherent-bulk-review-r02')
spec=importlib.util.spec_from_file_location('independent_r05_helpers',ROOT/'Tests'/LANE/'bulk_review_r04.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
freeze=q.read('Results/'+str(LANE)+'/bulk-input-freeze-r04.json')
for r in freeze['inputs']:q.pin(r)
model=freeze['families']['C41']['model'];m=q.module(model['path'],'independent_c_reduction_r05')
old=q.module('Tools/fullscope-private-c-r01/coherent-level083-fixed-top-r65/fixed_top_model.py','independent_c_old_class_only_r05')
q.check(m.Refusal is not old.Refusal,'distinct old/new imported Refusal classes; no replay of old campaign')
keys=[r['package_key'] for r in q.read('Build/'+str(LANE)+'/level083-original-oracle.json')]
tick=time.perf_counter();cases=[]
for key in [keys[0],keys[35]]:
    f=m.FixedTopFlow(key);f.set_top(f.token(),q.top_choice(f))
    # Reach the final original source harmony's full texture; extra substitute still pending on C.
    while not(f.harmony_index==len(f.card['source_harmonies'])-1 and f.stage_index==3):q.texture(f)
    def lost(report):
        report['duties']['melody_clear']='no'
        report['diagnosis']='Full-voicing melody loss requires source immediate bass+melody reduction.'
    q.texture(f,modify_report=lost)
    source_index=f.harmony_index;stage_index=f.stage_index;before=deepcopy(f.__dict__)
    q.check(f.state=='needs_reduction' and f.reduction_required,'exact original full-voicing-loss causal state')
    oldtoken=f.token();f.cancel(f.token());f.reopen(f.token())
    q.refuse(lambda:f.restart_top(f.token(),dict(q.top_choice(f),diagnosis='Synthetic.')),'R05 reopen cannot skip release',m.Refusal,lambda:deepcopy(f.__dict__))
    q.refuse(lambda:f.release(oldtoken,{'learner_released':True}),'R05 stale pre-cancel owner',m.Refusal,lambda:deepcopy(f.__dict__))
    f.release(f.token(),{'learner_released':True});q.check(f.state=='needs_reduction' and f.reduction_required,'loss debt survives cancel/reopen physicalrelease')
    low=48 if f.card['literal_top']=='C' else 40
    choice=q.top_choice(f,low);choice['diagnosis']='Explicitly choose a low register; pending reduction must remain.'
    f.restart_top(f.token(),choice)
    q.check(f.current()['stage']=='bass_melody_reduction' and f.reduction_required and f.restart_after_reduction,'lowregister restart retains reduction debt')
    q.check(f.harmony_index==source_index and f.stage_index==stage_index,'reduction belongs to interrupted exact source harmony')
    q.refuse(lambda:f.finish(f.token()),'R05 pending debt no finish',m.Refusal,lambda:deepcopy(f.__dict__))
    f.sing_top(f.token(),deepcopy(q.SING))
    try:q.plan(f)
    except AssertionError:q.check(True,'independent exhaustive chosen contact search confirms unusable low register')
    else:raise AssertionError('Expected genuinely unusable pending-reduction register')
    invalid=dict({n:f.current()[n] for n in ('key','harmony','stage')},contacts=[deepcopy(f.top)],rationale='Insufficient low-register bass+melody attempt.')
    q.refuse(lambda:f.choose_voicing(f.token(),invalid),'R05 unusable low voicing refused',m.Refusal,lambda:deepcopy(f.__dict__))
    f.cannot_realize(f.token(),'No available guitar root below this chosen top; source obligation retained.')
    q.check(f.state=='needs_retry' and f.reduction_required,'impossible realization is diagnosed without invented root')
    new=q.top_choice(f);new['diagnosis']='Choose feasible register, preserve interrupted reduction then repeat whole source system.'
    before_new=deepcopy(f.__dict__);f.restart_top(f.token(),new)
    q.check(f.history[:len(before_new['history'])]==before_new['history'] and f.response_history==before_new['response_history'] and f.realization_history==before_new['realization_history'],'rechoice retains all old source/response/realization histories')
    q.check(f.harmony_index==source_index and f.current()['stage']=='bass_melody_reduction' and f.reduction_required,'feasible rechoice still requires same-harmony reduction')
    # Unknown reduction report must preserve debt and reach another complete reduction.
    def unknown(report):
        report['attack_counts'][0]=None;report['duties']['melody_clear']='uncertain';report['diagnosis']='Unknown reduction count and melody clarity; no completion inferred.'
    q.texture(f,modify_report=unknown)
    q.check(f.state=='needs_retry' and f.reduction_required and f.recovery,'unknown reduction report retains debt')
    q.refuse(lambda:f.advance(f.token()),'R05 unknown reduction cannot advance',m.Refusal,lambda:deepcopy(f.__dict__))
    f.cancel(f.token());f.reopen(f.token());f.release(f.token(),{'learner_released':True})
    q.check(f.state=='needs_retry' and f.reduction_required,'unknown-debt survives cancel and physical release')
    old_response=deepcopy(f.response_history);f.diagnose(f.token(),'Repeat complete source bass+melody reduction in feasible register.')
    q.check(f.response_history==old_response and f.current()['stage']=='bass_melody_reduction','diagnosed retry retains unknown declaration and reduction')
    q.texture(f)
    q.check(not f.reduction_required and not f.recovery and not f.restart_after_reduction,'only positive explicit reduction discharges obligation')
    q.check(f.harmony_index==f.stage_index==0 and f.state=='need_sing' and f.harmonies==f.card['source_harmonies'],'whole source re-realization begins after required reduction')
    textures=q.remaining(f)
    q.check(textures==(4 if f.card['module']=='AB' else 16) and f.state=='completed','replacement whole source system including C chosen extra reaches completion')
    q.check(f.history[:len(before['history'])]==before['history'] and len(f.response_history)>len(before['response_history']),'original lost melody, unknown and old history remain retained after finish')
    q.check(f.learner_view()['source_clocks'] is None and not f.learner_view()['mastery_awarded'] and not f.learner_view()['actual_performance_verified'],'no clock/hearing/mastery claims in corrected recovery')
    cases.append({'key':key,'interrupted_harmony':before['harmonies'][source_index],'interrupted_stage':stage_index,'failed_chosen_top_midi':low,'complete_replacement_textures':textures,'final_state':f.state,'loss_report_retained':before['response_history'][-1]['report'] in [x.get('report') for x in f.response_history],'source_reduction_completed_before_restart':True})
for r in freeze['inputs']:q.pin(r)
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcome':'PASS','model':model,'packet':freeze['families']['C41']['packet'],'checks':q.checks,'refusals':q.refusals,'refusal_criteria':q.labels,'elapsed_seconds':time.perf_counter()-tick,'cases':cases,'independent_fixture':'Original-derived source/chord role/tuning arithmetic, exhaustive finite contact search; no producer tests imported.','source_B_reused_by_hash':True,'old_r65_failure_retained':True,'Refusal_classes_distinct':True,'synthetic_reports_are_observations':False,'official_runtime_acceptance_increments':0,'inputs':freeze['inputs'],'command':'bundled-python Tests/'+str(LANE)+'/affected_recovery_r05.py'}
out=ROOT/'Results'/LANE/'affected-recovery-r05.json'
with out.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['inputs']},indent=2))
