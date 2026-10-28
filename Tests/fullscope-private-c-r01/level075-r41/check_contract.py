from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r41')
s=importlib.util.spec_from_file_location('cell',R/'Tools'/L/'handoff_cell_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def plan():
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':70,
        'harmonic_slots':[{'source_order':i,'voicing_reference':'chosen rhythm voicing','articulation':'chosen attack'} for i in range(1,8)],
        'lead_contacts':[{'source_order':i,'source_pitch_class':pc,'string':'e','fret':f} for i,(pc,f) in enumerate(zip(('C','E','G','B','A','G','E','D','C'),(8,12,15,19,17,15,12,10,8)),8)],
        'bars':[{'source_bar':i,'chosen_onsets':q} for i,q in enumerate(([[0,1],[1,4],[1,2],[3,4]],[[0,1],[1,4],[1,2]],[[1,4],[3,8],[1,2],[5,8],[3,4],[7,8]],[[0,1],[1,8],[1,4]]),1)],
        'spacing_rationale':'Synthetic chosen realization; source display columns not interpreted as a fixed clock.'}
def ready(phase=0):
    f=m.HandoffCellFlow();f.set_plan(f.token(),plan())
    if phase:reporting(f);f.report(f.token(),response(f));f.advance(f.token())
    return f
def reporting(f):f.begin(f.token());f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):
    route=list(range(1,17)) if f.phase==0 else list(range(8,17))+list(range(1,8))
    return {'source_symbols':[{'performance_order':i,'source_order':n,'played':'yes'} for i,n in enumerate(route,1)],
        'duties':dict.fromkeys(m.COMMON+(m.REVERSE if f.phase else ()),'yes'),'notes':'Synthetic manual report only.'}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl');old=json.loads((R/basepath).read_text().splitlines()[60])
packet=Path('Build')/L/'handoff-cell-overlay.jsonl';row=json.loads((R/packet).read_text());source=json.loads((R/'Build'/L/'source-check.json').read_text())
c=row['implementation']['task']['contract'];events=row['implementation']['events']
for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'original '+k)
check(old['implementation']['events']==[] and len(events)==16,'source extraction omission repaired')
expected=[(1,i,'P') for i in (0,4,8,12)]+[(2,i,'P') for i in (0,4,8)]+[(3,i,p) for i,p in zip((4,6,8,10,12,14),('C','E','G','B','A','G'))]+[(4,i,p) for i,p in zip((0,2,4),('E','D','C'))]
check([b['body_width'] for b in source['matched_bars']]==[16,16,17,16],'exact original display widths')
for i,(event,expect) in enumerate(zip(events,expected),1):
    check((event['source_bar'],event['source_column_zero_based'],event['source_token'])==expect,'independent source coordinate/token vector')
    check(event['source_order']==i,'source order retained')
    check(source['matched_bars'][event['source_bar']-1]['body'][event['source_column_zero_based']]==event['source_token'],'original body coordinate')
    check(all(event[k] is None for k in ('octave','string','fret','midi','onset_q','duration_q','sounded_duration_q')),'source realization remains unspecified')
    check(event['is_rest'] is False,'P and named notes not rests')
check([e['pitch_class'] for e in events[7:]]==['C','E','G','B','A','G','E','D','C'],'nine exact named lead pitches')
check(all(e['pitch_class'] is None for e in events[:7]),'P has no invented chord/root')
check(c['source_footer'].endswith('entering the rhythm texture exactly on the next bar 1.'),'full wrapped reverse instruction')
check('intentional preparation, not missing material' in c['source_footer'],'intentional empty space retained')
check(not c['dash_tokens_converted_to_events'],'no tail hyphen event')
for flag in ('automatic_evaluation','performance_observed','audio_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):check(c[flag] is False,flag)
f=ready();refuse(f,lambda:f.advance(f.token()),'cannot skip forward')
for phase,route in ((0,list(range(1,17))),(1,list(range(8,17))+list(range(1,8)))):
    check([e['source_order'] for e in m.phase_events(phase)]==route,'reverse role blocks preserve internal note order')
    t=f.token();f.begin(t);check(f.history[-1]['data']['source_order_route']==route,'actual model route')
    refuse(f,lambda:f.begin(t),'duplicate begin');refuse(f,lambda:f.report(f.token(),response(f)),'report before end')
    refuse(f,lambda:f.release(f.token(),True),'release cannot bypass end');refuse(f,lambda:f.set_plan(f.token(),plan()),'active plan change')
    f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'report before release');f.release(f.token(),True)
    t=f.token();r=response(f);f.report(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','reply custody')
    refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.advance(f.token())
check(f.state=='completed','both roles reported')
saved=deepcopy(f.history);p=plan();p['bars'][2]['chosen_onsets']=[[1,8],[1,4],[3,8],[1,2],[5,8],[3,4]]
f.set_plan(f.token(),p);p['lead_contacts'][0]['fret']=9;check(f.state=='ready' and f.phase==0 and f.history[:-1]==saved and f.plan['lead_contacts'][0]['fret']==8,'different valid spacing resets phase and preserves choices')
for phase in (0,1):
    for kind,field in [('symbol',i) for i in range(16)]+[('duty',k) for k in m.COMMON+(m.REVERSE if phase else ())]:
        for value in ('no','uncertain'):
            g=ready(phase);reporting(g);r=response(g)
            if kind=='symbol':r['source_symbols'][field]['played']=value
            else:r['duties'][field]=value
            g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'every source obligation retained')
            refuse(g,lambda:g.advance(g.token()),'failed phase cannot advance');g.retry(g.token(),'Retry source sequence/preparation.');check(g.phase==phase,'retry same phase')
    for state in ('ready','performing','await_release','reporting','reported','needs_retry','completed'):
        if state=='completed' and phase==0:continue
        g=ready(phase)
        if state!='ready':g.begin(g.token())
        if state in ('await_release','reporting','reported','needs_retry','completed'):g.end_take(g.token(),True)
        if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
        if state in ('reported','needs_retry','completed'):
            r=response(g)
            if state=='needs_retry':r['duties']['pulse_and_tempo_held']='no'
            g.report(g.token(),r)
        if state=='completed':g.advance(g.token())
        check(g.state==state,'cancellation state');h=deepcopy(g.history);p=deepcopy(g.plan);t=g.token()
        g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t),'stale callback');refuse(g,lambda:g.begin(g.token()),'release fence')
        g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.state==('ready' if state in ('performing','await_release','reporting') else state) and g.phase==phase,'interrupted phase repeats')
        check(g.plan==p and g.history[:len(h)]==h,'source choices and prior reports retained')
# All six standard strings can realize each source pitch in a chosen octave.
for string,open_midi in m.TUNING.items():
    p=plan()
    for c in p['lead_contacts']:c['string']=string;c['fret']=(m.PC[c['source_pitch_class']]-open_midi)%12
    g=m.HandoffCellFlow();g.set_plan(g.token(),p);check(g.state=='ready','alternative chosen registers')
    for j in range(9):
        q=deepcopy(p);q['lead_contacts'][j]['fret']+=1;refuse(g,lambda q=q:g.set_plan(g.token(),q),'wrong printed pitch class')
g=m.HandoffCellFlow();p=plan();mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,-1,True,'70',float('inf'),float('nan'),10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for k in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,k=k:q['prerequisites'].__setitem__(k,False))
bad('missing harmonic slot',lambda q:q['harmonic_slots'].pop());bad('missing lead note',lambda q:q['lead_contacts'].pop())
bad('changed source pitch',lambda q:q['lead_contacts'][0].__setitem__('source_pitch_class','D'))
for k,v in [('source_order',True),('string','R'),('fret',True),('fret',-1),('fret',25)]:bad('invalid contact',lambda q,k=k,v=v:q['lead_contacts'][0].__setitem__(k,v))
bad('no voicing',lambda q:q['harmonic_slots'][0].__setitem__('voicing_reference',''))
bad('no articulation',lambda q:q['harmonic_slots'][0].__setitem__('articulation',''))
bad('missing bar',lambda q:q['bars'].pop());bad('missing onset',lambda q:q['bars'][2]['chosen_onsets'].pop())
bad('duplicate onset',lambda q:q['bars'][2]['chosen_onsets'].__setitem__(1,q['bars'][2]['chosen_onsets'][0]))
for bar,index,v in [(0,0,[1,4]),(1,2,[3,4]),(2,0,[0,1]),(3,2,[1,1]),(0,1,[True,4]),(0,1,[1,0]),(0,1,[1,-4])]:
    bad('chosen onset constraint',lambda q,bar=bar,index=index,v=v:q['bars'][bar]['chosen_onsets'].__setitem__(index,v))
bad('spacing rationale absent',lambda q:q.__setitem__('spacing_rationale',''))
for label,q in mutants:refuse(g,lambda q=q:g.set_plan(g.token(),q),label)
g=ready(1);t=g.token()
for i in range(7):
    a=list(t);a[i]='foreign' if type(t[i]) is str else 99;refuse(g,lambda a=tuple(a):g.begin(a),'token component')
refuse(g,lambda:g.begin(ready(1).token()),'foreign instance');reporting(g)
r=response(g);r['source_symbols'].reverse();refuse(g,lambda:g.report(g.token(),r),'reversing melody instead of role blocks')
r=response(g);r['duties'].pop('lead_ended_and_released_before_boundary');refuse(g,lambda:g.report(g.token(),r),'missing lead-release obligation')
r=response(g);r['source_symbols'][0]['source_order']=True;refuse(g,lambda:g.report(g.token(),r),'boolean source ordinal')
g.report(g.token(),response(g));g.advance(g.token());check(g.state=='completed','valid current reverse after refusals')
g=m.HandoffCellFlow();g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True);check(g.state=='setup','setup cancel/reopen')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
 'finite_existing_keys':1,'source_symbols':16,'harmonic_P_symbols':7,'named_pitch_class_occurrences':9,'forward_reverse_symbol_reports':32,
 'alternative_string_pitchclass_choices_tested':54,'source_notes_gates_or_timing_invented':0,'packet':pin(packet),'base':pin(basepath),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'native_runs':0,'app_runs':0,'actual_performances':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
