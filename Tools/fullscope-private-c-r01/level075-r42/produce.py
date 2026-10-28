from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from ladder_contract import KEY,PASSES,HIERARCHY,FOOTER,contract
from master_source import PROFILES,MASTER_BARS
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r42')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
old=json.loads((R/base).read_text().splitlines()[53]);assert old['package_key']==KEY and old['implementation']['events']==[]
pdf=Path(old['source_refs'][0]['path']);txt=Path(old['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[13].extract_text();norm=lambda s:' '.join(s.split());lines=page.splitlines();matches=[]
for i,(material,test) in enumerate(PASSES,1):
    literal='\n'.join((str(i),material,test,'no structural errors'));assert page.count(literal)==1
    matches.append({'pass':i,'physical_page':14,'original_fields_text':literal,'pdf_text_start_line':lines.index(str(i))+1})
assert HIERARCHY in norm(page) and FOOTER in norm(page)
txtlines=(R/txt).read_text().splitlines()
for profile in PROFILES:
    n=profile['txt_start_line']-1;assert txtlines[n:n+3]==profile['original_lines']
assert [b['bar'] for b in MASTER_BARS]==list(range(1,61))
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':54,'physical_page':14,
    'original_page_text':page,'matched_passes':matches,'full_error_hierarchy':HIERARCHY,'full_footer':FOOTER,
    'master_profile_count':9,'master_bar_count':60,'master_source_module':pin(Path('Tools')/L/'master_source.py'),
    'source_key':KEY,'method':'original PDF text stream/TXT exact joins; no fresh rendered visual inspection'})
r=deepcopy(old);c=contract();r['schema_version']='fathom-private-source-implementation.42';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
    'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'ladder_contract.py'),'class':'LadderFlow','pure_python_reference':True}
r['unresolved_reasons']=[{'disposition':'LEARNER_FULL_FORM_REALIZATION_AND_SELF_REPORT_REQUIRED',
    'reason':'Full private source ladder/error-policy contract implemented; choices and reports are not original note events, recognized performance or app audio.'}]
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
r['contract_capabilities']['complete_manual_response_contract']=True
r['provenance']['manual_r42']={'base_packet':pin(base),'base_jsonl_line':54,'source_check':pin(source),
    'author':'private producer C','independent_source_review':'Pending','source_event_or_score_invented':False}
packet=Path('Build')/L/'rehearsal-ladder-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'ladder_contract.py'),
    'master_source_module':pin(Path('Tools')/L/'master_source.py'),'exact_replaced_keys':[KEY],
    'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
    'source_passes':8,'source_master_bars':60,'source_contacts_added':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
