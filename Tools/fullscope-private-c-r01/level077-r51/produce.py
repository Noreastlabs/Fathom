from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from progression_contract import KEYS,RAW,FOOTER,NO_SEARCH,literal,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r51');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][54:66];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[5].extract_text();lines=page.splitlines();t=(R/txt).read_text();matches=[]
for i,r in enumerate(rows):
    values=list(RAW[i]);block='\n'.join(values);assert page.count(block)==1
    assert r['implementation']['task']['table_fields'][0]['values']==values
    matches.append({'key':KEYS[i],'base_jsonl_line':55+i,'full_pdf_fields':values,'pdf_block_text':block,
      'pdf_block_first_text_line':next(n+1 for n in range(len(lines)-3) if lines[n:n+4]==values),
      'printed_chord_tokens':values[1].split('-'),'terminal_roman':values[2].split('-')[-1],'literal_terminal_I_omission':literal(i)})
assert FOOTER in ' '.join(page.split()) and NO_SEARCH in t
assert '12 PROGRESSIONS | 96 CHORD EVENTS' in ' '.join(page.split())
assert [i+1 for i in range(12) if literal(i)]==[1,2,3,8]
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':6,
  'original_page_text':page,'matched_rows':matches,'full_second_pass_footer':FOOTER,'no_search':NO_SEARCH,
  'printed_harmonic_token_count':48,'literal_heading_chord_events':96,'invented_events':0,
  'method':'original PDF text stream; no new rendered visual review','non_I_ending_rows_pending':[i+1 for i in range(12) if not literal(i)]})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.51';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
      'learner_response':None,'completion_claim':None,'automatic_score':False,'whole_contract_available':literal(i)}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'progression_contract.py'),'class':'ProgressionFlow','pure_python_reference':True,'whole_completion_available':literal(i)}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT' if literal(i) else 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW' if literal(i) else 'SECONDARY_SOURCE_INTERPRETATION_PENDING'
    r['contract_capabilities']['complete_manual_response_contract']=literal(i)
    r['unresolved_reasons']=([{'disposition':'EXTERNAL_SOURCE_AND_MANUAL_TONIC_REALIZATION_REQUIRED','reason':'Full two-pass manual contract; actual source sound, contextual nearest judgement and performance remain external/unverified.'}] if literal(i) else
      [{'disposition':'SECONDARY_SOURCE_INTERPRETATION_PENDING','primary_dictation_implemented':True,'reason':c['secondary_pending_reason'],'source_correction_adopted':False}])
    r['provenance']['manual_r51']={'base_packet':pin(base),'base_jsonl_line':55+i,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    out.append(r)
packet=Path('Build')/L/'progression-dictation-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
referral={'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'source_check':pin(source),'overlay':pin(packet),'physical_page':6,
  'literal_footer':FOOTER,'literal_heading':'12 PROGRESSIONS | 96 CHORD EVENTS','printed_chord_tokens':48,
  'unresolved_rows':[{'key':KEYS[i],'base_jsonl_line':55+i,'overlay_jsonl_line':i+1,'printed_source':list(RAW[i]),
    'missing_interpretation':'Printed final chord is IV or V, not the terminal I described by omission footer. Primary four-chord dictation available; no tonic insertion/replacement or non-tonic omission.'} for i in range(12) if not literal(i)],
  'literal_rows':[1,2,3,8],'literal_omission_rule':'Remove only final token, retain penultimate I in rows3/8.','source_correction_adopted':False,'source_conflict_count_increment':0}
write(Path('Results')/L/'terminal-tonic-source-referral.json',referral)
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'progression_contract.py'),
  'exact_replaced_keys':list(KEYS),'attempted':12,'source_supported_manual_contracts':4,'usable_primary_partial_contracts':8,
  'partial_unresolved':8,'unattempted':0,'printed_harmonic_tokens_retained':48,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
