from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r47')
s=importlib.util.spec_from_file_location('atlas',R/'Tools'/L/'interval_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i):return {'prerequisites':{'own_instrument':True,'original_workbook':True},'provider':{'kind':'external_human','reference':'External source supplies chosen notes','ready':True},
    'root_midi':48,'upper_midi':49+i,'target_contact':{'string':'E','fret':9+i}}
def to_report(f):
    f.begin(f.token(),True);f.heard(f.token(),True);f.sung(f.token(),True)
    if f.phase==0:f.setup_target(f.token(),True);f.attempt_attack(f.token(),True)
    f.release(f.token(),True)
def response(f):
    r={'source_interval':m.LABELS[f.index],'direction':f.direction(),'learner_label':m.LABELS[f.index],'common':dict.fromkeys(m.COMMON,'yes'),
      'diagnosis':'','notes':'Synthetic manual hearing/singing report, no audio observed.'}
    if f.phase==0:r.update(attack_count=1,upward_duties=dict.fromkeys(m.UP_DUTIES,'yes'))
    return r
def ready(i,phase=0):
    f=m.IntervalFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i))
    if phase:to_report(f);f.report(f.token(),response(f));f.next_direction(f.token())
    return f
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'interval-atlas-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()]
labels=['m2','M2','m3','M3','P4','TT','P5','m6','M6','m7','M7','P8'];uppers=['Db','D','Eb','E','F','F#','G','Ab','A','Bb','B','C']
check(len(rows)==12 and [r['package_key'] for r in rows]==list(m.KEYS),'twelve exact keys')
for i,row in enumerate(rows):
    old=base[i];c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source note/gate/timing invention')
    check(c['source_fields']=={'Interval':labels[i],'Semitones':i+1,'Reference':'C-'+uppers[i],'Sing upward':'','Sing downward':''},'independent case-sensitive row')
    check([p['pitch_class'] for p in c['source_reference']]==['C',uppers[i]] and all(p['octave'] is None and p['fret'] is None and p['onset'] is None for p in c['source_reference']),'pitch classes not fixed contacts')
    check(c['source_practice']=='Practice: hear root -> sing interval -> play it. Then hear the upper note -> sing downward to the root. Use C only as the first reference; later modules randomize the root.','full joined source practice')
    check(c['source_no_search_rule']=='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.','full no-search rule')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    f=ready(i);p=plan(i);f.set_plan(f.token(),p);p['target_contact']['fret']=0;check(f.plan['target_contact']['fret']==9+i,'plan custody')
    for phase in range(2):
        check(f.phase==phase and f.provider_view()['supply_midi']==(48 if phase==0 else 49+i),'source provider direction')
        for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'current provider readiness')
        t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.sung(f.token(),True),'hear before sing')
        refuse(f,lambda:f.setup_target(f.token(),True),'setup before sing');refuse(f,lambda:f.report(f.token(),response(f)),'early report')
        refuse(f,lambda:f.set_plan(f.token(),plan(i)),'active plan');f.heard(f.token(),True);refuse(f,lambda:f.attempt_attack(f.token(),True),'attack before singing')
        f.sung(f.token(),True)
        if phase==0:
            refuse(f,lambda:f.attempt_attack(f.token(),True),'attack before setup');f.setup_target(f.token(),True);t=f.token();f.attempt_attack(t,True);refuse(f,lambda:f.attempt_attack(t,True),'duplicate attack action')
        else:
            check(f.state=='await_release','downward singing needs no forced guitar attack');refuse(f,lambda:f.setup_target(f.token(),True),'no invented downward setup');refuse(f,lambda:f.attempt_attack(f.token(),True),'no invented downward attack')
        refuse(f,lambda:f.report(f.token(),response(f)),'release fence');refuse(f,lambda:f.release(f.token(),1),'release boolean');f.release(f.token(),True)
        r=response(f);t=f.token();f.report(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','reply custody')
        check(f.history[-1]['data']['performance_verified'] is False and f.history[-1]['data']['automatic_score'] is False,'symbolic/manual not acoustic')
        refuse(f,lambda:f.report(t,response(f)),'duplicate report')
        if phase==0:refuse(f,lambda:f.finish(f.token()),'both directions required');f.next_direction(f.token())
        else:refuse(f,lambda:f.next_direction(f.token()),'no third direction');f.finish(f.token())
    check(f.state=='completed','all12both-directions complete');history=deepcopy(f.history);f.set_plan(f.token(),plan(i))
    check(f.phase==0 and f.state=='ready' and f.history[:len(history)]==history,'plan resets direction with history')
    for phase in range(2):
        modifications=[('wrong symbolic label',lambda r:r.update(learner_label='unknown'))]
        for field,names in [('common',m.COMMON)]+([('upward_duties',m.UP_DUTIES)] if phase==0 else []):
            for name in names:
                for v in ('no','uncertain'):modifications.append((name,lambda r,field=field,name=name,v=v:r[field].update({name:v})))
        if phase==0:
            for count in (0,2,7):modifications.append(('actual attack count',lambda r,count=count:r.update(attack_count=count)))
        for label,mutate in modifications:
            g=ready(i,phase);to_report(g);r=response(g);mutate(r);refuse(g,lambda:g.report(g.token(),r),'missing failure diagnosis '+label)
            r['diagnosis']='Reported failure; isolate cause and retry without searching';g.report(g.token(),r)
            check(g.state=='needs_retry' and g.history[-1]['data']['manual_requirements_reported'] is False,'retained failed report')
            refuse(g,lambda:g.finish(g.token()),'failed completion');refuse(g,lambda:g.next_direction(g.token()),'failed direction advance')
            g.retry(g.token(),'Retry current direction');check(g.state=='ready' and g.phase==phase,'retry same phase')
        g=ready(i,phase);to_report(g)
        for field,value in [('source_interval','WRONG'),('direction','wrong'),('learner_label',''),('notes','')]:
            r=response(g);r[field]=value;refuse(g,lambda:g.report(g.token(),r),'response binding '+field)
        if phase==0:
            for count in (True,-1,1.0,'1'):
                r=response(g);r['attack_count']=count;refuse(g,lambda:g.report(g.token(),r),'attack count type')
    mutations=[]
    for field in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
    mutations.extend([('app provider',lambda p:p['provider'].update(kind='app_audio')),('unavailable provider',lambda p:p['provider'].update(ready=False)),('provider reference',lambda p:p['provider'].update(reference='')),
      ('nonC root',lambda p:p.update(root_midi=49)),('wrong upper',lambda p:p.update(upper_midi=p['upper_midi']+1)),('root boolean',lambda p:p.update(root_midi=True)),
      ('root belowMIDI',lambda p:p.update(root_midi=-12)),('upper beyondMIDI',lambda p:p.update(upper_midi=128)),('bad string',lambda p:p['target_contact'].update(string='x')),
      ('fret boolean',lambda p:p['target_contact'].update(fret=True)),('fret low',lambda p:p['target_contact'].update(fret=-1)),('fret high',lambda p:p['target_contact'].update(fret=25)),
      ('wrong target contact',lambda p:p['target_contact'].update(fret=0))])
    for label,mutate in mutations:
        g=ready(i);p=plan(i);mutate(p);refuse(g,lambda:g.set_plan(g.token(),p),label)
    g=ready(i);p=plan(i);p.update(root_midi=60,upper_midi=61+i,target_contact={'string':'B','fret':2+i});p['provider']['kind']='external_recording';g.set_plan(g.token(),p)
    check(g.plan['upper_midi']-g.plan['root_midi']==i+1,'alternative C octave chosen, full interval extent')
    for phase in range(2):
        for state in ('ready','hearing','singing','await_release','reporting','reported','needs_retry')+(('silent_setup','attack') if phase==0 else ()):
            h=ready(i,phase)
            if state!='ready':h.begin(h.token(),True)
            if state not in ('ready','hearing'):h.heard(h.token(),True)
            if state not in ('ready','hearing','singing'):h.sung(h.token(),True)
            if phase==0 and state not in ('ready','hearing','singing','silent_setup'):h.setup_target(h.token(),True)
            if phase==0 and state not in ('ready','hearing','singing','silent_setup','attack'):h.attempt_attack(h.token(),True)
            if state in ('reporting','reported','needs_retry'):h.release(h.token(),True)
            if state in ('reported','needs_retry'):
                r=response(h)
                if state=='needs_retry':r['learner_label']='wrong';r['diagnosis']='Wrong label'
                h.report(h.token(),r)
            check(h.state==state,'fixture state');history=deepcopy(h.history);p=deepcopy(h.plan);t=h.token();h.cancel(t);refuse(h,lambda:h.cancel(t),'duplicate cancel')
            h.reopen(h.token());h.cancel(h.token());h.reopen(h.token());refuse(h,lambda:h.begin(h.token(),True),'reopen release bypass');h.release(h.token(),True)
            target='ready' if state in ('hearing','singing','silent_setup','attack','await_release','reporting') else state
            check(h.state==target and h.phase==phase and h.plan==p and h.history[:len(history)]==history,'cancel/reopen preserves direction and custody')
    g=ready(i);other=ready(i);refuse(g,lambda:g.begin(other.token(),True),'foreign instance');t=g.token();g.set_plan(g.token(),plan(i));refuse(g,lambda:g.begin(t,True),'stale generation')
check(rows[11]['implementation']['task']['contract']['source_fields']['Semitones']==12,'octave never collapsed to unison')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'interval_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
