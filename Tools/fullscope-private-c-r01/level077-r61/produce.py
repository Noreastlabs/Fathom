from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from degree_contract import RAW,KEYS,FOOTER,HEADING,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r61');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
allrows=[json.loads(x) for x in (R/base).read_text().splitlines()];old=allrows[110:124];assert [r['package_key'] for r in old]==list(KEYS)
pdf=Path(old[0]['source_refs'][0]['path']);txt=Path(old[0]['source_refs'][1]['path']);assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce';assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[12].extract_text();joined=' '.join(page.split());assert FOOTER in joined and HEADING in joined and '14 COMMANDS | 56 REALIZATIONS' in joined
paired=(R/txt).read_text();assert 'Practice named scale degrees and chord tones in low, middle, and high registers with one silent setup and one attack.' in paired
joins=[]
for i,r in enumerate(old):
    parts=[*RAW[i],'','',''];assert r['implementation']['task']['printed_components']==parts and ' '.join(RAW[i]) in joined
    assert r['implementation']['events']==[] and r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    joins.append({'key':KEYS[i],'base_jsonl_line':111+i,'physical_page':13,'original_components':parts})
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':13,'original_page_text':page,'full_footer':FOOTER,'exact_selected_joins':joins,
 'extent':{'literal_header':'14 COMMANDS | 56 REALIZATIONS','actual_commands':14,'printed_register_columns':['Low','Mid','High'],'chosen_three_register_realizations':42,'source_contacts_invented':0},
 'locator_note':'Final official key p013-t1-r15/amelodicminor preserved;14printedcommands, no renumbering or source-identity correction.',
 'method':'original PDF text and paired TXT context; no new rendered visual campaign'})
rows=[]
for i,o in enumerate(old):
    r=deepcopy(o);c=contract(i);r['schema_version']='fathom-private-source-implementation.61';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'chosen_plan_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'degree_contract.py'),'class':'DegreeFlow','pure_python_reference':True}
    r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'original_raw_retained':True,'identity_changed':False}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_SPOKEN_CUE_AND_MANUAL_PERFORMANCE_REQUIRED','reason':'Complete private manual source contract. Actual partner speaks context/degree only; sung-name/contact/performance self-report, explicit relative-register choices. No app source audio, measured reaction or performance qualification.'}]
    r['provenance']['manual_r61']={'base_packet':pin(base),'base_jsonl_line':111+i,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False};rows.append(r)
packet=Path('Build')/L/'degree-realization-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'degree_contract.py'),
 'exact_replaced_keys':list(KEYS),'attempted':14,'source_supported_manual_contracts':14,'partial_unresolved':0,'unattempted_selected_keys':0,'chosen_register_realizations':42,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
