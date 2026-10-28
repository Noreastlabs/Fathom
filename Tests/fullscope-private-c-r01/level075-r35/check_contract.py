from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r35')
s=importlib.util.spec_from_file_location('cue',R/'Tools'/L/'cue_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(index):
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':72,
        'old_chord':'G7','old_voicing':'Synthetic learner G7 choice','waiting_chord':'Cmaj7','waiting_voicing':'Synthetic Cmaj7 choice',
        'cue':m.ROWS[index][3],'provider':{'type':'human','capabilities':dict.fromkeys(('visual','audio','musical','named_section'),True),
         'provision_description':'External human supplies chosen source cue and unannounced named-section request.'},
        'destinations':{k:{'source_first_chord':r[2],'voicing':'Learner choice','texture_realization':'Learner realization of visible source chart context'} for k,r in zip(m.KEYS,m.ROWS)}}
def ready(index):
    f=m.CueFlow(m.KEYS[index]);f.set_plan(f.token(),plan(index));return f
def reporting(f):f.begin(f.token(),True);f.release(f.token(),True)
def response(f,requested=None,missed=False):
    return {'attack_coverage':[{'source_order':i,'covered':'yes'} for i in range(1,9)] if f.phase==0 else [],
        'obligations':dict.fromkeys(m.TRANSITION if f.phase==0 else m.RECOVERY,'yes'),
        'recovery':None if f.phase==0 else {'requested_destination_key':requested or m.KEYS[(f.index+1)%8],
        'cue_missed':missed,'entry_delay_bars':1 if missed else 0,'continued_current_bar':'yes' if missed else None},
        'notes':'Synthetic learner report, not a performed cue observation.'}
def pass_phase(f):reporting(f);f.report(f.token(),response(f));f.advance(f.token())
def second(index):
    f=ready(index);pass_phase(f);return f
def pin(p):
    b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
base=[json.loads(x) for x in (R/basepath).read_text().splitlines()][18:26]
packet=Path('Build')/L/'section-cue-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
check(len(rows)==8,'finite keys')
for index,(old,row) in enumerate(zip(base,rows)):
    c=row['implementation']['task']['contract']
    for key in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
        check(row[key]==old[key],'original '+key)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source pitch events invented')
    slots=c['source_harmonic_attack_slots'];check(len(slots)==8,'eight harmonic slots')
    for i,x in enumerate(slots,1):
        check(x['source_order']==i and x['chord_symbol']==('G7' if i<=4 else m.ROWS[index][2]),'source slot order/chord')
        check(all(x[n] is None for n in ('pitch','fret','onset_q','duration_q')),'unprinted realization unknown')
    check(c['source_no_look_instruction']==m.NOLOOK and c['source_p6_support']==m.SUPPORT,'whole source instructions')
    check(c['source_example_calls']==list(m.CALLS),'four example calls')
    check([x['existing_row_key'] for x in c['no_look_destination_options']]==list(m.KEYS),'all existing destination options')
    for x in c['no_look_destination_options']:check(x['master_chart_context']['line_end']-x['master_chart_context']['line_start']==2,'source context locator')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','cue_generated','cue_recognized','mastery_awarded','credit_awarded','persistence'):
        check(c[flag] is False,flag)
    # Every row must support actual external requests for every other row, not a preselected target.
    for dest in m.KEYS:
        for missed in (False,True):
            f=second(index);f.begin(f.token(),True)
            check(f.history[-1]['data']['requested_destination'] is None,'app does not preselect request')
            refuse(f,lambda:f.report(f.token(),response(f,dest,missed)),'report before release')
            f.release(f.token(),True);token=f.token();r=response(f,dest,missed);f.report(token,r)
            check(f.state=='reported' and f.history[-1]['data']['response']['recovery']['requested_destination_key']==dest,'external request retained')
            refuse(f,lambda:f.report(token,r),'duplicate report')
            f.advance(f.token());check(f.state=='completed','ontime or one-bar-later source route')
    for phase in (0,1):
        names=list(m.TRANSITION if phase==0 else m.RECOVERY)+([f'attack{i}' for i in range(8)] if phase==0 else [])
        for name in names:
            for value in ('no','uncertain'):
                f=ready(index) if phase==0 else second(index);reporting(f);r=response(f)
                if name.startswith('attack'):r['attack_coverage'][int(name[-1])]['covered']=value
                else:r['obligations'][name]=value
                f.report(f.token(),r);check(f.state=='needs_retry' and f.history[-1]['data']['response']==r,'negative/uncertain retained')
                refuse(f,lambda:f.advance(f.token()),'unfulfilled source duty')
                refuse(f,lambda:f.begin(f.token(),True),'explicit retry required')
                f.retry(f.token(),'Isolate the current source duty.');check(f.phase==phase,'retry scope retained')
    # Wrong actual entry timing is recorded honestly rather than discarded as malformed input.
    for missed,delay,continued in ((False,1,None),(True,0,'yes'),(True,2,'yes'),(True,1,'no'),(True,1,'uncertain')):
        f=second(index);reporting(f);r=response(f,missed=missed)
        r['recovery']['entry_delay_bars']=delay;r['recovery']['continued_current_bar']=continued
        f.report(f.token(),r);check(f.state=='needs_retry' and f.history[-1]['data']['response']==r,'wrong delay or stopped current bar retained')
        refuse(f,lambda:f.advance(f.token()),'recovery timing not satisfied')
    # Source cue provider is explicit, with no assumption that a generic timer supplies music or named requests.
    f=m.CueFlow(m.KEYS[index]);good=plan(index)
    for cap in (*m.ROWS[index][4],'named_section'):
        p=deepcopy(good);p['provider']['capabilities'][cap]=False
        refuse(f,lambda p=p:f.set_plan(f.token(),p),'missing external cue capability '+cap)
    p=deepcopy(good);p['provider']['type']='app_audio';refuse(f,lambda:f.set_plan(f.token(),p),'app provider unsupported')
    p=deepcopy(good);p['provider']['type']='external_source';f.set_plan(f.token(),p)
    for ready_value in (False,None,1):refuse(f,lambda ready_value=ready_value:f.begin(f.token(),ready_value),'fresh provider readiness')
    token=f.token();f.begin(token,True);refuse(f,lambda:f.begin(token,True),'duplicate begin')
    refuse(f,lambda:f.set_plan(f.token(),good),'active choice mutation')
    f.release(f.token(),True);refuse(f,lambda:f.set_plan(f.token(),good),'held report choice mutation')
    history=deepcopy(f.history);oldtoken=f.token();f.cancel(oldtoken);f.reopen(f.token())
    refuse(f,lambda:f.begin(oldtoken,True),'pre-cancel callback');refuse(f,lambda:f.begin(f.token(),True),'reopen release fence')
    f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True)
    check(f.state=='ready' and f.history[:len(history)]==history,'reopen restarts incomplete phase with history')
    refuse(f,lambda:f.begin(f.token(),False),'reopen rechecks provider')
    pass_phase(f);pass_phase(f);history=deepcopy(f.history);p=plan(index);p['bpm']=80
    f.set_plan(f.token(),p);check(f.phase==0 and f.state=='ready' and f.history[:-1]==history,'plan revision resets phases retains history')
    p['bpm']=81;check(f.plan['bpm']==80,'plan custody')

f=m.CueFlow(m.KEYS[0]);p=plan(0);mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for value in (True,0,-1,float('nan'),float('inf'),10**1000,'72'):bad('invalid BPM',lambda q,value=value:q.__setitem__('bpm',value))
for name in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,name=name:q['prerequisites'].__setitem__(name,False))
bad('wrong oldchord',lambda q:q.__setitem__('old_chord','Cmaj7'))
bad('wrong waitingchord',lambda q:q.__setitem__('waiting_chord','G7'))
bad('wrong cue',lambda q:q.__setitem__('cue','generic beep'))
bad('empty oldvoicing',lambda q:q.__setitem__('old_voicing',''))
bad('unknown provider capability',lambda q:q['provider']['capabilities'].__setitem__('recognition',True))
bad('truthy provider flag',lambda q:q['provider']['capabilities'].__setitem__('named_section',1))
bad('empty provider description',lambda q:q['provider'].__setitem__('provision_description',''))
bad('missing destination',lambda q:q['destinations'].pop(m.KEYS[7]))
bad('wrong destinationfirstchord',lambda q:q['destinations'][m.KEYS[1]].__setitem__('source_first_chord','Cmaj7'))
bad('empty texturechoice',lambda q:q['destinations'][m.KEYS[1]].__setitem__('texture_realization',''))
for label,q in mutants:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
f=ready(0);t=f.token()
for i in range(7):
    x=list(t);x[i]='foreign' if type(t[i]) is str else 99
    refuse(f,lambda x=tuple(x):f.begin(x,True),'token field ownership')
refuse(f,lambda:f.begin(ready(0).token(),True),'other instance')
f=second(0);reporting(f)
for field,value in [('requested_destination_key','unknown'),('cue_missed',1),('entry_delay_bars',True),('entry_delay_bars',-1),('continued_current_bar','yes')]:
    r=response(f);r['recovery'][field]=value
    refuse(f,lambda r=r:f.report(f.token(),r),'malformed recovery')
r=response(f);r['attack_coverage']=[{'source_order':1,'covered':'yes'}];refuse(f,lambda:f.report(f.token(),r),'no fixed waiting attack count')
r=response(f);f.report(f.token(),r);r['notes']='outside change';check(f.history[-1]['data']['response']['notes']!='outside change','response custody')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
    'finite_children':8,'external_request_destination_combinations':64,'ontime_and_missed_paths_per_combination':2,
    'source_harmonic_attack_slots':64,'fixed_pitches':0,'packet':pin(packet),'base':pin(basepath),
    'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_cues_generated_or_inspected':0,
    'actual_performance_observed':False,'native_runs':0,'app_runs':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
