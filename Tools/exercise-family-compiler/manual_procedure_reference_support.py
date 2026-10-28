#!/usr/bin/env python3
"""Future compiler-only cached witness support; no owner/admission/UI defaults.

Resolve original row and source-action witnesses once per pinned payload file.
Project trusted finite domain expectations for a later owner's comparison only.
The functions never produce learner reports or imply execution/release.
"""
import hashlib,json
from pathlib import Path

class BindingError(ValueError): pass
class UnresolvedReport(ValueError): pass

def require(value,message):
 if not value:raise BindingError(message)
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
def sha(value):return hashlib.sha256(value).hexdigest()
def exact(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
 return a==b

def path_value(value,path):
 require(isinstance(path,list) and len(path)>0,'EMPTY_REFERENCE')
 for part in path:
  if type(part) is str:require(isinstance(value,dict) and part in value,'MISSING_REFERENCE');value=value[part]
  elif type(part) is int:require(isinstance(value,list) and 0<=part<len(value),'REFERENCE_RANGE');value=value[part]
  else:raise BindingError('REFERENCE_TYPE')
 return value

class CachedWitnesses:
 def __init__(self,root):self.root=Path(root).resolve(strict=True);self.cache={};self.files_hashed=0;self.rows_bound={}
 def payload(self,reference):
  require(set(reference)=={'path','bytes','sha256','jsonl_line'},'EXACT_PAYLOAD_REF')
  name=reference['path'];require(type(name) is str and name and not Path(name).is_absolute() and all(x not in ('','.', '..') for x in name.split('/')),'PAYLOAD_PATH')
  require(type(reference['jsonl_line']) is int and reference['jsonl_line']>0,'PAYLOAD_LINE')
  require(type(reference['bytes']) is int and 0<reference['bytes']<=32*1024*1024,'PAYLOAD_BYTES')
  filepin=(reference['bytes'],reference['sha256'])
  if name not in self.cache:
   path=self.root
   for part in name.split('/'):
    path/=part;require(not path.is_symlink(),'PAYLOAD_SYMLINK')
   require(path.is_file(),'PAYLOAD_FILE');raw=path.read_bytes();require(len(raw)==reference['bytes'] and sha(raw)==reference['sha256'],'PAYLOAD_PIN_DRIFT')
   self.cache[name]=(filepin,raw.splitlines());self.files_hashed+=1
  pin,lines=self.cache[name];require(pin==filepin,'PAYLOAD_PIN_CONTRADICTION');index=reference['jsonl_line']-1;require(index<len(lines),'PAYLOAD_LINE_RANGE')
  raw=lines[index];require(bool(raw),'EMPTY_PAYLOAD_ROW');return raw,json.loads(raw)
 def resolve(self,row):
  require(row['schema']=='fathom.manual-procedure-reference-definition.1','REFERENCE_SCHEMA')
  raw,original=self.payload(row['payload_ref']);require(sha(raw)==row['original_row_sha256'] and sha(compact(original))==row['original_compact_sha256'],'ORIGINAL_ROW_HASH')
  require(original['package_key']==row['source_key'] and original['source_identity']==row['source_identity'],'ORIGINAL_IDENTITY')
  contract=path_value(original,row['retained_contract_path']);require(sha(compact(row['program']))==row['contract_sha256'],'COMPILED_PROGRAM_HASH')
  require(type(contract) is dict,'SOURCE_CONTRACT_OBJECT')
  if row['retained_contract_path']==['implementation','table_task']:
   require(original['implementation']['kind']=='manual_table_curriculum_task' and set(contract)=={'printed_fields'} and type(contract['printed_fields']) is list and len(contract['printed_fields'])==4 and all(type(x) is str for x in contract['printed_fields']),'CLOSED_SOURCE_TABLE')
   program=row['program'];facts=program['source_facts'];require(facts['printed_fields']==contract['printed_fields'] and facts['printed_geometry'] is None and facts['printed_strokes'] is None and facts['source_clock'] is None and facts['fixed_bpm'] is None and program['fixed_bpm'] is None and program['grants_credit'] is False and program['performance_observed'] is False and program['automatic_mastery'] is False,'MANUAL_SOURCE_TABLE_BOUNDARY')
  elif row['retained_contract_path']==['implementation','task_contract']:
   require(original['implementation']['kind']=='source_defined_task' and contract.get('performance_observed') is False and contract.get('task_kind')==row['program']['source_task_kind'] and type(contract.get('ordered_source_instructions')) is list and all(type(x) is dict and set(x)=={'line','text'} and type(x['line']) is int and x['line']>0 and type(x['text']) is str for x in contract['ordered_source_instructions']),'MANUAL_SOURCE_ASSESSMENT_BOUNDARY')
   require(row['program']['fixed_bpm'] is None and row['program']['grants_credit'] is False and row['program']['performance_observed'] is False and row['program']['automatic_mastery'] is False and row['program']['runtime_admitted'] is False,'NO_SOURCE_ASSESSMENT_ADMISSION')
  elif row['retained_contract_path']==['implementation']:
   require(original['implementation']['kind']=='manual_curriculum_task' and row['program']['original_kind_preserved'] is True and row['program']['source_kind']=='manual_curriculum_task' and row['program']['fixed_bpm'] is None and row['program']['grants_credit'] is False and row['program']['performance_observed'] is False and row['program']['automatic_mastery'] is False and row['program']['runtime_admitted'] is False,'MANUAL_CURRICULUM_SOURCE_BOUNDARY')
  else:require(contract.get('package_key')==row['source_key'] and contract.get('fixed_bpm') is None and contract.get('grants_credit') is False and contract.get('runtime_admitted') is False,'MANUAL_SOURCE_BOUNDARY')
  require(row['source_key'] not in self.rows_bound,'DUPLICATE_SOURCE_KEY');self.rows_bound[row['source_key']]=(row['source_identity'],row['original_row_sha256'],row['contract_sha256'])
  return original,contract

def source_step(contract,reference):
 require(set(reference)=={'original_contract_path'},'EXACT_SOURCE_STEP_REF');p=reference['original_contract_path'];require(type(p) is list and len(p)==2 and p[0]=='steps' and type(p[1]) is int,'BOUNDED_SOURCE_STEP_REF')
 return path_value(contract,p)

def resolve_node_bindings(contract,node):
 # Preserve the literal sustain/release witness separately: neither a inferred
 # duration nor an executed release is returned by this compile-time operation.
 out={}
 require(not ('source_action_ref' in node and 'source_action_refs' in node),'DUPLICATE_SOURCE_BINDING_FORM')
 if 'source_action_refs' in node:
  refs=node['source_action_refs'];require(type(refs) is list and 1<=len(refs)<=2,'FINITE_SOURCE_UNIT')
  indices=[ref['original_contract_path'][1] for ref in refs];require(all(type(x) is int for x in indices) and indices==list(range(indices[0],indices[0]+len(indices))),'ORDERED_UNINTERRUPTED_SOURCE_UNIT')
  require(len(refs)==1 or node.get('physical') is True,'PHYSICAL_SOURCE_UNIT')
  out['source_action_refs']=[source_step(contract,ref) for ref in refs]
 for kind in ('source_action_ref','release_source_action_ref'):
  if kind in node:out[kind]=source_step(contract,node[kind])
 return out

def selected_domain_reports(operator,selection,domains):
 require(set(operator)=={'kind','domain','selection','fields'} and operator['kind']=='selected_domain_reports','EXACT_DOMAIN_OPERATOR')
 require(type(selection) is dict and set(selection)==set(operator['selection']),'EXACT_SELECTION_FIELDS')
 require(type(domains) is list and 0<len(domains)<=4096,'FINITE_SOURCE_DOMAIN')
 require(type(operator['fields']) is dict and bool(operator['fields']),'DOMAIN_PROJECTIONS')
 for field,property_name in operator['fields'].items():require(type(field) is str and field and property_name in {'printed_note','role','string','fret','pick','chosen_pick'},'CLOSED_CONTACT_PROPERTY')
 seen=[];match=[]
 for entry in domains:
  require(type(entry) is dict and set(entry)=={'selection','contacts'},'EXACT_SOURCE_DOMAIN_RECORD')
  require(type(entry['selection']) is dict and set(entry['selection'])==set(selection),'DOMAIN_SELECTION_SHAPE')
  require(not any(exact(entry['selection'],x) for x in seen),'DUPLICATE_SOURCE_DOMAIN');seen.append(entry['selection'])
  contacts=entry['contacts'];require(type(contacts) is list and 0<len(contacts)<=64,'FINITE_SOURCE_CONTACTS')
  for name in operator['fields'].values():require(all(type(x) is dict and name in x for x in contacts),'SOURCE_CONTACT_PROPERTY')
  if exact(entry['selection'],selection):match.append(entry)
 if any(x is None for x in selection.values()):raise UnresolvedReport('UNKNOWN_DOMAIN_SELECTION')
 require(len(match)==1,'CLOSED_DOMAIN_SELECTION')
 return {field:[x[property_name] for x in match[0]['contacts']] for field,property_name in operator['fields'].items()}

def nonempty_trimmed_text(descriptor,value):
 require(set(descriptor)=={'kind','value_ref','minimum','maximum'} and descriptor['kind']=='nonempty_trimmed_text','EXACT_TRIMMED_TEXT_GUARD')
 require(descriptor['value_ref']=={'scope':'payload','path':['simplified_remainder_description']},'CLOSED_REMAINDER_REFERENCE')
 require(type(descriptor['minimum']) is int and type(descriptor['maximum']) is int and 1<=descriptor['minimum']<=descriptor['maximum']<=512,'TRIMMED_TEXT_BOUNDS')
 require(type(value) is str,'TRIMMED_TEXT_TYPE')
 return descriptor['minimum']<=len(value.strip())<=descriptor['maximum']
