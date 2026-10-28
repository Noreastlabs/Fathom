"""Offline manual source-player/learner workflow; no audio or correctness claims."""
import copy
class TonicCardSession:
 def __init__(self,contract):
  self.c=copy.deepcopy(contract);self.pass_number=1;self.data={1:{},2:{}};self.cancelled=False;self.revealed_passes=[]
 def current(self):return self.data[self.pass_number]
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def source_view(self):
  self.active();return {'role':'source_player','source_notes':self.c['source_passes'][self.pass_number-1]['ordered_notes'],'expected_tonic':self.c['source_expected_tonic'],'withhold_label_until_commit':True,'audio_synthesized':False,'prerequisite':self.c['source_player_prerequisite']}
 def learner_view(self):
  self.active();d=self.current()
  if d.get('answer_committed') and self.pass_number not in self.revealed_passes:self.revealed_passes.append(self.pass_number)
  return {'role':'learner','pass':self.pass_number,'instructions':self.c['learner_pass_instructions'][self.pass_number-1],'expected_tonic':self.c['source_expected_tonic'] if d.get('answer_committed') else None,'prior_reference_disclosure':bool(self.revealed_passes),'performance_verified':False}
 def report_source_performed(self,declaration):
  self.active()
  if not isinstance(declaration,str) or not declaration.strip():raise ValueError('source-player declaration required')
  self.current()['source_performed_report']=declaration
 def report_singing_attempt(self,declaration):
  self.active()
  if not self.current().get('source_performed_report'):raise ValueError('source performance report precedes learner singing')
  if not isinstance(declaration,str) or not declaration.strip():raise ValueError('singing declaration required')
  self.current()['singing_attempt_report']=declaration
 def commit_answer(self,tonic,confidence):
  self.active();d=self.current()
  if not d.get('singing_attempt_report'):raise ValueError('singing report precedes answer')
  if not isinstance(tonic,str) or not tonic.strip():raise ValueError('tonic response required')
  if type(confidence) is not int or not 0<=confidence<=2:raise ValueError('printed confidence range0–2')
  if d.get('answer_committed'):raise ValueError('answer already committed for this pass')
  d.update(tonic_response=tonic,confidence=confidence,answer_committed=True,origin='manual_self_report',verified_correct=False)
 def reveal_label(self):
  self.active()
  if not self.current().get('answer_committed'):raise ValueError('answer commitment required before label reveal')
  if self.pass_number not in self.revealed_passes:self.revealed_passes.append(self.pass_number)
  return {'expected_tonic':self.c['source_expected_tonic'],'comparison':'manual only','verified_correct':False,'credit_awarded':False}
 def report_one_string_confirmation(self,string_number,declaration):
  self.active();d=self.current()
  if not d.get('singing_attempt_report') or not d.get('answer_committed'):raise ValueError('sing/name precedes one-string confirmation')
  if type(string_number) is not int or not 1<=string_number<=6:raise ValueError('one guitar string selection required')
  if not isinstance(declaration,str) or not declaration.strip():raise ValueError('manual guitar confirmation declaration required')
  d['one_string_confirmation']={'string_number':string_number,'declaration':declaration,'observed':False}
 def begin_second_pass(self):
  self.active()
  if self.pass_number!=1 or not self.current().get('one_string_confirmation'):raise ValueError('complete first-pass manual sequence before second pass')
  self.pass_number=2
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'pass':self.pass_number,'data':self.data,'cancelled':self.cancelled,'revealed_passes':self.revealed_passes,'source_audio_generated':False,'audio_inspected':False,'correctness_scored':False,'Attempt_credit':False,'mastery_awarded':False})
