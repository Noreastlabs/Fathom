from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r34')
s=importlib.util.spec_from_file_location('texture',R/'Tools'/L/'texture_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
    return {'prerequisites':dict.fromkeys(['own_instrument','original_workbook','external_recorder'],True),'bpm':72,
        'ladder_realizations':[{'level':i,'chords':[{'source_chord':c,'realization':'Synthetic learner realization'} for c in m.CHORDS],
                               'isolated_variable_preparation':'Learner isolates each variable before combining.'} for i in range(1,7)],
        'ramp_blocks':[{'bars':[2*i+1,2*i+2],'source_texture':v,'chosen_register':'Learner register choice',
                        'realization':'Synthetic learner texture choice'} for i,v in enumerate(m.BLOCKS)],
        'ramp_loudness_plan':'Maintain chosen intentional loudness while density changes.',
        'bar_allocation':[{'bar':i,'progression_positions':[(i-1)%4+1],'within_bar_placement':'Chosen one chord for this bar.'} for i in range(1,13)]}
def ready():
    f=m.TextureFlow();f.set_plan(f.token(),plan());return f
def response(f,kind='external_reference'):
    return {'coverage':[{'position':i,'covered':'yes'} for i in range(1,5 if f.stage<6 else 7)],
        'obligations':dict.fromkeys(m.LADDER_REPORTS if f.stage<6 else m.RAMP_REPORTS,'yes'),
        'notes':'Synthetic self-report, no observed performance.',
        'recording':None if f.stage<6 else {'kind':kind,'value':'External recording reference or explicitly self-reported recording; not inspected.'}}
def reporting(f):f.begin(f.token());f.release(f.token(),True)
def pass_stage(f):reporting(f);f.report(f.token(),response(f));f.advance(f.token())
def at(stage):
    f=ready()
    for _ in range(stage):pass_stage(f)
    return f
def pin(p):
    b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
old=[json.loads(x) for x in (R/basepath).read_text().splitlines()][13]
packet=Path('Build')/L/'texture-ladder-overlay.jsonl';row=json.loads((R/packet).read_text());c=row['implementation']['task']['contract']
for key in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
    check(row[key]==old[key],'original '+key)
check(row['implementation']['events']==old['implementation']['events']==[],'no128contact invention')
check([(x['voicing'],x['register'],x['dynamic'],x['rhythm']) for x in c['source_ladder']]==list(m.LEVELS),'six exact table rows')
check([x['bars'] for x in c['source_ramp']]==[[1,2],[3,4],[5,6],[7,8],[9,10],[11,12]],'source12bar extent')
check(c['full_source_footer']==m.FOOTER,'whole footer')
check(c['source_progression']==['Cmaj7','Am7','Dm7','G7'],'progression')
for flag in ('automatic_evaluation','performance_observed','audio_supplied','recording_inspected','mastery_awarded','credit_awarded','persistence'):
    check(c[flag] is False,flag)
f=ready()
for stage in range(7):
    check(f.stage==stage,'ordered source stage')
    initial=f.token();f.begin(initial)
    refuse(f,lambda:f.begin(initial),'duplicate begin')
    refuse(f,lambda:f.report(f.token(),response(f)),'report without release')
    refuse(f,lambda:f.release(f.token(),False),'release false')
    for bpm in (73,70):
        q=plan();q['bpm']=bpm;refuse(f,lambda q=q:f.set_plan(f.token(),q),'active tempo/plan change')
    f.release(f.token(),True);q=plan();q['bpm']=73
    refuse(f,lambda:f.set_plan(f.token(),q),'held report tempo change')
    token=f.token();r=response(f);f.report(token,r)
    r['notes']='external mutation';check(f.history[-1]['data']['response']['notes']!='external mutation','response custody')
    refuse(f,lambda:f.report(token,response(f)),'duplicate report')
    check(not f.history[-1]['data']['performance_verified'] and not f.history[-1]['data']['recording_inspected'],'manual evidence only')
    f.advance(f.token());check(f.plan['bpm']==72,'unchanged chosen external tempo')
check(f.state=='completed','seven-stage completion')
history=deepcopy(f.history);q=plan();q['bpm']=80;f.set_plan(f.token(),q)
check(f.stage==0 and f.state=='ready' and f.history[:-1]==history,'new plan resets stage retains history')
q['bpm']=81;check(f.plan['bpm']==80,'plan custody')
for stage in range(7):
    names=list(m.LADDER_REPORTS if stage<6 else m.RAMP_REPORTS)+[f'coverage{i}' for i in range(4 if stage<6 else 6)]
    for name in names:
        for value in ('no','uncertain'):
            g=at(stage);reporting(g);r=response(g)
            if name.startswith('coverage'):r['coverage'][int(name[-1])]['covered']=value
            else:r['obligations'][name]=value
            g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'negative or uncertain retained')
            refuse(g,lambda:g.advance(g.token()),'unsatisfied source obligation')
            refuse(g,lambda:g.begin(g.token()),'retry must be explicit')
            g.retry(g.token(),'Isolate and repeat source duty.');check(g.stage==stage,'retry same scope')
            pass_stage(g);check(g.stage==min(stage+1,6),'retry can complete source duty')
# Shape and ownership guards including all missing external prerequisites.
f=m.TextureFlow();valid=plan();bads=[]
def bad(label,fn):
    q=deepcopy(valid);fn(q);bads.append((label,q))
for value in (0,-1,True,float('nan'),float('inf'),10**1000,'72'):
    bad('invalid BPM',lambda q,value=value:q.__setitem__('bpm',value))
for k in valid['prerequisites']:bad('missing '+k,lambda q,k=k:q['prerequisites'].__setitem__(k,False))
bad('missing source level',lambda q:q['ladder_realizations'].pop())
bad('level order',lambda q:q['ladder_realizations'][0].__setitem__('level',True))
bad('missing chord',lambda q:q['ladder_realizations'][0]['chords'].pop())
bad('wrong chord',lambda q:q['ladder_realizations'][0]['chords'][0].__setitem__('source_chord','C7'))
bad('blank realization',lambda q:q['ladder_realizations'][0]['chords'][0].__setitem__('realization',''))
bad('blank preparation',lambda q:q['ladder_realizations'][0].__setitem__('isolated_variable_preparation',''))
bad('wrong block bars',lambda q:q['ramp_blocks'][0].__setitem__('bars',[1,3]))
bad('wrong texture',lambda q:q['ramp_blocks'][0].__setitem__('source_texture','full comping'))
bad('no register',lambda q:q['ramp_blocks'][0].__setitem__('chosen_register',''))
bad('no loudness plan',lambda q:q.__setitem__('ramp_loudness_plan',''))
bad('only eleven bars',lambda q:q['bar_allocation'].pop())
bad('wrong bar',lambda q:q['bar_allocation'][0].__setitem__('bar',True))
bad('wrong progression order',lambda q:q['bar_allocation'][1].__setitem__('progression_positions',[3]))
bad('bad progression position',lambda q:q['bar_allocation'][0].__setitem__('progression_positions',[True]))
bad('bad ending extent',lambda q:q['bar_allocation'][-1].__setitem__('progression_positions',[3]))
bad('no withinbar plan',lambda q:q['bar_allocation'][0].__setitem__('within_bar_placement',''))
for label,q in bads:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
q=plan()
# A distinct authored choice with two chords per bar proves bar placement is not hardcoded to one source mapping.
for i,b in enumerate(q['bar_allocation']):b['progression_positions']=[1,2] if i%2==0 else [3,4]
f.set_plan(f.token(),q);check(f.plan['bar_allocation']==q['bar_allocation'],'explicit alternative harmonic placement')
token=f.token()
for idx in range(7):
    forged=list(token);forged[idx]='foreign' if type(token[idx]) is str else 99
    refuse(f,lambda t=tuple(forged):f.begin(t),'forged ownership component')
refuse(f,lambda:f.begin(ready().token()),'other instance')
for stage in range(7):
    g=at(stage);reporting(g);before=deepcopy(g.history);oldplan=deepcopy(g.plan);oldtoken=g.token()
    g.cancel(oldtoken);g.reopen(g.token())
    refuse(g,lambda:g.begin(oldtoken),'pre-cancel callback')
    refuse(g,lambda:g.begin(g.token()),'reopen requires release')
    g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
    check(g.stage==stage and g.state=='ready' and g.history[:len(before)]==before and g.plan==oldplan,'interrupted scope/choice/history retained')
for kind in ('external_reference','self_report'):
    g=at(6);reporting(g);g.report(g.token(),response(g,kind));g.advance(g.token());check(g.state=='completed','recording source route')
g=at(6);reporting(g)
for recording in (None,{}, {'kind':'app_microphone','value':'anything'}, {'kind':'self_report','value':''}):
    r=response(g);r['recording']=recording;refuse(g,lambda r=r:g.report(g.token(),r),'recording absent or unsupported')
for field,value in [('notes',''),('coverage',[]),('obligations',{})]:
    r=response(g);r[field]=value;refuse(g,lambda r=r:g.report(g.token(),r),'incomplete ramp response')
g.report(g.token(),response(g));check(g.state=='reported','valid reply after refusal')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
    'seven_stage_synthetic_campaign':True,'source_events_invented':0,'packet':pin(packet),'base':pin(basepath),
    'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'recordings_inspected':0,'host_tempo_changes':0,'native_runs':0,'app_runs':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
