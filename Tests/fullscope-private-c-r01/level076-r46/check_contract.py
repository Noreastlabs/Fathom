from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level076-r46')
s=importlib.util.spec_from_file_location('workflow',R/'Tools'/L/'workflow_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan():return {'original_workbook':True,'provider':'external_recording','reference':'Learner-provided excerpt reference, not inspected','excerpt_boundaries':'chosen start/end landmarks','source_ready':True}
def answer(mark):return {'mark':mark,'answers':[] if mark=='?' else (['First plausible answer','Second plausible answer'] if mark=='/' else ['Learner answer']),
 'clues':[{'id':'clue1','family':'bass evidence','observation':'learner described bass observation'},{'id':'clue2','family':'cadence evidence','observation':'learner described cadence observation'}] if mark=='!' else [],
 'independence_self_report':mark=='!','notes':'Learner rationale, no app verification','next_check':'Re-listen or test hypothesis' if mark in ('?','/') else ''}
def response(f,mark='hypothesis'):return {'source_stage':m.STAGES[f.stage][0],'source_question':m.STAGES[f.stage][1],
    'responses':{k:answer(mark) for k in m.STAGES[f.stage][2]}}
def responding(f):f.begin(f.token(),True);f.end_stage(f.token(),True);f.release(f.token(),True)
def ready(stage=0):
    f=m.Workflow(m.KEY);f.set_plan(f.token(),plan())
    for _ in range(stage):responding(f);f.submit(f.token(),response(f));f.next_stage(f.token())
    return f
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'workflow-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()];check(len(rows)==1,'one exact key');r=rows[0]
old=json.loads((R/'Build/fullscope-private-c-r01/level076-r06/implementation-packet.jsonl').read_text().splitlines()[0]);c=r['implementation']['task']['contract']
for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(r[k]==old[k],'immutable '+k)
check(r['implementation']['events']==old['implementation']['events']==[],'no musical event invented')
expected=[('FORM',('bar_count','repeats','strongest_arrival')),('PULSE',('clap_beat','subdivision')),('TONIC',('finished_pitch',)),('BASS',('structural_bass_at_each_change',)),
 ('QUALITY',('chord_quality',)),('RHYTHM',('contacts','rests','ties','anticipations','releases')),('MELODY',('structural_targets','approaches')),
 ('ARRANGEMENT',('register','density','articulation','dynamics','cue_behavior'))]
check([(s['name'],tuple(s['authored_response_fields'])) for s in c['source_stages']]==expected,'independent all20subquestion fields in source order')
check(c['source_txt_stack']==['Form','Pulse','Bass','Harmony','Rhythm','Melody','Arrangement'],'distinct seven TXT stack')
check(c['source_pdf_uncertainty']=='Uncertainty marks: ? = unresolved; / = two plausible answers; ( ) = optional or ornamental; ! = verified by at least two independent clues.','full PDF notation')
check(c['source_txt_uncertainty'][-1]=='! = verified by two independent clues','TXT notation not rewritten')
source=json.loads((R/'Build'/L/'source-check.json').read_text())
for s in c['source_stages']:check(s['question'] in source['original_page_text'],'full original source question')
for k in ('source_answers_prefilled','automatic_evaluation','performance_observed','audio_supplied','audio_inspected','app_verified','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
for mark in m.MARKS:
    f=ready();history=[]
    for stage in range(8):
        check(f.stage==stage and f.state=='ready','eight ordered phases')
        for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'current external readiness')
        t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.next_stage(f.token()),'early next')
        refuse(f,lambda:f.submit(f.token(),response(f,mark)),'early answer');refuse(f,lambda:f.release(f.token(),True),'end bypass');refuse(f,lambda:f.set_plan(f.token(),plan()),'active excerpt replacement')
        refuse(f,lambda:f.end_stage(f.token(),False),'not ended');f.end_stage(f.token(),True);refuse(f,lambda:f.submit(f.token(),response(f,mark)),'release bypass');refuse(f,lambda:f.release(f.token(),1),'release exact true')
        f.release(f.token(),True);r=response(f,mark);t=f.token();f.submit(t,r);first=next(iter(r['responses']));r['responses'][first]['notes']='outside mutation'
        check(f.latest[stage]['response']['responses'][first]['notes']!='outside mutation','response custody')
        check(all(x['app_verified'] is False and x['independence_verified'] is False and x['audio_inspected'] is False for x in f.latest[stage]['dispositions'].values()),'manual clue boundary')
        refuse(f,lambda:f.submit(t,response(f,mark)),'duplicate reply')
        if stage<7:
            refuse(f,lambda:f.finish(f.token()),'premature finish');oldtoken=f.token();f.next_stage(f.token());refuse(f,lambda:f.repeat(oldtoken,'stale stage'),'previous stage token')
        else:
            refuse(f,lambda:f.next_stage(f.token()),'ninth stage');f.finish(f.token())
    end=f.history[-1]['data'];check(f.state=='completed' and end['manual_workflow_recorded'] is True,'workflow recorded')
    check(end['unresolved_fields']==(20 if mark in ('?','/') else 0),'honest unresolved count')
    check(end['learner_marked_verified_fields']==(20 if mark=='!' else 0) and end['app_verified'] is False and end['credit_awarded'] is False and end['mastery_awarded'] is False,'no promotion to verified/mastery')
    prior=deepcopy(f.history);p=plan();p['reference']='different excerpt';f.set_plan(f.token(),p);p['reference']='outside'
    check(f.stage==0 and f.state=='ready' and f.latest=={} and f.plan['reference']=='different excerpt' and f.history[:len(prior)]==prior,'new excerpt reset and deep custody')
# Each field must remain present; each notation boundary must refuse atomically on all20fields.
for stage in range(8):
    f=ready(stage);responding(f)
    for field in m.STAGES[stage][2]:
        r=response(f);r['responses'].pop(field);refuse(f,lambda:f.submit(f.token(),r),'missing '+field)
        mutations=[('unknown mark',lambda a:a.update(mark='pass')),('blank notes',lambda a:a.update(notes='')),
          ('? no next',lambda a:a.update(mark='?',answers=[],next_check='')),('/ one answer',lambda a:a.update(mark='/',answers=['one'],next_check='next')),
          ('/ duplicate answers',lambda a:a.update(mark='/',answers=['same',' Same '],next_check='next')),
          ('optional omitted answer',lambda a:a.update(mark='()',answers=[])),('hypothesis two answers',lambda a:a.update(answers=['one','two'])),
          ('! no clues',lambda a:a.update(mark='!',clues=[],independence_self_report=True)),
          ('false independence',lambda a:a.update(**{**answer('!'),'independence_self_report':False})),
          ('duplicate clue ID',lambda a:a.update(**{**answer('!'),'clues':[{'id':'same','family':'a','observation':'x'},{'id':' SAME ','family':'b','observation':'y'}]})),
          ('same clue family',lambda a:a.update(**{**answer('!'),'clues':[{'id':'1','family':'same','observation':'x'},{'id':'2','family':' SAME ','observation':'y'}]})),
          ('empty clue',lambda a:a.update(**{**answer('!'),'clues':[{'id':'1','family':'a','observation':''},{'id':'2','family':'b','observation':'y'}]})),
          ('? two answers',lambda a:a.update(mark='?',answers=['one','two'],next_check='next')),
          ('nonverified independence',lambda a:a.update(independence_self_report=True)),('next check type',lambda a:a.update(next_check=None))]
        for label,mutate in mutations:
            r=response(f);mutate(r['responses'][field]);refuse(f,lambda:f.submit(f.token(),r),label+' '+field)
    for field,value in (('source_stage','wrong'),('source_question','truncated question')):
        r=response(f);r[field]=value;refuse(f,lambda:f.submit(f.token(),r),'source binding')
    r=response(f,'?');f.submit(f.token(),r);latest=deepcopy(f.latest);t=f.token();f.repeat(t,'Re-listen unresolved fields')
    check(f.stage==stage and f.latest==latest and f.state=='ready','repeat same stage retains old result');refuse(f,lambda:f.finish(f.token()),'repeat requires new response')
    responding(f);r=response(f,'!')
    for a in r['responses'].values():a['clues'].append({'id':'3','family':'third clue family','observation':'learner additional observation'})
    f.submit(f.token(),r);check(f.latest[stage]['unresolved_fields']==0 and all(x['manual_status']=='learner_marked_verified' for x in f.latest[stage]['dispositions'].values()),'at least two supports three clues, not app truth')
for field,bad in [('original_workbook',False),('source_ready',False),('source_ready',1),('provider','app_audio'),('reference',''),('excerpt_boundaries','')]:
    f=ready();p=plan();p[field]=bad;refuse(f,lambda:f.set_plan(f.token(),p),'plan prerequisite '+field)
f=ready();p=plan();p['provider']='external_human_player';f.set_plan(f.token(),p);check(f.plan['provider']=='external_human_player','human source role')
for stage in (0,4,7):
    for state in ('ready','listening','await_release','responding','reported'):
        f=ready(stage)
        if state in ('listening','await_release','responding','reported'):f.begin(f.token(),True)
        if state in ('await_release','responding','reported'):f.end_stage(f.token(),True)
        if state in ('responding','reported'):f.release(f.token(),True)
        if state=='reported':f.submit(f.token(),response(f,'?'))
        history=deepcopy(f.history);latest=deepcopy(f.latest);p=deepcopy(f.plan);t=f.token();f.cancel(t);refuse(f,lambda:f.cancel(t),'duplicate cancel')
        f.reopen(f.token());f.cancel(f.token());f.reopen(f.token());refuse(f,lambda:f.begin(f.token(),True),'reopen release bypass');f.release(f.token(),True)
        target='ready' if state in ('listening','await_release','responding') else state
        check(f.stage==stage and f.state==target and f.latest==latest and f.plan==p and f.history[:len(history)]==history,'cancel/reopen preserves stage/answers/source')
f=m.Workflow(m.KEY);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup','setup cancel route')
f=ready(7);responding(f);f.submit(f.token(),response(f));f.finish(f.token());f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='completed','completed cancel route')
f=ready();other=ready();refuse(f,lambda:f.begin(other.token(),True),'foreign instance');t=f.token();f.set_plan(f.token(),plan());refuse(f,lambda:f.begin(t,True),'stale generation');refuse(f,lambda:f.begin(list(f.token()),True),'token type')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'workflow_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_audio_or_analysis_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
