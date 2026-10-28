from pathlib import Path
import json,hashlib,re,sys,importlib.util,resource,datetime
from dataclasses import replace
from pypdf import PdfReader
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level073-r26');checks=0
p=R/'Tools'/L/'mediant_contract.py';s=importlib.util.spec_from_file_location('mediant_r26',p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def check(c,msg):
 global checks
 checks+=1
 if not c:raise AssertionError(msg)
def refused(fn,session):
 old=session.snapshot()
 try:fn()
 except ValueError:check(session.snapshot()==old,'refusal unchanged state')
 else:raise AssertionError('unexpected accepted action')
rows=[json.loads(x) for x in (R/'Build'/L/'chromatic-mediant-overlays.jsonl').read_text().splitlines()];base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()][17:23]
source=json.loads((R/'Build'/L/'source-check.json').read_text());lines=(R/source['original_txt']['path']).read_text().splitlines();pdf=PdfReader(R/source['original_pdf']['path']);tuning={'e':64,'B':59,'G':55,'D':50,'A':45,'E':40};strings={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6};pcs={'C':0,'C#':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'Ab':8,'A':9,'B':11}
for r,old in zip(rows,base):
 check(r['package_key']==old['package_key'] and r['source_identity']==old['source_identity'],'keys unchanged');check(r['implementation']['events']==old['implementation']['events'],'all event objects exact')
 j=old['provenance']['exact_conversion_joins'][0];lo,hi=j['txt_event_lines'];block=lines[lo-1:hi];page=pdf.pages[j['pdf_physical_page']-1].extract_text()
 for line in block:check(line.strip() in page,'original TXT block equals PDF stream')
 notes=block[0].split('|')[1:];roles=block[1].split('|')[1:];rawrows={line.strip().split('|')[0]:line.strip().split('|')[1:] for line in block[2:]};parsed=[]
 for bar,segment in enumerate(notes):
  for note in re.finditer(r'[A-G](?:#|b)?',segment):
   column=note.start();found=[]
   for string,data in rawrows.items():
    for fret in re.finditer(r'\d+',data[bar]):
     if fret.start()==column:found.append((string,int(fret.group())))
   check(len(found)==1,'exact one printed contact per note');string,fret=found[0];role=re.match(r'[A-Za-z0-9#]+',roles[bar][column:]).group();parsed.append((string,fret,note.group(),role,tuning[string]+fret))
 check(len(parsed)==12,'twelve contacts')
 for parsed_event,event in zip(parsed,r['implementation']['events']):
  string,fret,note,role,midi=parsed_event
  check((event['string_name'],event['fret'],event['printed_note'],event['printed_role'])==(string,fret,note,role),'source contact parity')
  check(event['string_number']==strings[string] and event['written_pitch_theory']['midi_at_stated_standard_tuning']==midi and midi%12==pcs[note],'independent standard pitch parity')
  check(event['onset_q'] is None and event['duration_q'] is None and event['finger'] is None,'no invented timing/finger')
 c=r['implementation']['task']['contract'];distinct=len({x[4] for x in parsed[4:8]});check(c['register_extent']['distinct_midi_pitches']==distinct,'register computation')
 session=m.MediantSession(c)
 if not c['complete_manual_contract']:
  check(distinct==3 and r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING','only precise pending scope');check(session.stage=='source_extent_pending','pending state')
  refused(lambda:session.configure(session.token(),True,'chosen dominant','chosen tonic','chosen pulse','yes'),session);refused(lambda:session.begin(session.token()),session)
  before=session.snapshot()['source_script'];tok=session.token();session.cancel(tok);refused(lambda:session.reopen(tok,True),session);session.reopen(session.token(),True)
  check(session.snapshot()['source_script']==before and not session.snapshot()['manual_reports_complete'],'source intact/pending after reopen');continue
 check(distinct==4 and r['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT','exact three completable')
 for bad in (False,None,1):refused(lambda b=bad:session.configure(session.token(),b,'dominant','tonic','free manual timing','yes'),session)
 refused(lambda:session.configure(session.token(),True,'','tonic','timing','yes'),session)
 session.configure(session.token(),True,'learner selected dominant voicing','learner selected tonic voicing','learner chosen unmeasured pulse','uncertain');check(session.stage=='choice_review','uncertain intent not ready');refused(lambda:session.begin(session.token()),session)
 t=session.token();session.configure(t,True,'chosen dominant','chosen tonic','manual timing','yes');refused(lambda:session.configure(t,True,'new','new','timing','yes'),session);check(len(session.history)==1,'prior choice retained')
 ready=session.token();other=m.MediantSession(c);refused(lambda:session.begin(other.token()),session);refused(lambda:session.begin(replace(ready,route='other')),session)
 session.begin(ready);refused(lambda:session.begin(ready),session);refused(lambda:session.report_cadence(session.token(),'yes','yes','early'),session)
 celltoken=session.token();session.report_cell(celltoken,'yes','yes','yes','printed source and bridge performed');refused(lambda:session.report_cell(celltoken,'yes','yes','yes','duplicate'),session)
 saved=session.snapshot();ct=session.token();session.cancel(ct);refused(lambda:session.reopen(ct,True),session);refused(lambda:session.reopen(session.token(),False),session);session.reopen(session.token(),True)
 check(session.cell==saved['cell'] and session.choice==saved['choice'] and session.stage=='perform_chosen_cadence','cancel preserves source phase/choice/reports')
 session.report_cadence(session.token(),'yes','yes','chosen cadence performed and destination heard, self-report');check(not session.snapshot()['manual_reports_complete'],'release required')
 refused(lambda:session.release(session.token(),False),session);rel=session.token();session.release(rel,True);refused(lambda:session.release(rel,True),session);check(session.snapshot()['manual_reports_complete'],'reports complete')
 for flag in ('performance_observed','app_audio_supplied','harmonic_validation_supplied','Attempt_credit','mastery_awarded','persistence_supplied'):check(session.snapshot()[flag] is False,'no inferred '+flag)
 oldtoken=session.token();oldchoice=session.choice.copy();session.request_retry(oldtoken,'repeat');refused(lambda:session.retry_release(session.token(),False),session);session.retry_release(session.token(),True)
 check(session.pass_number==2 and session.choice==oldchoice and session.cell is None and session.cadence is None and len(session.history)>=4,'retry preserves history/choice');refused(lambda:session.request_retry(oldtoken,'stale'),session)
 # Each source/cadence obligation individually false/uncertain blocks completion and retains its report.
 for phase,count in [('cell',3),('cadence',2)]:
  for index in range(count):
   for answer in ('no','uncertain'):
    ss=m.MediantSession(c);ss.configure(ss.token(),True,'dominant','tonic','timing','yes');ss.begin(ss.token());values=['yes']*3
    if phase=='cell':values[index]=answer
    ss.report_cell(ss.token(),*values,'retained explanation')
    if phase=='cadence':vals=['yes','yes'];vals[index]=answer;ss.report_cadence(ss.token(),*vals,'retained explanation')
    else:refused(lambda:ss.report_cadence(ss.token(),'yes','yes','skipped failed cell'),ss)
    ss.release(ss.token(),True);check(ss.stage=='retry_required' and not ss.snapshot()['manual_reports_complete'],'unsatisfied duty blocks complete')
    check(any(answer==v for v in (ss.cell if phase=='cell' else ss.cadence).values()),'negative answer retained')
check(sum(r['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT' for r in rows)==3,'three completed')
check(sum(r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING' for r in rows)==3,'three pending')
for ref in (source['original_pdf'],source['original_txt']):check(hashlib.sha256((R/ref['path']).read_bytes()).hexdigest()==ref['sha256'],'original source final pin')
out={'status':'PASS','checks':checks,'source_contacts_independently_parsed':72,'complete_manual_cases':3,'register_extent_pending_cases':3,'physical_pages_text_checked':[8,9],'synthetic_manual_responses_only':True,'new_source_events':0,'native_runs':0,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
