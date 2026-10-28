from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r57');sys.path.insert(0,str(R/'Tools'/L))
from motif_contract import MotifFlow,Refusal,KEYS,CHOICE,DICTATION_DUTIES,DUTIES,STAGES,validate_plan,rhythm_signature,contract
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
DEG=['1','3','2','5','4','3','2','1'];PITCH=['G','B','A','D','C','B','A','G'];MIDI=[55,59,57,62,60,59,57,55]
DURS=[[1,1],[1,1],[1,2],[1,2],[1,1],[1,1],[1,2],[1,2]]
def plan(alternate=False):
    slots=[{'kind':'note','duration':deepcopy(d)} for d in DURS]
    if alternate:slots.insert(4,{'kind':'rest','duration':[2,1]})
    return {'original_workbook':True,'provider':{'kind':'external_human','reference':'chosen local source player','ready':True,'motif_choice':CHOICE,
      'chosen_midi':[x+12 if alternate else x for x in MIDI],'chosen_rhythm':{'meter_quarters':[4 if alternate else 3,1],'bar_count':2,'slots':slots}}}
def ready(alternate=False):
    f=MotifFlow(KEYS[0]);f.set_plan(f.token(),plan(alternate));return f
def hear(f):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});check(f.source_release_required);f.end_listening(f.token(),True);check(f.source_stop_requested)
    f.release(f.token(),{'learner_released':True,'source_stopped':True})
def written(f,pitch=None,rhythm='reference'):
    hear(f);f.commit(f.token(),'pitch',DEG if pitch is None else pitch,'medium');hear(f)
    f.commit(f.token(),'rhythm',f.plan['provider']['chosen_rhythm'] if rhythm=='reference' else rhythm,'medium');f.reveal(f.token())
def d_report(f):return {'key':f.key,'duties':{k:'yes' for k in DICTATION_DUTIES},'diagnosis':'','notes':'Manual hearing report only.'}
def stage_ready(stage=0):
    f=ready();written(f);f.report_dictation(f.token(),d_report(f))
    for _ in range(stage):perform(f);f.report_verification(f.token(),v_report(f));f.next_stage(f.token())
    return f
def perform(f):
    f.begin_verification(f.token(),{'stage':STAGES[f.stage],'ready':True});f.end_verification(f.token(),True);f.release(f.token(),{'learner_released':True,'source_stopped':None})
def v_report(f):return {'key':f.key,'stage':STAGES[f.stage],'duties':{k:'yes' for k in DUTIES[STAGES[f.stage]]},'diagnosis':'','notes':'Manual isolated/combined phrase report only.'}
packet=Path('Build')/L/'qqee-dictation-overlay.jsonl';r=json.loads((R/packet).read_text());o=json.loads((R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()[88])
c=contract(0);check(json.loads(json.dumps(c))==r['implementation']['task']['contract']);check(c['printed_degrees']==DEG and c['derived_pitch_names_confirmed_in_paired_txt']==PITCH)
check(c['chosen_pattern_durations_quarters']==DURS and c['required_authored_motif_choice']==CHOICE and c['printed_rhythm_label']=='q q 2eighths')
for field in ('source_refs','source_payload','timing_authority','source_identity','package_key'):check(r[field]==o[field])
for field in ('events','tab_blocks'):check(r['implementation'][field]==o['implementation'][field])
check(c['source_note_events']==[] and c['page_actual_degree_tokens']==53)
for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[flag] is False)
for alternate in (False,True):
    f=ready(alternate);s=rhythm_signature(f.plan['provider']['chosen_rhythm']);check(s[0]==(4 if alternate else 3) and s[1]==2 and s[3]==(8 if alternate else 6))
    expected=[Fraction(0),Fraction(1),Fraction(2),Fraction(5,2),Fraction(5 if alternate else 3),Fraction(6 if alternate else 4),Fraction(7 if alternate else 5),Fraction(15,2) if alternate else Fraction(11,2)]
    check([x[0] for x in s[2]]==expected and [x[1] for x in s[2]]==[Fraction(*d) for d in DURS]);check('reference_answer' not in f.learner_view())
    written(f);f.report_dictation(f.token(),d_report(f));check(f.state=='verification_ready')
    for stage in range(3):
        check(f.stage==stage);perform(f);f.report_verification(f.token(),v_report(f));check(f.state=='verification_reported')
        if stage<2:refuse(f,lambda:f.finish(f.token()));f.next_stage(f.token())
    refuse(f,lambda:f.next_stage(f.token()));f.finish(f.token());check(f.state=='completed')
    prior=deepcopy(f.answer_history);f.set_plan(f.token(),plan());check(f.answers=={} and f.ever_revealed and f.answer_history==prior and f.layer==0 and f.stage==0)

# Explicit policy and contiguous motif ordering distinguish this source from homogeneous notes.
mutations=[lambda p:p['provider'].pop('motif_choice'),lambda p:p['provider'].update(motif_choice=''),lambda p:p['provider'].update(motif_choice='one_repetition'),
 lambda p:p['provider'].update(motif_choice=True),lambda p:p['provider'].update(kind='app_audio'),lambda p:p['provider'].update(reference=''),lambda p:p['provider'].update(ready=1),
 lambda p:p.update(original_workbook=False),lambda p:p['provider']['chosen_midi'].__setitem__(0,54),lambda p:p['provider']['chosen_midi'].__setitem__(0,True),
 lambda p:p['provider']['chosen_midi'].__setitem__(0,128),lambda p:p['provider']['chosen_rhythm'].update(bar_count=1),lambda p:p['provider']['chosen_rhythm'].update(bar_count=True),
 lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[4,1]),lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[6,2]),lambda p:p['provider']['chosen_rhythm'].update(meter_quarters=[1,0]),
 lambda p:p['provider']['chosen_rhythm']['slots'][0].update(duration=[True,1]),lambda p:p['provider']['chosen_rhythm']['slots'][0].update(kind='rest'),lambda p:p['provider']['chosen_rhythm']['slots'].pop()]
for mutation in mutations:
    p=plan();mutation(p);f=MotifFlow(KEYS[0]);refuse(f,lambda:f.set_plan(f.token(),p))
for durations in ([[1,1]]*8,[[1,2]]*8,[DURS[(i+2)%8] for i in range(8)]):
    p=plan();p['provider']['chosen_rhythm']['slots']=[{'kind':'note','duration':x} for x in durations]
    total=sum((Fraction(*x) for x in durations),Fraction(0))/2;p['provider']['chosen_rhythm']['meter_quarters']=[total.numerator,total.denominator]
    refuse(None,lambda:validate_plan(p,0))
for location in (1,2,3,5,6,7):
    p=plan();p['provider']['chosen_rhythm']['slots'].insert(location,{'kind':'rest','duration':[2,1]});p['provider']['chosen_rhythm']['meter_quarters']=[4,1];refuse(None,lambda:validate_plan(p,0))
for key in ('exercise-completeness-r01/level077/moduled/p010-t1-r1/1','exercise-completeness-r01/level077/moduled/p010-t1-r2/2','exercise-completeness-r01/level077/moduled/p010-t1-r4/4','exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7',None,True):refuse(None,lambda k=key:MotifFlow(k))
f=ready(True);answer=deepcopy(f.plan['provider']['chosen_rhythm']);answer['slots'][4:5]=[{'kind':'rest','duration':[1,1]},{'kind':'rest','duration':[1,1]}]
check(rhythm_signature(answer)==rhythm_signature(f.plan['provider']['chosen_rhythm']));written(f,rhythm=answer);f.report_dictation(f.token(),d_report(f));check(f.state=='verification_ready')
for kind in ('unknown_pitch','wrong_pitch','unknown_rhythm','wrong_rhythm'):
    f=ready();pitch=deepcopy(DEG);rhythm=deepcopy(f.plan['provider']['chosen_rhythm'])
    if kind=='unknown_pitch':pitch[0]='?'
    elif kind=='wrong_pitch':pitch[0]='7'
    elif kind=='unknown_rhythm':rhythm=None
    else:rhythm['slots'][0]['duration']=[3,2]
    written(f,pitch,rhythm);d=d_report(f);refuse(f,lambda:f.report_dictation(f.token(),d));d['diagnosis']='Unresolved written layer';f.report_dictation(f.token(),d)
    check(f.state=='dictation_retry');prior=deepcopy(f.answer_history);f.repeat_dictation(f.token(),'Rehear each layer');check(f.layer==0 and f.answers=={} and f.answer_history==prior and f.ever_revealed)
for duty in DICTATION_DUTIES:
    for outcome in ('no','uncertain'):
        f=ready();written(f);d=d_report(f);d['duties'][duty]=outcome;refuse(f,lambda:f.report_dictation(f.token(),d));d['diagnosis']='Source hearing unresolved';f.report_dictation(f.token(),d);check(f.state=='dictation_retry')
for stage in range(3):
    for duty in DUTIES[STAGES[stage]]:
        for outcome in ('no','uncertain'):
            f=stage_ready(stage);perform(f);v=v_report(f);v['duties'][duty]=outcome;refuse(f,lambda:f.report_verification(f.token(),v));v['diagnosis']='Repeat this isolated/combined layer';f.report_verification(f.token(),v)
            refuse(f,lambda:f.next_stage(f.token()));refuse(f,lambda:f.finish(f.token()));f.repeat_stage(f.token(),'Explicit stage retry');check(f.stage==stage and f.state=='verification_ready')

f=ready();samples=[deepcopy(f)]
for layer in range(2):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});samples.append(deepcopy(f));f.end_listening(f.token(),True);samples.append(deepcopy(f))
    f.release(f.token(),{'learner_released':True,'source_stopped':True});samples.append(deepcopy(f));f.commit(f.token(),('pitch','rhythm')[layer],DEG if layer==0 else f.plan['provider']['chosen_rhythm'],'high');samples.append(deepcopy(f))
f.reveal(f.token());samples.append(deepcopy(f));f.report_dictation(f.token(),d_report(f));samples.append(deepcopy(f))
for stage in range(3):
    f.begin_verification(f.token(),{'stage':STAGES[stage],'ready':True});samples.append(deepcopy(f));f.end_verification(f.token(),True);samples.append(deepcopy(f));f.release(f.token(),{'learner_released':True,'source_stopped':None});samples.append(deepcopy(f))
    f.report_verification(f.token(),v_report(f));samples.append(deepcopy(f))
    if stage<2:f.next_stage(f.token());samples.append(deepcopy(f))
f.finish(f.token());samples.append(deepcopy(f))
for sample in samples:
    f=deepcopy(sample);t=f.token();refuse(f,lambda:f.cancel(MotifFlow(f.key).token()));refuse(f,lambda:f.cancel(list(t)));before=deepcopy(f.answers);prior=deepcopy(f.answer_history);revealed=f.ever_revealed;pending=f.source_release_required
    f.cancel(t);refuse(f,lambda:f.cancel(t));check(not pending or f.source_stop_requested);f.reopen(f.token())
    refuse(f,lambda:f.release(f.token(),{'learner_released':False,'source_stopped':True if pending else None}));refuse(f,lambda:f.release(f.token(),{'learner_released':True,'source_stopped':None if pending else True}))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None});check(f.answers==before and f.answer_history==prior and f.ever_revealed==revealed)
    if sample.state in ('listening','listening_release'):check(f.state=='ready_listen' and f.layer==sample.layer)
    if sample.state in ('verifying','verification_release','verification_report'):check(f.state=='verification_ready' and f.stage==sample.stage)
    for call in (lambda:f.set_plan(t,plan()),lambda:f.begin_listening(t,{}),lambda:f.end_listening(t,True),lambda:f.release(t,{}),lambda:f.commit(t,'pitch',[],'low'),lambda:f.reveal(t),lambda:f.report_dictation(t,{}),
      lambda:f.repeat_dictation(t,'retry'),lambda:f.begin_verification(t,{}),lambda:f.end_verification(t,True),lambda:f.report_verification(t,{}),lambda:f.next_stage(t),lambda:f.repeat_stage(t,'retry'),lambda:f.finish(t),lambda:f.reopen(t)):refuse(f,call)
    v=f.source_player_view();v['derived_pitches_confirmed_by_paired_txt'].clear();lv=f.learner_view();lv['answers'].clear();check(f.answers==before and f.source_player_view()['derived_pitches_confirmed_by_paired_txt']==PITCH)
    if sample.state not in ('setup','dictation_retry','completed'):refuse(sample,lambda s=sample:s.set_plan(s.token(),plan()))
for layer in range(2):
    f=ready()
    if layer:hear(f);f.commit(f.token(),'pitch',DEG,'high')
    for call in (lambda:f.reveal(f.token()),lambda:f.begin_verification(f.token(),{'stage':STAGES[0],'ready':True}),lambda:f.finish(f.token())):refuse(f,call)
    hear(f);kind=('pitch','rhythm')[layer];valid=DEG if layer==0 else f.plan['provider']['chosen_rhythm']
    for bad in ([],True,'bad',{'extra':1}):refuse(f,lambda x=bad:f.commit(f.token(),kind,x,'high'))
    refuse(f,lambda:f.commit(f.token(),('rhythm','pitch')[layer],valid,'high'));t=f.token();f.commit(t,kind,valid,'high');refuse(f,lambda:f.commit(t,kind,valid,'high'))
for stage in range(3):
    f=stage_ready(stage);refuse(f,lambda:f.begin_verification(f.token(),{'stage':STAGES[(stage+1)%3],'ready':True}));refuse(f,lambda:f.begin_verification(f.token(),{'stage':STAGES[stage],'ready':1}))
    perform(f);v=v_report(f);v['stage']=STAGES[(stage+1)%3];refuse(f,lambda:f.report_verification(f.token(),v));v=v_report(f);v['duties'][DUTIES[STAGES[stage]][0]]=True;refuse(f,lambda:f.report_verification(f.token(),v))
    v=v_report(f);t=f.token();f.report_verification(t,v);v['duties'].clear();refuse(f,lambda:f.report_verification(t,v_report(f)));check(bool(f.history[-1]['data']['response']['duties']))
out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),
 'model':pin(Path('Tools')/L/'motif_contract.py'),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
