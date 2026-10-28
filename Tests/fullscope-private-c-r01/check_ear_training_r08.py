from pathlib import Path
import sys,json,datetime,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'Tools/fullscope-private-c-r01'));from ear_training_contract_r08 import EarTrainingSession
checks=0

def ck(v,m):
 global checks
 checks+=1
 if not v:raise AssertionError(m)
def refuses(fn):
 try:fn()
 except ValueError:return True
 return False
p=ROOT/'Build/fullscope-private-c-r01/level073-r08/ear-training-record-overlay.json';r=json.loads(p.read_text());c=r['implementation']['task']['contract'];joined=c['joined_source_instruction'];ck(joined=='Sing the retained tone, identify the pivot chord in both keys, and name the bar where the destination tonic becomes stable. Record before checking the score.','full joined source');ck(c['source_line_range']==[2,3],'source range');ck(len(c['source_obligations'])==5,'all obligations');ck(c['source_obligations'][-1]['precedes']=='score_reference_reveal','source ordering')
answers={'retained_tone':'E','pivot_function_source_key':'iii','pivot_function_destination_key':'ii','stable_destination_tonic_bar':'6','singing_self_report':True};synthetic=True
s=EarTrainingSession();ck(refuses(s.reveal_reference),'early reveal');ck(refuses(lambda:s.record({'kind':'microphone_capture'})),'capture not supported');ck(refuses(lambda:s.record({'kind':'self_report','declaration':''})),'empty recording declaration');ck(refuses(lambda:s.respond({'retained_tone':'E'})),'incomplete answer');ck(refuses(lambda:s.respond(dict(answers,automatic_score=100))),'foreign automatic score')
s.respond(answers);ck(refuses(s.reveal_reference),'answers alone insufficient');s.cancel();saved=s.snapshot();ck(saved['responses']==answers and saved['recording_report'] is None,'partial preserved');ck(refuses(s.reveal_reference),'cancelled reveal');ck(refuses(lambda:s.record({'kind':'self_report','declaration':'Synthetic test recording report'})),'cancelled edit');ck(s.reopen()=='awaiting_manual_input','reopen partial');s.record({'kind':'self_report','declaration':'Synthetic test recording report; no audio observed'});ck(s.state()=='ready_for_reference','reported recording and answers');v=s.reveal_reference();ck(v['source_reference_access'] and not v['verified_pass'] and not v['attempt_credit'] and not v['mastery_awarded'] and not v['audio_inspected'],'no fabricated verification');s.cancel();ck(s.snapshot()['reference_was_ever_revealed'],'prior disclosure retained on cancel');s.reopen();ck(s.snapshot()['reference_was_ever_revealed'],'prior disclosure retained on reopen')
s2=EarTrainingSession();s2.record({'kind':'local_or_external_reference','reference':'Synthetic fixture reference only; intentionally no file inspection'});ck(refuses(s2.reveal_reference),'recording reference alone insufficient');s2.respond(dict(answers,singing_self_report=False));ck(s2.state()=='ready_for_reference','failed singing self-report still a response, not a verified pass');v=s2.reveal_reference();ck(not v['verified_pass'],'failure not auto-evaluated');snap=s2.snapshot();snap['responses']['retained_tone']='mutated';ck(s2.snapshot()['responses']['retained_tone']=='E','snapshot isolated');ck(not s2.snapshot()['attempt_credit'] and not s2.snapshot()['mastery_awarded'],'no credit')
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'synthetic_test_only':True,'recording_audio_inspected':False,'overlay_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'runtime_native_gui':'NOT_RUN'};dest=ROOT/'Results/fullscope-private-c-r01/level073-r08/integrity.json';ck(not dest.exists(),'immutable');dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
