from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from call_response_contract import RAW,KEYS,FOOTER,NO_SEARCH,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r58');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
old=[json.loads(x) for x in (R/base).read_text().splitlines()][94:102];assert [r['package_key'] for r in old]==list(KEYS)
pdf=Path(old[0]['source_refs'][0]['path']);txt=Path(old[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce' and pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[10].extract_text();joined=' '.join(page.split());txtlines=(R/txt).read_text().splitlines()
assert FOOTER in joined and '8 PAIRS | 64 SOURCE + 64 RESPONSE TONES' in joined and NO_SEARCH in (R/txt).read_text()
joins=[]
for i,(r,raw) in enumerate(zip(old,RAW)):
    parts=r['implementation']['task']['printed_components'];assert parts[:3]==[raw[0],raw[1],'write/play exact']
    assert parts[3].splitlines()[0]==raw[2] and ' '.join((raw[0],raw[1],'write/play exact',raw[2])) in joined
    literal=f'{raw[0]}: question {raw[1]}; answer {raw[2]}';match=[j+1 for j,v in enumerate(txtlines) if v==literal];assert len(match)==1
    assert r['implementation']['events']==[] and r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    joins.append({'key':KEYS[i],'base_jsonl_line':95+i,'physical_page':11,'txt_line':match[0],'printed_chord':raw[0],'printed_question':raw[1],'clean_answer_model':raw[2],
      'original_model_field_retained':parts[3],'annotation_overlap_recovered_in_new_contract_only':i==7})
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':11,
 'original_page_text':page,'full_footer':FOOTER,'paired_no_search':NO_SEARCH,'exact_joins':joins,
 'extent':{'literal_header':'8 PAIRS | 64 SOURCE + 64 RESPONSE TONES','actual_rows':8,'actual_question_tokens':32,'actual_answer_model_tokens':32,'extra_notes_manufactured':0},
 'method':'original PDF text and exact paired TXT; last answer annotation overlap recovered without changing original raw/key; no new rendered visual review'})
rows=[]
for i,o in enumerate(old):
    r=deepcopy(o);c=contract(i);r['schema_version']='fathom-private-source-implementation.58';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'chosen_plan_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'call_response_contract.py'),'class':'CallResponseFlow','pure_python_reference':True}
    r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'clean_answer_model':c['printed_answer_model'],'original_raw_retained':True,'identity_changed':False}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_SOURCE_AND_EXPLICIT_RESPONSE_CHOICES_REQUIRED','reason':'Complete four-pass manual contract; original notes/models retained. Rhythm/register/contact/next-chord response choices authored, external question/held next-chord self-reported, no fixed source projection or delayed-echo mastery.'}]
    r['provenance']['manual_r58']={'base_packet':pin(base),'base_jsonl_line':95+i,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False};rows.append(r)
packet=Path('Build')/L/'call-response-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'call_response_contract.py'),
 'exact_replaced_keys':list(KEYS),'attempted':8,'source_supported_manual_contracts':8,'partial_unresolved':0,'unattempted':0,
 'printed_question_tokens':32,'printed_answer_model_tokens':32,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
