from pathlib import Path
from copy import deepcopy
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r55');sys.path.insert(0,str(R/'Tools'/L))
from melody_contract import MelodyFlow,Refusal,KEYS,RAW,LAYERS,DICTATION_DUTIES,TARGET_DUTIES,validate_source_plan,validate_guitar_plan,contract
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
MIDI=([60,62,64,67,64,62,60],[67,69,67,64,62,60],[55,59,57,62,60,59,57,55],
 [69,66,64,62,61,62],[57,60,62,64,67,64,60,57],[59,57,55,54,52],[64,65,68,69,68,64],[57,59,60,64,66,68,69])
CONTOURS=('UUUDDD','UDDDD','UDUDDDD','DDDDU','UUUUDDD','DDDD','UUUDD','UUUUUU')
DEGREES=('1 2 3 5 3 2 1','5 6 5 3 2 1','1 3 2 5 4 3 2 1','5 3 2 1 7 1','1 b3 4 5 b7 5 b3 1','5 4 b3 2 1','5 b6 7 1 7 5','1 2 b3 5 6 7 1')
NOTES=('C D E G E D C','G A G E D C','G B A D C B A G','A F# E D C# D','A C D E G E C A','B A G F# E','E F G# A G# E','A B C E F# G# A')
TUNING=(('E',40),('A',45),('D',50),('G',55),('B',59),('e',64))
def source_plan(i,shift=0):return {'prerequisites':{'own_instrument':True,'original_workbook':True},'provider':{'kind':'external_human','reference':'local source partner chosen by learner','ready':True,'chosen_midi':[n+shift for n in MIDI[i]],'chosen_timing':'partner-selected free timing, repeated consistently for three passes'}}
def guitar_plan(i,shift=0):
    notes=[n+shift for n in MIDI[i]]
    return {'sung_midi':notes,'contacts':[{'string':s,'fret':n-root} for n in notes for s,root in [next((s,v) for s,v in TUNING if 0<=n-v<=24)]]}
def ready(i,shift=0):
    f=MelodyFlow(KEYS[i]);f.set_source_plan(f.token(),source_plan(i,shift));return f
def perform_listening(f):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});check(f.source_release_required)
    f.end_listening(f.token(),True);check(f.source_stop_requested)
    f.release(f.token(),{'learner_released':True,'source_stopped':True});check(not f.source_release_required)
def written(f,unknown=None,enharmonic=False):
    responses=[list(CONTOURS[f.index]),DEGREES[f.index].split(),NOTES[f.index].split()]
    if unknown is not None:responses[unknown][0]='?'
    if enharmonic:responses[2]=[{'F#':'Gb','C#':'Db','G#':'Ab'}.get(x,x) for x in responses[2]]
    for layer in range(3):
        check(f.layer==layer and 'reference_answer' not in f.learner_view());perform_listening(f)
        f.commit(f.token(),LAYERS[layer],responses[layer],'medium')
    check(f.state=='committed' and set(f.answers)==set(LAYERS));f.reveal(f.token());check(f.ever_revealed)
def dictation_report(f):return {'key':f.key,'duties':{k:'yes' for k in DICTATION_DUTIES},'diagnosis':'','notes':'Manual source and written layers reviewed; no acoustic verification.'}
def targets_ready(i,shift=0):
    f=ready(i,shift);written(f);f.report_dictation(f.token(),dictation_report(f));check(f.state=='guitar_plan');f.set_guitar_plan(f.token(),guitar_plan(i,shift));return f
def perform_target(f):
    f.begin_target(f.token(),True);f.sung(f.token(),True);f.setup_target(f.token(),True);f.attack(f.token(),True)
    f.release(f.token(),{'learner_released':True,'source_stopped':None})
def target_report(f):return {'key':f.key,'source_order':f.target+1,'chosen_contact':deepcopy(f.guitar['contacts'][f.target]),'attack_count':1,
 'duties':{k:'yes' for k in TARGET_DUTIES},'diagnosis':'','notes':'Manual only; physical performance not observed.'}

packet=Path('Build')/L/'melodic-dictation-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][78:86]
check(len(rows)==8 and [r['package_key'] for r in rows]==list(KEYS));check(sum(len(s.split()) for s in NOTES)==53)
for i,(r,o) in enumerate(zip(rows,old)):
    c=contract(i);check(c==r['implementation']['task']['contract']);check(c['printed_degrees']==DEGREES[i].split() and c['printed_notes']==NOTES[i].split())
    check(c['source_extent_header']=='8 PHRASES | 64 TONES' and c['actual_eight_row_pitch_token_count']==53)
    for field in ('source_refs','source_payload','timing_authority','source_identity','package_key'):check(r[field]==o[field])
    for field in ('events','tab_blocks','source_field_occurrences'):check(r['implementation'][field]==o['implementation'][field])
    check(r['implementation']['events']==[] and r['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[flag] is False)
    for shift in (0,12):
        f=ready(i,shift);check(f.source_player_view()['chosen_contour']==list(CONTOURS[i]));check('chosen_midi' not in f.learner_view())
        written(f,enharmonic=True);check(all(f.symbolic_matches().values()));f.report_dictation(f.token(),dictation_report(f))
        f.set_guitar_plan(f.token(),guitar_plan(i,shift));check(f.state=='target_ready')
        for target in range(len(MIDI[i])):
            check(f.target==target);perform_target(f);f.report_target(f.token(),target_report(f));check(f.state=='target_reported')
            if target<len(MIDI[i])-1:refuse(f,lambda:f.finish(f.token()));f.next_target(f.token())
        refuse(f,lambda:f.next_target(f.token()));f.finish(f.token());check(f.state=='completed')
        check(all(x.get('data',{}).get('performance_verified',False) is False for x in f.history))
        before=deepcopy(f.answer_history);f.set_source_plan(f.token(),source_plan(i));check(f.layer==0 and f.target==0 and f.answers=={} and f.guitar is None and f.ever_revealed and f.answer_history==before)

for badkey in ('exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7',KEYS[0]+'x',None,0):refuse(None,lambda k=badkey:MelodyFlow(k))
# Both source-compatible register directions are explicit choices, not source-derived defaults.
p=source_plan(3);p['provider']['chosen_midi'][-1]-=12;validate_source_plan(p,3);f=MelodyFlow(KEYS[3]);f.set_source_plan(f.token(),p);check(f.source_player_view()['chosen_contour'][-1]=='D')
for i in range(8):
    p=source_plan(i)
    mutations=[lambda q:q.update(extra=True),lambda q:q['prerequisites'].update(own_instrument=False),lambda q:q['prerequisites'].update(original_workbook=1),
      lambda q:q['provider'].update(kind='app_audio'),lambda q:q['provider'].update(reference=' '),lambda q:q['provider'].update(ready=1),
      lambda q:q['provider'].update(chosen_timing=''),lambda q:q['provider'].update(chosen_midi=q['provider']['chosen_midi'][:-1]),
      lambda q:q['provider']['chosen_midi'].__setitem__(0,True),lambda q:q['provider']['chosen_midi'].__setitem__(0,-1),
      lambda q:q['provider']['chosen_midi'].__setitem__(0,128),lambda q:q['provider']['chosen_midi'].__setitem__(0,q['provider']['chosen_midi'][0]+1)]
    for mutation in mutations:
        q=deepcopy(p);mutation(q);f=MelodyFlow(KEYS[i]);refuse(f,lambda:f.set_source_plan(f.token(),q))
    gp=guitar_plan(i)
    mutations=[lambda q:q.update(extra=1),lambda q:q['sung_midi'].__setitem__(0,q['sung_midi'][0]+12),lambda q:q['sung_midi'].__setitem__(0,True),
      lambda q:q['contacts'][0].update(fret=True),lambda q:q['contacts'][0].update(fret=-1),lambda q:q['contacts'][0].update(fret=25),
      lambda q:q['contacts'][0].update(string='X'),lambda q:q['contacts'][0].update(fret=q['contacts'][0]['fret']+1),lambda q:q.update(contacts=[])]
    for mutation in mutations:
        q=deepcopy(gp);mutation(q);refuse(None,lambda:validate_guitar_plan(q,MIDI[i]))
    for unknown in range(3):
        f=ready(i);written(f,unknown);r=dictation_report(f);refuse(f,lambda:f.report_dictation(f.token(),r));r['diagnosis']='Uncertain written target must be reheard';f.report_dictation(f.token(),r)
        check(f.state=='dictation_retry');prior=deepcopy(f.answer_history);f.repeat_dictation(f.token(),'Repeat all three layers');check(f.state=='ready_listen' and f.layer==0 and f.ever_revealed and f.answer_history==prior)
    for duty in DICTATION_DUTIES:
        for value in ('no','uncertain'):
            f=ready(i);written(f);r=dictation_report(f);r['duties'][duty]=value;refuse(f,lambda:f.report_dictation(f.token(),r));r['diagnosis']='Required hearing duty unresolved';f.report_dictation(f.token(),r);check(f.state=='dictation_retry')
    for duty in TARGET_DUTIES:
        for value in ('no','uncertain'):
            f=targets_ready(i);perform_target(f);r=target_report(f);r['duties'][duty]=value;refuse(f,lambda:f.report_target(f.token(),r));r['diagnosis']='Same-note retry required';f.report_target(f.token(),r)
            check(f.state=='target_retry');refuse(f,lambda:f.next_target(f.token()));f.repeat_target(f.token(),'Release then repeat current target');check(f.target==0 and f.state=='target_ready')
    for count in (0,2,8):
        f=targets_ready(i);perform_target(f);r=target_report(f);r['attack_count']=count;refuse(f,lambda:f.report_target(f.token(),r));r['diagnosis']='Actual attack count failed';f.report_target(f.token(),r);check(f.state=='target_retry')

# Causal ordering, token/custody and cancellation tests from real valid states.
f=ready(0);snapshots=[deepcopy(f)]
for layer in range(3):
    f.begin_listening(f.token(),{'key':f.key,'ready':True,'same_chosen_phrase':True});snapshots.append(deepcopy(f))
    f.end_listening(f.token(),True);snapshots.append(deepcopy(f));f.release(f.token(),{'learner_released':True,'source_stopped':True});snapshots.append(deepcopy(f))
    response=[list(CONTOURS[0]),DEGREES[0].split(),NOTES[0].split()][layer];f.commit(f.token(),LAYERS[layer],response,'low');snapshots.append(deepcopy(f))
f.reveal(f.token());snapshots.append(deepcopy(f));f.report_dictation(f.token(),dictation_report(f));snapshots.append(deepcopy(f))
f.set_guitar_plan(f.token(),guitar_plan(0));snapshots.append(deepcopy(f));f.begin_target(f.token(),True);snapshots.append(deepcopy(f));f.sung(f.token(),True);snapshots.append(deepcopy(f))
f.setup_target(f.token(),True);snapshots.append(deepcopy(f));f.attack(f.token(),True);snapshots.append(deepcopy(f));f.release(f.token(),{'learner_released':True,'source_stopped':None});snapshots.append(deepcopy(f))
f.report_target(f.token(),target_report(f));snapshots.append(deepcopy(f))
for sample in snapshots:
    f=deepcopy(sample);t=f.token();foreign=MelodyFlow(f.key).token();refuse(f,lambda:f.cancel(foreign));refuse(f,lambda:f.cancel(list(t)))
    f.cancel(t);refuse(f,lambda:f.cancel(t));check(f.state=='cancelled');answers=deepcopy(f.answers);history=deepcopy(f.answer_history);revealed=f.ever_revealed
    pending=f.source_release_required;check(not pending or f.source_stop_requested);f.reopen(f.token());refuse(f,lambda:f.release(f.token(),{'learner_released':False,'source_stopped':True if pending else None}))
    refuse(f,lambda:f.release(f.token(),{'learner_released':True,'source_stopped':None if pending else True}))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None});check(f.answers==answers and f.answer_history==history and f.ever_revealed==revealed)
    if sample.state in ('listening','listening_release'):check(f.state=='ready_listen' and f.layer==sample.layer)
    if sample.state in ('sing_target','silent_setup','attack','attack_release','target_report'):check(f.state=='target_ready' and f.target==sample.target)
    # All action methods must reject a stale token even when given otherwise suitable values.
    stale=t
    calls=[lambda:f.set_source_plan(stale,source_plan(0)),lambda:f.begin_listening(stale,{'key':f.key,'ready':True,'same_chosen_phrase':True}),lambda:f.end_listening(stale,True),
      lambda:f.release(stale,{'learner_released':True,'source_stopped':None}),lambda:f.commit(stale,LAYERS[f.layer],['?']*7,'uncertain'),lambda:f.reveal(stale),
      lambda:f.report_dictation(stale,dictation_report(f)),lambda:f.repeat_dictation(stale,'diagnosis'),lambda:f.set_guitar_plan(stale,guitar_plan(0)),lambda:f.begin_target(stale,True),
      lambda:f.sung(stale,True),lambda:f.setup_target(stale,True),lambda:f.attack(stale,True),lambda:f.report_target(stale,{'wrong':True}),lambda:f.repeat_target(stale,'diagnosis'),lambda:f.next_target(stale),lambda:f.finish(stale),lambda:f.reopen(stale)]
    for call in calls:refuse(f,call)
    v=f.learner_view();v['answers']['forged']={};sv=f.source_player_view();sv['printed_notes'].clear();check('forged' not in f.answers and f.source_player_view()['printed_notes']==NOTES[0].split())

for layer in range(3):
    f=ready(0)
    for earlier in range(layer):perform_listening(f);f.commit(f.token(),LAYERS[earlier],[list(CONTOURS[0]),DEGREES[0].split(),NOTES[0].split()][earlier],'high')
    for call in (lambda:f.reveal(f.token()),lambda:f.set_guitar_plan(f.token(),guitar_plan(0)),lambda:f.begin_target(f.token(),True),lambda:f.finish(f.token())):refuse(f,call)
    for conf in ({'key':KEYS[1],'ready':True,'same_chosen_phrase':True},{'key':f.key,'ready':1,'same_chosen_phrase':True},{'key':f.key,'ready':True,'same_chosen_phrase':False}):refuse(f,lambda c=conf:f.begin_listening(f.token(),c))
    perform_listening(f)
    valid=[list(CONTOURS[0]),DEGREES[0].split(),NOTES[0].split()][layer]
    for bad in ([],valid[:-1],valid+[valid[0]],[True]*len(valid),['invalid']*len(valid)):refuse(f,lambda x=bad:f.commit(f.token(),LAYERS[layer],x,'high'))
    for kind in (LAYERS[(layer+1)%3],None):refuse(f,lambda x=kind:f.commit(f.token(),x,valid,'high'))
    for confidence in (None,1,'',True):refuse(f,lambda x=confidence:f.commit(f.token(),LAYERS[layer],valid,x))
    t=f.token();f.commit(t,LAYERS[layer],valid,'high');refuse(f,lambda:f.commit(t,LAYERS[layer],valid,'high'))

# Wrong reference response cannot be promoted by a positive manual hearing report.
for layer,bad in ((0,'S'),(1,'7'),(2,'B')):
    f=ready(0)
    for j in range(3):
        perform_listening(f);v=[list(CONTOURS[0]),DEGREES[0].split(),NOTES[0].split()][j]
        if j==layer:v[0]=bad
        f.commit(f.token(),LAYERS[j],v,'high')
    f.reveal(f.token());r=dictation_report(f);refuse(f,lambda:f.report_dictation(f.token(),r));r['diagnosis']='Wrong committed symbol retained';f.report_dictation(f.token(),r);check(f.state=='dictation_retry')

f=targets_ready(0);perform_target(f)
for field,value in (('source_order',True),('source_order',2),('key',KEYS[1]),('attack_count',True),('attack_count',-1),('attack_count',1.0),('chosen_contact',{'string':'E','fret':0})):
    r=target_report(f);r[field]=value;refuse(f,lambda:f.report_target(f.token(),r))
p=source_plan(0);f=MelodyFlow(KEYS[0]);f.set_source_plan(f.token(),p);p['provider']['chosen_midi'][0]=1;check(f.plan['provider']['chosen_midi'][0]==60)
for sample in snapshots:
    if sample.state not in ('setup','dictation_retry','completed'):refuse(sample,lambda s=sample:s.set_source_plan(s.token(),source_plan(0)))

out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),
 'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'melody_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
