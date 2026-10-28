from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r52')
s=importlib.util.spec_from_file_location('guide',R/'Tools'/L/'guide_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i,octave=0):
    pitches=(m.ROOT[i],m.RAW[i][1],m.RAW[i][3])
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'shell_form':'root_third_seventh',
      'sung_midi':{'guide1':60+m.PC[pitches[1]]+12*octave,'guide2':60+m.PC[pitches[2]]-12*octave},
      'shell_contacts':{role:{'string':string,'fret':(m.PC[pitch]-m.TUNING[string])%12+12*octave} for role,pitch,string in zip(m.ROLES,pitches,('D','G','B'))}}
def response(f):return {'chord':m.RAW[f.index][0],'source_guides':m.source_guides(f.index),'chosen_contacts':deepcopy(f.plan['shell_contacts']),
  'attack_count':1,'duties':dict.fromkeys(m.DUTIES,'yes'),'diagnosis':'','notes':'Synthetic singing/shell self-report, no sound inspected.'}
def ready(i,octave=0):
    f=m.GuideFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i,octave));return f
def to_report(f):
    f.begin(f.token(),True);f.cue_read(f.token(),True);f.sing_guide(f.token(),1,True);f.sing_guide(f.token(),2,True)
    f.setup_target(f.token(),True);f.attempt_attack(f.token(),True);f.release(f.token(),True)
def at_state(i,state):
    f=ready(i)
    if state=='ready':return f
    acts=[lambda:f.begin(f.token(),True),lambda:f.cue_read(f.token(),True),lambda:f.sing_guide(f.token(),1,True),lambda:f.sing_guide(f.token(),2,True),
      lambda:f.setup_target(f.token(),True),lambda:f.attempt_attack(f.token(),True),lambda:f.release(f.token(),True)]
    for action in acts:
        action()
        if f.state==state:return f
    r=response(f)
    if state=='needs_retry':r['duties']['guide1_sung_correct']='uncertain';r['diagnosis']='Could not establish reliable reference'
    f.report(f.token(),r)
    if f.state==state:return f
    if state=='completed':f.finish(f.token());return f
    raise AssertionError('fixture '+state)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'sung-guide-shell-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()]
chords=['Cmaj7','Dm7','G7','Fmaj7','AmMaj7','Bm7b5','E7','Dm7'];roots=[0,2,7,5,9,11,4,2]
guides=[(4,11),(5,0),(11,5),(9,4),(0,8),(2,9),(8,2),(5,0)];roles=[('3','7'),('b3','b7'),('3','b7'),('3','7'),('b3','7'),('b3','b7'),('3','b7'),('b3','b7')]
offset={'3':4,'b3':3,'7':11,'b7':10}
check(len(rows)==8 and [r['package_key'] for r in rows]==list(m.KEYS),'exact eight unquarantined identities')
for i,row in enumerate(rows):
    old=base[m.SPEC[i][3]-1];c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'no fixed source notes/events')
    check(row['implementation']['task']['table_fields']==old['implementation']['task']['table_fields'],'old annotation-overlap raw preserved')
    fields=c['source_fields'];check(fields['Chord']==chords[i] and fields['Task']=='sing both -> play shell','exact chord/task')
    check((fields['Role 1'],fields['Role 2'])==roles[i] and (m.PC[fields['Guide 1']],m.PC[fields['Guide 2']])==guides[i],'independent source pitch/role pair')
    check(tuple((g-roots[i])%12 for g in guides[i])==tuple(offset[r] for r in roles[i]),'independent third/seventh quality arithmetic')
    check(c['source_role_tokens_are_rests'] is False and c['source_fixed_octave_fret_timing'] is None and c['source_page_extent']=='10 VOICES | 60 SUNG TARGETS','source roles not rests and no heading-derived extra notes')
    if i in (3,7):check(row['implementation']['task']['source_field_recovery']['identity_changed'] is False and '-r6/' in row['package_key'],'recovered row6 does not touch row5 identity')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    for octave in (0,1):
        f=ready(i,octave);v=f.view();check(v['guides']==m.source_guides(i) and v['selected_shell_omits_fifth'] and not v['whole_chord_quality_automatically_verified'],'source guide view and fifth limitation')
        refuse(f,lambda:f.finish(f.token()),'no early completion')
        for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'current readiness')
        t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.set_plan(f.token(),plan(i,octave)),'active plan')
        refuse(f,lambda:f.sing_guide(f.token(),1,True),'cue first');f.cue_read(f.token(),True)
        refuse(f,lambda:f.sing_guide(f.token(),2,True),'guide1 before guide2');refuse(f,lambda:f.setup_target(f.token(),True),'sing before hand')
        t=f.token();f.sing_guide(t,1,True);refuse(f,lambda:f.sing_guide(t,1,True),'duplicate guide1')
        refuse(f,lambda:f.setup_target(f.token(),True),'both guides before hand');refuse(f,lambda:f.attempt_attack(f.token(),True),'both guides before attack')
        f.sing_guide(f.token(),2,True);refuse(f,lambda:f.attempt_attack(f.token(),True),'setup before attack');f.setup_target(f.token(),True)
        t=f.token();f.attempt_attack(t,True);refuse(f,lambda:f.attempt_attack(t,True),'duplicate attack');refuse(f,lambda:f.report(f.token(),response(f)),'physical release before report');refuse(f,lambda:f.release(f.token(),1),'release bool')
        f.release(f.token(),True);r=response(f);t=f.token();f.report(t,r);r['chosen_contacts']['root']['fret']=99
        check(f.state=='reported' and f.history[-1]['data']['response']['chosen_contacts']['root']['fret']!=99,'report custody')
        check(f.history[-1]['data']['performance_verified'] is False and f.history[-1]['data']['whole_chord_quality_verified'] is False,'no acoustic/full-quality proof')
        refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.finish(f.token());check(f.state=='completed','all eight chosen realization routes')
        history=deepcopy(f.history);f.set_plan(f.token(),plan(i));check(f.state=='ready' and f.history[:len(history)]==history,'new plan preserves history')
    mutations=[]
    for duty in m.DUTIES:
        for value in ('no','uncertain'):mutations.append((duty,lambda r,duty=duty,value=value:r['duties'].update({duty:value})))
    for count in (0,2,7):mutations.append(('actual count',lambda r,count=count:r.update(attack_count=count)))
    for label,mutate in mutations:
        f=ready(i);to_report(f);r=response(f);mutate(r);refuse(f,lambda:f.report(f.token(),r),'failure diagnosis '+label)
        r['diagnosis']='Reported issue; isolate reference/setup without searching and repeat';f.report(f.token(),r);check(f.state=='needs_retry','failed report retained')
        refuse(f,lambda:f.finish(f.token()),'failure cannot complete');refuse(f,lambda:f.retry(f.token(),''),'explicit retry diagnosis');f.retry(f.token(),'Repeat full row after diagnosis');to_report(f);f.report(f.token(),response(f));check(f.state=='reported','manual retry can complete')
    f=ready(i);to_report(f)
    for field,value in [('chord','wrong'),('notes',''),('attack_count',True),('attack_count',-1),('attack_count',1.0),('attack_count','1')]:
        r=response(f);r[field]=value;refuse(f,lambda:f.report(f.token(),r),'typed bound response '+field)
    for field in ('pitch_class','role'):
        r=response(f);r['source_guides'][0][field]='wrong';refuse(f,lambda:f.report(f.token(),r),'source guide binding')
    r=response(f);r['chosen_contacts']['guide1']['fret']+=1;refuse(f,lambda:f.report(f.token(),r),'chosen contact binding')
    r=response(f);r['duties']['no_searching']=True;refuse(f,lambda:f.report(f.token(),r),'explicit outcome enum')
    for state in ('ready','read_cue','sing_guide1','sing_guide2','silent_setup','attack','await_release','reporting','reported','needs_retry','completed'):
        f=at_state(i,state);check(f.state==state,'cancellation fixture');p=deepcopy(f.plan);h=deepcopy(f.history);t=f.token();f.cancel(t)
        refuse(f,lambda:f.cancel(t),'duplicate cancel');f.reopen(f.token());f.cancel(f.token());f.reopen(f.token());refuse(f,lambda:f.begin(f.token(),True),'reopen release');f.release(f.token(),True)
        expected=state if state in ('ready','reported','needs_retry','completed') else 'ready'
        check(f.state==expected and f.plan==p and f.history[:len(h)]==h,'cancel/reopen source/plan/history custody');refuse(f,lambda:f.begin(t,True),'stale pre-cancel action')
    planmut=[('wrong shell form',lambda p:p.update(shell_form='full_triad')),('untyped sung note',lambda p:p['sung_midi'].update(guide1=True)),
      ('wrong sung pitch',lambda p:p['sung_midi'].update(guide2=p['sung_midi']['guide2']+1)),('sung bound',lambda p:p['sung_midi'].update(guide1=128)),
      ('missing guide',lambda p:p['sung_midi'].pop('guide2')),('extra contact',lambda p:p['shell_contacts'].update(fifth={'string':'E','fret':0}))]
    for field in ('own_instrument','original_workbook'):planmut.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
    for role in m.ROLES:
        planmut.extend([('wrong role pitch',lambda p,role=role:p['shell_contacts'][role].update(fret=(p['shell_contacts'][role]['fret']+1)%12)),
          ('bad string',lambda p,role=role:p['shell_contacts'][role].update(string='x')),('fret bool',lambda p,role=role:p['shell_contacts'][role].update(fret=True)),
          ('negative fret',lambda p,role=role:p['shell_contacts'][role].update(fret=-1)),('fret high',lambda p,role=role:p['shell_contacts'][role].update(fret=25))])
    def same_string(p):
        p['shell_contacts']['guide2']={'string':p['shell_contacts']['guide1']['string'],'fret':(guides[i][1]-m.TUNING[p['shell_contacts']['guide1']['string']])%12}
    planmut.append(('different pitches on same string cannot sound selected shell together',same_string))
    for label,mutate in planmut:
        f=ready(i);p=plan(i);mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
    f=ready(i);g=ready(i);refuse(f,lambda:f.begin(g.token(),True),'foreign instance');t=f.token();p=plan(i);f.set_plan(f.token(),p);p['shell_contacts']['root']['fret']=99;check(f.plan['shell_contacts']['root']['fret']!=99,'plan custody');refuse(f,lambda:f.begin(t,True),'stale generation')
    v=f.view();v['guides'][0]['pitch_class']='wrong';v['chosen_realization']['sung_midi']['guide1']=0;check(f.view()['guides'][0]['pitch_class']!='wrong' and f.plan['sung_midi']['guide1']!=0,'view custody')
f=ready(0)
for key in ('exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7','exercise-completeness-r01/level077/modulec/p007-supplement01/majoriivivoiceleading','exercise-completeness-r01/level077/modulec/p008-supplement01/minoriivivoiceleading'):
    refuse(f,lambda key=key:m.GuideFlow(key),'quarantines and separate supplements excluded')
check(rows[4]['implementation']['task']['contract']['source_fields']['Guide 2']=='G#' and rows[4]['implementation']['task']['contract']['source_fields']['Role 2']=='7','minor-major raised seventh retained')
check('Bm7b5'==rows[5]['implementation']['task']['contract']['source_fields']['Chord'] and ready(5).view()['selected_shell_omits_fifth'],'half-diminished label retained with fifth omission limitation')
f=m.GuideFlow(m.KEYS[0]);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup','unconfigured cancellation')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'guide_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
