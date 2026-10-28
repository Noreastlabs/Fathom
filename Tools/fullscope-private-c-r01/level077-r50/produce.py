from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from function_contract import KEYS,ROMAN,FAMILY,SENSATION,BLIND,REPEAT,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r50');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][46:54];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[4].extract_text();lines=page.splitlines();t=(R/txt).read_text();matches=[]
for i,r in enumerate(rows[:7]):
    values=[ROMAN[i],FAMILY[i],SENSATION[i],'root then 3rd','I'];block='\n'.join(values);assert page.count(block)==1
    if i<6:assert r['implementation']['task']['table_fields'][0]['values']==values
    matches.append({'key':KEYS[i],'base_jsonl_line':47+i,'full_pdf_fields':values,'pdf_block_text':block,
      'pdf_block_first_text_line':next(n+1 for n in range(len(lines)-4) if lines[n:n+5]==values),
      'prior_extracted_values':r['implementation']['task']['table_fields'][0]['values'],
      'mapping':'exact unique full source text block; official key retained, no ordinal reassignment'})
    assert ROMAN[i]+': '+FAMILY[i]+'; '+SENSATION[i] in t
assert BLIND in ' '.join(page.split()) and REPEAT in ' '.join(page.split())
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':5,
  'original_page_text':page,'matched_rows':matches,'full_blind_instruction':BLIND,'repeat_no_shape_instruction':REPEAT,
  'exact_eighth_supplement_key':KEYS[7],'vii_dim_recovery':'Full text block remains visible in original PDF text stream; old table extraction split last row and mixed following annotation. Raw extraction and official r8 locator preserved.',
  'method':'original PDF text stream; no new rendered visual review','no_source_pitch_octave_fret_events_added':True})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.50';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
      'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'function_contract.py'),'class':'FunctionFlow','pure_python_reference':True}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_PARTNER_AND_VOICING_REQUIRED','reason':'Full manual response/reveal/singing/resolution/repeat contract; actual partner sound and rootless/shell voicing remain external prerequisites. Performance remains self-report, not native or source acceptance.'}]
    r['provenance']['manual_r50']={'base_packet':pin(base),'base_jsonl_line':47+i,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    if i==6:r['implementation']['task']['source_field_recovery']={'original_extracted_fields_retained':True,'recovered_fields':c['source_fields'],'authority':pin(source),'identity_changed':False}
    if i==7:r['implementation']['task']['prior_contract_correction']={'base_packet':pin(base),'base_jsonl_line':54,'reason':'Two generic split-text response fields failed to represent full family/Roman/chord order, answer withholding, singing/resolution, no-shape and repeat obligations; corrected without extra child or manual-count increment.'}
    out.append(r)
packet=Path('Build')/L/'function-hearing-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'function_contract.py'),
  'exact_replaced_keys':list(KEYS),'attempted':8,'source_supported_manual_contracts':8,'new_complete_manual_contracts':7,'existing_manual_contract_corrections':1,
  'partial_unresolved':0,'unattempted':0,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'prior-contract-correction.json',{'base_packet':pin(base),'overlay':pin(packet),'key':KEYS[7],'base_line':54,'overlay_line':8,
  'old_contract':'Two generic text fields split family/Roman and chord-name clauses; no complete ordered source-role/reveal/singing/repeat model.',
  'replacement':'Concrete two-presentation partner-source contract; ordered typed answers/reveal/root-third/tonic/release/report; no-shape and rootless/shell repeat.',
  'manual_count_increment_for_this_key':0,'historical_packet_changed':False})
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
