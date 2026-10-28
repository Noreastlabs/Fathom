from pathlib import Path
from copy import deepcopy
import sys,json,hashlib,datetime,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r61');sys.path.insert(0,str(R/'Tools'/L))
from degree_contract import DegreeFlow,Refusal,KEYS,RAW,PC,REGISTERS,CUE_DUTIES,COMMON,INITIAL,TRANSFER,contract
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
EXPECTED=(('C major','3','E'),('C major','7','B'),('G major','3','B'),('D major','7','C#'),('A major','6','F#'),('E major','2','F#'),('F major','4','Bb'),('A minor','b3','C'),('A minor','b7','G'),('E minor','5','B'),('D minor','b6','Bb'),('A harmonic minor','7','G#'),('A melodic minor','6','F#'),('A melodic minor','7','G#'))
PITCH_CLASSES=(4,11,11,1,6,6,10,0,7,11,10,8,6,8);TUNE=(('E',40),('A',45),('D',50),('G',55),('B',59),('e',64))
def plan():return {'prerequisites':{'original_workbook':True,'own_instrument':True},'partner':{'kind':'external_human','reference':'local partner','ready':True}}
def locations(pc,alt=False):
    low=next(n for n in range(40,52) if n%12==pc)+(12 if alt else 0);m=[low,low+12,low+24];out={}
    for k,n in zip(('low','mid','high'),m):
        choices=[(s,v) for s,v in TUNE if 0<=n-v<=24];s,v=choices[-1] if alt else choices[0];out[k]={'midi':n,'string':s,'fret':n-v}
    return out
def confirm(f):return {'key':f.key,'context':EXPECTED[f.index][0],'degree':EXPECTED[f.index][1],'ready':True}
def ready(i=0):
    f=DegreeFlow(KEYS[i]);f.set_plan(f.token(),plan());return f
def named(i=0,name='correct',cue=None):
    f=ready(i);f.begin(f.token(),confirm(f));f.heard(f.token(),{k:'yes' for k in CUE_DUTIES} if cue is None else cue)
    f.sung_name(f.token(),{'pitch_name':EXPECTED[i][2] if name=='correct' else name,'singing_attempted':True});return f
def prepared(i=0,alt=False,name='correct',pc=None,cue=None):
    f=named(i,name,cue);f.choose_locations(f.token(),locations(PITCH_CLASSES[i] if pc is None else pc,alt));return f
def perform(f):
    f.setup_target(f.token(),True);f.attack(f.token(),True);f.release(f.token(),True)
    if f.stage==0:
        check('reference_answer' not in f.learner_view());f.reveal(f.token())
    check(f.state=='reporting')
def report(f):
    target=f.target();return {'key':f.key,'context':EXPECTED[f.index][0],'degree':EXPECTED[f.index][1],'register':target['register'],'contact':target['contact'],'named_pitch':f.named_pitch,
      'attack_count':1,'common':{k:'yes' for k in COMMON},'stage_duties':{k:'yes' for k in (INITIAL if f.stage==0 else TRANSFER)},'diagnosis':'','notes':'Manual reply only; no audio inspected.'}
packet=Path('Build')/L/'degree-realization-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()];base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()];old=base[110:124]
check(RAW==EXPECTED and len(rows)==14 and [x['package_key'] for x in rows]==list(KEYS));check(KEYS[-1].endswith('p013-t1-r15/amelodicminor'))
for i,(r,o) in enumerate(zip(rows,old)):
    check(r['implementation']['task']['contract']==contract(i));check(r['implementation']['task']['printed_components']==[*EXPECTED[i],'','',''])
    for key in ('source_refs','source_payload','timing_authority','package_key','source_identity'):check(r[key]==o[key])
    for key in ('events','tab_blocks','source_field_occurrences'):check(r['implementation'][key]==o['implementation'][key])
    check(contract(i)['chosen_register_realizations']==42 and contract(i)['source_extent_header']=='14 COMMANDS | 56 REALIZATIONS')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(contract(i)[flag] is False)
    for alt in (False,True):
        f=prepared(i,alt);check('reference_answer' not in f.learner_view());check(f.source_player_view()['spoken_cue']=={'context':EXPECTED[i][0],'degree':EXPECTED[i][1]})
        for stage in range(3):
            check(f.stage==stage);refuse(f,lambda:f.finish(f.token()));refuse(f,lambda:f.next_register(f.token()));perform(f);t=f.token();f.report(t,report(f));refuse(f,lambda:f.report(t,report(f)))
            if stage<2:
                refuse(f,lambda:f.finish(f.token()));f.next_register(f.token());refuse(f,lambda:f.begin(f.token(),confirm(f)));f.begin(f.token())
            else:refuse(f,lambda:f.next_register(f.token()));f.finish(f.token());check(f.state=='completed')
        hist=deepcopy(f.response_history);f.set_plan(f.token(),plan());check(f.stage==0 and f.state=='ready' and f.locations is None and f.ever_revealed and f.response_history==hist)
    for name,pc in ((None,PITCH_CLASSES[i]),(EXPECTED[i][2],(PITCH_CLASSES[i]+1)%12),('C#' if PITCH_CLASSES[i]!=1 else 'D',PITCH_CLASSES[i])):
        f=prepared(i,name=name,pc=pc);check(f.named_pitch==name and f.locations['low']['midi']%12==pc and 'reference_answer' not in f.learner_view());perform(f)
        r=report(f);refuse(f,lambda:f.report(f.token(),r));r['diagnosis']='Retain wrong/unknown name or chosen location after playing';f.report(f.token(),r);check(f.state=='needs_retry')
        refuse(f,lambda:f.next_register(f.token()));h=deepcopy(f.response_history);f.retry(f.token(),'Repeat cue and name');check(f.state=='ready' and f.locations is None and f.response_history==h and f.ever_revealed)
    for duty in CUE_DUTIES:
        for val in ('no','uncertain'):
            cue={k:'yes' for k in CUE_DUTIES};cue[duty]=val;f=prepared(i,cue=cue);perform(f);r=report(f);refuse(f,lambda:f.report(f.token(),r));r['diagnosis']='Cue/root contamination';f.report(f.token(),r);check(f.state=='needs_retry')
    for stage in (0,1):
        for duty in COMMON+(INITIAL if stage==0 else TRANSFER):
            for val in ('no','uncertain'):
                f=prepared(i)
                if stage:perform(f);f.report(f.token(),report(f));f.next_register(f.token());f.begin(f.token())
                perform(f);r=report(f);r['common' if duty in COMMON else 'stage_duties'][duty]=val;refuse(f,lambda:f.report(f.token(),r));r['diagnosis']='Manual target duty failed';f.report(f.token(),r);check(f.state=='needs_retry');f.retry(f.token(),'Retry released stage');check(f.stage==stage and f.state=='ready')
    for count in (0,2,7):
        f=prepared(i);perform(f);r=report(f);r['attack_count']=count;refuse(f,lambda:f.report(f.token(),r));r['diagnosis']='Actual attack count';f.report(f.token(),r);check(f.state=='needs_retry')

for mutate in (lambda p:p.update(extra=True),lambda p:p['prerequisites'].update(own_instrument=1),lambda p:p['partner'].update(kind='app_audio'),lambda p:p['partner'].update(reference=''),lambda p:p['partner'].update(ready=1)):
    p=plan();mutate(p);f=DegreeFlow(KEYS[0]);refuse(f,lambda:f.set_plan(f.token(),p))
f=ready()
for field,val in (('key',KEYS[1]),('context','A minor'),('degree','7'),('ready',1)):
    c=confirm(f);c[field]=val;refuse(f,lambda:f.begin(f.token(),c))
f.begin(f.token(),confirm(f));refuse(f,lambda:f.choose_locations(f.token(),locations(4)));refuse(f,lambda:f.reveal(f.token()));refuse(f,lambda:f.attack(f.token(),True))
r={k:'yes' for k in CUE_DUTIES};r['no_guitar_root_reference']=True;refuse(f,lambda:f.heard(f.token(),r));f.heard(f.token(),{k:'yes' for k in CUE_DUTIES})
for value in ('E4',4,True,{},''):
    refuse(f,lambda:f.sung_name(f.token(),{'pitch_name':value,'singing_attempted':True}))
refuse(f,lambda:f.sung_name(f.token(),{'pitch_name':'E','singing_attempted':1}));f.sung_name(f.token(),{'pitch_name':'Fb','singing_attempted':True})
for mutate in (lambda p:p.update(extra=True),lambda p:p['low'].update(midi=True),lambda p:p['low'].update(fret=True),lambda p:p['low'].update(string='X'),lambda p:p['low'].update(fret=25),
 lambda p:p['low'].update(fret=p['low']['fret']+1),lambda p:p.update(mid=deepcopy(p['low'])),lambda p:p.update(high=deepcopy(p['mid'])),lambda p:p.update(mid=locations(5)['mid'])):
    p=locations(4);mutate(p);refuse(f,lambda:f.choose_locations(f.token(),p))
p=locations(4);f.choose_locations(f.token(),p);p['low']['midi']=0;check(f.target()['contact']['midi']==40);f.learner_view()['chosen_locations']['low']['midi']=0;check(f.target()['contact']['midi']==40)
perform(f);f.report(f.token(),report(f));check(f.state=='reported') # Enharmonic Fb accepted as printed E pitch class.
for stage in ('singing','choose_locations'):
    f=ready();f.begin(f.token(),confirm(f));f.heard(f.token(),{k:'yes' for k in CUE_DUTIES})
    if stage=='choose_locations':f.sung_name(f.token(),{'pitch_name':None,'singing_attempted':True})
    refuse(f,lambda:f.cannot_respond(f.token(),'',True));refuse(f,lambda:f.cannot_respond(f.token(),'Unknown',False));f.cannot_respond(f.token(),'Unable to supply response',True);check(f.state=='needs_retry' and f.locations is None)

# Causal release/reopen across initial and transfer states; no manual focus/route shortcuts.
f=ready();samples=[deepcopy(f)];f.begin(f.token(),confirm(f));samples.append(deepcopy(f));f.heard(f.token(),{k:'yes' for k in CUE_DUTIES});samples.append(deepcopy(f));f.sung_name(f.token(),{'pitch_name':'E','singing_attempted':True});samples.append(deepcopy(f));f.choose_locations(f.token(),locations(4));samples.append(deepcopy(f))
for stage in range(3):
    f.setup_target(f.token(),True);samples.append(deepcopy(f));f.attack(f.token(),True);samples.append(deepcopy(f));f.release(f.token(),True);samples.append(deepcopy(f))
    if stage==0:f.reveal(f.token());samples.append(deepcopy(f))
    f.report(f.token(),report(f));samples.append(deepcopy(f))
    if stage<2:f.next_register(f.token());samples.append(deepcopy(f));f.begin(f.token());samples.append(deepcopy(f))
    else:f.finish(f.token());samples.append(deepcopy(f))
for sample in samples:
    f=deepcopy(sample);t=f.token();h=deepcopy(f.response_history);lh=deepcopy(f.location_history);ever=f.ever_revealed
    refuse(f,lambda:f.cancel(DegreeFlow(f.key).token()));refuse(f,lambda:f.cancel(list(t)));f.cancel(t);refuse(f,lambda:f.cancel(t));f.reopen(f.token());refuse(f,lambda:f.release(f.token(),False));f.release(f.token(),True)
    check(f.response_history==h and f.location_history==lh and f.ever_revealed==ever)
    if sample.state in ('hearing','singing','choose_locations','silent_setup','attack','await_release','reveal'):
        check(f.state=='ready' and f.stage==sample.stage)
        if f.stage==0:check(f.locations is None and f.named_pitch is None)
        else:check(f.first_correct and f.locations==sample.locations)
    if sample.state not in ('setup','completed'):refuse(sample,lambda s=sample:s.set_plan(s.token(),plan()))
    for call in (lambda:f.set_plan(t,plan()),lambda:f.begin(t,confirm(f)),lambda:f.heard(t,{}),lambda:f.sung_name(t,{}),lambda:f.choose_locations(t,{}),lambda:f.cannot_respond(t,'unknown',True),lambda:f.setup_target(t,True),lambda:f.attack(t,True),lambda:f.release(t,True),lambda:f.reveal(t),lambda:f.report(t,{}),lambda:f.next_register(t),lambda:f.retry(t,'Retry'),lambda:f.finish(t),lambda:f.reopen(t)):refuse(f,call)
    v=f.source_player_view();v['spoken_cue']['context']='mutated';check(f.source_player_view()['spoken_cue']['context']=='C major')
for key in [r['package_key'] for r in base[102:110]]+['exercise-completeness-r01/level077/modulef/p013-t1-r14/amelodicminor',None,True]:refuse(None,lambda k=key:DegreeFlow(k))
f=prepared();perform(f)
for field,val in (('key',KEYS[1]),('named_pitch','F'),('register','mid'),('attack_count',True),('attack_count',-1),('notes','')):
    r=report(f);r[field]=val;refuse(f,lambda:f.report(f.token(),r))
r=report(f);t=f.token();f.report(t,r);r['common'].clear();check(bool(f.history[-1]['data']['response']['common']));refuse(f,lambda:f.report(t,report(f)))
out={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),
 'model':pin(Path('Tools')/L/'degree_contract.py'),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
