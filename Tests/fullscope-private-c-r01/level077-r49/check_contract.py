from pathlib import Path
from copy import deepcopy
from itertools import combinations
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r49')
s=importlib.util.spec_from_file_location('transfer',R/'Tools'/L/'transfer_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def refuse(f,fn,label):
    global refusals
    before=deepcopy(f.__dict__)
    try:fn()
    except m.Refusal:refusals+=1
    else:raise AssertionError('accepted '+label)
    check(f.__dict__==before,'atomic refusal '+label)
def contact(midi,other=False):
    found=[{'midi':midi,'string':s,'fret':midi-n} for s,n in m.TUNING.items() if 0<=midi-n<=24]
    return found[-1 if other else 0]
def plan(i,direction='up',reverse=False):
    root=(48 if direction=='up' else 72)+m.PC[m.RAW[i][0]]
    target=root+m.SEMITONES[m.RAW[i][1]]*(1 if direction=='up' else -1)
    choices=[x for x in range(40,89) if x%12==target%12]
    triple=next(x for x in combinations(choices,3) if target in x)
    registers={label:contact(n) for label,n in zip(m.REGISTERS,triple)}
    first=m.REGISTERS[triple.index(target)];remaining=[x for x in m.REGISTERS if x!=first]
    if reverse:remaining.reverse()
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},
      'provider':{'kind':'external_human','reference':'External root-reference player for synthetic fixture','ready':True},
      'direction':direction,'root_midi':root,'registers':registers,'first_register':first,'transfer_order':[first,*remaining]}
def to_report(f):
    f.begin(f.token(),True if f.stage==0 else None)
    if f.stage==0:f.heard_root(f.token(),True);f.sung(f.token(),True)
    f.setup_target(f.token(),True);f.attempt_attack(f.token(),True);f.release(f.token(),True)
def response(f):
    target=f.target()
    return {'source_interval':m.RAW[f.index][1],**target,'attack_count':1,'common':dict.fromkeys(m.COMMON,'yes'),
      'stage_duties':dict.fromkeys(m.INITIAL if f.stage==0 else m.TRANSFER,'yes'),'diagnosis':'','notes':'Synthetic manual report; no sound observed.'}
def ready(i,stage=0,direction='up',reverse=False):
    f=m.TransferFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i,direction,reverse))
    for _ in range(stage):to_report(f);f.report(f.token(),response(f));f.next_register(f.token())
    return f
def at_state(i,stage,state):
    f=ready(i,stage)
    if state=='ready':return f
    f.begin(f.token(),True if stage==0 else None)
    if f.state==state:return f
    if stage==0:
        f.heard_root(f.token(),True)
        if f.state==state:return f
        f.sung(f.token(),True)
        if f.state==state:return f
    f.setup_target(f.token(),True)
    if f.state==state:return f
    f.attempt_attack(f.token(),True)
    if f.state==state:return f
    f.release(f.token(),True)
    if f.state==state:return f
    r=response(f)
    if state=='needs_retry':r['common']['target_correct']='uncertain';r['diagnosis']='Unable to confirm target'
    f.report(f.token(),r)
    if f.state==state:return f
    if state=='completed':f.finish(f.token());return f
    raise AssertionError('unknown fixture '+state)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'register-transfer-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][34:46]
roots=['C','F#','Bb','E','Ab','D','B','F','C#','G','Eb','A']
intervals=['M3','P5','m3','M6','P4','m7','M7','M2','TT','m6','m2','P8'];distances=[4,7,3,9,5,10,11,2,6,8,1,12]
check(len(rows)==12 and [r['package_key'] for r in rows]==list(m.KEYS),'exact twelve source children')
for i,(row,old) in enumerate(zip(rows,base)):
    c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source contact/event invention')
    check(c['source_fields']=={'Card':str(i+1),'Given root':roots[i],'Requested interval':intervals[i],'Sing destination':'','Low / mid / high':''},'independent five source fields including blanks')
    check(c['requested_interval_semitones']==distances[i],'independent case-sensitive interval distance')
    check(c['source_footer']=='After the first correct note, repeat the same pitch class in two other registers without re-singing. This converts interval hearing into immediate neck navigation.','full original joined footer')
    check(c['source_no_search']=='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.','full no-search obligation')
    check(c['source_extent_header']=='12 ROOTS | 48 REALIZATIONS' and c['source_direction'] is None and c['source_register_bounds'] is None and c['source_octave_fret_timing'] is None,'extent literal; no invented source realization')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    for direction in ('up','down'):
        for reverse in (False,True):
            f=ready(i,direction=direction,reverse=reverse);p=plan(i,direction,reverse)
            chosen=p['registers'][p['first_register']]['midi']
            check(chosen-p['root_midi']==distances[i]*(1 if direction=='up' else -1),'full signed interval, including octave')
            check(f.provider_view()['audio_supplied'] is False and f.provider_view()['source_interval']==intervals[i],'external root provider boundary')
            f.set_plan(f.token(),p);p['registers']['low']['fret']=99;check(f.plan['registers']['low']['fret']!=99,'plan copy custody')
            initial=None
            for stage in range(3):
                check(f.stage==stage and f.target()['register']==f.plan['transfer_order'][stage],'authored transfer order')
                refuse(f,lambda:f.next_register(f.token()),'no premature next register');refuse(f,lambda:f.finish(f.token()),'no premature finish')
                if stage==0:
                    for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'fresh root provider readiness')
                else:
                    check(f.first_correct==initial,'first correct target retained across transfers')
                    refuse(f,lambda:f.begin(f.token(),True),'no required new root in transfer')
                t=f.token();f.begin(t,True if stage==0 else None);refuse(f,lambda:f.begin(t,True if stage==0 else None),'duplicate begin')
                refuse(f,lambda:f.set_plan(f.token(),plan(i,direction,reverse)),'active plan mutation')
                refuse(f,lambda:f.report(f.token(),response(f)),'early report');refuse(f,lambda:f.attempt_attack(f.token(),True),'attack before setup')
                if stage==0:
                    refuse(f,lambda:f.sung(f.token(),True),'sing before hear');f.heard_root(f.token(),True)
                    refuse(f,lambda:f.setup_target(f.token(),True),'setup before singing');f.sung(f.token(),True)
                else:
                    check(f.state=='silent_setup','no transfer hearing/singing stages')
                    refuse(f,lambda:f.heard_root(f.token(),True),'no transfer root action');refuse(f,lambda:f.sung(f.token(),True),'no transfer singing action')
                t=f.token();f.setup_target(t,True);refuse(f,lambda:f.setup_target(t,True),'duplicate silent setup')
                t=f.token();f.attempt_attack(t,True);refuse(f,lambda:f.attempt_attack(t,True),'duplicate attack')
                refuse(f,lambda:f.report(f.token(),response(f)),'release fence');refuse(f,lambda:f.release(f.token(),1),'release explicit boolean')
                f.release(f.token(),True);r=response(f);t=f.token();f.report(t,r);r['contact']['fret']=99
                check(f.history[-1]['data']['response']['contact']['fret']!=99,'response custody')
                check(f.history[-1]['data']['manual_requirements_reported'] is True and f.history[-1]['data']['performance_verified'] is False,'positive self-report not acoustic verification')
                refuse(f,lambda:f.report(t,response(f)),'duplicate report')
                if stage==0:initial=deepcopy(f.first_correct);check(initial['target']['contact']['midi']==chosen,'first correct exact target')
                if stage<2:refuse(f,lambda:f.finish(f.token()),'all three required');f.next_register(f.token())
                else:refuse(f,lambda:f.next_register(f.token()),'no fourth register');f.finish(f.token())
            check(f.state=='completed','all twelve × both directions × both remaining orders')
            check(sum(x['kind']=='sung' for x in f.history)==1 and sum(x['kind']=='attack_attempt' for x in f.history)==3,'one initial singing and three attack attempts')
            history=deepcopy(f.history);f.set_plan(f.token(),plan(i,direction));check(f.state=='ready' and f.stage==0 and f.first_correct is None and f.history[:len(history)]==history,'new plan resets first-correct gate, keeps history')
    for stage in range(3):
        modifications=[]
        for field,names in [('common',m.COMMON),('stage_duties',m.INITIAL if stage==0 else m.TRANSFER)]:
            for name in names:
                for value in ('no','uncertain'):modifications.append((name,lambda r,field=field,name=name,value=value:r[field].update({name:value})))
        for count in (0,2,7):modifications.append(('physical attack count',lambda r,count=count:r.update(attack_count=count)))
        for label,mutate in modifications:
            f=ready(i,stage);first=deepcopy(f.first_correct);to_report(f);r=response(f);mutate(r)
            refuse(f,lambda:f.report(f.token(),r),'failure needs diagnosis '+label)
            r['diagnosis']='Reported failure; stop searching and retry current register';f.report(f.token(),r)
            check(f.state=='needs_retry' and f.history[-1]['data']['manual_requirements_reported'] is False,'retained failed or uncertain report')
            refuse(f,lambda:f.next_register(f.token()),'failed transfer gate');refuse(f,lambda:f.finish(f.token()),'failed completion')
            refuse(f,lambda:f.retry(f.token(),''),'retry diagnosis required');f.retry(f.token(),'Explicit retry after diagnosis')
            check(f.stage==stage and f.state=='ready' and f.first_correct==first,'retry retains stage and prior first-correct target')
            before=len(f.history);to_report(f)
            check(sum(x['kind']=='sung' for x in f.history[before:])==(1 if stage==0 else 0),'later failure retry does not re-sing')
            f.report(f.token(),response(f));check(f.state=='reported','corrected manual retry can proceed')
        f=ready(i,stage);to_report(f)
        for field,value in [('source_interval','wrong'),('register','wrong'),('notes',''),('attack_count',True),('attack_count',-1),('attack_count',1.0),('attack_count','1')]:
            r=response(f);r[field]=value;refuse(f,lambda:f.report(f.token(),r),'bad typed response '+field)
        for field in ('midi','string','fret'):
            r=response(f);r['contact'][field]='wrong';refuse(f,lambda:f.report(f.token(),r),'contact response mismatch')
        for field in ('common','stage_duties'):
            r=response(f);r[field][next(iter(r[field]))]=True;refuse(f,lambda:f.report(f.token(),r),'explicit outcome enum')
        states=('ready','silent_setup','attack','await_release','reporting','reported','needs_retry')+(('hearing_root','singing') if stage==0 else ())+(('completed',) if stage==2 else ())
        for state in states:
            f=at_state(i,stage,state);check(f.state==state,'cancel fixture state');history=deepcopy(f.history);p=deepcopy(f.plan);first=deepcopy(f.first_correct);t=f.token()
            f.cancel(t);refuse(f,lambda:f.cancel(t),'duplicate cancel');f.reopen(f.token());f.cancel(f.token());f.reopen(f.token())
            refuse(f,lambda:f.begin(f.token(),True if stage==0 else None),'reopen release bypass');refuse(f,lambda:f.release(f.token(),False),'reopen needs physical release');f.release(f.token(),True)
            expected='ready' if state in ('hearing_root','singing','silent_setup','attack','await_release','reporting') else state
            check(f.state==expected and f.stage==stage and f.plan==p and f.first_correct==first and f.history[:len(history)]==history,'cancel/reopen preserves source, plan, first-correct and stage')
            refuse(f,lambda:f.begin(t,True if stage==0 else None),'pre-cancel stale token')
    mutations=[]
    for field in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
    mutations.extend([('app source',lambda p:p['provider'].update(kind='app_audio')),('source readiness',lambda p:p['provider'].update(ready=1)),('source reference',lambda p:p['provider'].update(reference='')),
      ('direction absent',lambda p:p.update(direction=None)),('rootPC',lambda p:p.update(root_midi=p['root_midi']+1)),('rootbool',lambda p:p.update(root_midi=True)),
      ('rootbound',lambda p:p.update(root_midi=-1)),('different first register',lambda p:p.update(first_register=next(x for x in m.REGISTERS if x!=p['first_register']))),
      ('order start',lambda p:p['transfer_order'].reverse()),('duplicate order',lambda p:p['transfer_order'].__setitem__(2,p['transfer_order'][0])),
      ('order type',lambda p:p.update(transfer_order=tuple(p['transfer_order']))),('wrong midi',lambda p:p['registers']['low'].update(midi=p['registers']['low']['midi']+1)),
      ('same sounding register',lambda p:p['registers'].update(mid=deepcopy(p['registers']['low']))),('wrong string',lambda p:p['registers']['low'].update(string='x')),
      ('wrong fret',lambda p:p['registers']['low'].update(fret=p['registers']['low']['fret']+1)),('negative fret',lambda p:p['registers']['low'].update(fret=-1)),
      ('fret bound',lambda p:p['registers']['low'].update(fret=25)),('fret bool',lambda p:p['registers']['low'].update(fret=True)),
      ('midi bool',lambda p:p['registers']['low'].update(midi=True))])
    for label,mutate in mutations:
        f=ready(i);p=plan(i);mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
    f=ready(i);p=plan(i);p['provider']['kind']='external_recording'
    for label in m.REGISTERS:p['registers'][label]=contact(p['registers'][label]['midi'],True)
    f.set_plan(f.token(),p);check(f.plan==p,'alternative string positions valid when sounding registers remain distinct')
    # An exact alternative fret position at the same MIDI is not a new sounding register.
    p=plan(i);shared=p['registers']['mid']['midi'];p['registers']['low']=contact(shared);p['registers']['mid']=contact(shared,True)
    check(p['registers']['low']['string']!=p['registers']['mid']['string'],'same MIDI two distinct fretboard positions fixture')
    refuse(f,lambda:f.set_plan(f.token(),p),'same MIDI different strings not new register')
    other=ready(i);refuse(f,lambda:f.begin(other.token(),True),'foreign instance');t=f.token();f.set_plan(f.token(),plan(i));refuse(f,lambda:f.begin(t,True),'stale plan generation')
    view=f.provider_view();view['initial_chosen_destination']['fret']=99;check(f.provider_view()['initial_chosen_destination']['fret']!=99,'view copy custody')
check(rows[-1]['implementation']['task']['contract']['requested_interval_semitones']==12,'P8 never unison')
check(all('p003' not in r['package_key'] and 'p007' not in r['package_key'] and 'p008' not in r['package_key'] for r in rows),'card20 and outside/quarantine rows untouched')
f=m.TransferFlow(m.KEYS[0]);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup' and f.plan is None,'unconfigured cancel/reopen retained')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'transfer_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
