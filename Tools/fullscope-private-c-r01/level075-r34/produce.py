from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import json,hashlib,datetime,time,resource
from texture_contract import KEY,LEVELS,BLOCKS,FOOTER,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r34')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
old=[json.loads(x) for x in (R/base).read_text().splitlines()][13];assert old['package_key']==KEY
pdf=Path(old['source_refs'][0]['path']);txt=Path(old['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[4].extract_text();norm=lambda x:' '.join(x.split())
assert '128 CONTACTS' in page and 'CHANGE ONE ARRANGEMENT VARIABLE AT A TIME' in page
for i,row in enumerate(LEVELS,1):assert norm(' '.join([str(i),*row])) in norm(page)
for i,texture in enumerate(BLOCKS):assert norm(f'Bars {2*i+1}-{2*i+2} {texture}') in norm(page)
assert norm(FOOTER) in norm(page)
module_txt='128 contacts. Practice foundation, comping, counterline, lead, and silence roles. Change density and register without changing tempo.'
txtlines=(R/txt).read_text().splitlines();assert module_txt in txtlines
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':14,
    'pdf_page':5,'method':'pypdf original text stream, no fresh rendered visual QA',
    'source_table':[[i,*row] for i,row in enumerate(LEVELS,1)],
    'source_blocks':[{'bars':[2*i+1,2*i+2],'texture':x} for i,x in enumerate(BLOCKS)],
    'full_footer':FOOTER,'module_txt_instruction':module_txt,'module_txt_line':txtlines.index(module_txt)+1})
r=deepcopy(old);assert r['implementation']['events']==[];c=contract()
r['schema_version']='fathom-private-source-implementation.34';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
    'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'texture_contract.py'),'class':'TextureFlow','pure_python_reference':True}
r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_REQUIRED_FOR_FIXED_PLAYBACK',
    'reason':'Manual task fully represented; selected notes/frets/register and harmonic placement remain learner choices.128header is not converted to invented timedcontacts.'}]
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_IMPLEMENTED_PENDING_REVIEW'
r['contract_capabilities']['complete_manual_response_contract']=True
r['provenance']['manual_r34']={'base_packet':pin(base),'base_jsonl_line':14,'source_check':pin(source),
    'author':'private producer C','independent_source_review':'Pending','source_events_invented':False}
packet=Path('Build')/L/'texture-ladder-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,
    'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),
    'model':pin(Path('Tools')/L/'texture_contract.py'),'exact_replaced_keys':[KEY],
    'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
    'source_contacts_preserved':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
