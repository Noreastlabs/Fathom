from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from handoff_contract import KEYS,ROWS,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r40')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
base_rows=[json.loads(x) for x in (R/base).read_text().splitlines()];rows=base_rows[54:60];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[14].extract_text();lines=page.splitlines();matches=[]
for i,row in enumerate(ROWS):
    literal='\n'.join(row[1:]);assert page.count(literal)==1 and rows[i]['source_payload']['printed_label']==row[1]
    matches.append({'key':KEYS[i],'base_jsonl_line':55+i,'physical_page':15,'original_fields_text':literal,'pdf_text_start_line':lines.index(row[1])+1})
assert 'CHANGE ROLE WITHOUT CHANGING THE CLOCK' in page
module='240 contacts. Speak chart, roots, shells, written textures, cues/fills, dynamics/register, role changes, then one uninterrupted take.'
txtlines=(R/txt).read_text().splitlines();assert module in txtlines
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'matched_rows':matches,
    'original_page_text':page,'module_txt_instruction':module,'module_txt_line':txtlines.index(module)+1,
    'scope_note':'Source localG7bar8/Cmaj7bar4 not master60-bar positions; six table rows only. Existing handoffcell row61 unchanged.',
    'method':'original PDF text stream/TXT, not fresh rendered visual inspection'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.40';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'handoff_contract.py'),'class':'HandoffFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_REQUIRED_FOR_PERFORMANCE',
        'reason':'Full private manual contract implemented. Chosen pitches, registers, spacing and positive rest duration are not printed source events or app playback.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['provenance']['manual_r40']={'base_packet':pin(base),'base_jsonl_line':55+i,'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','source_events_or_master_mapping_invented':False}
    out.append(r)
packet=Path('Build')/L/'role-handoff-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'handoff_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':6,'source_supported_manual_contracts':6,'partial_unresolved':0,'unattempted':0,
    'source_contacts_added':0,'new_official_keys':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
