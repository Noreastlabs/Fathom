from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r54')
s=importlib.util.spec_from_file_location('minor',R/'Tools'/L/'minor_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def contact(note):return next({'string':s,'fret':note-n} for s,n in m.TUNING.items() if 0<=note-n<=24)
def plan(octave=0):
    x=50+12*octave;y=57+12*octave
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'vocal_midi':{'lower':[x,x,x-2],'upper':[y,y-1,y-2],'resolution':[y-1,y]},
      'partner':{'kind':'external_human','reference':'External human source partner, synthetic fixture declaration',
        'chord_capabilities':{chord:{'reference':'Partner supplies '+chord+' without third','can_supply_without_third':True} for chord in m.CHORDS}},
      'dominant_realizations':{chord:{'sung_third_midi':60+m.PC[third]+12*octave,'contact':contact(60+m.PC[third]+12*octave)} for chord,third in zip(m.CHORDS,m.THIRDS)}}
def confirmation(f):return {'chord':m.CHORDS[f.stage-3],'ready':True,'third_omitted':True,'chord_held':True}
def release_reply(f):return {'learner_released':True,'partner_stopped':True if f.partner_release_required else None}
def response(f):
    r={'stage_id':f.cue()['stage_id'],'source_targets':f.cue()['targets'],'duties':dict.fromkeys(m.V_DUTIES if f.stage<3 else m.D_DUTIES,'yes'),
      'diagnosis':'','notes':'Synthetic manual hearing/singing/source-role report, no actual audio inspected.'}
    if f.stage>=3:r.update(chosen_contact=deepcopy(f.plan['dominant_realizations'][m.CHORDS[f.stage-3]]['contact']),attack_count=1)
    return r
def to_report(f):
    if f.stage<3:f.begin_vocal(f.token(),True);f.cue_read(f.token(),f.cue()['targets']);f.sing_line(f.token(),True)
    else:f.begin_dominant(f.token(),confirmation(f));f.heard_partial(f.token(),True);f.sing_third(f.token(),True);f.setup_target(f.token(),True);f.add_third(f.token(),True)
    f.end_take(f.token(),True);f.release(f.token(),release_reply(f))
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'minor-voiceleading-overlay.jsonl';row=json.loads((R/packet).read_text());old=json.loads((R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()[77]);c=row['implementation']['task']['contract']
check(row['package_key']==m.KEY,'one exact minor supplement')
for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
check(row['implementation']['events']==old['implementation']['events']==[] and row['implementation']['task']['table_fields']==old['implementation']['task']['table_fields'],'original raw and empty note events preserved')
check(c['printed_progression']==['Bm7b5','E7','Am7'] and c['printed_lower']==['D','D','C'] and c['printed_upper']==['A','G#','G'],'clean printed progression and guide voices')
check(c['printed_critical_descending']==c['printed_upper'] and c['printed_critical_resolution']==['G#','A'] and 'same performed upper-line route' in c['critical_descending_coverage'],'identical critical motion alias retains both references')
check(c['guide_role_context']=={'lower':['b3','b7','b3'],'upper':['b7','3','b7'],'critical_resolution':None},'explicit guide roles, no invented critical-resolution harmony')
for voice,role_values in [('lower',['b3','b7','b3']),('upper',['b7','3','b7'])]:
    for pitch,root,role in zip(c['printed_'+voice],[11,4,9],role_values):
        check((m.PC[pitch]-root)%12=={'b3':3,'3':4,'b7':10}[role],'independent minor guide role arithmetic')
check(c['source_dominant_instruction']=='Dominant test: partner plays E7 without its third. Player sings G# and adds it on the guitar. Repeat for A7, D7, G7, C7, and B7.','full source role and six-chord instruction')
roots=[4,9,2,7,0,11];thirds=['G#','C#','F#','B','E','D#']
for j,(root,third) in enumerate(zip(roots,thirds)):
    check(c['dominant_targets'][j]['third']==third and (m.PC[third]-root)%12==4,'independent major thirds')
    check((c['dominant_targets'][j]['authority']=='printed')==(j==0),'E7 printed versus five derived')
for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
cache={}
for octave in (0,1):
    f=m.MinorFlow(m.KEY);f.set_plan(f.token(),plan(octave))
    for stage in range(9):
        check(f.stage==stage and f.state=='ready','exact source stage order')
        if octave==0:cache[stage]=deepcopy(f)
        view=f.source_player_view();check(view['audio_supplied_by_app'] is False and view['actual_voicing_notes'] is None and not view['omission_acoustically_verified'],'external source claims remain manual')
        check(view['cue']['guide_roles']==(['b3','b7','b3'] if stage==0 else ['b7','3','b7'] if stage==1 else None if stage==2 else ['3']),'typed current guide-role cue')
        refuse(f,lambda:f.next_stage(f.token()),'no early next');refuse(f,lambda:f.finish(f.token()),'no early finish')
        if stage<3:
            refuse(f,lambda:f.begin_dominant(f.token(),{'chord':'E7','ready':True,'third_omitted':True,'chord_held':True}),'no forced partner in vocal route')
            for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin_vocal(f.token(),bad),'current readiness')
            t=f.token();f.begin_vocal(t,True);refuse(f,lambda:f.begin_vocal(t,True),'duplicate begin');refuse(f,lambda:f.set_plan(f.token(),plan()),'active vocal plan')
            refuse(f,lambda:f.sing_line(f.token(),True),'read source cue first');refuse(f,lambda:f.cue_read(f.token(),['wrong']),'exact target cue');f.cue_read(f.token(),f.cue()['targets'])
            refuse(f,lambda:f.setup_target(f.token(),True),'no invented solo guitar setup');f.sing_line(f.token(),True)
            check(f.partner_release_required is False,'vocal route has no partner audio ownership')
        else:
            refuse(f,lambda:f.begin_vocal(f.token(),True),'correct stage method')
            for field,value in [('chord','Awrong'),('ready',False),('third_omitted',False),('chord_held',False),('ready',1),('third_omitted',1)]:
                r=confirmation(f);r[field]=value;refuse(f,lambda:f.begin_dominant(f.token(),r),'source confirmation '+field)
            t=f.token();f.begin_dominant(t,confirmation(f));refuse(f,lambda:f.begin_dominant(t,confirmation(f)),'duplicate partner start')
            check(f.partner_release_required and not f.partner_stop_requested,'partner role remains held during hearing/addition')
            refuse(f,lambda:f.end_take(f.token(),True),'do not remove source before addition');refuse(f,lambda:f.sing_third(f.token(),True),'hear partial first');f.heard_partial(f.token(),True)
            refuse(f,lambda:f.setup_target(f.token(),True),'sing before hand setup');f.sing_third(f.token(),True);refuse(f,lambda:f.add_third(f.token(),True),'silent setup before attack');f.setup_target(f.token(),True)
            t=f.token();f.add_third(t,True);refuse(f,lambda:f.add_third(t,True),'duplicate added attack');check(f.partner_release_required and not f.partner_stop_requested,'partner chord retained until third addition')
        f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'physical/source release before report')
        check(f.partner_stop_requested==(stage>=3),'only dominant end requests partner stop')
        r=release_reply(f);r['learner_released']=False;refuse(f,lambda:f.release(f.token(),r),'learner physical release')
        r=release_reply(f);r['partner_stopped']=None if stage>=3 else True;refuse(f,lambda:f.release(f.token(),r),'explicit applicable source stop, no fake solo partner')
        f.release(f.token(),release_reply(f));check(not f.partner_release_required and not f.partner_stop_requested,'manual stop acknowledgement clears role obligation')
        r=response(f);t=f.token();f.report(t,r);r['source_targets'][0]='outside';check(f.history[-1]['data']['response']['source_targets'][0]!='outside','report custody')
        check(f.state=='reported' and f.history[-1]['data']['performance_verified'] is False and f.history[-1]['data']['source_omission_acoustically_verified'] is False,'self-report not acoustic proof')
        refuse(f,lambda:f.report(t,response(f)),'duplicate report')
        if stage<8:refuse(f,lambda:f.finish(f.token()),'all nine required');f.next_stage(f.token())
        else:refuse(f,lambda:f.next_stage(f.token()),'no tenth stage');f.finish(f.token())
    check(f.state=='completed' and sum(x['kind']=='report' for x in f.history)==9 and sum(x['kind']=='add_third' for x in f.history)==6,'nine stages, six attempted additions only')
    h=deepcopy(f.history);f.set_plan(f.token(),plan());check(f.stage==0 and f.state=='ready' and f.history[:len(h)]==h,'new plan resets with history')
for stage,ready in cache.items():
    modifications=[]
    for duty in m.V_DUTIES if stage<3 else m.D_DUTIES:
        for value in ('no','uncertain'):modifications.append((duty,lambda r,duty=duty,value=value:r['duties'].update({duty:value})))
    if stage>=3:
        for count in (0,2,7):modifications.append(('actual count',lambda r,count=count:r.update(attack_count=count)))
    for label,mutate in modifications:
        f=deepcopy(ready);to_report(f);r=response(f);mutate(r);refuse(f,lambda:f.report(f.token(),r),'failure needs diagnosis '+label)
        r['diagnosis']='Reported source/hearing/coordination problem, retry current stage';f.report(f.token(),r);check(f.state=='needs_retry','failed report retained')
        refuse(f,lambda:f.next_stage(f.token()),'failure blocks next');refuse(f,lambda:f.finish(f.token()),'failure blocks whole finish');refuse(f,lambda:f.retry(f.token(),''),'retry diagnosis')
        f.retry(f.token(),'Retry after manual diagnosis');check(f.stage==stage and f.state=='ready' and not f.partner_release_required,'retry current released stage');to_report(f);f.report(f.token(),response(f));check(f.state=='reported','manual retry can succeed')
    f=deepcopy(ready);to_report(f)
    for field,value in [('stage_id','wrong'),('source_targets',['wrong']),('notes','')]+([('attack_count',True),('attack_count',-1),('attack_count',1.0),('attack_count','1')] if stage>=3 else []):
        r=response(f);r[field]=value;refuse(f,lambda:f.report(f.token(),r),'typed source response '+field)
    r=response(f);r['duties'][next(iter(r['duties']))]=True;refuse(f,lambda:f.report(f.token(),r),'explicit outcome enum')
    if stage>=3:
        r=response(f);r['chosen_contact']['fret']+=1;refuse(f,lambda:f.report(f.token(),r),'exact chosen contact binding')
    states=[];f=deepcopy(ready);states.append(deepcopy(f))
    if stage<3:
        acts=[lambda:f.begin_vocal(f.token(),True),lambda:f.cue_read(f.token(),f.cue()['targets']),lambda:f.sing_line(f.token(),True)]
    else:acts=[lambda:f.begin_dominant(f.token(),confirmation(f)),lambda:f.heard_partial(f.token(),True),lambda:f.sing_third(f.token(),True),lambda:f.setup_target(f.token(),True),lambda:f.add_third(f.token(),True)]
    acts.extend([lambda:f.end_take(f.token(),True),lambda:f.release(f.token(),release_reply(f)),lambda:f.report(f.token(),response(f))])
    for action in acts:action();states.append(deepcopy(f))
    for f in states:
        before=f.state;pending=f.partner_release_required;p=deepcopy(f.plan);h=deepcopy(f.history);t=f.token();f.cancel(t)
        check(f.partner_release_required==pending and f.partner_stop_requested==pending,'cancel requests stop without claiming actual stop')
        if pending:check('Stop/release' in f.source_player_view()['instruction'],'source player sees stop request')
        refuse(f,lambda:f.cancel(t),'duplicate cancel');f.reopen(f.token());f.cancel(f.token());f.reopen(f.token());refuse(f,lambda:f.begin_vocal(f.token(),True),'reopen release fence')
        if pending:
            for bad in (False,None,1):
                r=release_reply(f);r['partner_stopped']=bad;refuse(f,lambda:f.release(f.token(),r),'pending partner stop confirmation')
        f.release(f.token(),release_reply(f));target=before if before in ('ready','reported') else 'ready'
        check(f.state==target and f.stage==stage and f.plan==p and f.history[:len(h)]==h and not f.partner_release_required,'reopen preserves source/stage/plan, repeats interrupted after release')
        refuse(f,lambda:f.begin_vocal(t,True),'stale canceled action')
f=m.MinorFlow(m.KEY);f.set_plan(f.token(),plan());mutations=[]
for field in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
mutations.extend([('wrong partner',lambda p:p['partner'].update(kind='app_audio')),('recording not specified human partner',lambda p:p['partner'].update(kind='external_recording')),
 ('missing partner ref',lambda p:p['partner'].update(reference='')),('wrong vocal pitch',lambda p:p['vocal_midi']['lower'].__setitem__(0,51)),('vocal bool',lambda p:p['vocal_midi']['upper'].__setitem__(0,True)),
 ('critical shared register',lambda p:p['vocal_midi'].update(resolution=[68,69]))])
for chord in m.CHORDS:
    mutations.extend([('missing source capability',lambda p,chord=chord:p['partner']['chord_capabilities'][chord].update(can_supply_without_third=False)),
      ('source ref',lambda p,chord=chord:p['partner']['chord_capabilities'][chord].update(reference='')),
      ('wrong third MIDI',lambda p,chord=chord:p['dominant_realizations'][chord].update(sung_third_midi=p['dominant_realizations'][chord]['sung_third_midi']+1)),
      ('third bool',lambda p,chord=chord:p['dominant_realizations'][chord].update(sung_third_midi=True)),
      ('fret bool',lambda p,chord=chord:p['dominant_realizations'][chord]['contact'].update(fret=True)),('fret below',lambda p,chord=chord:p['dominant_realizations'][chord]['contact'].update(fret=-1)),
      ('fret above',lambda p,chord=chord:p['dominant_realizations'][chord]['contact'].update(fret=25)),('wrong string',lambda p,chord=chord:p['dominant_realizations'][chord]['contact'].update(string='x'))])
for label,mutate in mutations:
    p=plan();mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
g=m.MinorFlow(m.KEY);g.set_plan(g.token(),plan());refuse(f,lambda:f.begin_vocal(g.token(),True),'foreign owner');t=f.token();p=plan();f.set_plan(f.token(),p);p['vocal_midi']['lower'][0]=0;check(f.plan['vocal_midi']['lower'][0]!=0,'plan custody');refuse(f,lambda:f.begin_vocal(t,True),'stale generation')
v=f.source_player_view();v['cue']['targets'][0]='wrong';check(f.cue()['targets'][0]!='wrong','source view custody')
for key in ('exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7','exercise-completeness-r01/level077/modulec/p007-supplement01/majoriivivoiceleading'):refuse(f,lambda key=key:m.MinorFlow(key),'excluded other identities')
f=m.MinorFlow(m.KEY);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),release_reply(f));check(f.state=='setup','unconfigured cancellation')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'minor_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
