from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from collections import Counter
from pypdf import PdfReader
import json,hashlib,re,sys,importlib.util,resource,datetime
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r30');checks=0
sp=importlib.util.spec_from_file_location('rhythm_r30',R/'Tools'/L/'rhythm_contract.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
def check(v,why):
    global checks
    checks+=1
    if not v:raise AssertionError(why)
def refused(fn,s):
    before=s.snapshot()
    try:fn()
    except ValueError:check(before==s.snapshot(),'refusal preserves exact state')
    else:raise AssertionError('unexpected accepted action')
def choice():return {'own_instrument':True,'tempo_bpm':60,**{k:'learner-specified '+k for k in m.RhythmCapstone.choice_fields}}
def yes(s):
    q={k:'yes' for k in m.RhythmCapstone.report_fields}
    if s.pass_number>=4:q['added_chord_changes']='yes'
    q.update(close_timing='on_time',recording=None,notes='')
    if s.pass_number==5:q['recording']={'recorded':'yes','mechanism':'self_report','reference_or_statement':'I recorded the complete form externally.'}
    return q
def at_report(c,target):
    s=m.RhythmCapstone(c);s.configure(s.token(),choice())
    for n in range(1,target+1):
        s.begin(s.token());s.release(s.token(),True)
        if n<target:s.respond(s.token(),yes(s))
    return s
def suspend(s):
    before=s.snapshot();old=s.token();s.cancel(old)
    refused(lambda:s.reopen(old,True),s);refused(lambda:s.reopen(s.token(),False),s)
    s.reopen(s.token(),True);after=s.snapshot()
    for k in ('key','cycle','pass','stage','choice','current_report','completed_passes','history','source_script','manual_reports_complete'):
        check(before[k]==after[k],'cancel/reopen retains '+k)
    check(after['generation']==before['generation']+2,'callbacks invalidated')
r=json.loads((R/'Build'/L/'rhythm-capstone-overlay.jsonl').read_text());c=r['implementation']['task']['contract']
old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl').read_text().splitlines()][44]
src=json.loads((R/'Build'/L/'source-check.json').read_text());proj=json.loads((R/src['projection_ref']['path']).read_text())
pdf=PdfReader(R/src['original_pdf']['path']);p18=pdf.pages[17].extract_text();p17=' '.join(pdf.pages[16].extract_text().split())
check(r['package_key']==old['package_key'] and r['source_identity']==old['source_identity'],'exact official key')
check(r['implementation']['events']==old['implementation']['events']==[],'original events remain empty')
check(r['implementation']['source_field_occurrences']==old['implementation']['source_field_occurrences'] and len(old['implementation']['source_field_occurrences'])==8,'all eight original motif literal occurrences exact')
for s in (c['source_script']['transition_instruction'],c['source_script']['close_instruction']):check(s in p17,'full joined original instruction')
for p in c['source_script']['performance_passes']:check(p['instruction'] in p17,'allfive literal source passes')
pitchline=next(x for x in p18.splitlines() if x.startswith('Pitch'))
cellline=next(x for x in p18.splitlines() if x.startswith('Cell'))
first=[x.strip().removesuffix(' repeating').split('-') for x in pitchline.split('|')[1:-1]]
second=[x.strip().split('-') for x in cellline.split('|')[1:-1]]
motif=re.search(r'Motif each bar: ([A-G\-]+)',p18).group(1).split('-')
notes=proj['ordered_pitch_voice_slots'];check(len(notes)==200,'200 derived uses exactly')
check(Counter(e['section'] for e in notes)=={1:48,2:80,3:32,4:40},'source section counts')
check([e['derived_order'] for e in notes]==list(range(1,201)),'deterministic derived order')
check([F(*e['onset_q_fraction']) for e in notes]==sorted(F(*e['onset_q_fraction']) for e in notes),'ordered rational times')
for e in notes:
    bar=e['source_bar'];q=F(*e['onset_q_fraction'])-4*(bar-1)
    check(F(0)<=q<4,'attack remains within original4/4bar')
    check(all(e[k] is None for k in ('duration_q','octave','midi','string_number','fret','finger')),'no fabricated realization/gate')
    check('authored expansion' in e['provenance'],'derived not misrepresented as old source contact')
    if bar<=8:
        j=int(q*4);cell=first[bar-1] if bar<=3 else second[bar-4]
        check(q*4==j and e['pitch_label']==cell[j%len(cell)] and e['voice']=='single','literal perbar cell/rate expansion')
        start,group=(1,3) if bar<=3 else (4,5)
        check(e['accent']==(((bar-start)*16+j)%group==0),'global accent phase no bar restart')
    elif bar<=12:
        j=e['index_in_voice_or_cell']-1
        check(q==F(bar-9+j,4) and e['pitch_label']==motif[j] and e['accent'] is None,'source displaced motif literal/rate')
    else:
        roots=['C','A','D','G'];thirds=['E','C','F','B'];j=e['index_in_voice_or_cell']-1
        check(e['pitch_label']==(roots if e['voice']=='lower_two_pulse' else thirds)[bar-13],'source poly voice pitch')
        check(q==(F(j) if e['voice']=='lower_two_pulse' else F(2*j,3)),'printed two beat3:2span')
for sec in (1,2):check(sum(e['accent'] is True for e in notes if e['section']==sec)==16,'16 source accents/fullcycle')
for bar in range(13,17):
    times=Counter(F(*e['onset_q_fraction'])-4*(bar-1) for e in notes if e['source_bar']==bar)
    check({q for q,n in times.items() if n==2}=={F(0),F(2)},'distinct simultaneous bass/upper atbeats1and3')
close=c['source_script']['close'];check(close['after_bar']==16 and close['duration']=='whole note' and close['included_in_200'] is False,'whole-note close separate from200')
cue=c['source_script']['cues'];check(cue[0]['preceding_printed_bar'] is None and cue[0]['beat']==4,'firstcue no inventedbar0')
check([(x['word'],x['preceding_printed_bar'],x['beat']) for x in cue[1:]]==[('five',3,4),('shift',8,4),('three-over-two',12,4)],'internal cue source positions')
check(not proj['canonical_ids'] and proj['source_contacts']==0,'derived objects not canonical contacts')

s=m.RhythmCapstone(c);suspend(s);refused(lambda:s.begin(s.token()),s)
for k in m.RhythmCapstone.choice_fields:
    q=choice();q[k]='';refused(lambda z=q:s.configure(s.token(),z),s)
for bpm in (0,-1,float('inf'),float('nan'),True,'60'):
    q=choice();q['tempo_bpm']=bpm;refused(lambda z=q:s.configure(s.token(),z),s)
for own in (False,None,1):
    q=choice();q['own_instrument']=own;refused(lambda z=q:s.configure(s.token(),z),s)
s.configure(s.token(),choice());q=choice();q['tempo_bpm']=72;s.configure(s.token(),q)
check(len(s.history)==1,'prior learner choices retained');suspend(s)
for n in range(1,6):
    check(s.pass_number==n and s.stage=='ready','exact pass progression')
    t=s.token()
    for bad in (m.RhythmCapstone(c).token(),replace(t,key='other'),replace(t,cycle=3),replace(t,pass_number=9),replace(t,action=99)):
        refused(lambda x=bad:s.begin(x),s)
    s.begin(t);refused(lambda:s.begin(t),s);suspend(s)
    refused(lambda:s.respond(s.token(),yes(s)),s);refused(lambda:s.release(s.token(),False),s)
    t=s.token();s.release(t,True);refused(lambda:s.release(t,True),s);suspend(s)
    q=yes(s);del q['group5_section'];refused(lambda:s.respond(s.token(),q),s)
    q=yes(s);q['extra']=True;refused(lambda:s.respond(s.token(),q),s)
    if n<5:
        q=yes(s);q['recording']={'recorded':'yes'};refused(lambda:s.respond(s.token(),q),s)
    else:
        for rec in (None,{}, {'recorded':'yes','mechanism':'app_microphone','reference_or_statement':'captured'},
                    {'recorded':'yes','mechanism':'external_artifact_reference','reference_or_statement':''}):
            q=yes(s);q['recording']=rec;refused(lambda z=q:s.respond(s.token(),z),s)
    token=s.token();q=yes(s);s.respond(token,q);q['group5_section']='no'
    check(s.completed_passes[n]['group5_section']=='yes','captured report detached');refused(lambda:s.respond(token,yes(s)),s)
    check(s.snapshot()['manual_reports_complete']==(n==5),'no earlycomplete')
suspend(s)
for f in ('performance_observed','audio_supplied','recording_inspected','automatic_evaluation','Attempt_credit','mastery_awarded','persistence_supplied'):
    check(s.snapshot()[f] is False,'no '+f)
prior=deepcopy(s.history);saved_choice=deepcopy(s.choice);oldtoken=s.token();s.repeat_cycle(oldtoken,'repeat form');suspend(s)
refused(lambda:s.repeat_release(s.token(),False),s);s.repeat_release(s.token(),True)
check(s.cycle==2 and s.pass_number==1 and not s.completed_passes and s.choice==saved_choice,'newcycle choices retained')
check(all(x in s.history for x in prior),'all prior reports retained');refused(lambda:s.repeat_cycle(oldtoken,'stale'),s)

for target in range(1,6):
    for field in (*m.RhythmCapstone.report_fields, *(['added_chord_changes'] if target>=4 else [])):
        for answer in ('no','uncertain'):
            ss=at_report(c,target);before=deepcopy(ss.completed_passes);q=yes(ss);q[field]=answer
            ss.respond(ss.token(),q);check(ss.stage=='retry_required' and ss.pass_number==target,'each unsatisfied source duty holds pass')
            check(ss.current_report==q and ss.completed_passes==before,'negative report/priorpasses preserved')
            ss.request_retry(ss.token(),'rehearse source duty');refused(lambda:ss.retry_release(ss.token(),False),ss)
            ss.retry_release(ss.token(),True);check(ss.pass_number==target and ss.completed_passes==before,'currentpassretry')
    for close_timing in ('early','late','uncertain'):
        ss=at_report(c,target);q=yes(ss);q['close_timing']=close_timing;ss.respond(ss.token(),q)
        check(ss.stage=='isolate_bars13_16','source close repair enforced');suspend(ss)
        refused(lambda:ss.request_retry(ss.token(),'skip isolation'),ss)
        refused(lambda:ss.report_isolation(ss.token(),False,'yes',''),ss)
        for answer in ('no','uncertain'):
            ss.report_isolation(ss.token(),True,answer,'retain repair attempt')
            check(ss.stage=='isolate_bars13_16','unsatisfied repair cannot bypass')
        old=ss.token();ss.report_isolation(old,True,'yes','isolated13–16');refused(lambda:ss.report_isolation(old,True,'yes','duplicate'),ss)
        check(ss.stage=='retry_required','isolation allows only retry, not source-passcompletion')
        ss.request_retry(ss.token(),'try fullpass');ss.retry_release(ss.token(),True)
        ss.begin(ss.token());ss.release(ss.token(),True);ss.respond(ss.token(),yes(ss))
        check(target in ss.completed_passes,'sourcepass completed after explicitrepair/fullretry')
for answer in ('no','uncertain'):
    s=at_report(c,5);q=yes(s);q['recording']['recorded']=answer;s.respond(s.token(),q)
    check(s.stage=='retry_required' and s.current_report['recording']['recorded']==answer,'unrecorded form cannot complete')
s=at_report(c,5);q=yes(s);q['recording']={'recorded':'yes','mechanism':'external_artifact_reference','reference_or_statement':'learner-local recording reference'}
s.respond(s.token(),q);check(s.stage=='complete_manual_reports' and not s.snapshot()['recording_inspected'],'externalref allowed withoutclaiminginspection')
for ref in (src['original_pdf'],src['original_txt'],src['projection_ref']):
    b=(R/ref['path']).read_bytes();check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'inputfinalpin')
out={'status':'PASS','checks':checks,'derived_pitch_voice_uses':200,'section_counts':[48,80,32,40],
     'original_source_events':0,'original_motif_occurrences':8,'manual_cases':1,'passes':5,
     'synthetic_responses_only':True,'recordings_inspected':0,'native_runs':0,
     'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
