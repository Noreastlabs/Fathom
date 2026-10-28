from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time,re
from handoff_cell_contract import KEY,BODIES,ROLES,FOOTER,source_events,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r41')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
old=json.loads((R/base).read_text().splitlines()[60]);assert old['package_key']==KEY and old['implementation']['events']==[]
pdf=Path(old['source_refs'][0]['path']);txt=Path(old['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[14].extract_text();lines=page.splitlines();matches=[]
for bar,(role,body) in enumerate(zip(ROLES,BODIES),1):
    found=[(i,line) for i,line in enumerate(lines,1) if re.fullmatch(r'BAR '+str(bar)+' '+role+r': +'+re.escape(body),line)]
    assert len(found)==1;line_no,literal=found[0];matches.append({'source_bar':bar,'original_line':literal,'body':body,'body_width':len(body),'pdf_text_line':line_no})
assert FOOTER in ' '.join(page.split()) and 'CHANGE ROLE WITHOUT CHANGING THE CLOCK' in page
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':61,'physical_page':15,
    'matched_bars':matches,'full_footer':FOOTER,'source_key':KEY,'method':'original PDF text stream; no fresh rendered visual inspection',
    'original_empty_events_were_unimplemented':True,'separate_six_table_rows_unchanged':True})
r=deepcopy(old);c=contract();r['schema_version']='fathom-private-source-implementation.41'
r['implementation']['events']=source_events();r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
    'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'handoff_cell_contract.py'),'class':'HandoffCellFlow','pure_python_reference':True}
r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_REQUIRED_FOR_FIXED_PLAYBACK',
    'reason':'Source16symbols and full forward/reverse manual contract implemented; source octaves/frets/timing/gates remain unspecified. Chosen normalized-bar timing is not printed source pulse.'}]
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_SOURCE_SYMBOL_AND_MANUAL_CONTRACT_PENDING_REVIEW'
r['contract_capabilities'].update({'complete_manual_response_contract':True,'literal_pitch_occurrences':9,'harmonic_attack_symbols':7,'ordered_pitch_or_contact_slots':16})
r['provenance']['manual_r41']={'base_packet':pin(base),'base_jsonl_line':61,'source_check':pin(source),
    'author':'private producer C','independent_source_review':'Pending','original_empty_events_were_unimplemented':True,'source_timing_or_frets_invented':False}
packet=Path('Build')/L/'handoff-cell-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'handoff_cell_contract.py'),
    'exact_replaced_keys':[KEY],'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
    'recovered_source_symbols':16,'harmonic_attack_symbols':7,'source_pitch_class_occurrences':9,'source_fret_contacts':0,
    'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
