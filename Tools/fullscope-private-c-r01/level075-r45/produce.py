from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from fill_role_contract import KEY,CONTACTS,TABLE,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r45');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r33/role-contact-overlay.jsonl');assert pin(base)['sha256']=='954dfb56594066941ef8d2c71f6d4d4b5f8f19a5e87b066bfeb279804f52844c'
r=deepcopy(json.loads((R/base).read_text().splitlines()[3]));assert r['package_key']==KEY
projection=Path('Build/fullscope-private-c-r01/level075-r33/source-contact-projection.json');assert pin(projection)['sha256']=='19cbaa8e23d16f493079a635be6181bcc9f3ab196a82b63a29c10c782c01a9ef'
card=json.loads((R/projection).read_text())['cards'][3];assert card['key']==KEY and card['events']==r['implementation']['events']
assert [(e['string'],e['fret']) for e in card['events']]==list(CONTACTS)
pdf=Path(r['source_refs'][0]['path']);txt=Path(r['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[3].extract_text();a=page.index('Fill-after-space role');b=page.index('Level 75 - complete-performance integration.');block=page[a:b]
assert page.count('Fill-after-space role')==1 and 'fill begins after beat 3' in block
for row in card['source_rows']:assert row['source_text'] in block
for row in TABLE:assert '\n'.join(row) in page
module='128 contacts. Practice foundation, comping, counterline, lead, and silence roles. Change density and register without changing tempo.'
t=(R/txt).read_text();assert module in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),
    'r33_source_projection':pin(projection),'r33_source_questions':pin('Results/fullscope-private-c-r01/level075-r33/source-questions.json'),
    'physical_page':4,'original_full_block':block,'label_text_line':page.splitlines().index('Fill-after-space role')+1,
    'source_role_table':[list(x) for x in TABLE],'txt_module':module,'txt_module_line':t.splitlines().index(module)+1,
    'events_unchanged_from_r33':True,'source_target_added':False,'method':'original PDF text stream; no new rendered visual review'})
c=contract();r['schema_version']='fathom-private-source-implementation.45';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
    'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'fill_role_contract.py'),'class':'FillRoleFlow','pure_python_reference':True}
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
r['unresolved_reasons']=[{'disposition':'LEARNER_SPACING_AND_ENDING_REQUIRED','reason':'Source11contacts and afterbeat3 retained. Explicit one-bar spacing/end is authored choice; exact source timing/gates and source extent remain unknown, no fixed-source qualification.'}]
r['provenance']['manual_r45']={'base_packet':pin(base),'base_jsonl_line':4,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','existing_source_events_unchanged':True}
packet=Path('Build')/L/'fill-role-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'fill_role_contract.py'),
    'exact_replaced_keys':[KEY],'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
    'existing_source_contacts_preserved':11,'source_contacts_added':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
