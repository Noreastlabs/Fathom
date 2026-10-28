from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from contour_contract import KEYS,ROWS,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r36')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][35:41]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[9].extract_text();norm=lambda x:' '.join(x.split());matches=[]
assert '20 CELLS | 160 CONTACTS' in page and 'DYNAMICS ARE A FORM PARAMETER, NOT AN AFTERTHOUGHT' in page
for i,(old,row) in enumerate(zip(rows,ROWS)):
    literal=' '.join([row[1],*row[2],row[3],'tempo and note count fixed'])
    assert norm(literal) in norm(page) and norm(literal) in norm(old['source_payload']['pdf_region_text'])
    matches.append({'key':old['package_key'],'base_jsonl_line':i+36,'physical_page':10,'table_row':i+1,'literal':literal})
module='160 contacts. Practice p-mp-mf-f contours, register ladders, and the complete arrangement map.'
lines=(R/txt).read_text().splitlines();assert module in lines
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'matched_rows':matches,
    'method':'original PDF text stream; no fresh rendered visual QA','module_txt_context':module,'module_txt_line':lines.index(module)+1,
    'separate_register_ladder_child_untouched':True,'header_realization_not_inferred':'20 CELLS | 160 CONTACTS'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.36';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'contour_contract.py'),'class':'ContourFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'LEARNER_MATERIAL_REQUIRED_FOR_FIXED_REALIZATION',
        'reason':'Complete manual source task; notes/rhythm/frets/counts chosen by learner, not invented from160header.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_IMPLEMENTED_PENDING_REVIEW'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['provenance']['manual_r36']={'base_packet':pin(base),'base_jsonl_line':i+36,'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','source_events_invented':False}
    out.append(r)
packet=Path('Build')/L/'dynamic-contour-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'contour_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':6,'source_supported_manual_contracts':6,'partial_unresolved':0,'unattempted':0,
    'source_contacts_preserved':0,'source_bar_dynamic_targets':24,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
