"""Manual source-bound contour practice; no audio execution or observation."""
import copy

class ContourSession:
 def __init__(self,contract):self.c=copy.deepcopy(contract);self.cancelled=False;self.realization=None;self.responses={};self.history=[];self.contour_revealed=False;self.pitch_revealed=False;self.guitar_ever_requested=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def text(self,x):
  if not isinstance(x,str) or not x.strip():raise ValueError('nonempty manual source/response text required')
 def bind_source_register(self,midis,external_source_description):
  self.active();self.text(external_source_description)
  if self.realization is not None:raise ValueError('source realization is immutable within this pass')
  if not isinstance(midis,list) or len(midis)!=4 or any(type(n) is not int or not 0<=n<=127 for n in midis):raise ValueError('four octave-specific external-source pitches required')
  if [n%12 for n in midis]!=self.c['source_pitch_classes']:raise ValueError('external register choice must preserve exact source pitch classes/order')
  self.realization={'external_source_pitch_midis':copy.deepcopy(midis),'external_source_description_self_report':external_source_description,'origin':'external source-player authored register selection; not printed octave, generated audio or observed performance','realization_specific_directions':['U' if b>a else 'D' if b<a else 'S' for a,b in zip(midis,midis[1:])]}
 def source_view(self):
  self.active();return {'role':'external_source_player','context':self.c['source_context'],'source_degrees':copy.deepcopy(self.c['source_degrees']),'source_pitch_spellings':copy.deepcopy(self.c['source_pitch_spellings']),'realization':copy.deepcopy(self.realization),'app_audio_supplied':False}
 def report_listening(self,description):
  self.active();self.text(description)
  if self.realization is None:raise ValueError('source-player register realization must be bound before reporting its contour')
  self.responses['listening_self_report']=description
 def report_contour_singing(self,description):
  self.active();self.text(description)
  if 'listening_self_report' not in self.responses:raise ValueError('report external source hearing before contour singing')
  self.responses['contour_singing_self_report']=description
 def submit_contour(self,directions):
  self.active()
  if 'contour_singing_self_report' not in self.responses:raise ValueError('sing contour before response progression')
  if 'contour_response' in self.responses:raise ValueError('use explicit contour revision to preserve downstream history')
  if not isinstance(directions,list) or len(directions)!=3 or any(x not in ['U','D','S'] for x in directions):raise ValueError('three U/D/S movements required')
  self.responses['contour_response']=copy.deepcopy(directions);self.responses['prior_contour_disclosure_at_commit']=self.contour_revealed;self.responses['prior_pitch_disclosure_at_commit']=self.pitch_revealed
 def reveal_contour_reference(self):
  self.active()
  if 'contour_response' not in self.responses:raise ValueError('write direction response before reference comparison')
  self.contour_revealed=True;return {'directions':copy.deepcopy(self.realization['realization_specific_directions']),'origin':'external authored register-specific reference; not a fixed printed source answer','correctness_verified':False}
 def confirm_contour(self,confirmed):
  self.active()
  if type(confirmed) is not bool or 'contour_response' not in self.responses:raise ValueError('manual direction-correct declaration after written contour required')
  if 'pitch_response' in self.responses:raise ValueError('revise contour explicitly before invalidating downstream pitch response')
  self.responses['contour_correct_self_report']=confirmed
 def submit_pitches(self,answers):
  self.active()
  if self.responses.get('contour_correct_self_report') is not True or 'contour_singing_self_report' not in self.responses:raise ValueError('singing and manual direction-correct declaration precede exact pitch naming')
  if 'pitch_response' in self.responses:raise ValueError('use explicit revision rather than overwrite')
  if not isinstance(answers,list) or len(answers)!=4 or any(not isinstance(x,str) or not x.strip() for x in answers):raise ValueError('four manual pitch responses required')
  self.responses['pitch_response']=copy.deepcopy(answers)
 def learner_view(self):
  self.active();answered='pitch_response' in self.responses
  if answered:self.pitch_revealed=True
  return {'role':'learner','source_pitch_reference':copy.deepcopy(self.c['source_pitch_spellings']) if answered else None,'source_degree_reference':copy.deepcopy(self.c['source_degrees']) if answered else None,'prior_contour_disclosure':self.contour_revealed,'prior_pitch_disclosure':self.pitch_revealed,'correctness_verified':False}
 def request_guitar_confirmation(self):
  self.active()
  if 'contour_singing_self_report' not in self.responses or 'pitch_response' not in self.responses:raise ValueError('singing and pitch-response work precede authored guitar-confirmation stage')
  self.guitar_ever_requested=True;return {'manual_request':'learner guitar confirmation','performance_observed':False,'app_audio_supplied':False}
 def revise_contour(self):
  self.active();self.history.append({'responses':copy.deepcopy(self.responses),'prior_contour_disclosure':self.contour_revealed,'prior_pitch_disclosure':self.pitch_revealed,'prior_guitar_request':self.guitar_ever_requested})
  for k in ['contour_response','prior_contour_disclosure_at_commit','prior_pitch_disclosure_at_commit','contour_correct_self_report','pitch_response']:self.responses.pop(k,None)
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'realization':self.realization,'responses':self.responses,'history':self.history,'cancelled':self.cancelled,'prior_contour_disclosure':self.contour_revealed,'prior_pitch_disclosure':self.pitch_revealed,'prior_guitar_request':self.guitar_ever_requested,'audio_generated':False,'listening_observed':False,'singing_observed':False,'correctness_verified':False,'Attempt_credit':False,'mastery_awarded':False})
