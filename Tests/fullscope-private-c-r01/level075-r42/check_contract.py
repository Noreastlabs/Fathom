from pathlib import Path
from copy import deepcopy
import datetime,hashlib,json,resource,sys
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r42')
sys.path.insert(0,str(R/'Tools'/L));import ladder_contract as m
checks=refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def refuse(f,fn,label):
    global refusals
    prior=deepcopy(f.__dict__)
    try:fn()
    except m.Refusal:refusals+=1
    else:raise AssertionError('accepted '+label)
    check(f.__dict__==prior,'atomic refusal '+label)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def plan():
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':72,
        'cue_provision':{'mode':'written_chart','description':'Self-directed source chart cues, no app playback.'},
        'bars':[{'bar':b['bar'],'source_chord':b['source_chord'],**{k:'learner realization for '+k for k in m.CHOICES}} for b in m.MASTER_BARS]}
def reporting(f):f.begin(f.token());f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):
    return {'source_pass':f.phase+1,'source_material':m.PASSES[f.phase][0],'source_primary_test':m.PASSES[f.phase][1],
        'bars':[{'bar':b['bar'],'source_chord':b['source_chord'],'traversed':'yes'} for b in m.MASTER_BARS],
        'common':dict.fromkeys(m.COMMON,'yes'),'material_duties':dict.fromkeys(m.MATERIAL_DUTIES[f.phase],'yes'),
        'incidents':[],'notes':'Synthetic manual report, not actual performance.'}
def ready(phase=0):
    f=m.LadderFlow();f.set_plan(f.token(),plan())
    for _ in range(phase):reporting(f);f.report(f.token(),response(f));f.advance(f.token())
    return f
def incident(cls,kind,handled='yes',n=1):return {'incident':n,'class':cls,'kind':kind,'bar':30,'handled_per_source':handled,'description':'Synthetic occurrence; action is learner self-report.'}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl');old=json.loads((R/basepath).read_text().splitlines()[53])
packet=Path('Build')/L/'rehearsal-ladder-overlay.jsonl';row=json.loads((R/packet).read_text());source=json.loads((R/'Build'/L/'source-check.json').read_text());c=row['implementation']['task']['contract']
for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'original '+k)
check(row['implementation']['events']==old['implementation']['events']==[],'no source note events invented')
check(c['fixed_source_contact_count'] is None and c['source_context_header']=='240 CONTACTS','no240invented contacts')
expected_material=['Speak chart + tap pulse','Roots only','Shells / triads','Written rhythm textures','Cues + fills','Dynamics + register','Lead / rhythm role changes','One uninterrupted take']
check([p['material'] for p in c['source_passes']]==expected_material,'independent eight-pass vector')
check(all(p['advance_when']=='no structural errors' for p in c['source_passes']),'source gate not generic perfection')
# Literal independent source form vector, including slash-bass spelling and Gmaj7 modulation.
expected_sections=[('Intro',1,4,['Cmaj7','Am7','Dm7','G7']),('Verse A',5,12,['Cmaj7','G/B','Am7','Em7','Fmaj7','C/E','Dm7','G7']),
 ('Pre-Chorus',13,16,['Am7','Em7','Fmaj7','G7']),('Chorus',17,24,['Cmaj7','G7','Am7','Fmaj7','Cmaj7','G7','Fmaj7','G7']),
 ('Verse B',25,32,['Cmaj7','G/B','Am7','Em7','Fmaj7','C/E','Dm7','G7']),('Bridge',33,40,['Am7','Fmaj7','Cmaj7','G7','Am7','Fmaj7','D7','G7']),
 ('Solo',41,48,['Dm7','G7','Cmaj7','Cmaj7','Am7','D7','Gmaj7','G7']),('Final Chorus',49,56,['Cmaj7','G7','Am7','Fmaj7','Cmaj7','G7','Fmaj7','G7']),
 ('Outro',57,60,['Cmaj7','Am7','Dm7','Cmaj7'])]
for p,e in zip(m.PROFILES,expected_sections):check((p['name'],p['start_bar'],p['end_bar'],p['chords'])==e,'independent master section/chord vector')
check([b['bar'] for b in m.MASTER_BARS]==list(range(1,61)),'complete master bar identity')
check(len(c['source_master_bars'])==60 and len(c['source_profiles'])==9,'full source context retained')
check('Simplify until function returns.' in c['source_error_hierarchy'] and c['source_finishing_footer'].endswith('restarting the first sixteen bars.'),'whole error/finishing instructions')
for flag in ('automatic_evaluation','performance_observed','audio_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):check(c[flag] is False,flag)
f=ready();refuse(f,lambda:f.advance(f.token()),'cannot skip initial pass')
for phase in range(8):
    check(f.phase==phase and f.state=='ready','source order');t=f.token();f.begin(t)
    check(f.history[-1]['data']['material']==expected_material[phase] and not f.history[-1]['data']['host_clock_used'],'source instructions not hostclock')
    refuse(f,lambda:f.begin(t),'duplicate begin');refuse(f,lambda:f.report(f.token(),response(f)),'report before end')
    refuse(f,lambda:f.release(f.token(),True),'end bypass');refuse(f,lambda:f.set_plan(f.token(),plan()),'active plan change')
    f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'before release');f.release(f.token(),True)
    t=f.token();r=response(f);f.report(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','report custody')
    refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.advance(f.token())
check(f.state=='completed' and f.phase==7,'all eight passes complete manually')
h=deepcopy(f.history);p=plan();p['bpm']=78;f.set_plan(f.token(),p);p['bars'][0]['root_realization']='outside'
check(f.phase==0 and f.state=='ready' and f.history[:-1]==h and f.plan['bars'][0]['root_realization']!='outside','new plan resets ladder and retains history')
for phase in range(8):
    for cls,(kinds,policy) in m.ERRORS.items():
        for kind in kinds:
            for handled in ('yes','no','uncertain'):
                g=ready(phase);reporting(g);r=response(g);r['incidents']=[incident(cls,kind,handled)];g.report(g.token(),r)
                expected=handled=='yes' and cls!='structural';check((g.state=='reported')==expected,'source-specific advancement policy')
                data=g.history[-1]['data'];check(data['reported_error_counts'][cls]==1 and data['response']==r,'diagnosis retained')
                check(data['incident_source_policies'][0]['source_policy']==policy and not data['performance_verified'],'policy reference not observed action')
                if not expected:refuse(g,lambda:g.advance(g.token()),'structural or unhandled error');g.retry(g.token(),'Repeat current pass after source repair.');check(g.phase==phase,'no whole-ladder reset')
                else:g.advance(g.token());check(g.phase==min(phase+1,7),'handled imperfection permits one-step advance')
    for group,names in (('common',m.COMMON),('material_duties',m.MATERIAL_DUTIES[phase])):
        for name in names:
            for value in ('no','uncertain'):
                g=ready(phase);reporting(g);r=response(g);r[group][name]=value;g.report(g.token(),r)
                check(g.state=='needs_retry','material duty required');refuse(g,lambda:g.advance(g.token()),'incomplete material')
    for bar in (0,29,59):
        for v in ('no','uncertain'):
            g=ready(phase);reporting(g);r=response(g);r['bars'][bar]['traversed']=v;g.report(g.token(),r);check(g.state=='needs_retry','full form required')
    for state in ('ready','performing','await_release','reporting','reported','needs_retry'):
        g=ready(phase)
        if state!='ready':g.begin(g.token())
        if state in ('await_release','reporting','reported','needs_retry'):g.end_take(g.token(),True)
        if state in ('reporting','reported','needs_retry'):g.release(g.token(),True)
        if state in ('reported','needs_retry'):
            r=response(g)
            if state=='needs_retry':r['incidents']=[incident('structural','lost form')]
            g.report(g.token(),r)
        check(g.state==state,'cancellation fixture');h=deepcopy(g.history);p=deepcopy(g.plan);t=g.token()
        g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t),'stale callback');refuse(g,lambda:g.begin(g.token()),'reopen release')
        g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.phase==phase and g.state==('ready' if state in ('performing','await_release','reporting') else state),'interrupted stage repeats')
        check(g.plan==p and g.history[:len(h)]==h,'diagnostic history/choice retained')
# Mixed incidents preserve every class; one structural error is sufficient to refuse.
g=ready(7);reporting(g);r=response(g);r['incidents']=[incident('functional','wrong chord quality',n=1),incident('cosmetic','weak articulation',n=2)]
g.report(g.token(),r);check(g.state=='reported','handled functional+cosmetic still finishable');g.advance(g.token());check(g.state=='completed','no invented perfection criterion')
h=deepcopy(g.history);g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True);check(g.state=='completed' and g.history[:len(h)]==h,'completed history retained')
g=ready(3);reporting(g);r=response(g);r['incidents']=[incident('functional','missed target',n=1),incident('structural','missed cue',n=2)]
g.report(g.token(),r);check(g.state=='needs_retry','one structural incident dominates advancement')
g=m.LadderFlow();g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True);check(g.state=='setup','empty-plan cancellation')
p=plan();mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,-1,True,'72',float('inf'),float('nan'),10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for k in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,k=k:q['prerequisites'].__setitem__(k,False))
bad('app cue invented',lambda q:q['cue_provision'].__setitem__('mode','app_audio'));bad('missing cue description',lambda q:q['cue_provision'].__setitem__('description',''))
bad('missing source bar',lambda q:q['bars'].pop());bad('changed source chord',lambda q:q['bars'][46].__setitem__('source_chord','G7'))
bad('boolean bar index',lambda q:q['bars'][0].__setitem__('bar',True))
for k in m.CHOICES:bad('missing material choice',lambda q,k=k:q['bars'][0].__setitem__(k,''))
for label,q in mutants:refuse(g,lambda q=q:g.set_plan(g.token(),q),label)
for mode in ('written_chart','partner','external_media'):
    q=plan();q['cue_provision']['mode']=mode;g.set_plan(g.token(),q);check(g.state=='ready','declared cue mode supported')
g=ready();t=g.token()
for i in range(7):
    a=list(t);a[i]='foreign' if type(t[i]) is str else 99;refuse(g,lambda a=tuple(a):g.begin(a),'ownership token')
refuse(g,lambda:g.begin(ready().token()),'foreign instance');reporting(g);p=response(g);mutants=[]
def bad_report(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
bad_report('wrong current pass',lambda q:q.__setitem__('source_pass',2));bad_report('wrong material',lambda q:q.__setitem__('source_material','Roots only'))
bad_report('missing primary test',lambda q:q.__setitem__('source_primary_test',''));bad_report('missing bar',lambda q:q['bars'].pop())
bad_report('changed source chord reply',lambda q:q['bars'][46].__setitem__('source_chord','G7'));bad_report('missing speak-chart duty',lambda q:q['material_duties'].pop('chart_spoken'))
bad_report('unknown source duty',lambda q:q['common'].__setitem__('pulse_and_tempo_held','verified'))
for label,q in mutants:refuse(g,lambda q=q:g.report(g.token(),q),label)
for field,value in [('incident',2),('class','timing'),('class',True),('kind','invented'),('kind','weak articulation'),('bar',0),('bar',61),('bar',True),('handled_per_source','verified'),('description','')]:
    r=response(g);r['incidents']=[incident('structural','lost form')];r['incidents'][0][field]=value
    refuse(g,lambda r=r:g.report(g.token(),r),'invalid incident '+field)
g.report(g.token(),response(g));check(g.state=='reported','valid current response after refusals')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
 'finite_existing_keys':1,'source_passes':8,'source_master_bars':60,'source_error_kinds':8,'source_contacts_invented':0,
 'packet':pin(packet),'base':pin(basepath),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'native_runs':0,'app_runs':0,'actual_performances':0}
p=R/'Results'/L/'integrity-final.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
