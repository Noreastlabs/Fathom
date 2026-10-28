"""Manual external verification evidence; no media operations or automatic grade."""
import copy
class VerificationSession:
 def __init__(self,c):self.c=copy.deepcopy(c);self.data={};self.history=[];self.cancelled=False;self.independent_reconstruction_report=None;self.external_chart_comparisons=[]
 def active(self):
  if self.cancelled:raise ValueError('reopen cancelled method')
 def text(self,x):
  if not isinstance(x,str) or not x.strip():raise ValueError('nonempty manual text required')
 def bind_candidate(self,candidate_reference,external_source_description):
  self.active();self.text(candidate_reference);self.text(external_source_description)
  if self.data:raise ValueError('candidate basis fixed for this method pass')
  self.data={'candidate_reference':candidate_reference,'external_source_description_self_report':external_source_description}
 def source_view(self):
  self.active();return {'method':self.c['source_method'],'operation':self.c['source_question'],'manual_observation_schema':copy.deepcopy(self.c['observation_fields']),'source_audio_supplied':False}
 def submit_observations(self,values):
  self.active()
  if 'candidate_reference' not in self.data:raise ValueError('candidate/source basis first')
  if 'observations' in self.data:raise ValueError('revise explicitly to retain prior evidence')
  schema=self.c['observation_fields']
  if not isinstance(values,dict) or set(values)!=set(schema):raise ValueError('exact method observation fields required')
  for key,spec in schema.items():
   if spec['type']=='text':self.text(values[key])
   elif spec['type']=='enum':
    if not isinstance(values[key],str) or values[key] not in spec['values']:raise ValueError('invalid manual observation choice')
   else:raise ValueError('unknown field type')
  self.data['observations']=copy.deepcopy(values)
 def conclude(self,answer,explanation):
  self.active();self.text(explanation)
  if 'observations' not in self.data:raise ValueError('method evidence before conclusion')
  if 'conclusion' in self.data:raise ValueError('revise explicitly before replacing conclusion')
  if answer not in ['yes','no','uncertain']:raise ValueError('yes/no/uncertain manual conclusion required')
  self.data['conclusion']={'answer':answer,'explanation_self_report':explanation,'interpretation':self.c['yes_response_interpretation'] if answer=='yes' else 'Manual negative or uncertain source-question response; further interpretation may be required.','source_question':self.c['source_question'],'verified_pass':False}
 def record_independent_reconstruction(self,description):
  self.active();self.text(description)
  if 'candidate_reference' not in self.data:raise ValueError('candidate first')
  self.independent_reconstruction_report=description
 def record_external_chart_comparison(self,description):
  self.active();self.text(description)
  if self.independent_reconstruction_report is None:raise ValueError('independent reconstruction must precede external chart comparison')
  self.external_chart_comparisons.append({'description_self_report':description,'external_chart_retrieved_or_inspected_by_app':False})
 def revise_observations(self):
  self.active();self.history.append({'prior_data':copy.deepcopy(self.data),'independent_reconstruction_report':self.independent_reconstruction_report,'external_chart_comparisons':copy.deepcopy(self.external_chart_comparisons)})
  self.data.pop('observations',None);self.data.pop('conclusion',None)
 def cancel(self):self.cancelled=True
 def reopen(self):self.cancelled=False
 def snapshot(self):return copy.deepcopy({'method_key':self.c['method_key'],'data':self.data,'history':self.history,'cancelled':self.cancelled,'independent_reconstruction_report':self.independent_reconstruction_report,'external_chart_comparisons':self.external_chart_comparisons,'performance_observed':False,'audio_generated_or_modified':False,'verified_pass':False,'Attempt_credit':False,'mastery_awarded':False})

class ConvergenceJournal:
 def __init__(self,candidate_reference):
  if not isinstance(candidate_reference,str) or not candidate_reference.strip():raise ValueError('candidate reference required')
  self.candidate=candidate_reference;self.methods={};self.reports=[]
 def add(self,session):
  if not isinstance(session,VerificationSession):raise ValueError('manual method session required')
  s=session.snapshot()
  if s['cancelled'] or s['data'].get('candidate_reference')!=self.candidate or 'conclusion' not in s['data']:raise ValueError('completed manual method conclusion for same candidate required')
  if s['method_key'] in self.methods:raise ValueError('duplicate method cannot supply a second independent clue')
  self.methods[s['method_key']]=s
 def record_convergence(self,independent_clues,agree,explanation):
  if len(self.methods)<2:raise ValueError('more than one distinct method required')
  if type(independent_clues) is not bool or type(agree) is not bool or not isinstance(explanation,str) or not explanation.strip():raise ValueError('manual independence/convergence declaration and explanation required')
  self.reports.append({'distinct_methods':list(self.methods),'independent_clues_self_report':independent_clues,'agreement_self_report':agree,'explanation_self_report':explanation,'claimed_convergence':independent_clues and agree,'verification_established_by_app':False,'Attempt_credit':False,'mastery_awarded':False})
 def snapshot(self):return copy.deepcopy({'candidate_reference':self.candidate,'methods':self.methods,'convergence_reports':self.reports,'verification_established_by_app':False})
