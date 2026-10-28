"""Manual one-column arrangement comparison; source declarations are not sound."""
import copy
class ArrangementSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.harmony=None;self.variant=None;self.changed_column=None;self.renditions={'baseline':[],'variation':[]};self.response=None;self.history=[];self.disclosed=False;self.cancelled=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled comparison')
 def text(self,x):
  if not isinstance(x,str) or not x.strip():raise ValueError('nonempty manual text required')
 def bind_harmony(self,chords,source_description):
  self.active();self.text(source_description)
  if self.harmony is not None:raise ValueError('same source progression is immutable across both renditions')
  if not isinstance(chords,list) or not chords or any(not isinstance(x,str) or not x.strip() for x in chords):raise ValueError('external ordered chord progression required')
  self.harmony={'ordered_chord_labels':copy.deepcopy(chords),'external_source_description_self_report':source_description,'origin':'performer-authored; no per-card progression printed','performance_verified':False}
 def declare_variation(self,fields):
  self.active()
  if self.harmony is None:raise ValueError('bind fixed external progression first')
  if self.variant is not None:raise ValueError('variation declaration immutable within comparison pass')
  base=self.c['source_arrangement_fields']
  if not isinstance(fields,dict) or set(fields)!=set(base):raise ValueError('exact five source columns required')
  for value in fields.values():self.text(value)
  norm=lambda x:' '.join(x.split()).casefold();changed=[k for k in base if norm(fields[k])!=norm(base[k])]
  if len(changed)!=1:raise ValueError('declare exactly one arrangement-column change')
  self.changed_column=changed[0];self.variant=copy.deepcopy(fields)
 def source_view(self):
  self.active();return {'role':'external_source_player','baseline':copy.deepcopy(self.c['source_arrangement_fields']),'declared_variation':copy.deepcopy(self.variant),'changed_column':self.changed_column,'shared_harmony':copy.deepcopy(self.harmony),'app_audio_supplied':False,'sonic_single_variable_compliance_verified':False}
 def report_rendition(self,phase,description):
  self.active();self.text(description)
  if self.variant is None or phase not in self.renditions:raise ValueError('declared baseline/variation source pair required')
  self.renditions[phase].append(description)
 def commit_answer(self,column,new_value_description):
  self.active();self.text(new_value_description)
  if not all(self.renditions.values()):raise ValueError('report both source renditions before comparison answer')
  if self.response is not None:raise ValueError('explicit answer revision required')
  if column not in [*self.c['source_arrangement_fields'],'uncertain']:raise ValueError('named source column or uncertain response required')
  self.response={'column_answer':column,'new_value_description_self_report':new_value_description,'prior_reference_disclosure':self.disclosed,'correctness_verified':False}
 def learner_view(self):
  self.active()
  if self.response is not None:self.disclosed=True
  return {'declared_changed_column':self.changed_column if self.response is not None else None,'declared_source_variation':copy.deepcopy(self.variant) if self.response is not None else None,'prior_reference_disclosure':self.disclosed,'learner_answer':copy.deepcopy(self.response),'automatic_correctness_score':None,'source_actual_performance_verified':False}
 def revise_answer(self):
  self.active();self.history.append({'previous_response':copy.deepcopy(self.response),'prior_reference_disclosure':self.disclosed,'rendition_reports':copy.deepcopy(self.renditions)});self.response=None
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'harmony':self.harmony,'declared_variation':self.variant,'changed_column':self.changed_column,'renditions':self.renditions,'response':self.response,'history':self.history,'prior_reference_disclosure':self.disclosed,'cancelled':self.cancelled,'performance_observed':False,'app_audio_supplied':False,'Attempt_credit':False,'mastery_awarded':False})
