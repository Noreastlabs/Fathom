from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r56');sys.path.insert(0,str(R/'Tools'/L))
from rhythm_contract import RhythmFlow,Refusal,KEYS,DEGREES,PITCHES,DICTATION_DUTIES,DUTIES,STAGES,validate_plan,rhythm_signature,contract
checks=refusals=0
def check(v):
    global checks
    checks+=1;assert v,checks
def refuse(f,call):
    global refusals
    before=deepcopy(f.__dict__) if f is not None else None
    try:call()
    except Refusal:refusals+=1
    else:raise AssertionError('expected refusal')
    check(f is None or f.__dict__==before)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
MIDIS=([60,62,64,67,64,62,60],[67,69,67,64,62,60])
DEG=('1 2 3 5 3 2 1','5 6 5 3 2 1');NOTES=('C D E G E D C','G A G E D C')
def plan(i,alternate=False):
    slots=[{'kind':'note','duration':[1,i+1]} for _ in MIDIS[i]]
    rest={'kind':'rest','duration':[1 if i==0 else 5,1]}
    if alternate:slots.insert(1,rest)
    else:slots.append(rest)
    return {'original_workbook':True,'provider':{'kind':'external_human','reference':'local chosen source-player rehearsal','ready':True,
      'chosen_midi':[x+12 if alternate else x for x in MIDIS[i]],'chosen_rhythm':{'meter_quarters':[4,1],'bar_count':2,'slots':slots}}}
def ready(i,alternate=False):
    f=RhythmFlow(KEYS[i]);f.set_plan(f.token(),plan(i,alternate));return f
def hear(f):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});check(f.source_release_required)
    f.end_listening(f.token(),True);check(f.source_stop_requested);f.release(f.token(),{'learner_released':True,'source_stopped':True});check(not f.source_release_required)
def written(f,pitch=None,rhythm='reference'):
    hear(f);f.commit(f.token(),'pitch',DEG[f.index].split() if pitch is None else pitch,'medium')
    hear(f);f.commit(f.token(),'rhythm',deepcopy(f.plan['provider']['chosen_rhythm']) if rhythm=='reference' else rhythm,'medium');check(f.state=='committed')
    f.reveal(f.token());check(f.ever_revealed)
def d_report(f):return {'key':f.key,'duties':{k:'yes' for k in DICTATION_DUTIES},'diagnosis':'','notes':'Manual source hearing report only.'}
def verification_ready(i):
    f=ready(i);written(f);f.report_dictation(f.token(),d_report(f));check(f.state=='verification_ready');return f
def perform(f):
    f.begin_verification(f.token(),{'stage':STAGES[f.stage],'ready':True});f.end_verification(f.token(),True);f.release(f.token(),{'learner_released':True,'source_stopped':None})
def v_report(f):return {'key':f.key,'stage':STAGES[f.stage],'duties':{k:'yes' for k in DUTIES[STAGES[f.stage]]},'diagnosis':'','notes':'Manual clap/singing report; not acoustically verified.'}
def stage_ready(i,stage):
    f=verification_ready(i)
    for _ in range(stage):perform(f);f.report_verification(f.token(),v_report(f));f.next_stage(f.token())
    return f

packet=Path('Build')/L/'rhythm-pitch-dictation-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][86:88]
check(len(rows)==2 and [r['package_key'] for r in rows]==list(KEYS))
for i,(r,o) in enumerate(zip(rows,old)):
    c=contract(i);check(json.loads(json.dumps(c))==r['implementation']['task']['contract']);check(c['printed_degrees']==DEG[i].split() and c['derived_pitch_names_confirmed_in_paired_txt']==NOTES[i].split())
    check(c['source_duration_class_quarters']==[1,i+1] and c['page_actual_degree_tokens']==53 and c['source_note_events']==[])
    for field in ('source_refs','source_payload','source_identity','package_key','timing_authority'):check(r[field]==o[field])
    for field in ('events','tab_blocks'):check(r['implementation'][field]==o['implementation'][field])
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[flag] is False)
    for alternate in (False,True):
        f=ready(i,alternate);view=f.learner_view();check('reference_answer' not in view and view['printed_context']=='C major')
        signature=rhythm_signature(f.plan['provider']['chosen_rhythm']);check(signature[0]==4 and signature[1]==2 and signature[3]==8)
        check(len(signature[2])==len(MIDIS[i]) and all(d==Fraction(1,i+1) for _,d in signature[2]))
        check(signature[2][1][0]==Fraction(1,i+1)+(Fraction(1 if i==0 else 5) if alternate else 0))
        written(f);f.report_dictation(f.token(),d_report(f));check(f.state=='verification_ready')
        for stage in range(3):
            check(f.stage==stage);perform(f);f.report_verification(f.token(),v_report(f));check(f.state=='verification_reported')
            if stage<2:refuse(f,lambda:f.finish(f.token()));f.next_stage(f.token())
        refuse(f,lambda:f.next_stage(f.token()));f.finish(f.token());check(f.state=='completed')
        answers=deepcopy(f.answer_history);f.set_plan(f.token(),plan(i));check(f.answers=={} and f.layer==0 and f.stage==0 and f.ever_revealed and f.answer_history==answers)
    # A different meter with no invented rests is also an explicit performer choice.
    p=plan(i);p['provider']['chosen_rhythm']['slots']=p['provider']['chosen_rhythm']['slots'][:-1]
    p['provider']['chosen_rhythm']['meter_quarters']=[7,2] if i==0 else [3,2];validate_plan(p,i);check(rhythm_signature(p['provider']['chosen_rhythm'])[3]==7 if i==0 else rhythm_signature(p['provider']['chosen_rhythm'])[3]==3)
    # Adjacent rest segments are equivalent, not a wrong rhythmic answer.
    f=ready(i);r=deepcopy(f.plan['provider']['chosen_rhythm']);r['slots']=r['slots'][:-1]+[{'kind':'rest','duration':[1 if i==0 else 5,2]}]*2
    check(rhythm_signature(r)==rhythm_signature(f.plan['provider']['chosen_rhythm']));written(f,rhythm=r);f.report_dictation(f.token(),d_report(f));check(f.state=='verification_ready')
    mutations=[lambda p:p.update(extra=True),lambda p:p.update(original_workbook=1),lambda p:p['provider'].update(kind='app_audio'),lambda p:p['provider'].update(ready=1),
      lambda p:p['provider'].update(reference=' '),lambda p:p['provider']['chosen_midi'].__setitem__(0,True),lambda p:p['provider']['chosen_midi'].__setitem__(0,128),
      lambda p:p['provider']['chosen_midi'].__setitem__(0,p['provider']['chosen_midi'][0]+1),lambda p:p['provider'].update(chosen_midi=[]),
      lambda p:p['provider']['chosen_rhythm'].update(bar_count=1),lambda p:p['provider']['chosen_rhythm'].update(bar_count=True),lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[3,1]),
      lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[0,1]),lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[4,0]),
      lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[8,2]),lambda p:p['provider']['chosen_rhythm']['slots'][0].update(duration=[True,1]),
      lambda p:p['provider']['chosen_rhythm']['slots'][0].update(duration=[0,1]),lambda p:p['provider']['chosen_rhythm']['slots'][0].update(kind='tie'),
      lambda p:p['provider']['chosen_rhythm']['slots'][0].update(kind='rest'),lambda p:p['provider']['chosen_rhythm']['slots'].pop()]
    for mutation in mutations:
        p=plan(i);mutation(p);f=RhythmFlow(KEYS[i]);refuse(f,lambda:f.set_plan(f.token(),p))
    # Preserve total two-bar extent but violate the source note duration class.
    p=plan(i);p['provider']['chosen_rhythm']['slots'][0]['duration']=[1,2] if i==0 else [1,1]
    p['provider']['chosen_rhythm']['slots'][-1]['duration']=[3,2] if i==0 else [9,2];refuse(None,lambda:validate_plan(p,i))
    for kind in ('unknown_pitch','wrong_pitch','unknown_rhythm','wrong_rhythm'):
        f=ready(i);pitch=DEG[i].split();rhythm=deepcopy(f.plan['provider']['chosen_rhythm'])
        if kind=='unknown_pitch':pitch[0]='?'
        elif kind=='wrong_pitch':pitch[0]='7'
        elif kind=='unknown_rhythm':rhythm=None
        else:rhythm['slots'][0]['duration']=[3,2]
        written(f,pitch,rhythm);r=d_report(f);refuse(f,lambda:f.report_dictation(f.token(),r));r['diagnosis']='Wrong or unknown layer retained for isolated diagnosis';f.report_dictation(f.token(),r);check(f.state=='dictation_retry')
        prior=deepcopy(f.answer_history);f.repeat_dictation(f.token(),'Rehear both separate layers');check(f.layer==0 and f.stage==0 and f.answers=={} and f.answer_history==prior and f.ever_revealed)
    for duty in DICTATION_DUTIES:
        for outcome in ('no','uncertain'):
            f=ready(i);written(f);r=d_report(f);r['duties'][duty]=outcome;refuse(f,lambda:f.report_dictation(f.token(),r));r['diagnosis']='Hearing obligation unresolved';f.report_dictation(f.token(),r);check(f.state=='dictation_retry')
    for stage in range(3):
        for duty in DUTIES[STAGES[stage]]:
            for outcome in ('no','uncertain'):
                f=stage_ready(i,stage);perform(f);r=v_report(f);r['duties'][duty]=outcome;refuse(f,lambda:f.report_verification(f.token(),r))
                r['diagnosis']='Diagnose this isolated/combined stage, preserve other reports';f.report_verification(f.token(),r);check(f.state=='verification_retry')
                refuse(f,lambda:f.next_stage(f.token()));refuse(f,lambda:f.finish(f.token()));f.repeat_stage(f.token(),'Repeat same released stage');check(f.stage==stage and f.state=='verification_ready')

for key in ('exercise-completeness-r01/level077/moduled/p010-t1-r3/3','exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7',None,True):refuse(None,lambda k=key:RhythmFlow(k))
f=ready(0);samples=[deepcopy(f)]
for layer in range(2):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});samples.append(deepcopy(f));f.end_listening(f.token(),True);samples.append(deepcopy(f))
    f.release(f.token(),{'learner_released':True,'source_stopped':True});samples.append(deepcopy(f));f.commit(f.token(),('pitch','rhythm')[layer],DEG[0].split() if layer==0 else f.plan['provider']['chosen_rhythm'],'low');samples.append(deepcopy(f))
f.reveal(f.token());samples.append(deepcopy(f));f.report_dictation(f.token(),d_report(f));samples.append(deepcopy(f))
for stage in range(3):
    f.begin_verification(f.token(),{'stage':STAGES[stage],'ready':True});samples.append(deepcopy(f));f.end_verification(f.token(),True);samples.append(deepcopy(f))
    f.release(f.token(),{'learner_released':True,'source_stopped':None});samples.append(deepcopy(f));f.report_verification(f.token(),v_report(f));samples.append(deepcopy(f))
    if stage<2:f.next_stage(f.token());samples.append(deepcopy(f))
f.finish(f.token());samples.append(deepcopy(f))
for sample in samples:
    f=deepcopy(sample);t=f.token();refuse(f,lambda:f.cancel(RhythmFlow(f.key).token()));refuse(f,lambda:f.cancel(list(t)))
    before=deepcopy(f.answers);prior=deepcopy(f.answer_history);revealed=f.ever_revealed;pending=f.source_release_required
    f.cancel(t);refuse(f,lambda:f.cancel(t));check(not pending or f.source_stop_requested);f.reopen(f.token())
    refuse(f,lambda:f.release(f.token(),{'learner_released':False,'source_stopped':True if pending else None}));refuse(f,lambda:f.release(f.token(),{'learner_released':True,'source_stopped':None if pending else True}))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None});check(f.answers==before and f.answer_history==prior and f.ever_revealed==revealed)
    if sample.state in ('listening','listening_release'):check(f.state=='ready_listen' and f.layer==sample.layer)
    if sample.state in ('verifying','verification_release','verification_report'):check(f.state=='verification_ready' and f.stage==sample.stage)
    for call in (lambda:f.set_plan(t,plan(0)),lambda:f.begin_listening(t,{}),lambda:f.end_listening(t,True),lambda:f.release(t,{}),lambda:f.commit(t,'pitch',[],'low'),lambda:f.reveal(t),
      lambda:f.report_dictation(t,{}),lambda:f.repeat_dictation(t,'retry'),lambda:f.begin_verification(t,{}),lambda:f.end_verification(t,True),lambda:f.report_verification(t,{}),lambda:f.next_stage(t),lambda:f.repeat_stage(t,'retry'),lambda:f.finish(t),lambda:f.reopen(t)):refuse(f,call)
    v=f.learner_view();v['answers'].clear();sv=f.source_player_view();sv['printed_degrees'].clear();check(f.answers==before and f.source_player_view()['printed_degrees']==DEG[0].split())
    if sample.state not in ('setup','dictation_retry','completed'):refuse(sample,lambda s=sample:s.set_plan(s.token(),plan(0)))

for layer in range(2):
    f=ready(0)
    if layer:hear(f);f.commit(f.token(),'pitch',DEG[0].split(),'high')
    for call in (lambda:f.reveal(f.token()),lambda:f.begin_verification(f.token(),{'stage':STAGES[0],'ready':True}),lambda:f.finish(f.token())):refuse(f,call)
    for c in ({'key':KEYS[1],'ready':True,'same_chosen_phrase':True},{'key':f.key,'ready':1,'same_chosen_phrase':True},{'key':f.key,'ready':True,'same_chosen_phrase':False}):refuse(f,lambda x=c:f.begin_listening(f.token(),x))
    hear(f);valid=DEG[0].split() if layer==0 else f.plan['provider']['chosen_rhythm'];kind=('pitch','rhythm')[layer]
    for confidence in ('',True,1,None):refuse(f,lambda x=confidence:f.commit(f.token(),kind,valid,x))
    for bad in ([],{'extra':1},True,'bad'):
        refuse(f,lambda x=bad:f.commit(f.token(),kind,x,'high'))
    refuse(f,lambda:f.commit(f.token(),('rhythm','pitch')[layer],valid,'high'))
    t=f.token();f.commit(t,kind,valid,'high');refuse(f,lambda:f.commit(t,kind,valid,'high'))
for stage in range(3):
    f=stage_ready(0,stage)
    refuse(f,lambda:f.begin_verification(f.token(),{'stage':STAGES[(stage+1)%3],'ready':True}));refuse(f,lambda:f.begin_verification(f.token(),{'stage':STAGES[stage],'ready':1}))
    perform(f)
    for field,value in (('key',KEYS[1]),('stage',STAGES[(stage+1)%3]),('notes','')):
        r=v_report(f);r[field]=value;refuse(f,lambda:f.report_verification(f.token(),r))
    r=v_report(f);r['duties'][DUTIES[STAGES[stage]][0]]=True;refuse(f,lambda:f.report_verification(f.token(),r))
    r=v_report(f);t=f.token();f.report_verification(t,r);r['duties'].clear();refuse(f,lambda:f.report_verification(t,v_report(f)));check(bool(f.history[-1]['data']['response']['duties']))

out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),
 'model':pin(Path('Tools')/L/'rhythm_contract.py'),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
