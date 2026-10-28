from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from workflow_contract import KEY,STAGES,TXT_STACK,PDF_MARKS,TXT_MARKS,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level076-r46');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level076-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='f15e868a4d6f57148ada4f36e73683acda75e4a0f4c925b256ecb054f2e6181c'
r=deepcopy(json.loads((R/base).read_text().splitlines()[0]));assert r['package_key']==KEY and r['implementation']['events']==[]
pdf=Path(r['source_refs'][0]['path']);txt=Path(r['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='504fcc4c233f43f98c48b5a05da42ce4cfcb03f2be33c094ba795d02f83d3e18'
assert pin(txt)['sha256']=='b2ef0970911a7fc81175b166db85fae972f84628a9dec2ad5e42fb6e04664675'
page=PdfReader(R/pdf).pages[1].extract_text();lines=page.splitlines();matches=[]
for i,(name,question,fields) in enumerate(STAGES,1):
    label=f'{i}. {name}';assert page.count(label)==1 and page.count(question)==1;assert page.index(label)<page.index(question)
    matches.append({'number':i,'name':name,'source_question':question,'pdf_label_text_line':lines.index(label)+1,'authored_field_split':list(fields)})
assert PDF_MARKS in page and 'DO NOT SOLVE ALL LAYERS AT ONCE' in page
t=(R/txt).read_text();stack='SEVEN-PASS TRANSCRIPTION STACK\n'+'\n'.join(f'{i}. {n}' for i,n in enumerate(TXT_STACK,1));assert stack in t
marks='UNCERTAINTY NOTATION\n'+'\n'.join(TXT_MARKS);assert marks in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':2,
    'original_page_text':page,'matched_stages':matches,'pdf_marks':PDF_MARKS,'txt_stack':stack,'txt_uncertainty':marks,
    'txt_stack_start_line':t.splitlines().index('SEVEN-PASS TRANSCRIPTION STACK')+1,'scope_decision':'Use exactPDFkey8stage route; retain TXT7passstack separately, no equivalence/correction claim.',
    'method':'originalPDFtextstream, no fresh rendered visual review'})
c=contract();r['schema_version']='fathom-private-source-implementation.46';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
    'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'workflow_contract.py'),'class':'Workflow','pure_python_reference':True}
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
r['unresolved_reasons']=[{'disposition':'EXTERNAL_EXCERPT_AND_MANUAL_ANALYSIS_REQUIRED','reason':'Complete manual workflow implemented; chosen external source and actual listening/analysis remain learner-supplied, no fixed playback or app verification.'}]
r['provenance']['manual_r46']={'base_packet':pin(base),'base_jsonl_line':1,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
packet=Path('Build')/L/'workflow-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'workflow_contract.py'),
    'exact_replaced_keys':[KEY],'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
    'source_stages':8,'authored_response_fields':20,'source_events_added':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
