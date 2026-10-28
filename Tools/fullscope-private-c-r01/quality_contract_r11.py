"""Private manual blind-pass state; reports and requests never observe audio."""
import copy

class QualitySession:
 def __init__(self,contract):
  if not contract.get('source_player_projection_resolved'):raise ValueError('source-player interpretation must be resolved before blind pass')
  self.c=copy.deepcopy(contract);self.cancelled=False;self.responses={};self.history=[];self.reference_revealed=False;self.full_voicing_ever_requested=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def text(self,x):
  if not isinstance(x,str) or not x.strip():raise ValueError('nonempty manual response required')
 def source_view(self):
  self.active();return {'role':'external_source_player','reduced_source_notes':copy.deepcopy(self.c['reduced_source_notes']),'complete_source_notes':copy.deepcopy(self.c['source_full_notes']),'quality_reference':self.c['source_quality_answer'],'clue':copy.deepcopy(self.c['singing_clue']),'app_audio_supplied':False,'source_projection_is_octave_free':True}
 def report_reduced_listening(self,description):
  self.active();self.text(description);self.responses['reduced_listening_self_report']=description
 def commit_quality(self,response):
  self.active();self.text(response)
  if 'reduced_listening_self_report' not in self.responses:raise ValueError('manual reduced-source report precedes quality response')
  if 'quality_response' in self.responses:raise ValueError('use explicit revision to preserve history')
  self.responses['quality_response']=response
  self.responses['prior_reference_disclosure_at_commit']=self.reference_revealed
  self.responses['prior_complete_voicing_request_at_commit']=self.full_voicing_ever_requested
 def learner_view(self):
  self.active();committed='quality_response' in self.responses
  if committed:self.reference_revealed=True
  return {'role':'learner','quality_reference':self.c['source_quality_answer'] if committed else None,'singing_clue':copy.deepcopy(self.c['singing_clue']) if committed else None,'prior_reference_disclosure':self.reference_revealed,'prior_full_voicing_request':self.full_voicing_ever_requested,'correctness_verified':False}
 def request_complete_voicing(self):
  self.active()
  if 'quality_response' not in self.responses:raise ValueError('identify quality before complete voicing request')
  self.full_voicing_ever_requested=True;return {'manual_request':'external complete source voicing','source_notes':copy.deepcopy(self.c['source_full_notes']),'audio_generated':False,'hearing_observed':False}
 def record_clue_singing(self,report):
  self.active();self.text(report)
  if 'quality_response' not in self.responses:raise ValueError('quality response before postcommit singing report')
  self.responses['clue_singing_self_report']=report
 def record_comparison(self,report):
  self.active();self.text(report)
  if not self.full_voicing_ever_requested:raise ValueError('request external complete source before comparison report')
  self.responses['comparison_self_report']=report
 def revise_quality(self):
  self.active();self.history.append({'responses':copy.deepcopy(self.responses),'prior_reference_disclosure':self.reference_revealed,'prior_full_voicing_request':self.full_voicing_ever_requested})
  for k in ['quality_response','clue_singing_self_report','comparison_self_report','prior_reference_disclosure_at_commit','prior_complete_voicing_request_at_commit']:self.responses.pop(k,None)
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'responses':self.responses,'history':self.history,'cancelled':self.cancelled,'prior_reference_disclosure':self.reference_revealed,'prior_full_voicing_request':self.full_voicing_ever_requested,'manual_response_fields_present':all(k in self.responses for k in ['reduced_listening_self_report','quality_response','clue_singing_self_report']),'audio_generated':False,'listening_observed':False,'singing_observed':False,'correctness_verified':False,'Attempt_credit':False,'mastery_awarded':False})
