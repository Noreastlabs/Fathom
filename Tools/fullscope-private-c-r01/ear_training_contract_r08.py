"""Private, offline manual ear-training workflow. No audio inspection, evaluation or credit."""
import copy
RESPONSE_KEYS={'retained_tone','pivot_function_source_key','pivot_function_destination_key','stable_destination_tonic_bar','singing_self_report'}
class EarTrainingSession:
 def __init__(self):
  self.recording_report=None;self.responses=None;self.cancelled=False;self.reference_was_ever_revealed=False;self.history=[]
 def state(self):
  if self.cancelled:return 'cancelled'
  if self.recording_report is not None and self.responses is not None:return 'ready_for_reference'
  return 'awaiting_manual_input'
 def record(self,report):
  if self.cancelled:raise ValueError('reopen cancelled task before editing')
  if not isinstance(report,dict) or report.get('kind') not in ['local_or_external_reference','self_report']:raise ValueError('recording report kind')
  field='reference' if report['kind']=='local_or_external_reference' else 'declaration'
  if set(report)!={'kind',field} or not isinstance(report[field],str) or not report[field].strip():raise ValueError('recording report is missing its manual value')
  self.recording_report=copy.deepcopy(report);self.history.append({'action':'recording_reported','origin':'learner_self_report','audio_inspected':False});return self.state()
 def respond(self,responses):
  if self.cancelled:raise ValueError('reopen cancelled task before editing')
  if not isinstance(responses,dict) or set(responses)!=RESPONSE_KEYS:raise ValueError('exact manual response fields required')
  for k,v in responses.items():
   if k=='singing_self_report':
    if type(v) is not bool:raise ValueError('singing self-report must be boolean')
   elif not isinstance(v,str) or not v.strip():raise ValueError('missing manual text response')
  self.responses=copy.deepcopy(responses);self.history.append({'action':'manual_response_recorded','origin':'learner_self_report','verified_correct':False});return self.state()
 def reveal_reference(self):
  if self.state()!='ready_for_reference':raise ValueError('recording report and manual responses required before score/reference reveal')
  self.reference_was_ever_revealed=True;self.history.append({'action':'source_reference_reveal_authorized','automatic_score':False});return {'source_reference_access':True,'manual_recording_report_only':True,'audio_inspected':False,'verified_pass':False,'attempt_credit':False,'mastery_awarded':False}
 def cancel(self):self.cancelled=True;self.history.append({'action':'cancelled','inputs_preserved':True})
 def reopen(self):self.cancelled=False;self.history.append({'action':'reopened','prior_disclosure_preserved':self.reference_was_ever_revealed});return self.state()
 def snapshot(self):return copy.deepcopy({'recording_report':self.recording_report,'responses':self.responses,'cancelled':self.cancelled,'reference_was_ever_revealed':self.reference_was_ever_revealed,'history':self.history,'audio_inspected':False,'attempt_credit':False,'mastery_awarded':False})
