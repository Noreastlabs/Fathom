from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r39')
s=importlib.util.spec_from_file_location('transition',R/'Tools'/L/'transition_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def refuse(f,fn,label):
    global refusals
    old=deepcopy(f.__dict__)
    try:fn()
    except m.Refusal:refusals+=1
    else:raise AssertionError('accepted '+label)
    check(old==f.__dict__,'atomic refusal '+label)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def plan(route=0,old=None,new=None):
    a=m.ROWS[route];old=old or m.ALIASES[a[4]][0];new=new or m.ALIASES[a[5]][0]
    context=m.context_for(route,old,new)
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':76,'meter':'Learner chosen4/4',
        'route':route,'old_profile':old,'new_profile':new,'provider':{'kind':'human','reference':'Synthetic external partner','can_cue_during_old_attacks':True},
        'priority_order':[m.KEYS[i] for i in (0,1,3,4,5,7,2,6)],'chosen_loop_onsets':[[i,4] for i in range(8)],
        'context_bars':[{'context_bar':i,'source_chord':b['source_chord'],'voicing':'chosen voicing',
            'register':'chosen register per printed profile','articulation':'chosen articulation per printed profile',
            'dynamic':'chosen dynamic per printed profile','texture_realization':'chosen source texture'} for i,b in enumerate(context,1)]}
def ready(index=0,route=None):
    f=m.TransitionFlow(m.KEYS[index]);f.set_plan(f.token(),plan(min(index,7) if route is None else route));return f
def reporting(f):f.begin(f.token(),True);f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):
    return {'transitions':[{'iteration':i,'attacks':[{'attack':j,'played':'yes'} for j in range(1,9)],'cue_received_old_attack':3,
        'first_destination':dict.fromkeys(m.DEST,'yes')} for i in range(1,5 if f.phase==0 else 2)],
        'context_bars':[] if f.phase==0 else [{'bar':i,'source_chord':b['source_chord'],'played_to_plan':'yes'} for i,b in enumerate(f.plan['context_bars'],1)],
        'global':dict.fromkeys(m.GLOBAL,'yes'),'notes':'Synthetic report only; no performance observed.'}
def phase_ready(index,phase):
    f=ready(index)
    if phase:reporting(f);f.report(f.token(),response(f));f.advance(f.token())
    return f
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
r13path=Path('Build/fullscope-private-c-r01/source-layout-r13/source-reconciliation-overlays.jsonl')
base=[json.loads(s) for s in (R/basepath).read_text().splitlines()];r13=[json.loads(s) for s in (R/r13path).read_text().splitlines()]
packet=Path('Build')/L/'transition-risk-overlay.jsonl';rows=[json.loads(s) for s in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
expected=[['Fmaj7','C/E','Dm7','G7','Am7','Em7','Fmaj7','G7'],['Am7','Em7','Fmaj7','G7','Cmaj7','G7','Am7','Fmaj7'],
 ['Cmaj7','G7','Fmaj7','G7','Cmaj7','G/B','Am7','Em7'],['Fmaj7','C/E','Dm7','G7','Am7','Fmaj7','Cmaj7','G7'],
 ['Am7','Fmaj7','D7','G7','Dm7','G7','Cmaj7','Cmaj7'],['Am7','D7','Gmaj7','G7','Cmaj7','G7','Am7','Fmaj7'],
 ['Cmaj7','G7','Fmaj7','G7','Cmaj7','Am7','Dm7','Cmaj7'],['Cmaj7','Cmaj7','Am7','D7','Gmaj7','G7','Cmaj7','G7']]
check(len(rows)==9 and [r['package_key'] for r in rows]==list(m.KEYS),'nine exact existing identities')
for i,row in enumerate(rows):
    old=r13[i-6] if i in (6,7) else base[43+i];c=row['implementation']['task']['contract']
    for field in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
        check(row[field]==old[field],'preserved original '+field)
    check(row['implementation']['events']==old['implementation']['events']==[],'source notes remain absent')
    if i in (6,7):
        check(row['source_reconciliation']==old['source_reconciliation'],'r13 source reconciliation unchanged')
        check(row['field_limitations'][0]==old['field_limitations'][0],'underlayer visibility limitation unchanged')
        check('visually occluded' in source['matched_risk_rows'][i]['visibility'],'no visible-source promotion')
    for slot in c['source_attack_slots']:
        check(all(slot[k] is None for k in ('pitch','fret','onset_q','duration_q','sounded_gate')),'no slot pitch/timing invention')
    check(len(c['source_attack_slots'])==8 and c['source_repeats']==4 and c['source_no_extra_count_in'],'full source loop')
    check(c['source_criterion'].endswith('Correct pitch with the wrong texture is still a missed section change.'),'full texture criterion')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):
        check(c[flag] is False,flag)
    f=ready(i);refuse(f,lambda:f.advance(f.token()),'cannot bypass first phase')
    for phase in (0,1):
        check(f.phase==phase and f.state=='ready','phase setup');t=f.token()
        refuse(f,lambda:f.begin(t,False),'provider not ready');f.begin(t,True)
        refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.report(f.token(),response(f)),'report before end')
        refuse(f,lambda:f.release(f.token(),True),'release cannot bypass end');refuse(f,lambda:f.set_plan(f.token(),plan(min(i,7))),'active plan change')
        f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'unreleased report');f.release(f.token(),True)
        t=f.token();r=response(f);f.report(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','response custody')
        refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.advance(f.token())
    check(f.state=='completed' and f.phase==1,'only manual two-phase completion')
    history=deepcopy(f.history);p=plan(min(i,7));p['chosen_loop_onsets']=[[0,1],[1,6],[1,3],[2,3],[1,1],[7,6],[3,2],[11,6]]
    f.set_plan(f.token(),p);p['context_bars'][0]['voicing']='outside'
    check(f.state=='ready' and f.phase==0 and f.history[:-1]==history and f.plan['context_bars'][0]['voicing']!='outside','new realization resets with history')
    for phase in (0,1):
        duties=[('global',k) for k in m.GLOBAL]+[('destination',k) for k in m.DEST]+[('attack',j) for j in range(8)]
        if phase:duties += [('bar',j) for j in range(8)]
        for kind,duty in duties:
            for v in ('no','uncertain'):
                g=phase_ready(i,phase);reporting(g);r=response(g)
                if kind=='global':r['global'][duty]=v
                elif kind=='destination':r['transitions'][-1]['first_destination'][duty]=v
                elif kind=='attack':r['transitions'][-1]['attacks'][duty]['played']=v
                else:r['context_bars'][duty]['played_to_plan']=v
                g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'failure in final loop/bar retained')
                refuse(g,lambda:g.advance(g.token()),'failed phase cannot advance');g.retry(g.token(),'Repeat source duty.');check(g.phase==phase,'retry same phase')
        for cue,success in ((0,False),(1,False),(2,False),(3,True),(4,True),(5,False),(None,False)):
            g=phase_ready(i,phase);reporting(g);r=response(g);r['transitions'][-1]['cue_received_old_attack']=cue;g.report(g.token(),r)
            check((g.state=='reported')==success,'old3/4 cue relation only, late/unknown retained')
        for state in ('ready','performing','await_release','reporting','reported','needs_retry','completed'):
            if state=='completed' and phase==0:continue
            g=phase_ready(i,phase)
            if state!='ready':g.begin(g.token(),True)
            if state in ('await_release','reporting','reported','needs_retry','completed'):g.end_take(g.token(),True)
            if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
            if state in ('reported','needs_retry','completed'):
                r=response(g)
                if state=='needs_retry':r['global']['pulse_held']='no'
                g.report(g.token(),r)
            if state=='completed':g.advance(g.token())
            check(g.state==state,'cancellation state');history=deepcopy(g.history);choice=deepcopy(g.plan);t=g.token()
            g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t,True),'stale prior phase');refuse(g,lambda:g.begin(g.token(),True),'reopen release fence')
            g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
            check(g.state==('ready' if state in ('performing','await_release','reporting') else state) and g.phase==phase,'reopen retains phase and restarts interrupted take')
            check(g.plan==choice and g.history[:len(history)]==history,'all prior choices/replies retained')

for route,oracle in enumerate(expected):
    for old in m.ALIASES[m.ROWS[route][4]]:
        for new in m.ALIASES[m.ROWS[route][5]]:
            f=m.TransitionFlow(m.KEYS[route]);p=plan(route,old,new);f.set_plan(f.token(),p)
            check([b['source_chord'] for b in p['context_bars']]==oracle,'independent chord vector across aliases')
            g=m.TransitionFlow(m.KEYS[8]);g.set_plan(g.token(),p);check(g.key==m.KEYS[8],'supplement exact route choice retains identity')
    c=m.context_for(route,m.ALIASES[m.ROWS[route][4]][0],m.ALIASES[m.ROWS[route][5]][0])
    if route==7:
        check([b['source_bar'] for b in c]==list(range(43,51)),'D7/Gmaj7 source window43–50')
        check(c[3]['source_chord']=='D7' and c[4]['source_chord']=='Gmaj7' and c[6]['source_profile']=='Final Chorus','exact harmonic target and source section crossing')
f=m.TransitionFlow(m.KEYS[0]);p=plan();mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,True,-1,float('inf'),float('nan'),'76',10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for k in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,k=k:q['prerequisites'].__setitem__(k,False))
for k,v in [('kind','app_audio'),('reference',''),('can_cue_during_old_attacks',False)]:bad('invalid provider',lambda q,k=k,v=v:q['provider'].__setitem__(k,v))
for k,v in [('route',1),('route',True),('old_profile','Chorus'),('new_profile','Outro'),('meter','')]:bad('wrong source route',lambda q,k=k,v=v:q.__setitem__(k,v))
bad('priority omission',lambda q:q['priority_order'].pop());bad('medium first',lambda q:q['priority_order'].reverse())
bad('priority duplicate',lambda q:q['priority_order'].__setitem__(1,q['priority_order'][0]))
bad('missing onset',lambda q:q['chosen_loop_onsets'].pop());bad('duplicate onset',lambda q:q['chosen_loop_onsets'].__setitem__(2,q['chosen_loop_onsets'][1]))
for i,v in [(0,[1,4]),(4,[5,4]),(3,[1,1]),(7,[2,1]),(1,[True,4]),(1,[1,0]),(1,[1,-4]),(1,0.25)]:bad('onset bound/shape',lambda q,i=i,v=v:q['chosen_loop_onsets'].__setitem__(i,v))
bad('missing context bar',lambda q:q['context_bars'].pop());bad('wrong context chord',lambda q:q['context_bars'][4].__setitem__('source_chord','C7'))
bad('boolean context ordinal',lambda q:q['context_bars'][0].__setitem__('context_bar',True))
for k in ('voicing','register','articulation','dynamic','texture_realization'):bad('missing realized duty',lambda q,k=k:q['context_bars'][0].__setitem__(k,''))
for label,q in mutants:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
f=ready();t=f.token()
for i in range(len(t)):
    x=list(t);x[i]='foreign' if type(t[i]) is str else 99;refuse(f,lambda x=tuple(x):f.begin(x,True),'ownership token component')
refuse(f,lambda:f.begin(ready().token(),True),'foreign instance');reporting(f)
p=response(f);mutants=[]
def bad_report(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
bad_report('only three loop iterations',lambda q:q['transitions'].pop())
bad_report('extra iteration',lambda q:q['transitions'].append(deepcopy(q['transitions'][0])))
bad_report('missing attack',lambda q:q['transitions'][0]['attacks'].pop())
bad_report('reordered attacks',lambda q:q['transitions'][0]['attacks'].reverse())
bad_report('bool cue',lambda q:q['transitions'][0].__setitem__('cue_received_old_attack',True))
bad_report('invalid cue',lambda q:q['transitions'][0].__setitem__('cue_received_old_attack',9))
bad_report('missing destination field',lambda q:q['transitions'][0]['first_destination'].pop('texture'))
bad_report('changed iteration ordinal',lambda q:q['transitions'][0].__setitem__('iteration',2))
bad_report('premature context report',lambda q:q['context_bars'].append({'bar':1,'source_chord':'Fmaj7','played_to_plan':'yes'}))
bad_report('no note',lambda q:q.__setitem__('notes',''))
for label,q in mutants:refuse(f,lambda q=q:f.report(f.token(),q),label)
f.report(f.token(),response(f));f.advance(f.token());reporting(f);r=response(f);r['context_bars'][0]['source_chord']='C7'
refuse(f,lambda:f.report(f.token(),r),'context report source substitution');f.report(f.token(),response(f));f.advance(f.token())
check(f.state=='completed','current correct two-phase report after refusals')
# Cancellation before any plan retains setup and requires a new source choice after release.
g=m.TransitionFlow(m.KEYS[0]);g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True);check(g.state=='setup' and g.plan is None,'setup cancellation')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
 'finite_existing_keys':9,'source_risk_routes':8,'source_contacts_invented':0,'abstract_source_attack_slots':72,
 'packet':pin(packet),'base':pin(basepath),'r13_reconciled':pin(r13path),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'native_runs':0,'app_runs':0,'audio_or_cues_supplied':0,'actual_performances':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
