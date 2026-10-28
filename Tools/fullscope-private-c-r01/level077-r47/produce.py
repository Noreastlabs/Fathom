from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from interval_contract import KEYS,LABELS,UPPER,PRACTICE,NO_SEARCH,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r47');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][:12];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[1].extract_text();lines=page.splitlines();t=(R/txt).read_text();matches=[]
for i,r in enumerate(rows):
    block='\n'.join((LABELS[i],str(i+1),'C-'+UPPER[i]));assert page.count(block)==1
    tx=f'{LABELS[i]}: {i+1} semitones; reference C-{UPPER[i]}';assert tx in t
    assert r['implementation']['task']['table_fields'][0]['values']==[LABELS[i],str(i+1),'C-'+UPPER[i],'','']
    matches.append({'key':KEYS[i],'base_jsonl_line':i+1,'pdf_row_text':block,'pdf_text_line':lines.index(LABELS[i])+1,'txt_line':t.splitlines().index(tx)+1,'txt_literal':tx})
assert PRACTICE in ' '.join(page.split()) and NO_SEARCH in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':2,
    'original_page_text':page,'matched_rows':matches,'full_practice':PRACTICE,'no_search_rule':NO_SEARCH,'no_search_txt_line':t.splitlines().index(NO_SEARCH)+1,
    'method':'original PDF text stream; no fresh rendered visual review'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.47';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
      'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'interval_contract.py'),'class':'IntervalFlow','pure_python_reference':True}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_REFERENCE_AND_MANUAL_PERFORMANCE_REQUIRED','reason':'Source interval/reference and direction contract retained; actual reference audio, chosen octaves/frets and hearing/singing/play reports remain external, not verified or native timed.'}]
    r['provenance']['manual_r47']={'base_packet':pin(base),'base_jsonl_line':i+1,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    out.append(r)
packet=Path('Build')/L/'interval-atlas-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'interval_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':12,'source_supported_manual_contracts':12,'partial_unresolved':0,'unattempted':0,
    'source_reference_pitch_classes':24,'source_note_events_added':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
