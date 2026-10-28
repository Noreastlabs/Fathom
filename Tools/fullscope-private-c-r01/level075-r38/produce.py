from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time
from recovery_contract import KEYS,ROWS,LADDER,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r38')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
allrows=[json.loads(x) for x in (R/base).read_text().splitlines()];base_lines=list(range(63,70));rows=[allrows[n-1] for n in base_lines]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[18].extract_text();norm=lambda x:' '.join(x.split());lines=page.splitlines()
for row in ROWS:
    joined='\n'.join(row[1:]);assert page.count(joined)==1
for i,s in enumerate(LADDER,1):assert f'{i}. {s}' in page
footer='Randomize one failure every eight bars during rehearsal. The exercise is passed when the injected error changes less than one measure of the performance.'
assert footer in norm(page)
txtlines=(R/txt).read_text().splitlines();module=contract(0)['txt_module_instruction'];assert module in txtlines
start=txtlines.index('RECOVERY ORDER');txtladder=txtlines[start+1:start+7]
assert txtladder==['1. Keep pulse.','2. Find active bar.','3. Play root or shell.',
    '4. Find next section landmark.','5. Restore texture.','6. Review only after the take ends.']
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':19,
    'original_page_text':page,'matched_cells':[{'key':r['package_key'],'base_jsonl_line':n,
    'original_three_field_text':'\n'.join(row[1:]),'pdf_text_start_line':lines.index(row[1])+1} for r,n,row in zip(rows,base_lines,ROWS)],
    'context_eighth_row':{'source_label':ROWS[7][1],'no_new_key':True},'full_footer':footer,
    'module_txt_instruction':module,'module_txt_line':txtlines.index(module)+1,'recovery_order_txt_lines':txtladder,
    'recovery_order_txt_start_line':start+2,'method':'original PDF text stream and TXT exact joins; no fresh rendered visual inspection'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    assert old['source_payload']['printed_label']==ROWS[i][1]
    assert old['implementation']['task']['table_fields'][0]['values']==[*ROWS[i][1:],None]
    r['schema_version']='fathom-private-source-implementation.38';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'recovery_contract.py'),'class':'RecoveryFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_RANDOM_CUE_AND_MANUAL_REALIZATION_REQUIRED',
        'reason':'Source recovery contract complete privately; external cue/reference provider and learner chosen performance remain necessary. No app audio or timing supplied.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['provenance']['manual_r38']={'base_packet':pin(base),'base_jsonl_line':base_lines[i],'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','note_or_time_events_invented':False}
    out.append(r)
packet=Path('Build')/L/'recovery-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'recovery_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':7,'source_supported_manual_contracts':7,'partial_unresolved':0,'unattempted':0,
    'source_contacts_added':0,'context_failure_rows':8,'new_official_keys':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
