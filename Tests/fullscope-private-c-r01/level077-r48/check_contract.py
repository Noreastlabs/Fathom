from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r48')
s=importlib.util.spec_from_file_location('dictation',R/'Tools'/L/'dictation_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i):
    a=60+m.PC[m.RAW[i][0]];b=a+m.delta(i);string=next(s for s,t in m.TUNING.items() if 0<=b-t<=24)
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'provider':{'kind':'external_human','reference':'Actual human supplies pair/named source prompts','ready':True},
      'start_midi':a,'destination_midi':b,'specified_string':string}
def answer_ready(f):f.begin(f.token(),True);f.end_listening(f.token(),True);f.release(f.token(),True)
def commit(f,quality=None,pitch=None):
    f.answer_quality(f.token(),m.RAW[f.index][3] if quality is None else quality);f.answer_pitch(f.token(),m.RAW[f.index][1] if pitch is None else pitch)
def review():return {'heard_pair':'yes','diagnosis':'','notes':'Synthetic manual source report.'}
def fret_ready(f):f.begin(f.token(),True);f.heard_prompt(f.token(),True);f.sung(f.token(),True);f.setup_target(f.token(),True);f.attempt_attack(f.token(),True);f.release(f.token(),True)
def fret_report(f):return {'specified_string':f.plan['specified_string'],'attack_count':1,'duties':dict.fromkeys(m.FRET_DUTIES,'yes'),'diagnosis':'','notes':'Synthetic guitar report; no observed audio.'}
def ready(i,phase=0):
    f=m.DictationFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i))
    if phase:answer_ready(f);commit(f);f.reveal(f.token());f.review_dictation(f.token(),review());f.next_pass(f.token())
    return f
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'interval-dictation-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()]
check(len(rows)==22 and [r['package_key'] for r in rows]==list(m.KEYS),'exact22officialkeys')
check(rows[-1]['package_key'].endswith('p003-t1-r25/24'),'printed24 officialrow25 unchanged')
check(all('/r22/' not in r['package_key'] and '/r24/23' not in r['package_key'] for r in rows),'no outside-child keys')
for i,row in enumerate(rows):
    old=base[i+12];c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'source unchanged '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source events')
    expected=old['implementation']['task']['table_fields'][0]['values']
    check([str(c['source_fields']['Card']),c['source_fields']['Start'],c['source_fields']['Destination'],c['source_fields']['Direction'],c['source_fields']['Answer']]==expected,'five exact original columns')
    if i==19:
        check(c['source_fields']=={'Card':20,'Start':'B','Destination':'D','Direction':'down','Answer':'m6'},'contradictory printed facts preserved')
        check(c['printed_signed_semitones']==-8 and c['pitch_pair_descending_semitones']==9 and c['private_workflow_available'] is False,'bounded card20 source refusal')
        check(row['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING' and row['contract_capabilities']['complete_manual_response_contract'] is False,'no unsupported completion')
        try:m.DictationFlow(m.KEYS[i])
        except m.Refusal:checks+=1;refusals+=1
        else:raise AssertionError('card20 source conflict instantiated')
        continue
    check((m.PC[c['source_fields']['Start']]+c['derived_signed_semitones'])%12==m.PC[c['source_fields']['Destination']],'signed pitch consistency')
    if m.CARD[i] in (12,24):check(abs(c['derived_signed_semitones'])==12,'octave retained')
    check(c['source_footer']=='Fretboard pass: source names only the starting note and interval. Player sings the destination, then plays it on a specified string without first playing the root.','full source footer')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    f=ready(i);full=f.source_view();check(full['destination']==m.RAW[i][1] and full['interval']==m.RAW[i][3],'source/player script retained')
    check('source_answer' not in f.learner_view() and f.learner_view()['previously_revealed'] is False,'fresh answer withholding')
    for bad in (False,1,'yes',None):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'provider readiness')
    f.begin(f.token(),True);refuse(f,lambda:f.answer_quality(f.token(),'m2'),'quality before listening end');refuse(f,lambda:f.release(f.token(),True),'end bypass')
    refuse(f,lambda:f.set_plan(f.token(),plan(i)),'active plan');f.end_listening(f.token(),True);refuse(f,lambda:f.answer_quality(f.token(),'m2'),'release bypass');f.release(f.token(),True)
    refuse(f,lambda:f.answer_pitch(f.token(),'C'),'quality before pitch');refuse(f,lambda:f.reveal(f.token()),'early reveal')
    t=f.token();f.answer_quality(t,m.RAW[i][3]);refuse(f,lambda:f.answer_quality(t,m.RAW[i][3]),'duplicate quality')
    check('source_answer' not in f.learner_view(),'quality alone does not reveal')
    refuse(f,lambda:f.reveal(f.token()),'quality-only reveal');f.answer_pitch(f.token(),m.RAW[i][1]);check('source_answer' not in f.learner_view(),'explicit reveal still required')
    refuse(f,lambda:f.review_dictation(f.token(),review()),'review before reveal');f.reveal(f.token());check(f.learner_view()['source_answer']['destination']==m.RAW[i][1] and f.ever_revealed,'reveal after both answers')
    r=review();t=f.token();f.review_dictation(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','review custody')
    refuse(f,lambda:f.review_dictation(t,review()),'duplicate review');refuse(f,lambda:f.finish(f.token()),'second pass needed');f.next_pass(f.token())
    view=f.learner_view();check(view['prompt']=={'start':m.RAW[i][0],'interval':m.RAW[i][3],'direction':m.RAW[i][2],'specified_string':f.plan['specified_string']},'named source fretboard prompt')
    check('source_answer' not in view and view['learner_answers']=={} and view['previously_revealed'] and view['prior_responses_retained'],'prior answer history honest without current destination prompt')
    check(f.source_view()['destination']==full['destination'],'source/player not erased')
    f.begin(f.token(),True);refuse(f,lambda:f.sung(f.token(),True),'heard prompt first');f.heard_prompt(f.token(),True)
    refuse(f,lambda:f.setup_target(f.token(),True),'sing before setup');f.sung(f.token(),True);refuse(f,lambda:f.attempt_attack(f.token(),True),'setup before attack')
    f.setup_target(f.token(),True);t=f.token();f.attempt_attack(t,True);refuse(f,lambda:f.attempt_attack(t,True),'duplicate attempt')
    refuse(f,lambda:f.report_fretboard(f.token(),fret_report(f)),'fret release fence');f.release(f.token(),True);r=fret_report(f);f.report_fretboard(f.token(),r)
    check(f.history[-1]['data']['performance_verified'] is False,'manual performance only');refuse(f,lambda:f.next_pass(f.token()),'no third pass');f.finish(f.token());check(f.state=='completed','21 complete two-pass routes')
    history=deepcopy(f.history);f.set_plan(f.token(),plan(i));check(f.phase==0 and f.answers=={} and f.ever_revealed and f.history[:len(history)]==history,'newplan resets but never erases reveal')
    # Symbolic and hearing failures are retained with diagnosis; recognized enharmonics do not rewrite source.
    wrong_pitch='C' if m.PC[m.RAW[i][1]]!=0 else 'C#'
    for quality,pitch,heard in [('wrong',m.RAW[i][1],'yes'),(m.RAW[i][3],wrong_pitch,'yes'),(m.RAW[i][3],m.RAW[i][1],'no'),(m.RAW[i][3],m.RAW[i][1],'uncertain')]:
        g=ready(i);answer_ready(g);commit(g,quality,pitch);g.reveal(g.token());r=review();r['heard_pair']=heard;refuse(g,lambda:g.review_dictation(g.token(),r),'failed dictation needs diagnosis')
        r['diagnosis']='Re-listen and diagnose response';g.review_dictation(g.token(),r);check(g.state=='needs_retry','dictation failure retained');refuse(g,lambda:g.next_pass(g.token()),'failed nextpass')
        g.retry(g.token(),'Repeat exact pair');check(g.ever_revealed and g.learner_view()['previously_revealed'],'retry cannot imply unseen')
    alternative=next((p for p,pc in m.PC.items() if pc==m.PC[m.RAW[i][1]] and p!=m.RAW[i][1]),None)
    if alternative:
        g=ready(i);answer_ready(g);commit(g,pitch=alternative);g.reveal(g.token());g.review_dictation(g.token(),review())
        check(g.state=='reported' and g.history[-1]['data']['source_spelling_match'] is False and g.source_view()['destination']==m.RAW[i][1],'enharmonic answer accepted with original spelling intact')
    for name in m.FRET_DUTIES:
        for value in ('no','uncertain'):
            g=ready(i,1);fret_ready(g);r=fret_report(g);r['duties'][name]=value;refuse(g,lambda:g.report_fretboard(g.token(),r),'manual failure requires diagnosis')
            r['diagnosis']='No-search/root/target issue reported';g.report_fretboard(g.token(),r);check(g.state=='needs_retry','negative fret duty retained');refuse(g,lambda:g.finish(g.token()),'failed finish')
            g.retry(g.token(),'Retry same specified string');check(g.phase==1 and g.state=='ready' and g.ever_revealed,'retry same phase preserves reveal')
    for count in (0,2,9):
        g=ready(i,1);fret_ready(g);r=fret_report(g);r['attack_count']=count;r['diagnosis']='Actual attack count violates single attack';g.report_fretboard(g.token(),r);check(g.state=='needs_retry','actual count failure')
    g=ready(i,1);fret_ready(g)
    for count in (True,-1,1.0,'1'):
        r=fret_report(g);r['attack_count']=count;refuse(g,lambda:g.report_fretboard(g.token(),r),'count type')
    r=fret_report(g);r['specified_string']='wrong';refuse(g,lambda:g.report_fretboard(g.token(),r),'specified string binding')
    for field,value in [('start_midi',True),('start_midi',-1),('destination_midi',128),('destination_midi',plan(i)['destination_midi']+1),('specified_string','x')]:
        g=ready(i);p=plan(i);p[field]=value;refuse(g,lambda:g.set_plan(g.token(),p),'chosen source realization '+field)
    for field,value in [('kind','app_audio'),('ready',False),('reference','')]:
        g=ready(i);p=plan(i);p['provider'][field]=value;refuse(g,lambda:g.set_plan(g.token(),p),'provider '+field)
    for phase,states in [(0,('ready','listening','answer_quality','answer_pitch','committed','review','reported')),(1,('ready','hearing_prompt','singing','silent_setup','attack','fret_report','reported'))]:
        for state in states:
            h=ready(i,phase)
            if state!='ready':h.begin(h.token(),True)
            if phase==0:
                if state not in ('ready','listening'):h.end_listening(h.token(),True);h.release(h.token(),True)
                if state in ('answer_pitch','committed','review','reported'):h.answer_quality(h.token(),m.RAW[i][3])
                if state in ('committed','review','reported'):h.answer_pitch(h.token(),m.RAW[i][1])
                if state in ('review','reported'):h.reveal(h.token())
                if state=='reported':h.review_dictation(h.token(),review())
            else:
                if state not in ('ready','hearing_prompt'):h.heard_prompt(h.token(),True)
                if state in ('silent_setup','attack','fret_report','reported'):h.sung(h.token(),True)
                if state in ('attack','fret_report','reported'):h.setup_target(h.token(),True)
                if state in ('fret_report','reported'):h.attempt_attack(h.token(),True);h.release(h.token(),True)
                if state=='reported':h.report_fretboard(h.token(),fret_report(h))
            check(h.state==state,'fixture state');history=deepcopy(h.history);p=deepcopy(h.plan);answers=deepcopy(h.answers);revealed=h.ever_revealed;t=h.token();h.cancel(t)
            refuse(h,lambda:h.cancel(t),'duplicate cancel');h.reopen(h.token());h.cancel(h.token());h.reopen(h.token());refuse(h,lambda:h.begin(h.token(),True),'reopen release fence');h.release(h.token(),True)
            target=state if state in ('ready','review','reported') else 'ready'
            check(h.state==target and h.phase==phase and h.plan==p and h.answers==answers and h.ever_revealed==revealed and h.history[:len(history)]==history,'cancel/reopen preserves answers and reveal')
    g=ready(i);other=ready(i);refuse(g,lambda:g.begin(other.token(),True),'foreign instance');t=g.token();g.set_plan(g.token(),plan(i));refuse(g,lambda:g.begin(t,True),'stale generation')
# Unsupported source cannot be bypassed by calling validator directly.
f=ready(0);refuse(f,lambda:m.validate_plan(plan(19),19),'card20 direct validator refusal')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'dictation_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'supported_manual_rows':21,'source_reconciliation_pending_rows':1,
 'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
