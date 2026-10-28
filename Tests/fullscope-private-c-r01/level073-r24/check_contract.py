from pathlib import Path
from dataclasses import replace
import copy,datetime,hashlib,json,re,resource,sys,time
ROOT=Path(__file__).resolve().parents[3];LANE=Path('fullscope-private-c-r01/level073-r24')
sys.path.insert(0,str(ROOT/'Tools'/LANE))
from bridge_contract import BridgeSession
checks=0;tick=time.monotonic()
def ck(v,label):
 global checks
 checks+=1
 if not v:raise AssertionError(label)
def refusal(s,fn,label):
 before=s.snapshot();token=s.token()
 try:fn()
 except ValueError:pass
 else:raise AssertionError('not refused: '+label)
 ck(s.snapshot()==before and s.token()==token,label+' is an atomic refusal')
def setup(s):s.setup(s.token(),True,'Synthetic chosen pulse','Synthetic chosen articulation')
def segments(s,failed=None):
 for n in range(1,5):
  current=s.current();ck(current['segment_number']==n,'current exact segment')
  expected=list(range((n-1)*4+1,n*4+1)) if n<4 else [9,10,11,12]
  ck(current['source_orders']==expected,'source order and tonic repeat reference')
  ck(current['contacts']==[s.c['printed_contacts'][i-1] for i in expected],'actual contacts for repeat derive from source')
  current['contacts'][0]['fret']=-1;ck(s.current()['contacts'][0]['fret']>=0,'presentation copy cannot alter source')
  old=s.token();s.report_segment(old,n,'uncertain' if n==failed else 'yes','Synthetic own-instrument report')
  refusal(s,lambda:s.report_segment(old,n,'yes','queued duplicate'),'stale action cannot acknowledge another segment')
 ck(s.stage=='summary' and s.current() is None,'tonic repeat complete before summary')
def summary(s,connected='yes',dominant='yes'):
 s.report_bridge(s.token(),connected,dominant,'Synthetic own-hearing report')
def full(s):
 s.begin(s.token());segments(s);summary(s);s.release(s.token(),True)

packet=ROOT/'Build'/LANE/'pivot-bridge-overlays.jsonl';rows=list(map(json.loads,packet.read_text().splitlines()))
base=list(map(json.loads,(ROOT/'Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl').read_text().splitlines()))[29:34]
ck(len(rows)==5 and [r['package_key'] for r in rows]==[r['package_key'] for r in base],'five exact original keys')
lines=next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*')).read_text().splitlines()
opens={'e':64,'B':59,'G':55,'D':50,'A':45,'E':40}
for r,b in zip(rows,base):
 c=r['implementation']['task']['contract'];events=r['implementation']['events'];join=r['provenance']['exact_conversion_joins'][0]
 ck(events==b['implementation']['events']==c['printed_contacts'],'all twelve source objects unchanged')
 ck(r['source_payload']==b['source_payload'] and r['source_refs']==b['source_refs'],'original custody untouched')
 ck(all(e['onset_q'] is None and e['duration_q'] is None for e in events),'no fabricated q timing')
 lo,hi=join['txt_event_lines'];block=lines[lo-1:hi];nte=block[0].split('|')[1:-1];rol=block[1].split('|')[1:-1];parsed=[]
 for bar in range(3):
  for stringline in block[2:]:
   name=stringline.split('|')[0].strip()
   for m in re.finditer(r'\d+',stringline.split('|')[bar+1]):
    col=m.start();parsed.append((bar+1,col,name,int(m.group()),re.match(r'[A-G][#b]?',nte[bar][col:]).group(),re.match(r'[^-]+',rol[bar][col:]).group()))
 parsed.sort(key=lambda x:(x[0],x[1]));ck(len(parsed)==12,'independent TXT literal contact census')
 for e,p in zip(events,parsed):
  ck((e['printed_bar'],e['printed_column'],e['string_name'],e['fret'],e['printed_note'],e['printed_role'])==p,'original literal TAB/note/role position')
  ck(e['written_pitch_theory']['midi_at_stated_standard_tuning']==opens[p[2]]+p[3],'source standard-tuning pitch parity')
 ck(c['printed_function']==lines[lo-3] and c['printed_bridge']==lines[lo-2],'exact pivot function and chord bridge')
 ck(c['segments'][3]['source_orders']==[9,10,11,12] and c['segments'][3]['origin']=='source_required_tonic_repeat_reference','repeat is reference use rather than new source events')
 ck('Repeat the final tonic once before looping.' in c['source_instruction'] and 'before replaying the full cell.' in c['source_failure_repair'],'full practice and repair instructions retained')
 ck([s['chord_symbol'] for s in c['segments']]==join['facts']['chords']+[join['facts']['chords'][-1]],'no source-tonic prefix or wrong repeat')
 for candidate in c['repair_candidates']:
  e=events[candidate['source_order']-1];bar=e['printed_bar']
  common=any(other['written_pitch_theory']['pitch_class']==e['written_pitch_theory']['pitch_class'] and abs(other['printed_bar']-bar)==1 for other in events)
  guide=e['printed_role'] in ('3','b3','7','b7')
  ck(common or guide,'repair candidate is source-supported common/guide-tone contact')
  ck(bool(candidate['basis']),'candidate derivation disclosed')
 ck(len({x['source_order'] for x in c['repair_candidates']})==len(c['repair_candidates']),'candidate menu no duplicate source identities')
 for ref in [*r['source_refs'],c['state_engine_ref'],c['source_page']['verification']]:
  ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest()==ref['sha256'],'source/engine proof pin')
 s=BridgeSession(c);refusal(s,lambda:s.begin(s.token()),'setup prerequisite');refusal(s,lambda:s.setup(s.token(),False,'p','a'),'own instrument prerequisite')
 refusal(s,lambda:s.setup(s.token(),True,'','a'),'pulse choice explicit')
 refusal(s,lambda:s.setup(BridgeSession(c).token(),True,'p','a'),'foreign instance refused')
 refusal(s,lambda:s.setup(replace(s.token(),route='wrong'),True,'p','a'),'foreign route refused')
 setup(s);ready=s.token();s.begin(ready);refusal(s,lambda:s.begin(ready),'duplicate start')
 refusal(s,lambda:s.report_segment(s.token(),2,'yes','skip'),'pivot cannot be skipped')
 refusal(s,lambda:s.report_segment(s.token(),True,'yes','bool'),'bool segment refused')
 refusal(s,lambda:s.report_segment(s.token(),1,True,'bool'),'non-report refused')
 for n in (1,2,3):s.report_segment(s.token(),n,'yes','Synthetic original segment')
 ck(s.current()['role']=='repeat_final_tonic_once','tonic repeat is actual displayed fourth action')
 refusal(s,lambda:summary(s),'summary cannot skip required tonic repeat');refusal(s,lambda:s.choose(s.token(),'loop'),'loop cannot skip tonic repeat')
 s.report_segment(s.token(),4,'yes','Synthetic final tonic repeat');summary(s)
 refusal(s,lambda:s.choose(s.token(),'finish'),'finish waits for manual release');refusal(s,lambda:s.release(s.token(),False),'negative release refused')
 old=s.token();s.release(old,True);refusal(s,lambda:s.release(old,True),'double release refused')
 choice=s.token();s.choose(choice,'loop');ck(s.loop==2 and s.stage=='ready','explicit loop choice and reset')
 refusal(s,lambda:s.choose(choice,'finish'),'old loop choice cannot finish current loop')
 refusal(s,lambda:s.begin(replace(s.token(),loop=1)),'old loop token refused')
 full(s);s.choose(s.token(),'finish');ck(s.snapshot()['manual_task_reports_complete'],'five campaigns each with two full loops and explicit finish')
 ck(len([h for h in s.history if h['kind']=='released_bridge'])==2,'both loop reports retained')
 ck(not any(s.snapshot()[k] for k in ('performance_observed','app_audio_supplied','Attempt_credit','mastery_awarded','persistence_supplied')),'manual reporting no audio/progress credit')
 # Footer's explicit repair path after disconnected bridge.
 t=BridgeSession(c);setup(t);t.begin(t.token());segments(t);summary(t,connected='no')
 refusal(t,lambda:t.request_retry(t.token(),'bypass'),'cannot bypass diagnosed repair before release')
 t.release(t.token(),True);ck(t.stage=='repair_required','unrelated arpeggios route to printed repair')
 refusal(t,lambda:t.begin(t.token()),'full replay waits for repair');refusal(t,lambda:t.request_retry(t.token(),'bypass'),'generic retry cannot bypass repair')
 refusal(t,lambda:t.choose_repair(t.token(),99,'bad'),'foreign repair source order refused')
 refusal(t,lambda:t.choose_repair(t.token(),True,'bad'),'bool repair source refused')
 tone=c['repair_candidates'][0]['source_order'];token=t.token();t.choose_repair(token,tone,'Synthetic relation and hold plan')
 refusal(t,lambda:t.choose_repair(token,tone,'duplicate'),'repair choice cannot repeat')
 refusal(t,lambda:t.report_repair(t.token(),True,'yes','bad'),'repair report schema explicit')
 before=copy.deepcopy(t.repair);old=t.token();t.cancel(old);refusal(t,lambda:t.report_repair(old,'yes','yes','queued'),'cancel fences repair report')
 t.reopen(t.token(),True);ck(t.repair==before and t.stage=='repair_report','reopen retains selected repair and original failed reports')
 refusal(t,lambda:t.report_repair(old,'yes','yes','queued'),'old repair token invalid after reopen')
 t.report_repair(t.token(),'uncertain','yes','Synthetic uncertain sustain');t.release_repair(t.token(),True)
 ck(t.stage=='repair_required' and t.history[-1]['repair']['sustained_chosen_tone_self_report']=='uncertain','uncertain sustain retained, no replay')
 t.choose_repair(t.token(),tone,'Synthetic revised hold plan');t.report_repair(t.token(),'yes','no','Synthetic dominant not heard');t.release_repair(t.token(),True)
 ck(t.stage=='repair_required','dominant hearing obligation cannot be omitted')
 t.choose_repair(t.token(),tone,'Synthetic revised hold plan');t.report_repair(t.token(),'yes','yes','Synthetic manual repair')
 refusal(t,lambda:t.release_repair(t.token(),False),'repair manual release required');t.release_repair(t.token(),True)
 ck(t.stage=='ready' and t.reports==[] and any(h['kind']=='released_bridge' and h['summary']['connected_bridge_self_report']=='no' for h in t.history),'repair enables full replay retaining failed bridge')
 full(t);t.choose(t.token(),'finish');ck(t.snapshot()['manual_task_reports_complete'],'all five complete repair then full bridge paths')
 # Incomplete source arpeggio -> explicit retry; history and cancel/reopen position preserved.
 u=BridgeSession(c);setup(u);u.begin(u.token());segments(u,failed=2);summary(u);u.release(u.token(),True)
 ck(u.stage=='retry_required','uncertain arpeggio not completed');old=u.token();u.request_retry(old,'Synthetic missed source notes')
 refusal(u,lambda:u.retry_release(u.token(),False),'retry release required');u.retry_release(u.token(),True)
 ck(u.stage=='ready' and u.reports==[] and len(u.history)>=3,'retry retains failed reports');refusal(u,lambda:u.request_retry(old,'stale'),'old failed action invalid')
 u.begin(u.token());u.report_segment(u.token(),1,'yes','Synthetic pivot');old=u.token();held=copy.deepcopy(u.reports);u.cancel(old)
 ck(u.current() is None,'cancel hides executable action');refusal(u,lambda:u.reopen(u.token(),False),'release before reopen')
 u.reopen(u.token(),True);ck(u.reports==held and u.current()['segment_number']==2,'mid-bridge position retained')
 refusal(u,lambda:u.report_segment(old,2,'yes','old'),'stale pre-cancel ack refused')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'elapsed_seconds':time.monotonic()-tick,
        'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'packet_sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),
        'five_two_loop_campaigns':True,'five_printed_repair_campaigns':True,'all_performance_reports_synthetic':True,'native_app_gui':'NOT_RUN',
        'original_source_contacts':60,'source_required_repeat_reference_uses':20}
p=ROOT/'Results'/LANE/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
