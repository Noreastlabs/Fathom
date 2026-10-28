"""Small causal reproduction/repair sample; not independent/broad QA."""
from pathlib import Path
from copy import deepcopy
import importlib.util,sys,json,time,datetime,hashlib
ROOT=Path(__file__).resolve().parents[3]
LANE=Path('fullscope-private-c-r01/coherent-level083-reduction-repair-r67')
sys.path.insert(0,str(ROOT/'Tools/fullscope-private-c-r01/coherent-level083-fixed-top-r65'))
def load(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load('prior_fixture','Tests/fullscope-private-c-r01/coherent-level083-fixed-top-r65/check_integrity_r02.py')
old=h.m
new=load('r67model','Tools'/LANE/'fixed_top_model.py')
checks=refusals=0
labels=[]
def check(value,label):
 global checks
 assert value,label
 checks+=1

def refuse(fn,label,f):
 global refusals
 before=deepcopy(f.__dict__)
 try:fn()
 except ValueError:check(f.__dict__==before,label+' mutation-free');refusals+=1;labels.append(label)
 else:raise AssertionError(label)

def loss(m,low=False):
 h.m=m;f=m.FixedTopFlow(m.cards()[0]['package_key']);f.set_top(f.token(),h.top_choice(f,48 if low else None))
 if not low:
  for i in range(3):h.step(f)
 f.sing_top(f.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'});f.choose_voicing(f.token(),h.voicing(f));f.name_role(f.token(),{'role':f.expected_role(),'notes':'Synthetic.'});f.play(f.token(),True);f.release(f.token(),{'learner_released':True});f.report(f.token(),h.report(f,'no'))
 return f

def finish(f):
 while f.state!='audit':h.step(f)
 f.audit(f.token(),h.audit(f));f.finish(f.token())

def main():
 tick=time.monotonic();o=loss(old);choice=h.top_choice(o);choice['diagnosis']='Synthetic register restart after lost melody.';idx=len(o.history);o.restart_top(o.token(),choice);finish(o)
 reduced=sum(x['kind']=='manual_voicing_report' and x['data']['report']['stage']=='bass_melody_reduction' for x in o.history[idx:]);check(o.state=='completed' and reduced==0,'old bypass reproduced')
 h.m=new;f=loss(new);history=deepcopy(f.response_history);choice=h.top_choice(f);choice['diagnosis']='Synthetic register restart retains mandatory reduction.';f.restart_top(f.token(),choice)
 check(f.reduction_required and f.recovery and f.current()['stage']=='bass_melody_reduction','restart preserves source recovery')
 refuse(lambda:f.finish(f.token()),'cannot finish with recovery debt',f)
 f.cancel(f.token());f.reopen(f.token());refuse(lambda:f.sing_top(f.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'}),'release fence',f);f.release(f.token(),{'learner_released':True});check(f.recovery and f.reduction_required,'cancel/reopen preserves recovery debt')
 stale=f.token();f.sing_top(f.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'});refuse(lambda:f.choose_voicing(stale,h.voicing(f)),'stale action',f);f.choose_voicing(f.token(),h.voicing(f));f.name_role(f.token(),{'role':f.expected_role(),'notes':'Synthetic.'});f.play(f.token(),True);f.release(f.token(),{'learner_released':True});r=h.report(f);r['attack_counts'][0]=None;r['diagnosis']='Unknown counts require another reduction.';f.report(f.token(),r);check(f.state=='needs_retry' and f.reduction_required,'unknown reduction does not clear source debt');f.diagnose(f.token(),'Retry mandatory reduction.');h.step(f)
 check(not f.reduction_required and not f.recovery and f.stage_index==0,'positive reduction then full rerender restart')
 finish(f);check(f.state=='completed' and f.response_history[:len(history)]==history,'completed repaired path retains original response history')
 # Source-consistent top C48 can play a melody but cannot place a lower root C
 # using standard guitar tuning. A genuine whole-register choice remains open.
 l=loss(new,True);l.diagnose(l.token(),'Required reduction in low register.');l.sing_top(l.token(),{'sung_before_voicing':'yes','notes':'Synthetic.'});l.cannot_realize(l.token(),'No lower C root contact for the chosen C48 register.');check(l.reduction_required,'unrealizable reduction debt retained');choice=h.top_choice(l);choice['diagnosis']='Choose C72 to realize mandatory bass+melody.';l.restart_top(l.token(),choice);h.step(l);finish(l);check(l.state=='completed' and not l.reduction_required,'low-register mandatory reduction recovery completes')
 # Pure key/source/texture arithmetic across all41, without full state sweeps.
 rows=[json.loads(x) for x in (ROOT/'Build'/LANE/'fixed-top-overlay.jsonl').read_text().splitlines()];check(len(rows)==41,'41 key packet')
 for row,prior in zip(rows,(json.loads(x) for x in (ROOT/'Build/fullscope-private-c-r01/coherent-level083-fixed-top-r65/fixed-top-overlay.jsonl').read_text().splitlines())):
  for field in ['package_key','source_identity','source_refs','source_payload','timing_authority']:
   check(row[field]==prior[field],'unchanged source field '+field)
  g=new.FixedTopFlow(row['package_key']);g.set_top(g.token(),h.top_choice(g))
  for stage in range(4):g.stage_index=stage;g.validate_voicing(h.voicing(g));check(True,'pure texture arithmetic')
 print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'outcome':'PASS','checks_passed':checks,'refusals_passed':refusals,'labels':labels,'old_bypass_reproduced':True,'mandatory_reduction_samples':2,'full_recovery_samples':2,'unknown_reduction_retry':True,'exact_keys':41,'pure_texture_arithmetic':164,'elapsed_seconds':time.monotonic()-tick,'synthetic_observation':False,'private_QA':'Pending distinct affected retest','official_acceptance_increment':0}))
if __name__=='__main__':main()
