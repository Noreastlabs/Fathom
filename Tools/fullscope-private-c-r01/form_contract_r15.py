"""Manual form reconstruction: observed grouping is distinct from interpretation."""
import copy
class FormMapSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.data={};self.history=[];self.cancelled=False;self.count_reference_revealed=False;self.plausible_labels_revealed=False
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled task')
 def strings(self,values):
  if not isinstance(values,list) or len(values)!=len(self.c['source_bar_groups']) or any(not isinstance(x,str) or not x.strip() for x in values):raise ValueError('one nonempty manual response per source group required; uncertainty is allowed')
 def bind_external_basis(self,description):
  self.active()
  if not isinstance(description,str) or not description.strip():raise ValueError('external source/observation description required')
  if self.data:raise ValueError('external basis immutable within current pass')
  self.data['external_basis_self_report']=description
 def source_view(self):
  self.active();return {'source_observed_bar_groups':copy.deepcopy(self.c['source_bar_groups']),'one_plausible_label_sequence':copy.deepcopy(self.c['source_plausible_labels']),'unique_correct_labels_claimed':False,'note_complete_source_script_supplied':False,'app_audio_supplied':False}
 def submit_counts(self,counts):
  self.active()
  if 'external_basis_self_report' not in self.data:raise ValueError('external source basis first')
  if 'counts' in self.data:raise ValueError('explicit revision required')
  if not isinstance(counts,list) or len(counts)!=len(self.c['source_bar_groups']) or any(type(x) is not int or x<=0 for x in counts):raise ValueError('positive integer count per source group required')
  self.data['counts']=copy.deepcopy(counts)
 def compare_count_reference(self):
  self.active()
  if 'counts' not in self.data:raise ValueError('count response precedes source comparison')
  self.count_reference_revealed=True;return {'source_observed_counts':copy.deepcopy(self.c['source_bar_groups']),'correctness_verified':False}
 def confirm_counts(self,confirmed):
  self.active()
  if 'counts' not in self.data or type(confirmed) is not bool:raise ValueError('manual count comparison declaration required')
  if 'repetition_groups' in self.data:raise ValueError('revise counts to retain downstream history')
  self.data['counts_confirmed_self_report']=confirmed
 def identify_repetition(self,group_ids,landmark_notes):
  self.active();self.strings(group_ids);self.strings(landmark_notes)
  if self.data.get('counts_confirmed_self_report') is not True:raise ValueError('manual count confirmation precedes repetition analysis')
  if 'repetition_groups' in self.data:raise ValueError('explicit revision required')
  self.data['repetition_groups']=copy.deepcopy(group_ids);self.data['landmark_notes_self_report']=copy.deepcopy(landmark_notes)
 def name_sections(self,labels):
  self.active();self.strings(labels)
  if 'repetition_groups' not in self.data:raise ValueError('identify repeated material before naming sections')
  if 'section_labels' in self.data:raise ValueError('explicit revision required')
  self.data['section_labels']=copy.deepcopy(labels);self.data['labels_origin']='manual interpretation; not graded against one plausible source example';self.data['prior_source_labels_disclosed_at_commit']=self.plausible_labels_revealed
 def learner_view(self):
  self.active();named='section_labels' in self.data
  if named:self.plausible_labels_revealed=True
  return {'one_plausible_source_label_sequence':copy.deepcopy(self.c['source_plausible_labels']) if named else None,'prior_count_reference_disclosure':self.count_reference_revealed,'prior_plausible_labels_disclosure':self.plausible_labels_revealed,'unique_correct_labels_claimed':False,'automatic_label_score':None}
 def revise_from(self,stage):
  self.active();stages={'counts':['counts','counts_confirmed_self_report','repetition_groups','landmark_notes_self_report','section_labels','labels_origin','prior_source_labels_disclosed_at_commit'],'repetition':['repetition_groups','landmark_notes_self_report','section_labels','labels_origin','prior_source_labels_disclosed_at_commit'],'labels':['section_labels','labels_origin','prior_source_labels_disclosed_at_commit']}
  if stage not in stages:raise ValueError('unknown revision stage')
  self.history.append({'stage':stage,'prior_data':copy.deepcopy(self.data),'prior_count_reference_disclosure':self.count_reference_revealed,'prior_plausible_labels_disclosure':self.plausible_labels_revealed})
  for key in stages[stage]:self.data.pop(key,None)
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'data':self.data,'history':self.history,'cancelled':self.cancelled,'prior_count_reference_disclosure':self.count_reference_revealed,'prior_plausible_labels_disclosure':self.plausible_labels_revealed,'automatic_label_score':None,'source_observed_audio_available':False,'counts_or_repetition_verified':False,'Attempt_credit':False,'mastery_awarded':False})
