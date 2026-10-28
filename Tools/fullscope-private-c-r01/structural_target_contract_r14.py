"""Private manual reduction/verification workflow; no acoustic evaluation."""
import copy
class StructuralTargetSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.cancelled=False;self.data={};self.history=[];self.reference_revealed=False;self.reduction_ever_requested=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def text(self,x):
  if not isinstance(x,str) or not x.strip():raise ValueError('nonempty manual response required')
 def source_view(self):
  self.active();return {'role':'external_source_player','harmony':self.c['source_harmony'],'source_phrase':copy.deepcopy(self.c['source_phrase']),'target_spelling':self.c['source_target'],'target_role':self.c['source_role'],'matching_target_positions':copy.deepcopy(self.c['source_matching_target_positions']),'source_has_fixed_target_occurrence_selection':False,'app_audio_supplied':False}
 def report_source_listening(self,description):
  self.active();self.text(description);self.data['external_source_listening_self_report']=description
 def commit_target(self,pitch_answer,role_answer,positions):
  self.active();self.text(pitch_answer);self.text(role_answer)
  if 'external_source_listening_self_report' not in self.data:raise ValueError('external source listening report required')
  if 'target_response' in self.data:raise ValueError('revise explicitly rather than overwrite')
  if not isinstance(positions,list) or not positions or any(type(i) is not int or not 1<=i<=len(self.c['source_phrase']) for i in positions) or positions!=sorted(set(positions)):raise ValueError('nonempty unique source positions in original order required')
  self.data['target_response']={'pitch_answer':pitch_answer,'role_answer':role_answer,'selected_source_positions':copy.deepcopy(positions),'selection_origin':'learner/interface occurrence choice, not a unique printed source selection','prior_reference_disclosure':self.reference_revealed}
 def learner_view(self):
  self.active();committed='target_response' in self.data
  if committed:self.reference_revealed=True
  return {'source_target_reference':self.c['source_target'] if committed else None,'source_role_reference':self.c['source_role'] if committed else None,'matching_reference_positions':copy.deepcopy(self.c['source_matching_target_positions']) if committed else None,'prior_reference_disclosure':self.reference_revealed,'correctness_verified':False}
 def request_reduced_rendition(self):
  self.active()
  if 'target_response' not in self.data:raise ValueError('commit target selection before reduced rendition')
  selected=self.data['target_response']['selected_source_positions'];self.data['current_reduction_requested']=True;self.reduction_ever_requested=True
  return {'manual_source_player_request':'render selected target occurrences only','retained_source_positions':copy.deepcopy(selected),'source_pitch_spellings':[self.c['source_phrase'][i-1] for i in selected],'onsets_and_durations':None,'audio_generated':False,'performance_observed':False}
 def report_verification(self,communicates_harmony,explanation):
  self.active();self.text(explanation)
  if not self.data.get('current_reduction_requested'):raise ValueError('request reduced line before verification report')
  if type(communicates_harmony) is not bool:raise ValueError('manual boolean harmony-communication report required')
  if 'verification' in self.data:raise ValueError('revise explicitly before replacing verification')
  self.data['verification']={'communicates_harmony_self_report':communicates_harmony,'explanation_self_report':explanation,'correctness_verified':False,'revision_required':not communicates_harmony}
 def revise_targets(self):
  self.active();self.history.append({'data':copy.deepcopy(self.data),'prior_reference_disclosure':self.reference_revealed,'prior_reduction_request':self.reduction_ever_requested})
  for k in ['target_response','current_reduction_requested','verification']:self.data.pop(k,None)
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'data':self.data,'history':self.history,'cancelled':self.cancelled,'prior_reference_disclosure':self.reference_revealed,'prior_reduction_request':self.reduction_ever_requested,'manual_verification_recorded':'verification' in self.data,'revision_required':self.data.get('verification',{}).get('revision_required',False),'audio_generated':False,'listening_observed':False,'correctness_verified':False,'Attempt_credit':False,'mastery_awarded':False})
