from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from pypdf import PdfReader
import json,hashlib,sys,importlib.util,resource,datetime
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r31');checks=0
sp=importlib.util.spec_from_file_location('practice_r31',R/'Tools'/L/'practice_contract.py');m=importlib.util.module_from_spec(sp);sys.modules[sp.name]=m;sp.loader.exec_module(m)
def check(v,why):
    global checks
    checks+=1
    if not v:raise AssertionError(why)
def refused(fn,s):
    before=s.snapshot()
    try:fn()
    except ValueError:check(before==s.snapshot(),'refusal unchanged state')
    else:raise AssertionError('unexpected accepted mutation')
def yes(s):
    q={k:'yes' for k in (*s.common_fields,*s.source_phase()['obligation_fields'])}
    q.update(quarter_click_exact='yes' if s.phase==6 else None,recording=None,notes='')
    if s.phase==10:q['recording']={'recorded':'yes','mechanism':'self_report','reference_or_statement':'I recorded the source capstone externally.'}
    return q
def at_phase(c,n,click=True,recorder=True,bpm=60):
    s=m.PracticeFlow(c);s.configure(s.token(),bpm,True,True,click,recorder)
    for i in range(1,n):
        cycle(s);s.advance_phase(s.token())
    return s
def cycle(s,changes=None):
    s.begin(s.token());s.release(s.token(),True);q=yes(s)
    if changes:q.update(changes)
    s.respond(s.token(),q)
def suspend(s):
    old=s.snapshot();t=s.token();s.cancel(t);refused(lambda:s.reopen(t,True),s)
    refused(lambda:s.reopen(s.token(),False),s);s.reopen(s.token(),True);new=s.snapshot()
    for k in ('key','phase','cycle','stage','bpm','mode','clean_cycles','last_quarter_click','external_click','recorder','current_report','repair_selection','history','source_phase','source_complete_report'):
        check(new[k]==old[k],'cancel/reopen retains '+k)
    check(new['generation']==old['generation']+2,'callback generation invalidated')

r=json.loads((R/'Build'/L/'practice-repair-overlay.jsonl').read_text());c=r['implementation']['task']['contract']
old=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl').read_text().splitlines()][45]
src=json.loads((R/'Build'/L/'source-check.json').read_text());pdf=PdfReader(R/src['original_pdf']['path']);norm=' '.join(pdf.pages[18].extract_text().split());txt=(R/src['original_txt']['path']).read_text().splitlines()
check(r['package_key']==old['package_key'] and r['source_identity']==old['source_identity'],'exactkey')
check(r['implementation']['events']==old['implementation']['events']==[],'no contact/rest event invention')
check(c['source_heading'] in norm and len(c['phases'])==10 and len(c['error_repairs'])==8,'fullsource scope')
for phase in c['phases']:
    n=phase['phase'];instruction=phase['source_instruction'];check(f'{n}. '+instruction in norm and f'{n}. {n}. '+instruction in txt,'originaltenphase parity')
    check(phase['source_task_reference']['canonical_binding'] is None,'no new canonicalchildbinding')
for error,repair in c['error_repairs'].items():
    check(error+' '+repair in norm and error+': '+repair+'.' in txt,'exactoriginalerrorrepair parity')
for k in ('source_advancement_instruction','source_physical_instruction'):check(c[k] in norm,'fulljoinedsourceinstruction')
check(c['tempo_policy']['consecutive_requirement_printed'] is False,'no inventedconsecutive requirement')

s=m.PracticeFlow(c);suspend(s);refused(lambda:s.begin(s.token()),s)
for bpm in (0,-1,float('nan'),float('inf'),True,'60'):
    refused(lambda x=bpm:s.configure(s.token(),x,True,True,True,True),s)
for values in ((False,True,True,True),(True,False,True,True),(True,True,1,True),(True,True,True,None)):
    refused(lambda x=values:s.configure(s.token(),60,*x),s)
s.configure(s.token(),60,True,True,True,True)
for phase in range(1,11):
    check(s.phase==phase and s.clean_cycles==0,'orderedphase and counterreset')
    check(s.source_phase()==c['phases'][phase-1],'actualsource phase view')
    t=s.token()
    for bad in (m.PracticeFlow(c).token(),replace(t,key='other'),replace(t,phase=99),replace(t,cycle=99),replace(t,action=99)):
        refused(lambda x=bad:s.begin(x),s)
    suspend(s);t=s.token();s.begin(t);refused(lambda:s.begin(t),s);suspend(s)
    refused(lambda:s.respond(s.token(),yes(s)),s);refused(lambda:s.release(s.token(),False),s)
    rel=s.token();s.release(rel,True);refused(lambda:s.release(rel,True),s);suspend(s)
    q=yes(s);del q[next(iter(q))];refused(lambda:s.respond(s.token(),q),s)
    q=yes(s);q['extra']='yes';refused(lambda:s.respond(s.token(),q),s)
    q=yes(s);q['clean']=True;refused(lambda:s.respond(s.token(),q),s)
    if phase==10:
        for rec in (None,{}, {'recorded':'yes','mechanism':'app_microphone','reference_or_statement':'recorded'},
                    {'recorded':'yes','mechanism':'external_reference','reference_or_statement':''}):
            q=yes(s);q['recording']=rec;refused(lambda x=q:s.respond(s.token(),x),s)
    t=s.token();q=yes(s);s.respond(t,q);q['clean']='no';refused(lambda:s.respond(t,yes(s)),s)
    check(s.stage=='cycle_complete' and s.clean_cycles==1 and s.current_report['clean']=='yes','fullclean cycle counted once/copied')
    check(s.tempo_suggestion() is None,'onecycle not tempoeligible');refused(lambda:s.acknowledge_external_increase(s.token(),True),s)
    cycle(s);check(s.clean_cycles==2 and s.tempo_suggestion() is None,'twocycles insufficient')
    cycle(s);check(s.clean_cycles==3 and s.tempo_suggestion()==s.bpm+2,'threecleancycles +2suggestion')
    suspend(s);refused(lambda:s.acknowledge_external_increase(s.token(),False),s)
    bpm=s.bpm;t=s.token();s.acknowledge_external_increase(t,True);refused(lambda:s.acknowledge_external_increase(t,True),s)
    check(s.bpm==bpm+2 and s.clean_cycles==0 and not s.snapshot()['host_tempo_changed'],'only privateexternaltempo ack reset')
    cycle(s);s.advance_phase(s.token())
check(s.stage=='complete_manual_workflow' and s.snapshot()['source_complete_report'],'allten phases reportcomplete')
suspend(s)
for k in ('performance_observed','host_tempo_changed','audio_supplied','recording_inspected','Attempt_credit','mastery_awarded','persistence_supplied'):
    check(s.snapshot()[k] is False,'no '+k)

# Each source obligation or general physical/music boundary causally gates completion.
for n in range(1,11):
    for field in (*m.PracticeFlow.common_fields,*c['phases'][n-1]['obligation_fields']):
        for answer in ('no','uncertain'):
            ss=at_phase(c,n);cycle(ss,{field:answer});check(ss.clean_cycles==0,'unsatisfiedscope cannotcount')
            check(ss.current_report[field]==answer,'retain unsatisfiedreply')
            refused(lambda:ss.advance_phase(ss.token()),ss)
            if field=='no_gripping_or_breath_holding':
                check(ss.stage=='physical_stop','physicalboundaryrequiresstop')
                refused(lambda:ss.resolve_physical(ss.token(),False,'yes'),ss)
                refused(lambda:ss.resolve_physical(ss.token(),True,'uncertain'),ss)
                ss.resolve_physical(ss.token(),True,'yes');check(ss.stage=='ready','releasedmanual physical retry')
            else:
                check(ss.stage=='repair_required','negative requiresrepair')
                refused(lambda:ss.choose_repair(ss.token(),'unprinted diagnosis'),ss)
                ss.choose_repair(ss.token(),'uncertain');refused(lambda:ss.repair_done(ss.token(),False,'yes',''),ss)
                ss.repair_done(ss.token(),True,'uncertain','review earliestlayer');check(ss.stage=='repair_review','uncertainrepairretained')
                ss.repair_done(ss.token(),True,'yes','manualreviewdone');check(ss.stage=='ready','explicitrepair permitsretry')
for error,repair in c['error_repairs'].items():
    s=at_phase(c,1);cycle(s,{'clean':'no'});s.choose_repair(s.token(),error)
    check(s.contract['error_repairs'][s.repair_selection]==repair,'actual exact chosen repair exposed bycontract')
    suspend(s);s.repair_done(s.token(),True,'yes','source repair performed');check(s.clean_cycles==0,'repair isnotfullcycle')

# Clean complete cycles need not be consecutive; failures do not become qualifying cycles.
s=at_phase(c,1);cycle(s);cycle(s,{'clean':'no'});s.choose_repair(s.token(),'BARLINE MOVES');s.repair_done(s.token(),True,'yes','tapquarters')
check(s.clean_cycles==1,'failedcycle excluded withoutinventedconsecutive reset')
cycle(s);cycle(s);check(s.tempo_suggestion()==62,'three clean complete cycles with repair between')
s.configure(s.token(),80,True,True,True,True);check(s.clean_cycles==0 and s.tempo_suggestion() is None,'changedtempo resets qualification')
for n in (2,3):
    s=at_phase(c,n);cycle(s);before=s.clean_cycles;s.begin(s.token(),'diagnostic_two_bars');s.release(s.token(),True)
    refused(lambda:s.respond(s.token(),yes(s)),s);s.report_diagnostic(s.token(),'yes','two-bar diagnostic excerpt')
    check(s.stage=='return_to_full_required' and s.clean_cycles==before,'diagnosis cannot count')
    refused(lambda:s.advance_phase(s.token()),s);refused(lambda:s.begin(s.token()),s);suspend(s)
    s.return_to_full(s.token());cycle(s);check(s.clean_cycles==before+1,'fullcycle required afterdiagnosis')
s=at_phase(c,1);refused(lambda:s.begin(s.token(),'diagnostic_two_bars'),s)

s=at_phase(c,6)
for i in range(3):cycle(s,{'quarter_click_exact':'no'})
check(s.clean_cycles==3 and s.tempo_suggestion() is None,'odd subdivision nextclick independently required')
refused(lambda:s.acknowledge_external_increase(s.token(),True),s);cycle(s,{'quarter_click_exact':'uncertain'})
check(s.tempo_suggestion() is None,'uncertainnextclick noteligible');cycle(s);check(s.tempo_suggestion()==62,'latestexactclick gate')
s=at_phase(c,6);s.configure(s.token(),60,True,True,False,True);refused(lambda:s.begin(s.token()),s)
s=at_phase(c,10);s.configure(s.token(),60,True,True,True,False);refused(lambda:s.begin(s.token()),s)
for answer in ('no','uncertain'):
    s=at_phase(c,10);s.begin(s.token());s.release(s.token(),True);q=yes(s);q['recording']['recorded']=answer;s.respond(s.token(),q)
    check(s.stage=='repair_required' and s.clean_cycles==0,'notrecorded cannot completefinalphase')
s=at_phase(c,10);s.begin(s.token());s.release(s.token(),True);q=yes(s);q['recording']={'recorded':'yes','mechanism':'external_reference','reference_or_statement':'learner-local recording'};s.respond(s.token(),q)
check(s.stage=='cycle_complete' and not s.snapshot()['recording_inspected'],'externalrefwithoutinspection')
s=at_phase(c,1);s.begin(s.token());t=s.token();s.report_physical_stop(t,'gripping during subdivision')
refused(lambda:s.release(t,True),s);refused(lambda:s.begin(s.token()),s);suspend(s)
s.resolve_physical(s.token(),True,'yes');check(s.clean_cycles==0,'interruptedcycle no completion credit')
s=at_phase(c,1,bpm=1e308)
for i in range(3):cycle(s)
check(s.tempo_suggestion() is None,'unrepresentable exact+2 refused, no fabricated arithmetic')
for ref in (src['original_pdf'],src['original_txt']):
    b=(R/ref['path']).read_bytes();check(len(b)==ref['bytes'] and hashlib.sha256(b).hexdigest()==ref['sha256'],'originalsourcefinalpin')
out={'status':'PASS','checks':checks,'manual_cases':1,'phases':10,'error_repairs':8,'source_events':0,
     'synthetic_responses_only':True,'native_runs':0,'actual_host_tempo_changes':0,'recordings_inspected':0,
     'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
