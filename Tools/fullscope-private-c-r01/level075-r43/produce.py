from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from contrast_contract import KEYS,ROWS,CONTEXT_SIXTH,EXAMPLE,FOOTER,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r43')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][30:35];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[8].extract_text();lines=page.splitlines();matches=[]
for i,row in enumerate(ROWS):
    literal='\n'.join((*row[1:],'same tempo'));assert page.count(literal)==1
    assert rows[i]['implementation']['task']['table_fields'][0]['values']==[*row[1:],'same tempo']
    matches.append({'key':KEYS[i],'base_jsonl_line':31+i,'physical_page':9,'original_fields_text':literal,'pdf_text_start_line':lines.index(row[1])+1})
assert '\n'.join(CONTEXT_SIXTH) in page
for line in EXAMPLE:assert page.count(line)==1
assert FOOTER in ' '.join(page.split())
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':9,'original_page_text':page,
    'matched_rows':matches,'context_sixth_row':list(CONTEXT_SIXTH),'context_row_new_key':False,
    'full_example_lines':list(EXAMPLE),'full_footer':FOOTER,'method':'original PDF text stream; no new rendered visual inspection'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.43';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'contrast_contract.py'),'class':'ContrastFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_AND_MANUAL_LISTENING_REPORT_REQUIRED',
        'reason':'Private full texture-contrast contract implemented; chosen voicings/controls are not printed source notes/timing or verified listening.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['provenance']['manual_r43']={'base_packet':pin(base),'base_jsonl_line':31+i,'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','source_events_or_keys_invented':False}
    out.append(r)
packet=Path('Build')/L/'texture-contrast-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'contrast_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':5,'source_supported_manual_contracts':5,'partial_unresolved':0,'unattempted':0,
    'source_contacts_added':0,'context_sixth_row_new_keys':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
