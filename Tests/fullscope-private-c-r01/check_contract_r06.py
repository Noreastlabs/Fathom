#!/usr/bin/env python3
from pathlib import Path
import sys,json,copy,hashlib,datetime,importlib.util
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Tools/fullscope-private-c-r01'))
from task_contract_r06 import ManualTaskSession
CATEGORIES={'TIMED_SOURCE_EVENT_CONTRACT','COMPLETE_MANUAL_NONPLAYBACK_CONTRACT','IMPLEMENTATION_OR_INTERPRETATION_PENDING','LEARNER_CHOICE_WITHOUT_FIXED_REALIZATION','DEMONSTRATED_SOURCE_CONFLICT'}
checks=0

def ck(x,msg):
 global checks
 checks+=1
 if not x:raise AssertionError(msg)
def refuse(fn):
 try:fn()
 except ValueError:return True
 return False

def main(n):
 p=ROOT/'Build/fullscope-private-c-r01'/f'level{n:03d}-r06'/'implementation-packet.jsonl';rr=[json.loads(s) for s in p.read_text().splitlines()];manual=0
 for r in rr:
  ck(r['contract_category'] in CATEGORIES,'category');c=r['implementation']['task']['contract'];ck(not c['performance_observed'] and not c['credit_awarded'] and not c['automatic_evaluation'],'fabricated evidence')
  for s in c['source_sequences']:ck(s['source_field']['value'] is not None and s['tokens'],'empty typed sequence')
  if r['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT':
   manual+=1;ck(bool(c['response_fields']),'manual shell');ck(all(f['learner_value'] is None for f in c['response_fields']),'source answer leaked')
   answers={f['key']:f['printed_minimum'] if f['type']=='integer' else 'Synthetic integrity-test response; not a learner observation' for f in c['response_fields']}
   session=ManualTaskSession(r);ck(session.state=='awaiting_manual_response','initial');ck(refuse(lambda:session.submit({})),'missing response refusal');ck(refuse(lambda:session.submit(dict(answers,foreign='x'))),'foreign response refusal')
   bad=copy.deepcopy(answers);f=c['response_fields'][0];bad[f['key']]=f['printed_maximum']+1 if f['type']=='integer' else '';ck(refuse(lambda:session.submit(bad)),'invalid value refusal')
   result=session.submit(answers);ck(result['state']=='manual_response_recorded','submit');ck(not result['verified_pass'] and not result['credit_awarded'] and not result['mastery_awarded'],'manual not verified credit');ck(refuse(lambda:session.submit(answers)),'closed duplicate refusal')
   s2=ManualTaskSession(r);s2.cancel();ck(refuse(lambda:s2.submit(answers)),'cancelled submission refusal')
  else:ck(refuse(lambda:ManualTaskSession(r)),'incomplete manual refusal')
  if r['contract_category']=='TIMED_SOURCE_EVENT_CONTRACT':ck(all(e['onset_q'] is not None for e in r['implementation']['events']),'timed shell')
  if r['contract_category']=='DEMONSTRATED_SOURCE_CONFLICT':ck(bool(r['contract_capabilities']['demonstrated_source_conflicts']),'conflict without evidence')
  if r['source_identity']=='level080/modulea/p003-card01/cmaj7melodyefge':ck(r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING','L80 full-unit overclaim')
 out={'schema':'fathom-private-contract-integrity.1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'level':n,'result':'PASS','checks':checks,'manual_contracts_tested':manual,'packet_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'synthetic_test_data':True,'runtime_native_gui':'NOT_RUN'};dest=ROOT/'Results/fullscope-private-c-r01'/f'level{n:03d}-r06'/'contract-integrity.json';ck(not dest.exists(),'immutable');dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'level':n,'contract_checks':checks,'manual_contracts':manual,'result':'PASS'}))
if __name__=='__main__':main(int(sys.argv[1]))
