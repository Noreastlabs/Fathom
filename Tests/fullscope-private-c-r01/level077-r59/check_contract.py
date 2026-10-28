from pathlib import Path
from copy import deepcopy
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r59');sys.path.insert(0,str(R/'Tools'/L))
from delay_contract import DelayFlow,Refusal,KEYS,BEAT_DUTIES,DELAY_DUTIES,PLAY_DUTIES,contract
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
MIDI=([60,64,67,64],[62,65,69,65],[55,59,62,65],[57,60,64,67],[53,57,60,64]);NOTES=('C E G E','D F A F','G B D F','A C E G','F A C E')
DELAYS=('1 beat','2 beats','1 bar','2 bars','4 beats + count');TUNE=(('E',40),('A',45),('D',50),('G',55),('B',59),('e',64))
def rhythm(alt=False):return {'onsets_q':[[0,1],[1,2],[2,1],[3,1]] if alt else [[0,1],[1,1],[2,1],[3,1]],'durations_q':[[1,2],[1,1],[1,2],[1,2]] if alt else [[1,1]]*4,'length_q':[4,1]}
def plan(i,alt=False):return {'prerequisites':{'original_workbook':True,'own_instrument':True},'provider':{'kind':'external_human','reference':'local source partner','ready':True,'question_midi':[x+12 if alt else x for x in MIDI[i]],'question_rhythm':rhythm(alt)},
 'external_pulse':{'reference':'external human beat keeper','beats_per_bar':6 if alt else 3,'beat_unit_q':[3,2] if alt else [1,1]}}
def contacts(m):return [{'string':s,'fret':n-v} for n in m for s,v in [next((s,v) for s,v in TUNE if 0<=n-v<=24)]]
def recalled(f):
    m=deepcopy(f.plan['provider']['question_midi']);return {'midi':m,'rhythm':deepcopy(f.plan['provider']['question_rhythm']),'contacts':contacts(m)}
def ready(i=0,alt=False):
    f=DelayFlow(KEYS[i]);f.set_plan(f.token(),plan(i,alt));return f
def begin_delay(f,hands='yes'):
    f.begin_question(f.token(),{'key':f.key,'ready':True,'same_chosen_question':True});check(f.source_release_required)
    f.source_ended_start_delay(f.token(),{'source_stopped':True,'hands_unformed':hands});check(not f.source_release_required and f.state=='delay')
def beat(f):return {'ordinal':f.beat_count+1,'duties':{k:'yes' for k in BEAT_DUTIES}}
def fill_beats(f):
    for _ in range(f.required_beats()):f.beat(f.token(),beat(f))
    check(f.state=='delay_review')
def d_report(f):return {'key':f.key,'beats':f.required_beats(),'duties':{k:'yes' for k in DELAY_DUTIES},'diagnosis':'','notes':'External elapsed delay manually confirmed; no app clock.'}
def to_recall(i=0,alt=False):
    f=ready(i,alt);begin_delay(f);fill_beats(f);f.review_delay(f.token(),d_report(f));f.begin_response(f.token(),True);return f
def perform(f,p=None):
    f.set_recalled_plan(f.token(),recalled(f) if p is None else p);check('reference_question' not in f.learner_view())
    f.sung(f.token(),True);f.setup_targets(f.token(),True);f.play(f.token(),True);f.release(f.token(),{'learner_released':True,'source_stopped':None})
    check('reference_question' not in f.learner_view());f.reveal_reference(f.token());check('reference_question' in f.learner_view())
def p_report(f):return {'key':f.key,'recalled_midi':deepcopy(f.recalled['midi']),'attack_counts':[1,1,1,1],'duties':{k:'yes' for k in PLAY_DUTIES},'diagnosis':'','notes':'Manual memory/performance report, not acoustically verified.'}

packet=Path('Build')/L/'delayed-memory-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()];base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()];old=base[102:107]
check(len(rows)==5 and [r['package_key'] for r in rows]==list(KEYS));check(sum(len(r['implementation']['task']['printed_components'][1].split('-')) for r in base[102:110])==32)
for i,(r,o) in enumerate(zip(rows,old)):
    c=contract(i);check(c==r['implementation']['task']['contract'] and c['printed_question']==NOTES[i].split() and c['printed_required_delay']==DELAYS[i])
    for field in ('source_refs','source_payload','timing_authority','source_identity','package_key'):check(r[field]==o[field])
    for field in ('events','tab_blocks','source_field_occurrences'):check(r['implementation'][field]==o['implementation'][field])
    check(c['source_note_events']==[] and c['actual_page_question_tokens']==32)
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','elapsed_delay_measured','credit_awarded','mastery_awarded','persistence'):check(c[flag] is False)
    for alt,expected in ((False,[1,2,3,6,4]),(True,[1,2,6,12,4])):
        f=ready(i,alt);check(f.required_beats()==expected[i]);check(not f.learner_view()['hand_formation_allowed']);begin_delay(f)
        for ordinal in range(1,expected[i]+1):
            for call in (lambda:f.begin_response(f.token(),True),lambda:f.set_recalled_plan(f.token(),recalled(f)),lambda:f.setup_targets(f.token(),True),lambda:f.reveal_reference(f.token()),lambda:f.finish(f.token())):refuse(f,call)
            check('reference_question' not in f.learner_view() and not f.learner_view()['hand_formation_allowed']);t=f.token();f.beat(t,beat(f));refuse(f,lambda:f.beat(t,beat(f)))
        refuse(f,lambda:f.beat(f.token(),beat(f)));refuse(f,lambda:f.begin_response(f.token(),True));f.review_delay(f.token(),d_report(f));check(not f.learner_view()['hand_formation_allowed'])
        refuse(f,lambda:f.set_recalled_plan(f.token(),recalled(f)));f.begin_response(f.token(),True);check(f.learner_view()['hand_formation_allowed']);perform(f)
        f.report(f.token(),p_report(f));f.finish(f.token());check(f.state=='completed')
        history=deepcopy(f.recall_history);f.set_plan(f.token(),plan(i));check(f.ever_revealed and f.recall_history==history and f.recalled is None and f.beat_count==0)
    # Mistaken recall is accepted structurally without answer feedback until after actual attempt.
    for error in ('pitch','rhythm'):
        f=to_recall(i);p=recalled(f)
        if error=='pitch':p['midi'][0]+=1;p['contacts']=contacts(p['midi'])
        else:p['rhythm']=rhythm(True)
        f.set_recalled_plan(f.token(),p);check(f.recalled==p and 'reference_question' not in f.learner_view());f.sung(f.token(),True);f.setup_targets(f.token(),True);f.play(f.token(),True)
        f.release(f.token(),{'learner_released':True,'source_stopped':None});f.reveal_reference(f.token());v=p_report(f);refuse(f,lambda:f.report(f.token(),v));v['diagnosis']='Retained wrong memory, now compare after playing';f.report(f.token(),v)
        check(f.state=='needs_retry');history=deepcopy(f.recall_history);f.retry(f.token(),'Repeat entire question/delay');check(f.state=='ready' and f.beat_count==0 and f.recall_history==history and f.ever_revealed)
    f=to_recall(i);refuse(f,lambda:f.cannot_recall(f.token(),'',True));refuse(f,lambda:f.cannot_recall(f.token(),'Memory unavailable',False));f.cannot_recall(f.token(),'Unable to recall without guessing',True)
    check(f.recalled is None and f.recall_history==[] and f.state=='needs_retry');f.retry(f.token(),'Replay the complete task');check(f.state=='ready')
    for start in ('no','uncertain'):
        f=ready(i);begin_delay(f,start);fill_beats(f);v=d_report(f);refuse(f,lambda:f.review_delay(f.token(),v));v['diagnosis']='Hand formed before delay';f.review_delay(f.token(),v);check(f.state=='needs_retry')
    for duty in BEAT_DUTIES:
        for val in ('no','uncertain'):
            f=ready(i);begin_delay(f);b=beat(f);b['duties'][duty]=val;f.beat(f.token(),b)
            while f.state=='delay':f.beat(f.token(),beat(f))
            v=d_report(f);refuse(f,lambda:f.review_delay(f.token(),v));v['diagnosis']='Auditory/count/hand report unresolved';f.review_delay(f.token(),v);check(f.state=='needs_retry');refuse(f,lambda:f.begin_response(f.token(),True))
    for duty in DELAY_DUTIES:
        for val in ('no','uncertain'):
            f=ready(i);begin_delay(f);fill_beats(f);v=d_report(f);v['duties'][duty]=val;refuse(f,lambda:f.review_delay(f.token(),v));v['diagnosis']='Elapsed delay manually unconfirmed';f.review_delay(f.token(),v);check(f.state=='needs_retry')
    for duty in PLAY_DUTIES:
        for val in ('no','uncertain'):
            f=to_recall(i);perform(f);v=p_report(f);v['duties'][duty]=val;refuse(f,lambda:f.report(f.token(),v));v['diagnosis']='Current recall performance failed';f.report(f.token(),v);check(f.state=='needs_retry');refuse(f,lambda:f.finish(f.token()))
    for count in (0,2,8):
        f=to_recall(i);perform(f);v=p_report(f);v['attack_counts'][1]=count;refuse(f,lambda:f.report(f.token(),v));v['diagnosis']='Actual target count failed';f.report(f.token(),v);check(f.state=='needs_retry')

mutations=[lambda p:p.update(extra=True),lambda p:p['prerequisites'].update(own_instrument=1),lambda p:p['provider'].update(kind='app_audio'),lambda p:p['provider'].update(reference=''),lambda p:p['provider'].update(ready=1),
 lambda p:p['provider']['question_midi'].__setitem__(0,True),lambda p:p['provider']['question_midi'].__setitem__(0,61),lambda p:p['provider']['question_midi'].__setitem__(0,36),
 lambda p:p['external_pulse'].update(reference=''),lambda p:p['external_pulse'].update(beats_per_bar=0),lambda p:p['external_pulse'].update(beats_per_bar=17),lambda p:p['external_pulse'].update(beats_per_bar=True),
 lambda p:p['external_pulse'].update(beat_unit_q=[0,1]),lambda p:p['external_pulse'].update(beat_unit_q=[2,2]),lambda p:p['provider']['question_rhythm'].update(length_q=[3,1]),
 lambda p:p['provider']['question_rhythm']['onsets_q'].__setitem__(1,[1,2]),lambda p:p['provider']['question_rhythm']['durations_q'].__setitem__(0,[0,1])]
for mutate in mutations:
    p=plan(0);mutate(p);f=DelayFlow(KEYS[0]);refuse(f,lambda:f.set_plan(f.token(),p))
f=ready(3);begin_delay(f)
for ordinal in (0,2,-1,True,1.0,99):
    b=beat(f);b['ordinal']=ordinal;refuse(f,lambda:f.beat(f.token(),b))
b=beat(f);b['duties']['hands_unformed']=True;refuse(f,lambda:f.beat(f.token(),b))
for key in [r['package_key'] for r in base[107:110]]+['exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7',None,True]:refuse(None,lambda k=key:DelayFlow(k))

f=ready(3);samples=[deepcopy(f)];f.begin_question(f.token(),{'key':f.key,'ready':True,'same_chosen_question':True});samples.append(deepcopy(f))
f.source_ended_start_delay(f.token(),{'source_stopped':True,'hands_unformed':'yes'});samples.append(deepcopy(f))
for _ in range(f.required_beats()):f.beat(f.token(),beat(f));samples.append(deepcopy(f))
f.review_delay(f.token(),d_report(f));samples.append(deepcopy(f));f.begin_response(f.token(),True);samples.append(deepcopy(f));f.set_recalled_plan(f.token(),recalled(f));samples.append(deepcopy(f))
f.sung(f.token(),True);samples.append(deepcopy(f));f.setup_targets(f.token(),True);samples.append(deepcopy(f));f.play(f.token(),True);samples.append(deepcopy(f));f.release(f.token(),{'learner_released':True,'source_stopped':None});samples.append(deepcopy(f))
f.reveal_reference(f.token());samples.append(deepcopy(f));f.report(f.token(),p_report(f));samples.append(deepcopy(f));f.finish(f.token());samples.append(deepcopy(f))
for sample in samples:
    f=deepcopy(sample);t=f.token();refuse(f,lambda:f.cancel(DelayFlow(f.key).token()));refuse(f,lambda:f.cancel(list(t)));history=deepcopy(f.recall_history);ever=f.ever_revealed;pending=f.source_release_required
    f.cancel(t);refuse(f,lambda:f.cancel(t));check(not pending or f.source_stop_requested);f.reopen(f.token())
    refuse(f,lambda:f.release(f.token(),{'learner_released':False,'source_stopped':True if pending else None}));refuse(f,lambda:f.release(f.token(),{'learner_released':True,'source_stopped':None if pending else True}))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None});check(f.recall_history==history and f.ever_revealed==ever)
    if sample.state not in ('setup','ready','reporting','reported','needs_retry','completed'):check(f.state=='ready' and f.beat_count==0 and f.recalled is None)
    for call in (lambda:f.set_plan(t,plan(3)),lambda:f.begin_question(t,{}),lambda:f.source_ended_start_delay(t,{}),lambda:f.beat(t,{}),lambda:f.review_delay(t,{}),lambda:f.begin_response(t,True),
      lambda:f.cannot_recall(t,'unknown',True),lambda:f.set_recalled_plan(t,{}),lambda:f.sung(t,True),lambda:f.setup_targets(t,True),lambda:f.play(t,True),lambda:f.release(t,{}),lambda:f.reveal_reference(t),lambda:f.report(t,{}),lambda:f.retry(t,'diagnosis'),lambda:f.finish(t),lambda:f.reopen(t)):refuse(f,call)
    if sample.state not in ('setup','completed'):refuse(sample,lambda s=sample:s.set_plan(s.token(),plan(3)))
    view=f.source_player_view();view['printed_question'].clear();check(f.source_player_view()['printed_question']==NOTES[3].split())

f=to_recall();p=recalled(f)
for mutate in (lambda q:q['midi'].__setitem__(0,True),lambda q:q['contacts'][0].update(fret=True),lambda q:q['contacts'][0].update(fret=-1),lambda q:q['contacts'][0].update(fret=25),
 lambda q:q['contacts'][0].update(string='X'),lambda q:q['contacts'][0].update(fret=q['contacts'][0]['fret']+1),lambda q:q.update(contacts=[])):
    v=deepcopy(p);mutate(v);refuse(f,lambda:f.set_recalled_plan(f.token(),v))
f.set_recalled_plan(f.token(),p);p['midi'][0]=1;check(f.recalled['midi'][0]==60);view=f.learner_view();view['learner_entered_recall']['midi'][0]=1;check(f.recalled['midi'][0]==60)
f=to_recall();perform(f)
for field,val in (('key',KEYS[1]),('attack_counts',[True,1,1,1]),('attack_counts',[1,-1,1,1]),('recalled_midi',[61,64,67,64]),('notes','')):
    v=p_report(f);v[field]=val;refuse(f,lambda:f.report(f.token(),v))
v=p_report(f);t=f.token();f.report(t,v);v['duties'].clear();refuse(f,lambda:f.report(t,p_report(f)));check(bool(f.history[-1]['data']['response']['duties']))

out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),
 'model':pin(Path('Tools')/L/'delay_contract.py'),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'elapsed_delay_measured':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
