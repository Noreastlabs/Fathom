"""Private source task contract. A response is manual data, never verified performance or credit."""
import re,hashlib,copy
NOTE=r'[A-G](?:#{1,2}|b{1,2})?'
PURE_NOTES=re.compile(r'^'+NOTE+r'(?:\s*(?:[-–→,]|\s)\s*'+NOTE+r')+$')
MANUAL=re.compile(r'\b(write|explain|identify|name|compare|document|rate|map|list|annotate|describe|classify|mark|calculate|audit|plan|state|answer|analyze|analyse|reflect|label)\b',re.I)
CHOICE=re.compile(r'\b(choose|select|create|compose|improvise|arrange|design|adapt|invent|transpose|another|your own|one of|learner|personal|repertoire|recording)\b',re.I)

def named_fields(task):
 out=[]
 for ti,t in enumerate(task['table_fields'],1):
  rows=[t['values']] if 'values' in t else t.get('rows',[])
  for i,row in enumerate(rows):
   for j,(col,val) in enumerate(zip(t.get('columns',[]),row)):
    out.append({'field':col or f'column{j+1}','table':ti,'table_row':i+1,'value':val,'physical_page':t.get('physical_page')})
 for i,line in enumerate(task['instructions']):
  q=re.match(r'^([A-Za-z][A-Za-z /-]{1,40}):\s*(.+)$',line['text'])
  if q:out.append({'field':q[1],'source_line_in_region':line['source_line_in_region'],'value':q[2]})
 return out

def sequences(fields):
 out=[]
 for f in fields:
  value=f.get('value') or '';name=f['field'];kind=None;tokens=None
  if not isinstance(value,str):continue
  stripped=value.strip()
  # Exact whole-field notes and leading labelled melody/bass sequences; no arbitrary words become notes.
  match=re.match(r'^('+NOTE+r'(?:\s*[-–→]\s*'+NOTE+r')+)(?:\s|$)',stripped)
  if PURE_NOTES.fullmatch(stripped):kind='ordered_pitch_names';tokens=re.findall(NOTE,stripped)
  elif match and re.search(r'melody|bass|note|target|tone|voice|route|reference',name,re.I):kind='ordered_pitch_names';tokens=re.findall(NOTE,match[1])
  elif re.fullmatch(NOTE,stripped) and re.search(r'start|destination|tonic|bass|note|target|tone|pitch',name,re.I):kind='pitch_name';tokens=[stripped]
  elif re.search(r'voicing|route|fret',name,re.I) and re.fullmatch(r'(?:[xX]|\d+)(?:[\s-]+(?:[xX]|\d+)){1,}',stripped):kind='unassigned_fret_route';tokens=re.split(r'[\s-]+',stripped)
  elif re.search(r'grid|rhythm|pattern|cell',name,re.I) and re.fullmatch(r'[PpXxRrOoSs><.\-_| /0-9]+',stripped) and re.search(r'[PpXx><]',stripped):kind='ordered_rhythm_symbols';tokens=[{'group':i+1,'symbols':list(g)} for i,g in enumerate(stripped.split())]
  elif ('|' in stripped or re.search(r'chord|harmony|progression',name,re.I)) and re.fullmatch(r'[A-Ga-z0-9#bø°+()/|\s-]+',stripped) and re.search(r'\b[A-G](?:#|b)?(?:maj|min|m|dim|aug|sus|7|9|11|13)',stripped):kind='chord_symbol_sequence';tokens=[x.strip() for x in stripped.split('|') if x.strip()] if '|' in stripped else [stripped]
  if kind:out.append({'source_field':f,'kind':kind,'tokens':tokens,'ordering':'within this exact printed field; different fields are not concatenated into a performed sequence','onset_duration':None,'string_axis':None,'source_not_observation':True})
 return out

def build_contract(r):
 task=r['implementation']['task'];fields=named_fields(task);seqs=sequences(fields);text='\n'.join(x['text'] for x in task['instructions']);prompts=[];response=[];choices=[]
 def add(label,quote,kind='text',options=None):
  key='response_'+hashlib.sha256((label+'\n'+quote).encode()).hexdigest()[:12]
  if any(x['key']==key for x in response):return
  field={'key':key,'label':label,'type':kind,'required_for_manual_submission':True,'source_prompt':quote,'learner_value':None}
  if options:field['source_options']=options
  response.append(field)
 for f in fields:
  name=f['field'];value=f.get('value') or ''
  if re.search(r'confidence|answer|response|reason|evidence|result|score|choice|observation|comment|reflection|deliverable',name,re.I):
   kind='integer' if re.search(r'\b\d+\s*[-–]\s*\d+\b',name) else 'text'
   add(name+f" (table {f.get('table',0)}, row {f.get('table_row',0)})",str(value) if value else name,kind)
   if kind=='integer':
    a,b=re.search(r'(\d+)\s*[-–]\s*(\d+)',name).groups();response[-1]['printed_minimum']=int(a);response[-1]['printed_maximum']=int(b)
  if re.search(r'options|choice|allowed answer',name,re.I):choices.append({'field':name,'literal':value,'options':[v.strip() for v in str(value).split('/') if v.strip()],'source_field':f})
 for x in task['instructions']:
  line=x['text']
  if MANUAL.search(line):
   prompts.append({'instruction':line,'source_line_in_region':x['source_line_in_region']});add('Response to source instruction',line)
  elif CHOICE.search(line):choices.append({'instruction':line,'source_line_in_region':x['source_line_in_region'],'learner_selection':None})
 explicit_nonplayback=task['type'] in ['assessment','written','reflection','planning_task']
 if explicit_nonplayback and not response:add('Manual task response',task['label'])
 contract={'schema_version':'fathom-private-manual-task-contract.1','source_fields':fields,'source_sequences':seqs,'source_instructions':task['instructions'],'response_prompts':prompts,'response_fields':response,'source_choice_fields':choices,'source_answer_fields':[f for f in fields if re.search(r'expected|answer|destination|tonic',f['field'],re.I)],'source_answer_policy':'reference answer is never copied into learner response; presentation must preserve source-player/answer withholding instructions','state_machine':{'initial':'awaiting_manual_response','valid_submission':'manual_response_recorded','cancel':'cancelled','verified_pass_state':None},'response_origin':'manual_self_report','automatic_evaluation':False,'performance_observed':False,'credit_awarded':False,'mastery_awarded':False,'manual_contract_origin':'Fathom-authored typed response envelope around exact source prompts; field types are not printed musical facts'}
 task['contract']=contract
 # Actual source note occurrences keep field/voice/reference roles. They do not become a synthesized sequential performance.
 r['implementation']['source_field_occurrences']=[{'source_field_sequence':i+1,'occurrence':j+1,'printed_note':note,'source_field':s['source_field'],'onset_q':None,'duration_q':None,'string':None,'fret':None,'performance_observation':False} for i,s in enumerate(seqs) if s['kind'] in ['ordered_pitch_names','pitch_name'] for j,note in enumerate(s['tokens'])]
 demonstrated=[d for d in (r['source_payload'].get('source_discrepancies') or []) if d.get('class') in ['known_source_conflict','pdf_visual_occlusion_unresolved','physically_overprinted_cards','pdf_table_annotation_overlap']]
 demonstrated +=r['source_payload'].get('extraction_limits',[])
 es=r['implementation']['events'];timed=bool(es) and all(e.get('onset_q') is not None and e.get('duration_q') is not None for e in es)
 fixed_pitch_content=any(s['kind'] in ['ordered_pitch_names','pitch_name','unassigned_fret_route','ordered_rhythm_symbols'] for s in seqs)
 complete_manual=bool(response) and (explicit_nonplayback or (bool(prompts) and not es and not fixed_pitch_content))
 if demonstrated:category='DEMONSTRATED_SOURCE_CONFLICT'
 elif timed:category='TIMED_SOURCE_EVENT_CONTRACT'
 elif complete_manual:category='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
 elif choices and not fixed_pitch_content and not es:category='LEARNER_CHOICE_WITHOUT_FIXED_REALIZATION'
 else:category='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
 r['contract_category']=category
 r['contract_capabilities']={'timed_source_event_contract':timed,'complete_manual_response_contract':complete_manual and not demonstrated,'literal_pitch_occurrences':len(r['implementation']['source_field_occurrences']),'actual_fret_contacts':sum(e.get('fret') is not None for e in es),'ordered_pitch_or_contact_slots':len(es),'demonstrated_source_conflicts':demonstrated,'native_projection_complete':False,'native_valid':False,'installed':False,'Accepted':False}
 prior=r['unresolved_reasons'];r['prior_draft_disposition']=prior
 r['unresolved_reasons']=[]
 if category=='DEMONSTRATED_SOURCE_CONFLICT':r['unresolved_reasons'].append({'disposition':'SOURCE_UNRESOLVED','facts':demonstrated,'action':'Resolve the exact source conflict/visibility; preserve supported fields meanwhile.'})
 if category=='IMPLEMENTATION_OR_INTERPRETATION_PENDING':r['unresolved_reasons'].append({'disposition':'IMPLEMENTATION_PENDING','action':'Implement remaining source interpretation/realization for the retained ordered fields; absence of a completed adapter is not a claim that source is ambiguous.','retained_source_fields':len(fields),'retained_source_sequences':len(seqs),'retained_timing_instructions':r['timing_authority']['printed_instruction_lines']})
 if category=='LEARNER_CHOICE_WITHOUT_FIXED_REALIZATION':r['unresolved_reasons'].append({'disposition':'DELIBERATE_LEARNER_CHOICE','action':'Obtain prescribed performer choices or separately author and review an explicit realization; the source does not provide one mandatory fixed performance.','choice_fields':choices})
 r['field_limitations']=[{'field':'fixed_bpm','status':'unknown; no invented fixed tempo'},{'field':'finger','status':'unknown unless retained source instruction supplies it'}]
 if es and any(e.get('fret') is None for e in es):r['field_limitations'].append({'field':'guitar_contact','status':'exact string/fret/octave not assigned for abstract source notes; not native-playback-ready'})
 if es and not timed:r['field_limitations'].append({'field':'relative_event_timing','status':'interpretation/implementation pending; optional BPM is not the blocker'})
 r['status']={'TIMED_SOURCE_EVENT_CONTRACT':'SOURCE_SUPPORTED_RELATIVE_EVENTS','COMPLETE_MANUAL_NONPLAYBACK_CONTRACT':'SOURCE_SUPPORTED_MANUAL_TASK','LEARNER_CHOICE_WITHOUT_FIXED_REALIZATION':'LEARNER_CHOICE_PLAN','DEMONSTRATED_SOURCE_CONFLICT':'SOURCE_UNRESOLVED','IMPLEMENTATION_OR_INTERPRETATION_PENDING':'IMPLEMENTATION_PENDING'}[category]
 if r['source_identity']=='level080/modulea/p003-card01/cmaj7melodyefge':r['provenance']['worked_example_boundary']='No supplemental worked example imported or counted as this full exact unit; source Melody/route/passes retained with interpretation pending.'
 return r

class ManualTaskSession:
 def __init__(self,record):
  if record['contract_category']!='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT':raise ValueError('manual contract not complete')
  self.contract=copy.deepcopy(record['implementation']['task']['contract']);self.state='awaiting_manual_response';self.responses=None
 def submit(self,responses):
  if self.state!='awaiting_manual_response':raise ValueError('session closed')
  fields={x['key']:x for x in self.contract['response_fields']}
  if set(responses)!=set(fields):raise ValueError('missing or foreign response fields')
  for key,value in responses.items():
   f=fields[key]
   if f['type']=='integer':
    if type(value) is not int or not f['printed_minimum']<=value<=f['printed_maximum']:raise ValueError('outside printed integer range')
   elif not isinstance(value,str) or not value.strip():raise ValueError('empty manual response')
  self.responses=copy.deepcopy(responses);self.state='manual_response_recorded'
  return {'state':self.state,'responses':self.responses,'origin':'manual_self_report','verified_pass':False,'credit_awarded':False,'mastery_awarded':False}
 def cancel(self):
  if self.state!='awaiting_manual_response':raise ValueError('session closed')
  self.state='cancelled'
