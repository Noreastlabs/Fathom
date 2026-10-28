from pathlib import Path
from dataclasses import replace
import copy,datetime,hashlib,json,re,resource,sys,time
ROOT=Path(__file__).resolve().parents[3];LANE=Path('fullscope-private-c-r01/level073-r25')
sys.path.insert(0,str(ROOT/'Tools'/LANE))
from motif_contract import MotifSession
checks=0;tick=time.monotonic()
def ck(v,msg):
 global checks
 checks+=1
 if not v:raise AssertionError(msg)
def refusal(s,fn,msg):
 before=s.snapshot();token=s.token()
 try:fn()
 except ValueError:pass
 else:raise AssertionError('no refusal '+msg)
 ck(s.snapshot()==before and s.token()==token,msg+' leaves state intact')
def setup(s):s.setup(s.token(),True,True,'Synthetic rhythm plan','Synthetic articulation plan','Synthetic phrase-length plan')
def performed(s,source='yes',dest='yes',rhythm='yes',articulation='yes',length='yes'):
 s.begin(s.token());s.report_source(s.token(),source,'Synthetic performer source report')
 s.report_destination(s.token(),dest,rhythm,articulation,length,'Synthetic performer destination report');s.release(s.token(),True)
packet=ROOT/'Build'/LANE/'motif-comparison-overlays.jsonl';rows=list(map(json.loads,packet.read_text().splitlines()))
base=list(map(json.loads,(ROOT/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()))[23:29]
ck(len(rows)==6 and [r['package_key'] for r in rows]==[r['package_key'] for r in base],'six exact original keys')
lines=next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*')).read_text().splitlines();opens={'e':64,'B':59,'G':55,'D':50,'A':45,'E':40}
for r,b in zip(rows,base):
 c=r['implementation']['task']['contract'];events=r['implementation']['events'];j=r['provenance']['exact_conversion_joins'][0]
 ck(events==b['implementation']['events']==c['source_script']['source_motif']+c['source_script']['destination_motif'],'all source contact objects exactly retained')
 ck(r['source_payload']==b['source_payload'] and r['source_refs']==b['source_refs'],'original source custody unchanged')
 ck(all(e['onset_q'] is None and e['duration_q'] is None and e['finger'] is None for e in events),'no metric/fingering invention')
 lo,hi=j['txt_event_lines'];block=lines[lo-1:hi];notes=block[0].split('|')[1:];roles=block[1].split('|')[1:];parsed=[]
 for n in range(2):
  for stringline in block[2:]:
   name=stringline.split('|')[0].strip()
   for m in re.finditer(r'\d+',stringline.split('|')[n+1]):
    col=m.start();parsed.append((n+1,col,name,int(m.group()),re.match(r'[A-G][#b]?',notes[n][col:]).group(),re.match(r'[^-]+',roles[n][col:]).group()))
 parsed.sort(key=lambda t:(t[0],t[1]));ck(len(parsed)==16,'independent original TXT contact census')
 for e,p in zip(events,parsed):
  ck((e['printed_bar'],e['printed_column'],e['string_name'],e['fret'],e['printed_note'],e['printed_role'])==p,'literal source note/role/TAB parity')
  ck(e['written_pitch_theory']['midi_at_stated_standard_tuning']==opens[p[2]]+p[3],'standard-tuning pitch parity')
 ck([e['printed_role'] for e in events[:8]]==[e['printed_role'] for e in events[8:]]==c['source_script']['degree_formula'],'exact degree contour preserved')
 ck(c['source_script']['route_label']==lines[lo-3] and 'Degree formula: '+'-'.join(c['source_script']['degree_formula'])==lines[lo-2],'exact source route/formula')
 ck(c['source_instruction'].endswith('before identifying the new key.'),'complete ordered listener instruction')
 for ref in [*r['source_refs'],c['state_engine_ref'],c['source_page']['verification']]:
  ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256'],'source/engine verification pin')
 s=MotifSession(c)
 ck(s.performer_view()['source_script']==c['source_script'],'full source-player script never erased')
 listener=s.listener_view();ck(listener['reference'] is None and not listener['reference_previously_revealed'],'initial listener answer withheld')
 ck(not any(k in listener for k in ('route','route_label','package_key','source_script','degree_formula','events')),'listener projection omits answer-bearing source metadata')
 refusal(s,lambda:s.begin(s.token()),'setup required')
 refusal(s,lambda:s.setup(s.token(),True,False,'r','a','l'),'external listener prerequisite')
 refusal(s,lambda:s.setup(s.token(),False,True,'r','a','l'),'own instrument prerequisite')
 refusal(s,lambda:s.setup(s.token(),True,True,'','a','l'),'manual rhythm choice explicit')
 refusal(s,lambda:s.setup(MotifSession(c).token(),True,True,'r','a','l'),'foreign instance')
 refusal(s,lambda:s.setup(replace(s.token(),route='foreign'),True,True,'r','a','l'),'foreign route')
 setup(s);old=s.token();s.begin(old);refusal(s,lambda:s.begin(old),'duplicate start')
 ck(s.performer_view()['current_motif']=='source','source motif first')
 refusal(s,lambda:s.report_destination(s.token(),'yes','yes','yes','yes','skip'),'destination cannot precede source')
 refusal(s,lambda:s.name_key(s.token(),'premature'),'no premature key response')
 refusal(s,lambda:s.reveal(s.token()),'no premature answer reveal')
 old=s.token();s.report_source(old,'yes','Synthetic source');refusal(s,lambda:s.report_source(old,'yes','queued'),'duplicate source acknowledgment')
 ck(s.performer_view()['current_motif']=='destination','exact destination motif second')
 refusal(s,lambda:s.report_destination(s.token(),'yes',True,'yes','yes','bad'),'bool preservation report refused')
 s.report_destination(s.token(),'yes','yes','yes','yes','Synthetic preserved rhythm/articulation/length')
 refusal(s,lambda:s.recognize(s.token(),'yes','premature'),'listener response waits for instrument release')
 refusal(s,lambda:s.release(s.token(),False),'negative manual release refused')
 s.release(s.token(),True)
 refusal(s,lambda:s.name_key(s.token(),c['destination_key']),'recognition before key identification')
 old=s.token();s.recognize(old,'yes','Synthetic recognition before key name');refusal(s,lambda:s.recognize(old,'yes','double'),'recognition double action refused')
 ck(s.listener_view()['reference'] is None,'recognized motif does not automatically reveal key')
 refusal(s,lambda:s.name_key(s.token(),''),'independent key text required')
 # Deliberately wrong text can be stored; it is not autocorrected or scored.
 s.name_key(s.token(),'Synthetic independent key response')
 ck(s.key_response['key_text']=='Synthetic independent key response' and not s.key_response['automatically_graded'],'source reference never copied into listener response')
 ck(s.listener_view()['reference'] is None,'key submission still awaits explicit reveal')
 old=s.token();s.reveal(old);refusal(s,lambda:s.reveal(old),'duplicate reveal refused')
 ck(s.listener_view()['reference']==c['destination_key'] and s.key_response['key_text']=='Synthetic independent key response','reference shown separately from independent answer')
 old=s.token();prior=copy.deepcopy(s.snapshot());s.cancel(old)
 ck(s.listener_view()['reference']==c['destination_key'] and s.performer_view()['source_script']==c['source_script'],'cancel retains exposed answer and player script')
 refusal(s,lambda:s.compare(old,'yes','queued'),'cancel fences listener compare');refusal(s,lambda:s.reopen(s.token(),False),'release before reopen')
 s.reopen(s.token(),True)
 ck(s.key_response==prior['key_response'] and s.reference_revealed and s.stage=='comparison','reopen preserves source response/reveal stage')
 refusal(s,lambda:s.compare(old,'yes','stale'),'pre-cancel acknowledgment invalid after reopen')
 s.compare(s.token(),'yes','Synthetic manual comparison; no automatic grading')
 ck(s.snapshot()['manual_task_reports_complete'],'six full manual performer/listener campaigns')
 ck(not any(s.snapshot()[k] for k in ('performance_observed','app_audio_supplied','Attempt_credit','mastery_awarded','persistence_supplied')),'no acoustic/progress claims')
 old=s.token();s.request_retry(old,'Synthetic further practice');refusal(s,lambda:s.retry_release(s.token(),False),'explicit release before new pass')
 s.retry_release(s.token(),True)
 ck(s.reference_revealed and s.listener_view()['reference_previously_revealed'] and not s.listener_view()['fresh_unseen_listening_claim'],'retry cannot erase prior answer exposure')
 ck(s.pass_number==2 and s.key_response is None and any(h.get('key_response',{} ) and h['key_response']['key_text']=='Synthetic independent key response' for h in s.history),'retry resets current response but retains independent old response/history')
 refusal(s,lambda:s.request_retry(old,'queued'),'old pass action cannot mutate new pass')
 refusal(s,lambda:s.begin(replace(s.token(),pass_number=1)),'old pass token refused')
 s.begin(s.token());old=s.token();s.cancel(old);s.reopen(s.token(),True)
 ck(s.performer_view()['current_motif']=='source' and s.reference_revealed,'mid-perform cancel/reopen preserves source position and prior exposure')
# Each distinct printed preservation/recognition/comparison obligation refuses completion when unsatisfied.
c=rows[0]['implementation']['task']['contract']
for failed in ('source','dest','rhythm','articulation','length','recognition','comparison'):
 s=MotifSession(c);setup(s);kwargs={failed:'uncertain'} if failed in ('source','dest','rhythm','articulation','length') else {}
 performed(s,**kwargs)
 if failed in ('recognition','comparison'):
  s.recognize(s.token(),'no' if failed=='recognition' else 'yes','Synthetic listener report')
  if failed=='comparison':s.name_key(s.token(),'Synthetic wrong key');s.reveal(s.token());s.compare(s.token(),'no','Synthetic mismatch')
 ck(s.stage=='retry_required' and not s.snapshot()['manual_task_reports_complete'],failed+' cannot count as completed reports')
 prior=copy.deepcopy(s.snapshot());s.request_retry(s.token(),'Synthetic corrective practice');s.retry_release(s.token(),True)
 saved=next(h for h in reversed(s.history) if h['kind']=='retry_requested')
 ck(saved['performance']==prior['performance'] and saved['recognition']==prior['recognition'] and saved['comparison']==prior['comparison'],failed+' retained verbatim through retry')
 ck(s.reference_revealed==prior['reference_revealed'],failed+' prior exposure preserved')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'elapsed_seconds':time.monotonic()-tick,
        'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),
        'six_manual_campaigns':True,'all_performance_reports_synthetic':True,'native_app_gui':'NOT_RUN','original_source_contacts':96}
p=ROOT/'Results'/LANE/'integrity.json';ck(not p.exists(),'fresh output');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
