from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r51')
s=importlib.util.spec_from_file_location('progression',R/'Tools'/L/'progression_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i,kind='external_human'):
    root=m.PC[m.RAW[i][0]]
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},
      'provider':{'kind':kind,'full_reference':'Exact four printed source chords','omission_reference':'Exact first three printed chords' if m.literal(i) else None,'ready':True},
      'tonic_realization':{'sung_tonic_midi':60+root,'current_hand_context':'Declared hand position for synthetic fixture','nearest_basis':'Learner judges this voicing nearest in the declared context; not computed',
        'triad':[{'string':string,'fret':(root+offset-m.TUNING[string])%12} for string,offset in [('D',0),('G',4),('B',7)]]} if m.literal(i) else None}
def response(f):
    r={'key':m.RAW[f.index][0],'duties':dict.fromkeys(m.FIRST if f.phase==0 else m.SECOND,'yes'),'diagnosis':'','notes':'Synthetic manual report; no acoustic proof.'}
    if f.phase:r.update(chosen_triad=deepcopy(f.plan['tonic_realization']['triad']),attack_count=1)
    return r
def to_report(f,answers=None):
    f.begin(f.token(),True);f.end_listening(f.token(),True);f.release(f.token(),True)
    if f.phase==0:
        a=answers or {k:f.source_view()[k] for k in ('function','roman')}
        f.answer(f.token(),'function',a['function']);f.answer(f.token(),'roman',a['roman']);f.reveal(f.token())
    else:f.sung(f.token(),True);f.setup_target(f.token(),True);f.attempt_attack(f.token(),True);f.release(f.token(),True)
def report(f,r):
    if f.phase==0:f.report_dictation(f.token(),r)
    else:f.report_tonic(f.token(),r)
def ready(i,phase=0,kind='external_human'):
    f=m.ProgressionFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i,kind))
    if phase:to_report(f);report(f,response(f));f.next_pass(f.token())
    return f
def at_state(i,phase,state):
    f=ready(i,phase)
    if state=='ready':return f
    acts=[lambda:f.begin(f.token(),True),lambda:f.end_listening(f.token(),True),lambda:f.release(f.token(),True)]
    if phase==0:acts.extend([lambda:f.answer(f.token(),'function',f.source_view()['function']),lambda:f.answer(f.token(),'roman',f.source_view()['roman']),lambda:f.reveal(f.token())])
    else:acts.extend([lambda:f.sung(f.token(),True),lambda:f.setup_target(f.token(),True),lambda:f.attempt_attack(f.token(),True),lambda:f.release(f.token(),True)])
    for action in acts:
        action()
        if f.state==state:return f
    r=response(f)
    if state=='needs_retry':r['duties'][next(iter(r['duties']))]='uncertain';r['diagnosis']='Cannot confirm source hearing'
    report(f,r)
    if f.state==state:return f
    if state=='completed':f.finish(f.token());return f
    raise AssertionError('fixture '+state)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'progression-dictation-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][54:66]
scales={'C':['C','D','E','F','G','A','B'],'G':['G','A','B','C','D','E','F#'],'D':['D','E','F#','G','A','B','C#'],
 'A':['A','B','C#','D','E','F#','G#'],'E':['E','F#','G#','A','B','C#','D#'],'F':['F','G','A','Bb','C','D','E']}
roman_index={'I':0,'ii':1,'iii':2,'IV':3,'V':4,'vi':5,'vii dim':6};function_map={'I':'T','ii':'P','iii':'T','IV':'P','V':'D','vi':'T','vii dim':'D'}
check(len(rows)==12 and [r['package_key'] for r in rows]==list(m.KEYS),'all exact twelve keys')
check([i+1 for i in range(12) if m.literal(i)]==[1,2,3,8],'exact source terminal-I subset')
check(sum(len(r['implementation']['task']['contract']['ordered_harmonic_slots']) for r in rows)==48,'48 explicit harmonic tokens; no invented96')
for i,(row,old) in enumerate(zip(rows,base)):
    c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'harmonic slots not source note events')
    check(row['implementation']['task']['table_fields']==old['implementation']['task']['table_fields'],'original table fields retained')
    check(list(c['source_fields'].values())==list(m.RAW[i]),'full four printed fields')
    for slot in c['ordered_harmonic_slots']:
        idx=roman_index[slot['roman']];name=scales[m.RAW[i][0]][idx]+('m' if idx in (1,2,5) else 'dim' if idx==6 else '')
        check(slot['chord']==name and slot['function']==function_map[slot['roman']],'independent diatonic chord and function map')
        check(slot['onset'] is None and slot['duration'] is None,'untimed harmonic source slot')
    check(c['source_footer']=='Second pass: source performer omits the tonic chord at the end. Player sings the tonic root, then plays the nearest tonic triad without searching.','full footer')
    check(c['source_extent_header']=='12 PROGRESSIONS | 96 CHORD EVENTS' and c['source_heading']=='WRITE T-P-D-T SHAPE BEFORE ROMAN NUMERALS','literal extent/heading')
    check(c['secondary_literal_omission_available']==(i in (0,1,2,7)),'secondary availability not all-row fallback')
    check(row['contract_capabilities']['complete_manual_response_contract']==m.literal(i),'only four whole contracts complete')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    for kind in ('external_human','external_recording'):
        f=ready(i,kind=kind)
        for phase in range(2 if m.literal(i) else 1):
            script=f.source_view()['performed_chord_script'];check(script==m.RAW[i][1].split('-')[:4-phase],'exact source script')
            if phase and i in (2,7):check(script[-1]==m.RAW[i][0],'penultimate tonic retained; remove last only')
            refuse(f,lambda:f.next_pass(f.token()),'no premature pass');refuse(f,lambda:f.finish(f.token()),'no premature completion')
            for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'current source readiness')
            t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.set_plan(f.token(),plan(i,kind)),'active plan')
            f.end_listening(f.token(),True)
            if phase==0:refuse(f,lambda:f.answer(f.token(),'function',f.source_view()['function']),'listen release')
            else:refuse(f,lambda:f.sung(f.token(),True),'listen release before singing')
            f.release(f.token(),True)
            if phase==0:
                check('reference_answer' not in f.learner_view(),'withheld current answers');refuse(f,lambda:f.answer(f.token(),'roman',f.source_view()['roman']),'function before Roman')
                a=f.source_view();f.answer(f.token(),'function',a['function']);refuse(f,lambda:f.reveal(f.token()),'Roman also required');f.answer(f.token(),'roman',a['roman'])
                check('reference_answer' not in f.learner_view(),'explicit reveal required');f.reveal(f.token());check(f.learner_view()['reference_answer']['full_printed_chords']==script,'reference after commit/reveal')
            else:
                check(f.learner_view()['previously_revealed'] and f.learner_view()['prior_answers_retained'],'first-pass answer history not erased')
                refuse(f,lambda:f.setup_target(f.token(),True),'sing before setup');f.sung(f.token(),True);refuse(f,lambda:f.attempt_attack(f.token(),True),'setup before attack');f.setup_target(f.token(),True)
                t=f.token();f.attempt_attack(t,True);refuse(f,lambda:f.attempt_attack(t,True),'duplicate attack action');refuse(f,lambda:f.report_tonic(f.token(),response(f)),'attack release fence');f.release(f.token(),True)
            r=response(f);t=f.token();report(f,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','report custody')
            check(f.state=='reported' and f.history[-1]['data']['performance_verified'] is False,'manual not acoustic proof')
            if phase==0:
                refuse(f,lambda:f.report_dictation(t,response(f)),'duplicate primary report');refuse(f,lambda:f.finish(f.token()),'primary never whole completion')
                if m.literal(i):f.next_pass(f.token())
                else:
                    refuse(f,lambda:f.next_pass(f.token()),'non-I ending cannot omit non-tonic or add I')
                    check(f.source_view()['secondary_barrier'] is not None and c['secondary_source_prefix'] is None,'specific pending source condition')
            else:
                refuse(f,lambda:f.report_tonic(t,response(f)),'duplicate tonic report');refuse(f,lambda:f.next_pass(f.token()),'no third pass');f.finish(f.token());check(f.state=='completed','literal whole two-pass route')
        history=deepcopy(f.history);answers=deepcopy(f.answer_history);f.set_plan(f.token(),plan(i,kind))
        check(f.phase==0 and f.state=='ready' and f.ever_revealed and f.answer_history==answers and f.history[:len(history)]==history,'new plan resets current pass, retains ever-revealed/history')
    for phase in range(2 if m.literal(i) else 1):
        mutations=[]
        for duty in m.FIRST if phase==0 else m.SECOND:
            for value in ('no','uncertain'):mutations.append((duty,lambda r,duty=duty,value=value:r['duties'].update({duty:value})))
        if phase:
            for count in (0,2,7):mutations.append(('attack_count',lambda r,count=count:r.update(attack_count=count)))
        for label,mutate in mutations:
            f=ready(i,phase);to_report(f);r=response(f);mutate(r);refuse(f,lambda:report(f,r),'diagnosis for '+label)
            r['diagnosis']='Reported failure; retry same pass without searching';report(f,r);check(f.state=='needs_retry','failed self-report retained')
            refuse(f,lambda:f.finish(f.token()),'failure cannot complete');refuse(f,lambda:f.next_pass(f.token()),'failure cannot advance');refuse(f,lambda:f.retry(f.token(),''),'retry requires diagnosis')
            history=deepcopy(f.answer_history);f.retry(f.token(),'Explicit retry');check(f.state=='ready' and f.phase==phase and f.answer_history==history,'retry same pass with history');to_report(f);report(f,response(f));check(f.state=='reported','retry manual success')
        f=ready(i,phase);to_report(f)
        for field,value in [('key','wrong'),('notes','')]+([('attack_count',True),('attack_count',-1),('attack_count',1.0),('attack_count','1')] if phase else []):
            r=response(f);r[field]=value;refuse(f,lambda:report(f,r),'typed bound response '+field)
        r=response(f);r['duties'][next(iter(r['duties']))]=True;refuse(f,lambda:report(f,r),'explicit yes/no/uncertain')
        if phase:
            r=response(f);r['chosen_triad'][0]['fret']+=1;refuse(f,lambda:report(f,r),'chosen triad response binding')
        states=('ready','listening','listening_release','reported','needs_retry')+(('answer_function','answer_roman','committed','dictation_report') if phase==0 else ('sing_tonic','silent_setup','attack','attack_release','tonic_report','completed'))
        for state in states:
            f=at_state(i,phase,state);check(f.state==state,'cancel fixture');p=deepcopy(f.plan);h=deepcopy(f.history);a=deepcopy(f.answer_history);e=f.ever_revealed;t=f.token()
            f.cancel(t);refuse(f,lambda:f.cancel(t),'duplicate cancel');f.reopen(f.token());f.cancel(f.token());f.reopen(f.token())
            refuse(f,lambda:f.begin(f.token(),True),'reopen release');refuse(f,lambda:f.release(f.token(),1),'release bool');f.release(f.token(),True)
            expected=state if state in ('ready','reported','needs_retry','completed') else 'ready'
            check(f.state==expected and f.phase==phase and f.plan==p and f.history[:len(h)]==h and f.answer_history==a and f.ever_revealed==e,'cancel/reopen exact pass and provenance')
            refuse(f,lambda:f.begin(t,True),'stale pre-cancel token')
    for kind in ('function','roman'):
        f=ready(i);a={k:f.source_view()[k] for k in ('function','roman')};domain=('T','P','D') if kind=='function' else m.ROMANS
        a[kind][0]=next(x for x in domain if x!=a[kind][0]);to_report(f,a);r=response(f);refuse(f,lambda:report(f,r),'wrong symbolic sequence diagnosis');r['diagnosis']='Typed sequence disagrees with printed reference';report(f,r)
        check(f.state=='needs_retry' and f.history[-1]['data']['symbolic_matches'][kind] is False,'wrong sequence not replaced')
    mutations=[('app audio',lambda p:p['provider'].update(kind='app_audio')),('provider readiness',lambda p:p['provider'].update(ready=False)),('reference',lambda p:p['provider'].update(full_reference=''))]
    for field in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
    if m.literal(i):
        mutations.extend([('omission reference',lambda p:p['provider'].update(omission_reference=None)),('tonic plan absent',lambda p:p.update(tonic_realization=None)),
          ('wrong sung root',lambda p:p['tonic_realization'].update(sung_tonic_midi=p['tonic_realization']['sung_tonic_midi']+1)),('bool root',lambda p:p['tonic_realization'].update(sung_tonic_midi=True)),
          ('root bound',lambda p:p['tonic_realization'].update(sung_tonic_midi=128)),('hand context',lambda p:p['tonic_realization'].update(current_hand_context='')),('nearest basis',lambda p:p['tonic_realization'].update(nearest_basis='')),
          ('wrong chord tone',lambda p:p['tonic_realization']['triad'][0].update(fret=(p['tonic_realization']['triad'][0]['fret']+1)%12)),
          ('same string',lambda p:p['tonic_realization']['triad'].__setitem__(1,deepcopy(p['tonic_realization']['triad'][0]))),
          ('fret bool',lambda p:p['tonic_realization']['triad'][0].update(fret=True)),('fret negative',lambda p:p['tonic_realization']['triad'][0].update(fret=-1)),
          ('fret high',lambda p:p['tonic_realization']['triad'][0].update(fret=25)),('invalid string',lambda p:p['tonic_realization']['triad'][0].update(string='x'))])
    else:mutations.extend([('invented second reference',lambda p:p['provider'].update(omission_reference='Unprinted tonic ending')),('invented secondary plan',lambda p:p.update(tonic_realization={}))])
    for label,mutate in mutations:
        f=ready(i);p=plan(i);mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
    for state,kind in [('answer_function','function'),('answer_roman','roman')]:
        f=at_state(i,0,state);v=f.source_view()[kind]
        for bad in (v[:-1],v+v[:1],tuple(v),[True]*4,['wrong']*4):refuse(f,lambda bad=bad:f.answer(f.token(),kind,bad),'typed four-element sequence')
    f=ready(i);g=ready(i);refuse(f,lambda:f.begin(g.token(),True),'foreign instance');t=f.token();p=plan(i);f.set_plan(f.token(),p);p['provider']['full_reference']='outside';check(f.plan['provider']['full_reference']!='outside','plan custody');refuse(f,lambda:f.begin(t,True),'stale generation')
    v=f.source_view();v['full_printed_chords'][0]='wrong';check(f.source_view()['full_printed_chords'][0]!='wrong','source view custody')
    if m.literal(i):
        p=plan(i);p['tonic_realization']['sung_tonic_midi']-=12
        for contact in p['tonic_realization']['triad']:contact['fret']+=12
        f.set_plan(f.token(),p);check(f.plan==p,'alternative authored octaves/frets accepted without source claims')
check(sum(r['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT' for r in rows)==4 and sum(r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING' for r in rows)==8,'four complete/eight actionable partial, no conflict adoption')
f=m.ProgressionFlow(m.KEYS[0]);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup','unconfigured cancellation')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'progression_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
