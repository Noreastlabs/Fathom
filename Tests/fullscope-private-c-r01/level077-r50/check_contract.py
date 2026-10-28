from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r50')
s=importlib.util.spec_from_file_location('function',R/'Tools'/L/'function_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i,key='C',roman=None,form='shell_voicing'):
    return {'prerequisites':{'instrument_access':True,'original_workbook':True},
      'partner':{'kind':'external_human','reference':'Actual external partner placeholder in synthetic fixture','ready':True},
      'key':key,'source_roman':roman or m.ROMAN[i if i<7 else 0],'repeat_form':form,
      'presentation_descriptions':{'ordinary':'Partner supplies ordinary diatonic chord in declared key','repeat':'Partner supplies and confirms chosen repeat form in same function'}}
def expected(f):
    v=f.source_view();return {'family':v['compressed_family'],'roman':v['roman'],'chord':deepcopy(v['chord'])}
def reply(f):return {'key':f.plan['key'],'source_roman':f.plan['source_roman'],'presentation':f.form(),'duties':dict.fromkeys(m.DUTIES,'yes'),'diagnosis':'','notes':'Synthetic manual hearing/singing report; no acoustic proof.'}
def to_report(f,answers=None):
    f.begin(f.token(),True,True);f.end_listening(f.token(),True);f.release(f.token(),True)
    a=answers or expected(f)
    for kind in ('family','roman','chord'):f.answer(f.token(),kind,a[kind])
    f.reveal(f.token());f.sing_root(f.token(),True);f.sing_third(f.token(),True);f.resolve_tonic(f.token(),True);f.release(f.token(),True)
def ready(i,phase=0,key='C',roman=None,form='shell_voicing'):
    f=m.FunctionFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i,key,roman,form))
    if phase:to_report(f);f.report(f.token(),reply(f));f.next_presentation(f.token())
    return f
def at_state(i,phase,state):
    f=ready(i,phase)
    if state=='ready':return f
    acts=[lambda:f.begin(f.token(),True,True),lambda:f.end_listening(f.token(),True),lambda:f.release(f.token(),True),
      lambda:f.answer(f.token(),'family',expected(f)['family']),lambda:f.answer(f.token(),'roman',expected(f)['roman']),
      lambda:f.answer(f.token(),'chord',expected(f)['chord']),lambda:f.reveal(f.token()),lambda:f.sing_root(f.token(),True),
      lambda:f.sing_third(f.token(),True),lambda:f.resolve_tonic(f.token(),True),lambda:f.release(f.token(),True)]
    for action in acts:
        action()
        if f.state==state:return f
    r=reply(f)
    if state=='needs_retry':r['duties']['no_fret_shape_inference']='uncertain';r['diagnosis']='Could not confirm source of inference'
    f.report(f.token(),r)
    if f.state==state:return f
    if state=='completed':f.finish(f.token());return f
    raise AssertionError('fixture '+state)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'function-hearing-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()][46:54]
romans=['I','ii','iii','IV','V','vi','vii dim'];family=['tonic','predominant','tonic','predominant','dominant','tonic','dominant']
names={'C':['C','Dm','Em','F','G','Am','Bdim'],'G':['G','Am','Bm','C','D','Em','F#dim'],
  'D':['D','Em','F#m','G','A','Bm','C#dim'],'A':['A','Bm','C#m','D','E','F#m','G#dim'],
  'E':['E','F#m','G#m','A','B','C#m','D#dim'],'F':['F','Gm','Am','Bb','C','Dm','Edim']}
thirds={'C':['E','F','G','A','B','C','D'],'G':['B','C','D','E','F#','G','A'],
  'D':['F#','G','A','B','C#','D','E'],'A':['C#','D','E','F#','G#','A','B'],
  'E':['G#','A','B','C#','D#','E','F#'],'F':['A','Bb','C','D','E','F','G']}
check(len(rows)==8 and [r['package_key'] for r in rows]==list(m.KEYS),'eight existing keys')
for i,(row,old) in enumerate(zip(rows,base)):
    c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'source notes/time not invented')
    check(row['implementation']['task']['table_fields']==old['implementation']['task']['table_fields'],'original raw table retained')
    check(c['source_blind_instruction']=='Partner plays one diatonic chord in C, G, D, A, E, or F major. Answer function family first; Roman numeral second; chord name third.','full joined instruction')
    check(c['source_repeat_instruction']=='Do not infer function from fretboard shape. Repeat the test with rootless triads or shell voicings.','repeat and no-shape retained')
    check(c['harmonic_rest_is_silence'] is False and c['source_fixed_voicing_octave_timing'] is None,'harmonic rest not silence/no fixed realization')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    if i<7:check(c['source_fields']['Roman']==romans[i] and c['source_fields']['Sing after chord']=='root then 3rd' and c['source_fields']['Resolve']=='I','full table duties')
    if i==6:
        check(c['source_fields']=={'Roman':'vii dim','Family':'dominant','Functional sensation':'leading-tone tension','Sing after chord':'root then 3rd','Resolve':'I'},'exact recovered vii dim row')
        check(row['package_key'].endswith('/p005-t1-r8/viidim') and row['implementation']['task']['source_field_recovery']['identity_changed'] is False,'official r8 key unchanged')
    if i==7:check(len(c['source_fields'])==7 and row['implementation']['task']['prior_contract_correction']['base_jsonl_line']==54,'existing supplement corrected once')
    for key in names:
        targets=range(7) if i==7 else (i,)
        for target in targets:
            for form in ('rootless_triad','shell_voicing'):
                f=ready(i,key=key,roman=romans[target],form=form);v=f.source_view();suffix={'major':'','minor':'m','diminished':'dim'}[v['chord']['quality']]
                check(v['chord']['root']+suffix==names[key][target] and v['compressed_family']==family[target],'independent major-key function/chord derivation')
                check([x['role'] for x in v['sing_order']]==['root','third'] and v['sing_order'][1]['pitch_class']==thirds[key][target],'independent root/third order and derivation')
                check(v['resolution']['chord']=={'root':key,'quality':'major'} and v['resolution']['roman']=='I','tonic resolution')
                check(v['voicing_notes'] is None and v['sound_supplied_by_app'] is False,'external voicing source remains prerequisite')
                for phase in range(2):
                    view=f.learner_view();check('reference_answer' not in view and view['preset_roman_visible']==(romans[i] if i<7 else None),'no premature reference and honest preset disclosure')
                    if phase:check(view['previously_revealed'] is True and view['prior_answers_retained'] is True,'repeat never falsely unseen')
                    refuse(f,lambda:f.reveal(f.token()),'early reveal');refuse(f,lambda:f.next_presentation(f.token()),'early repeat');refuse(f,lambda:f.finish(f.token()),'early finish')
                    for a,b in ((False,True),(True,False),(1,True),(True,1)):refuse(f,lambda a=a,b=b:f.begin(f.token(),a,b),'current partner and form confirmation')
                    t=f.token();f.begin(t,True,True);refuse(f,lambda:f.begin(t,True,True),'duplicate begin')
                    refuse(f,lambda:f.set_plan(f.token(),plan(i,key,romans[target],form)),'active plan')
                    refuse(f,lambda:f.answer(f.token(),'family',family[target]),'answer before release');f.end_listening(f.token(),True)
                    refuse(f,lambda:f.answer(f.token(),'family',family[target]),'listening release fence');f.release(f.token(),True)
                    a=expected(f)
                    refuse(f,lambda:f.answer(f.token(),'roman',a['roman']),'family first')
                    t=f.token();f.answer(t,'family',a['family']);refuse(f,lambda:f.answer(t,'family',a['family']),'duplicate family')
                    refuse(f,lambda:f.answer(f.token(),'chord',a['chord']),'Roman second');f.answer(f.token(),'roman',a['roman'])
                    refuse(f,lambda:f.reveal(f.token()),'all three before reveal');f.answer(f.token(),'chord',a['chord'])
                    check('reference_answer' not in f.learner_view(),'explicit reveal, not automatic on commit');f.reveal(f.token())
                    check(f.learner_view()['reference_answer']==f.source_view() and f.ever_revealed,'reference revealed with script retained')
                    refuse(f,lambda:f.sing_third(f.token(),True),'root before third');f.sing_root(f.token(),True)
                    refuse(f,lambda:f.resolve_tonic(f.token(),True),'third before resolution');f.sing_third(f.token(),True);f.resolve_tonic(f.token(),True)
                    refuse(f,lambda:f.report(f.token(),reply(f)),'final release fence');f.release(f.token(),True)
                    r=reply(f);t=f.token();f.report(t,r);r['duties']['chord_heard']='no'
                    check(f.history[-1]['data']['response']['duties']['chord_heard']=='yes','report custody')
                    check(f.history[-1]['data']['acoustically_verified'] is False and f.history[-1]['data']['manual_requirements_reported'] is True,'manual completion not acoustic proof')
                    refuse(f,lambda:f.report(t,reply(f)),'duplicate report')
                    if phase==0:refuse(f,lambda:f.finish(f.token()),'repeat required');f.next_presentation(f.token());check(f.form()==form,'chosen literal source repeat alternative')
                    else:refuse(f,lambda:f.next_presentation(f.token()),'no third presentation');f.finish(f.token())
                check(f.state=='completed' and len(f.answer_history)==6,'all source answers preserved across two presentations')
                oldhistory=deepcopy(f.history);oldanswers=deepcopy(f.answer_history);f.set_plan(f.token(),plan(i,key,romans[target],form))
                check(f.phase==0 and f.state=='ready' and f.ever_revealed and not f.current_revealed and f.history[:len(oldhistory)]==oldhistory and f.answer_history==oldanswers,'reset retains provenance/reveal history')
    for phase in range(2):
        for duty in m.DUTIES:
            for value in ('no','uncertain'):
                f=ready(i,phase);to_report(f);r=reply(f);r['duties'][duty]=value
                refuse(f,lambda:f.report(f.token(),r),'manual failure needs diagnosis');r['diagnosis']='Specific reported failure, retry current presentation';f.report(f.token(),r)
                check(f.state=='needs_retry','failed report retained');refuse(f,lambda:f.next_presentation(f.token()),'failure blocks repeat');refuse(f,lambda:f.finish(f.token()),'failure blocks completion')
                oldhistory=deepcopy(f.answer_history);f.retry(f.token(),'Diagnose and repeat');check(f.phase==phase and f.ever_revealed and f.answer_history==oldhistory,'retry does not erase/reblind');to_report(f);f.report(f.token(),reply(f));check(f.state=='reported','retry can succeed manually')
        for kind in ('family','roman','chord'):
            f=ready(i,phase);a=expected(f)
            if kind=='family':a[kind]=next(x for x in ('tonic','predominant','dominant') if x!=a[kind])
            elif kind=='roman':a[kind]=next(x for x in romans if x!=a[kind])
            else:a[kind]['quality']=next(x for x in ('major','minor','diminished') if x!=a[kind]['quality'])
            to_report(f,a);r=reply(f);refuse(f,lambda:f.report(f.token(),r),'wrong typed answer needs diagnosis');r['diagnosis']='Symbolic answer disagreed with source reference';f.report(f.token(),r)
            check(f.state=='needs_retry' and f.history[-1]['data']['symbolic_matches'][kind] is False,'wrong typed response retained instead of hidden correction')
        f=ready(i,phase);to_report(f)
        for field,value in [('key','wrong'),('source_roman','wrong'),('presentation','wrong'),('notes','')]:
            r=reply(f);r[field]=value;refuse(f,lambda:f.report(f.token(),r),'report binding '+field)
        r=reply(f);r['duties']['chord_heard']=True;refuse(f,lambda:f.report(f.token(),r),'explicit manual outcome enum')
        for state in ('ready','listening','answer_release','answer_family','answer_roman','answer_chord','committed','sing_root','sing_third','resolve_tonic','report_release','reporting','reported','needs_retry')+(('completed',) if phase==1 else ()):
            f=at_state(i,phase,state);check(f.state==state,'cancel fixture');before=deepcopy(f.history);answers=deepcopy(f.answer_history);plan_before=deepcopy(f.plan);ever=f.ever_revealed;t=f.token()
            f.cancel(t);refuse(f,lambda:f.cancel(t),'duplicate cancel');f.reopen(f.token());f.cancel(f.token());f.reopen(f.token())
            refuse(f,lambda:f.begin(f.token(),True,True),'reopen release fence');refuse(f,lambda:f.release(f.token(),1),'release typed bool');f.release(f.token(),True)
            expected_state=state if state in ('ready','reported','needs_retry','completed') else 'ready'
            check(f.state==expected_state and f.phase==phase and f.plan==plan_before and f.answer_history==answers and f.ever_revealed==ever and f.history[:len(before)]==before,'cancel/reopen exact custody and presentation')
            refuse(f,lambda:f.begin(t,True,True),'cancel stale token')
    mutations=[('partner kind',lambda p:p['partner'].update(kind='app_audio')),('recording cannot replace specified partner',lambda p:p['partner'].update(kind='external_recording')),
      ('partner unavailable',lambda p:p['partner'].update(ready=False)),('partner reference',lambda p:p['partner'].update(reference='')),
      ('key not printed',lambda p:p.update(key='Bb')),('wrong Roman spelling',lambda p:p.update(source_roman='VII')),
      ('unknown form',lambda p:p.update(repeat_form='full_chord')),('description',lambda p:p['presentation_descriptions'].update(repeat=''))]
    for name in ('instrument_access','original_workbook'):mutations.append(('prerequisite',lambda p,name=name:p['prerequisites'].update({name:False})))
    if i<7:mutations.append(('different source row',lambda p:p.update(source_roman=romans[(i+1)%7])))
    for label,mutate in mutations:
        f=ready(i);p=plan(i);mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
    for state,kind,bad in [('answer_family','family','tonic family'),('answer_family','family',True),('answer_roman','roman','iv'),('answer_chord','chord',{'root':'H','quality':'major'}),('answer_chord','chord',{'root':'C','quality':'maj'})]:
        f=at_state(i,0,state);refuse(f,lambda:f.answer(f.token(),kind,bad),'typed answer domain')
    f=ready(i);other=ready(i);refuse(f,lambda:f.begin(other.token(),True,True),'foreign owner');t=f.token();p=plan(i);f.set_plan(f.token(),p);p['presentation_descriptions']['repeat']='outside';check(f.plan['presentation_descriptions']['repeat']!='outside','plan custody');refuse(f,lambda:f.begin(t,True,True),'stale plan')
    v=f.source_view();v['chord']['root']='H';check(f.source_view()['chord']['root']!='H','source view custody')
    f=at_state(i,0,'answer_roman');v=f.learner_view();v['learner_answers']['family']='wrong';check(f.learner_view()['learner_answers']['family']!='wrong','learner reply view custody')
# Typed enharmonic answers are symbolic pitch-class answers, not source spelling changes.
f=ready(7,key='G',roman='vii dim');a=expected(f);a['chord']['root']='Gb';to_report(f,a);f.report(f.token(),reply(f))
check(f.state=='reported' and f.history[-1]['data']['symbolic_matches']['chord'] and not f.history[-1]['data']['root_spelling_match'] and f.source_view()['chord']['root']=='F#','enharmonic manual answer preserves conventional reference spelling')
f=m.FunctionFlow(m.KEYS[-1]);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup','unconfigured cancellation')
check(rows[0]['implementation']['task']['contract']['source_fields']['Functional sensation']=='home / rest','harmonic rest retained as sensation')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'function_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
