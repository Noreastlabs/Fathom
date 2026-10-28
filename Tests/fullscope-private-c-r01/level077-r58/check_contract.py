from pathlib import Path
from copy import deepcopy
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r58');sys.path.insert(0,str(R/'Tools'/L))
from call_response_contract import CallResponseFlow,Refusal,KEYS,RAW,ECHO_DUTIES,PLAY_DUTIES,validate_source_plan,validate_response,contract
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
MIDI=([60,64,67,64],[62,65,69,65],[55,59,62,65],[57,60,64,67],[53,57,60,64],[59,62,65,69],[52,56,59,62],[57,60,64,68])
QUESTIONS=('C E G E','D F A F','G B D F','A C E G','F A C E','B D F A','E G# B D','A C E G#')
MODELS=('G B E C','A C F D','F D B G','G E C A','E C A F','A F D B','D B G# E','G# E C A')
PCS={'C':0,'D':2,'E':4,'F':5,'G':7,'G#':8,'A':9,'B':11};TUNE=(('E',40),('A',45),('D',50),('G',55),('B',59),('e',64))
def rhythm(alt=False):return {'onsets_q':[[0,1],[1,2],[2,1],[3,1]] if alt else [[0,1],[1,1],[2,1],[3,1]],'durations_q':[[1,2],[1,1],[1,2],[1,2]] if alt else [[1,1]]*4,'length_q':[4,1]}
def source_plan(i,alt=False):return {'prerequisites':{'original_workbook':True,'own_instrument':True},'provider':{'kind':'external_human','reference':'chosen external source player','ready':True,'can_hold_next_chord':True,'question_midi':[x+12 if alt else x for x in MIDI[i]],'question_rhythm':rhythm(alt)}}
def contacts(m):return [{'string':s,'fret':n-v} for n in m for s,v in [next((s,v) for s,v in TUNE if 0<=n-v<=24)]]
def response(f,own=False):
    question=f.plan['provider']['question_midi'];p=f.phase;chord=None;r=deepcopy(f.plan['provider']['question_rhythm'])
    if p==0:basis='exact_echo';m=deepcopy(question)
    elif p==1:
        basis='own_new_pitch_order' if own else 'answer_model';m=list(reversed(question)) if own else [60+PCS[x] for x in MODELS[f.index].split()]
    elif p==2:basis='original_question_octave';shift=12 if max(question)<=76 else -12;m=[x+shift for x in question]
    else:basis='chosen_next_chord';chord='Dm7';m=[62,65,69,72];r=rhythm(False)
    return {'basis':basis,'midi':m,'rhythm':r,'contacts':contacts(m),'next_chord':chord}
def ready(i=0,alt=False):
    f=CallResponseFlow(KEYS[i]);f.set_source_plan(f.token(),source_plan(i,alt));return f
def hear(f):
    f.begin_question(f.token(),{'key':f.key,'ready':True,'same_chosen_question':True});check(f.source_role=='question' and f.source_release_required)
    f.end_question(f.token(),True);check(f.source_stop_requested);f.release(f.token(),{'learner_released':True,'source_stopped':True})
def echo_report(f):return {'key':f.key,'duties':{k:'yes' for k in ECHO_DUTIES},'diagnosis':'','notes':'Manual written echo review.'}
def write_echo(f,notes=None):
    f.commit_echo(f.token(),QUESTIONS[f.index].split() if notes is None else notes);check('question_reference' not in f.learner_view())
    f.reveal_question(f.token());check('question_reference' in f.learner_view() and 'answer_model' not in f.learner_view())
def prepare(f,own=False):
    if f.phase==0:
        hear(f);write_echo(f);f.review_echo(f.token(),echo_report(f));f.choose_response(f.token(),response(f))
    else:
        f.choose_response(f.token(),response(f,own));hear(f)
        if f.phase==3:f.begin_next_chord(f.token(),{'chord':'Dm7','ready':True,'held':True});check(f.source_role=='held_next_chord')
def play(f):
    f.sung(f.token(),True);f.setup_targets(f.token(),True);f.play_response(f.token(),True);f.end_response(f.token(),True)
    pending=f.source_release_required;check(pending==(f.phase==3));f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None})
def report(f):return {'key':f.key,'pass':f.phase+1,'midi':deepcopy(f.responses[f.phase]['midi']),'next_chord':f.responses[f.phase]['next_chord'],'attack_counts':[1,1,1,1],
 'duties':{k:'yes' for k in PLAY_DUTIES+(('next_chord_present_during_response',) if f.phase==3 else ())},'diagnosis':'','notes':'Manual performance report, not acoustic proof.'}
def phase_start(i,phase):
    f=ready(i)
    for _ in range(phase):prepare(f);play(f);f.report(f.token(),report(f));f.next_pass(f.token())
    return f
def at_report(i,phase):
    f=phase_start(i,phase);prepare(f);play(f);return f
def at_choice(i,phase):
    f=phase_start(i,phase)
    if phase==0:hear(f);write_echo(f);f.review_echo(f.token(),echo_report(f))
    return f

packet=Path('Build')/L/'call-response-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()];old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][94:102]
check(len(rows)==8 and [r['package_key'] for r in rows]==list(KEYS));check(sum(len(x.split()) for x in QUESTIONS)==32 and sum(len(x.split()) for x in MODELS)==32)
for i,(r,o) in enumerate(zip(rows,old)):
    c=contract(i);check(c==r['implementation']['task']['contract']);check(c['printed_question']==QUESTIONS[i].split() and c['printed_answer_model']==MODELS[i].split())
    for field in ('source_refs','source_payload','timing_authority','source_identity','package_key'):check(r[field]==o[field])
    for field in ('events','tab_blocks','source_field_occurrences'):check(r['implementation'][field]==o['implementation'][field])
    check(c['source_note_events']==[] and c['source_fixed_octave_rhythm_meter_fret_next_chord'] is None)
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[flag] is False)
    for alt in (False,True):
        f=ready(i,alt)
        for phase in range(4):
            check(f.phase==phase);prepare(f,own=alt);play(f);f.report(f.token(),report(f));check(f.state=='reported')
            if phase==0:check(f.echo_passed and f.learner_view()['answer_model']==MODELS[i].split())
            if phase<3:refuse(f,lambda:f.finish(f.token()));f.next_pass(f.token())
        refuse(f,lambda:f.next_pass(f.token()));f.finish(f.token());check(f.state=='completed')
        history=deepcopy(f.written_history);f.set_source_plan(f.token(),source_plan(i));check(f.phase==0 and not f.echo_passed and f.ever_revealed and f.written_history==history and f.responses=={})
    for phase in range(4):
        # Every manually reported duty has a causal no/uncertain path and no premature advancement.
        for duty in PLAY_DUTIES+(('next_chord_present_during_response',) if phase==3 else ()):
            for value in ('no','uncertain'):
                f=at_report(i,phase);v=report(f);v['duties'][duty]=value;refuse(f,lambda:f.report(f.token(),v));v['diagnosis']='Unresolved current-pass duty';f.report(f.token(),v)
                check(f.state=='needs_retry');refuse(f,lambda:f.next_pass(f.token()));refuse(f,lambda:f.finish(f.token()));f.retry(f.token(),'Retry released current pass');check(f.phase==phase and f.state=='ready_listen')
        for count in (0,2,7):
            f=at_report(i,phase);v=report(f);v['attack_counts'][2]=count;refuse(f,lambda:f.report(f.token(),v));v['diagnosis']='One-attack-per-target requirement failed';f.report(f.token(),v);check(f.state=='needs_retry')
    for bad in ('?', 'B' if i!=5 else 'C'):
        f=ready(i);hear(f);notes=QUESTIONS[i].split();notes[0]=bad;write_echo(f,notes);v=echo_report(f);refuse(f,lambda:f.review_echo(f.token(),v));v['diagnosis']='Wrong/unknown written echo';f.review_echo(f.token(),v);check(f.state=='needs_retry');f.retry(f.token(),'Rehear exact question')
    for duty in ECHO_DUTIES:
        for val in ('no','uncertain'):
            f=ready(i);hear(f);write_echo(f);v=echo_report(f);v['duties'][duty]=val;refuse(f,lambda:f.review_echo(f.token(),v));v['diagnosis']='Manual echo hearing unresolved';f.review_echo(f.token(),v);check(f.state=='needs_retry')

# Source viability and exact symbolic/temporal plan constraints.
mutations=[lambda p:p['prerequisites'].update(own_instrument=1),lambda p:p['provider'].update(kind='app_audio'),lambda p:p['provider'].update(reference=''),lambda p:p['provider'].update(ready=1),
 lambda p:p['provider'].update(can_hold_next_chord=False),lambda p:p['provider']['question_midi'].__setitem__(0,True),lambda p:p['provider']['question_midi'].__setitem__(0,61),
 lambda p:p['provider'].update(question_midi=[36,40,43,40]),lambda p:p['provider'].update(question_midi=[48,88,79,88]),
 lambda p:p['provider']['question_rhythm'].update(length_q=[3,1]),lambda p:p['provider']['question_rhythm']['onsets_q'].__setitem__(1,[1,2]),
 lambda p:p['provider']['question_rhythm']['durations_q'].__setitem__(0,[0,1]),lambda p:p['provider']['question_rhythm']['onsets_q'].__setitem__(0,[-1,1]),
 lambda p:p['provider']['question_rhythm']['onsets_q'].__setitem__(0,[0,2]),lambda p:p['provider']['question_rhythm'].update(length_q=[True,1])]
for mutation in mutations:
    p=source_plan(0);mutation(p);f=CallResponseFlow(KEYS[0]);refuse(f,lambda:f.set_source_plan(f.token(),p))
for phase in range(4):
    f=at_choice(0,phase);p=response(f)
    mutations=[lambda q:q.update(extra=True),lambda q:q.update(basis='wrong'),lambda q:q['midi'].__setitem__(0,True),lambda q:q['contacts'][0].update(fret=True),
      lambda q:q['contacts'][0].update(fret=-1),lambda q:q['contacts'][0].update(fret=25),lambda q:q['contacts'][0].update(string='X'),lambda q:q['contacts'][0].update(fret=q['contacts'][0]['fret']+1)]
    for mutate in mutations:
        q=deepcopy(p);mutate(q);refuse(f,lambda:f.choose_response(f.token(),q))
    if phase in (0,1,2):
        q=deepcopy(p);q['rhythm']=rhythm(True);refuse(f,lambda:f.choose_response(f.token(),q))
    if phase==0:
        q=deepcopy(p);q['midi']=[x+12 for x in q['midi']];q['contacts']=contacts(q['midi']);refuse(f,lambda:f.choose_response(f.token(),q))
    elif phase==1:
        q=deepcopy(p);q.update(basis='own_new_pitch_order',midi=deepcopy(MIDI[0]),contacts=contacts(MIDI[0]));refuse(f,lambda:f.choose_response(f.token(),q))
        q=deepcopy(p);q['midi'][0]+=1;q['contacts']=contacts(q['midi']);refuse(f,lambda:f.choose_response(f.token(),q))
    elif phase==2:
        q=deepcopy(p);q['midi']=deepcopy(MIDI[0]);q['contacts']=contacts(q['midi']);refuse(f,lambda:f.choose_response(f.token(),q))
        q=deepcopy(p);q['midi'][0]-=12;q['contacts']=contacts(q['midi']);refuse(f,lambda:f.choose_response(f.token(),q))
    else:
        q=deepcopy(p);q['next_chord']='not_a_chord';refuse(f,lambda:f.choose_response(f.token(),q))
        q=deepcopy(p);q['midi'][0]=61;q['contacts']=contacts(q['midi']);refuse(f,lambda:f.choose_response(f.token(),q))
        q=deepcopy(p);q['rhythm']['length_q']=[5,1];refuse(f,lambda:f.choose_response(f.token(),q))

for key in ('exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7',KEYS[0]+'x',None,True):refuse(None,lambda k=key:CallResponseFlow(k))
# State snapshots from exact echo and held-next-chord pass retain the actual source-role lifecycle.
f=ready();samples=[deepcopy(f)]
f.begin_question(f.token(),{'key':f.key,'ready':True,'same_chosen_question':True});samples.append(deepcopy(f));f.end_question(f.token(),True);samples.append(deepcopy(f));f.release(f.token(),{'learner_released':True,'source_stopped':True});samples.append(deepcopy(f))
f.commit_echo(f.token(),QUESTIONS[0].split());samples.append(deepcopy(f));f.reveal_question(f.token());samples.append(deepcopy(f));f.review_echo(f.token(),echo_report(f));samples.append(deepcopy(f));f.choose_response(f.token(),response(f));samples.append(deepcopy(f))
for phase in (0,3):
    if phase==3:
        f=phase_start(0,3);samples.append(deepcopy(f));f.choose_response(f.token(),response(f));hear(f);samples.append(deepcopy(f))
        for c in ({'chord':'G7','ready':True,'held':True},{'chord':'Dm7','ready':True,'held':False},{'chord':'Dm7','ready':1,'held':True}):refuse(f,lambda x=c:f.begin_next_chord(f.token(),x))
        f.begin_next_chord(f.token(),{'chord':'Dm7','ready':True,'held':True});samples.append(deepcopy(f))
    f.sung(f.token(),True);samples.append(deepcopy(f));f.setup_targets(f.token(),True);samples.append(deepcopy(f));f.play_response(f.token(),True);samples.append(deepcopy(f));f.end_response(f.token(),True);samples.append(deepcopy(f))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if phase==3 else None});samples.append(deepcopy(f));f.report(f.token(),report(f));samples.append(deepcopy(f))
f.finish(f.token());samples.append(deepcopy(f))
for sample in samples:
    f=deepcopy(sample);t=f.token();refuse(f,lambda:f.cancel(CallResponseFlow(f.key).token()));refuse(f,lambda:f.cancel(list(t)))
    written=deepcopy(f.written);history=deepcopy(f.written_history);responses=deepcopy(f.responses);revealed=f.ever_revealed;pending=f.source_release_required
    f.cancel(t);refuse(f,lambda:f.cancel(t));check(not pending or f.source_stop_requested);f.reopen(f.token())
    refuse(f,lambda:f.release(f.token(),{'learner_released':False,'source_stopped':True if pending else None}));refuse(f,lambda:f.release(f.token(),{'learner_released':True,'source_stopped':None if pending else True}))
    f.release(f.token(),{'learner_released':True,'source_stopped':True if pending else None});check(f.written==written and f.written_history==history and f.responses==responses and f.ever_revealed==revealed and f.phase==sample.phase)
    for call in (lambda:f.set_source_plan(t,source_plan(0)),lambda:f.begin_question(t,{}),lambda:f.end_question(t,True),lambda:f.release(t,{}),lambda:f.commit_echo(t,[]),lambda:f.reveal_question(t),lambda:f.review_echo(t,{}),
      lambda:f.choose_response(t,{}),lambda:f.begin_next_chord(t,{}),lambda:f.sung(t,True),lambda:f.setup_targets(t,True),lambda:f.play_response(t,True),lambda:f.end_response(t,True),lambda:f.report(t,{}),lambda:f.next_pass(t),lambda:f.retry(t,'diagnosis'),lambda:f.finish(t),lambda:f.reopen(t)):refuse(f,call)
    if sample.state not in ('setup','completed'):refuse(sample,lambda s=sample:s.set_source_plan(s.token(),source_plan(0)))
    view=f.source_player_view();view['printed_question'].clear();check(f.source_player_view()['printed_question']==QUESTIONS[0].split())

f=ready();future={'basis':'own_new_pitch_order','midi':[64,67,64,60],'rhythm':rhythm(),'contacts':contacts([64,67,64,60]),'next_chord':None}
for s in ('ready','heard','written','revealed','reviewed','prepared','played'):
    if s=='heard':hear(f)
    elif s=='written':f.commit_echo(f.token(),QUESTIONS[0].split())
    elif s=='revealed':f.reveal_question(f.token())
    elif s=='reviewed':f.review_echo(f.token(),echo_report(f))
    elif s=='prepared':f.choose_response(f.token(),response(f))
    elif s=='played':play(f)
    refuse(f,lambda:f.choose_response(f.token(),future));refuse(f,lambda:f.next_pass(f.token()));refuse(f,lambda:f.finish(f.token()));check('answer_model' not in f.learner_view())
for field,value in (('pass',True),('pass',2),('key',KEYS[1]),('attack_counts',[True,1,1,1]),('attack_counts',[1,-1,1,1]),('next_chord','Dm7')):
    v=report(f);v[field]=value;refuse(f,lambda:f.report(f.token(),v))
v=report(f);t=f.token();f.report(t,v);v['duties'].clear();refuse(f,lambda:f.report(t,report(f)));check(bool(f.history[-1]['data']['response']['duties']))
f=ready(6);hear(f);notes=['E','Ab','B','D'];write_echo(f,notes);f.review_echo(f.token(),echo_report(f));check(f.state=='echo_plan')

out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),
 'model':pin(Path('Tools')/L/'call_response_contract.py'),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
