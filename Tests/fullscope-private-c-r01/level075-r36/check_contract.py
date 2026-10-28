from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r36')
s=importlib.util.spec_from_file_location('contour',R/'Tools'/L/'contour_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=0;refusals=0
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
def plan():
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':72,
        'comparison_material':'Same synthetic four-bar phrase reused across all6contours; no source notes implied.',
        'bars':[{'bar':i,'material':'Chosen musical material' if n else 'Chosen rest bar',
                 'rhythm':'Chosen unchanged rhythm','planned_note_count':n} for i,n in enumerate((3,0,5,2),1)]}
def ready(index):
    f=m.ContourFlow(m.KEYS[index]);f.set_plan(f.token(),plan());return f
def reporting(f):f.begin(f.token());f.release(f.token(),True)
def response(f):
    return {'bars':[{'bar':i,'source_dynamic':v,'dynamic_match':'yes','reported_note_count':b['planned_note_count']}
                     for i,(v,b) in enumerate(zip(m.ROWS[f.index][2],f.plan['bars']),1)],
            'obligations':dict.fromkeys(m.OBLIGATIONS,'yes'),'notes':'Synthetic manual report; dynamics were not heard or measured.'}
def pin(p):
    b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
base=[json.loads(x) for x in (R/basepath).read_text().splitlines()][35:41]
packet=Path('Build')/L/'dynamic-contour-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
expected=[['mp']*4,['p','mp','mf','f'],['f','mf','mp','p'],['p','mf','f','mp'],['p','p','f','f'],['f','p','f','p']]
check(len(rows)==6,'six exact contours')
for index,(old,row) in enumerate(zip(base,rows)):
    c=row['implementation']['task']['contract']
    for key in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
        check(row[key]==old[key],'original '+key)
    check(row['implementation']['events']==old['implementation']['events']==[],'no contacts invented')
    check([x['dynamic'] for x in c['source_bar_targets']]==expected[index],'independent exact source map')
    check([x['bar'] for x in c['source_bar_targets']]==[1,2,3,4],'four source bars')
    for x in c['source_bar_targets']:check(all(x[n] is None for n in ('pitch','onset_q','velocity','decibels')),'no unprinted acoustic/timing values')
    check(c['source_constraint']=='tempo and note count fixed' and c['diagnostic_only']==(index==0),'fixed constraint/Flat diagnostic')
    for flag in ('automatic_evaluation','performance_observed','dynamics_measured','audio_supplied','mastery_awarded','credit_awarded','persistence'):
        check(c[flag] is False,flag)
    f=ready(index);token=f.token();f.begin(token)
    refuse(f,lambda:f.begin(token),'duplicate begin')
    refuse(f,lambda:f.report(f.token(),response(f)),'report before release')
    refuse(f,lambda:f.release(f.token(),False),'release false')
    refuse(f,lambda:f.release(f.token(),1),'truthy release')
    p=plan();p['bpm']=80;refuse(f,lambda:f.set_plan(f.token(),p),'active tempo/material change')
    f.release(f.token(),True);refuse(f,lambda:f.set_plan(f.token(),p),'held report plan change')
    token=f.token();r=response(f);f.report(token,r)
    check(f.state=='reported' and f.history[-1]['data']['reported_count_matches_plan']==[True]*4,'heterogeneous counts satisfy each chosen bar')
    check(not f.history[-1]['data']['performance_verified'] and not f.history[-1]['data']['dynamics_measured'],'no audible verification')
    r['notes']='outside change';check(f.history[-1]['data']['response']['notes']!='outside change','response custody')
    refuse(f,lambda:f.report(token,response(f)),'duplicate report');f.finish(f.token());check(f.state=='completed','manual report completion')
    history=deepcopy(f.history);p=plan();p['bars'][0]['planned_note_count']=4;f.set_plan(f.token(),p)
    check(f.state=='ready' and f.history[:-1]==history,'changed plan resets completion keeps history')
    p['bars'][0]['planned_note_count']=99;check(f.plan['bars'][0]['planned_note_count']==4,'plan custody')
    for bar in range(4):
        for kind in ('more_notes','dynamic_no','dynamic_uncertain'):
            g=ready(index);reporting(g);r=response(g)
            if kind=='more_notes':r['bars'][bar]['reported_note_count']+=1
            else:r['bars'][bar]['dynamic_match']=kind.removeprefix('dynamic_')
            g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'different count/dynamic retained')
            refuse(g,lambda:g.finish(g.token()),'unsatisfied target')
            refuse(g,lambda:g.begin(g.token()),'explicit retry')
            g.retry(g.token(),'Isolate and repeat the same material.');check(g.plan==plan(),'retry fixed material/tempo')
            reporting(g);g.report(g.token(),response(g));g.finish(g.token());check(g.state=='completed','retry can satisfy reports')
    for name in m.OBLIGATIONS:
        for value in ('no','uncertain'):
            g=ready(index);reporting(g);r=response(g);r['obligations'][name]=value;g.report(g.token(),r)
            check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'tempo/material/extent report retained')
            refuse(g,lambda:g.finish(g.token()),'unsatisfied source invariance')
    for state in ('setup','ready','performing','reporting','reported','needs_retry','completed'):
        g=m.ContourFlow(m.KEYS[index])
        if state!='setup':g.set_plan(g.token(),plan())
        if state in ('performing','reporting','reported','needs_retry','completed'):g.begin(g.token())
        if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
        if state in ('reported','needs_retry','completed'):
            r=response(g)
            if state=='needs_retry':r['obligations']['tempo_held']='no'
            g.report(g.token(),r)
        if state=='completed':g.finish(g.token())
        check(g.state==state,'cancel fixture state');before=deepcopy(g.history);oldplan=deepcopy(g.plan);t=g.token()
        g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t),'old callback after reopen')
        refuse(g,lambda:g.begin(g.token()),'reopen release fence');g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.state==('ready' if state in ('performing','reporting') else state),'resume state or interrupted pass repeat')
        check(g.plan==oldplan and g.history[:len(before)]==before,'cancel retains choices and replies')

f=m.ContourFlow(m.KEYS[0]);p=plan();mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,-1,True,'72',float('inf'),float('nan'),10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for name in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,name=name:q['prerequisites'].__setitem__(name,False))
bad('blank comparison material',lambda q:q.__setitem__('comparison_material',''))
bad('three bars',lambda q:q['bars'].pop())
bad('wrong bar order',lambda q:q['bars'].reverse())
bad('boolean bar number',lambda q:q['bars'][0].__setitem__('bar',True))
for field in ('material','rhythm'):bad('blank '+field,lambda q,field=field:q['bars'][0].__setitem__(field,''))
for v in (-1,True,1.5,'3'):bad('invalid planned count',lambda q,v=v:q['bars'][0].__setitem__('planned_note_count',v))
bad('entire phrase silent',lambda q:[b.__setitem__('planned_note_count',0) for b in q['bars']])
for label,q in mutants:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
f=ready(0);t=f.token()
for i in range(6):
    x=list(t);x[i]='foreign' if type(t[i]) is str else 99;refuse(f,lambda x=tuple(x):f.begin(x),'token component')
refuse(f,lambda:f.begin(ready(0).token()),'other instance');reporting(f)
for field,value in [('bar',True),('source_dynamic','f'),('dynamic_match',True),('reported_note_count',-1),('reported_note_count',True),('reported_note_count',1.2)]:
    r=response(f);r['bars'][0][field]=value;refuse(f,lambda r=r:f.report(f.token(),r),'invalid bar response')
for field,value in [('bars',[]),('obligations',{}),('notes','')]:
    r=response(f);r[field]=value;refuse(f,lambda r=r:f.report(f.token(),r),'incomplete response')
f.report(f.token(),response(f));check(f.state=='reported','valid response after refusals')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
    'finite_contours':6,'source_bar_targets':24,'shared_comparison_plan_tested':True,'actual_dynamics_heard_or_measured':0,
    'source_events_invented':0,'packet':pin(packet),'base':pin(basepath),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'native_runs':0,'app_runs':0,'host_tempo_changes':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
