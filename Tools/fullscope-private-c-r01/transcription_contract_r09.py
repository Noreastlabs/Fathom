"""Manual offline transcription contracts; no performed or acoustic observation."""
import copy
class BassRouteSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.data={};self.history=[];self.cancelled=False;self.reference_revealed=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def submit(self,stage,values):
  self.active();order=['scale_degrees','pitch_names','chord_families']
  if stage not in order:raise ValueError('unknown bass stage')
  i=order.index(stage)
  if any(x not in self.data for x in order[:i]):raise ValueError('source degrees/pitches/families order')
  if stage in self.data:raise ValueError('use revision operation to preserve dependent history')
  if not isinstance(values,list) or len(values)!=6 or any(not isinstance(v,str) or not v.strip() for v in values):raise ValueError('six manual source-position responses required')
  self.data[stage]=copy.deepcopy(values);self.history.append({'stage':stage,'origin':'manual_response','verified':False})
 def reveal_bass_reference(self):
  self.active()
  if 'pitch_names' not in self.data:raise ValueError('pitch response precedes source answer reveal')
  self.reference_revealed=True;return {'scale_degrees':self.c['source_scale_degrees'],'pitch_names':self.c['source_bass_notes'],'verified_correct':False}
 def confirm_bass(self,confirmed):
  self.active()
  if type(confirmed) is not bool or 'pitch_names' not in self.data:raise ValueError('manual bass comparison required')
  self.data['bass_confirmed_self_report']=confirmed
 def classify_inversions(self,roles,upper_voice_evidence):
  self.active()
  if 'chord_families' not in self.data or self.data.get('bass_confirmed_self_report') is not True:raise ValueError('bass must be manually confirmed before inversion interpretation')
  if not isinstance(roles,list) or len(roles)!=6 or any(x not in ['root','third','fifth','pedal','uncertain'] for x in roles):raise ValueError('six inversion/pedal interpretations required')
  if not isinstance(upper_voice_evidence,str) or not upper_voice_evidence.strip():raise ValueError('external upper-voice evidence description required')
  self.data['inversion_roles']=copy.deepcopy(roles);self.data['upper_voice_evidence_self_report']=upper_voice_evidence
 def revise_from(self,stage):
  self.active();order=['scale_degrees','pitch_names','chord_families']
  if stage not in order:raise ValueError('unknown revision stage')
  self.history.append({'action':'revise','stage':stage,'prior_data':copy.deepcopy(self.data),'prior_reference_disclosure':self.reference_revealed})
  for k in order[order.index(stage):]+['bass_confirmed_self_report','inversion_roles','upper_voice_evidence_self_report','chord_root_certainty_self_report']:self.data.pop(k,None)
 def record_root_certainty(self,report):
  self.active()
  if 'chord_families' not in self.data or not isinstance(report,str) or not report.strip():raise ValueError('manual chord-root certainty report after family proposals required')
  self.data['chord_root_certainty_self_report']=report
 def learner_view(self):
  self.active();return {'role':'learner','manual_stages':list(self.data),'source_pitch_answer':self.c['source_bass_notes'] if self.reference_revealed else None,'prior_reference_disclosure':self.reference_revealed,'verified_correct':False}
 def source_view(self):
  self.active();return {'role':'source_player','source_key':self.c['source_key'],'bass_notes':self.c['source_bass_notes'],'upper_voice_part':None,'prerequisite':self.c['external_source_prerequisite'],'audio_generated':False}
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'data':self.data,'history':self.history,'cancelled':self.cancelled,'reference_revealed':self.reference_revealed,'correctness_verified':False,'Attempt_credit':False,'mastery_awarded':False})

class ProgressionSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.listen_requests=0;self.responses={};self.cancelled=False;self.answer_committed=False;self.reference_revealed=False;self.written_answer_ever=False;self.history=[]
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def request_listen(self):
  self.active()
  if self.listen_requests>=3 and not self.written_answer_ever:raise ValueError('source three-listen limit before written answer')
  self.listen_requests+=1
  return {'manual_source_request':self.listen_requests,'purpose':['form_and_bass','quality','verify_cadence'][self.listen_requests-1] if self.listen_requests<=3 else 'extra_loop_after_written_answer','audio_generated':False,'listen_observed':False}
 def record_roots(self,response):
  self.active()
  if self.listen_requests<1 or not isinstance(response,str) or not response.strip():raise ValueError('first-listen root-motion response required')
  if 'quality' in self.responses or self.answer_committed:raise ValueError('revise roots explicitly to retain dependent response history')
  self.responses['root_motion']=response
 def record_quality(self,response,roots_survived_second_listen):
  self.active()
  if 'root_motion' not in self.responses or self.listen_requests<2 or roots_survived_second_listen is not True:raise ValueError('roots first and manual second-listen confirmation before quality')
  if not isinstance(response,str) or not response.strip():raise ValueError('quality response required')
  if self.answer_committed:raise ValueError('written answer already committed; revise explicitly')
  self.responses['quality']=response;self.responses['roots_second_listen_confirmed_self_report']=True
 def commit_written_answer(self,response,cadence_notes):
  self.active()
  if 'quality' not in self.responses:raise ValueError('root/quality work precedes written answer commitment')
  if self.answer_committed:raise ValueError('answer already committed')
  if not isinstance(response,str) or not response.strip() or not isinstance(cadence_notes,str) or not cadence_notes.strip():raise ValueError('written answer and cadence note required')
  self.responses['written_answer']=response;self.responses['cadence_note']=cadence_notes;self.answer_committed=True;self.written_answer_ever=True
 def revise_roots(self):
  self.active();self.history.append({'responses':copy.deepcopy(self.responses),'reference_revealed':self.reference_revealed,'listen_requests':self.listen_requests});self.responses={};self.answer_committed=False
 def source_view(self):
  self.active();return {'role':'source_player','source_chords':self.c['source_chords'],'roman_answer':self.c['source_roman_answer'],'external_source_required':True,'app_audio_supplied':False}
 def learner_view(self):
  self.active()
  if self.answer_committed:self.reference_revealed=True
  return {'listen_requests':self.listen_requests,'source_roman_answer':self.c['source_roman_answer'] if self.answer_committed else None,'verified_correct':False,'prior_reference_disclosure':self.reference_revealed}
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'listen_requests':self.listen_requests,'responses':self.responses,'history':self.history,'written_answer_ever':self.written_answer_ever,'answer_committed':self.answer_committed,'reference_revealed':self.reference_revealed,'cancelled':self.cancelled,'listening_observed':False,'audio_generated':False,'Attempt_credit':False,'mastery_awarded':False})
