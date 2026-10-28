from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,resource,time,re,importlib.util
from fill_contract import KEYS,TARGETS,TABLE,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r37')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
parser=Path('Tools/fullscope-private-c-r01/level075-r33/tab_contacts.py')
assert pin(parser)['sha256']=='b1d525636f2cb64dab519cbf1a17dbf305ebd8a9e8d34e954f466c14d51bc2c7'
s=importlib.util.spec_from_file_location('frozen_tab_contacts',R/parser);tab=importlib.util.module_from_spec(s);s.loader.exec_module(tab)
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
allrows=[json.loads(x) for x in (R/base).read_text().splitlines()];base_lines=[27,30,28,29];rows=[allrows[n-1] for n in base_lines]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[7].extract_text();norm=lambda x:' '.join(x.split());matches=[];parsed=[]
assert '16 FILL CELLS | 128 CONTACTS' in page and 'A FILL MUST END BEFORE THE NEXT STRUCTURAL ATTACK' in page
for row in TABLE:assert norm(' '.join([*row,'land on next section beat 1'])) in norm(page)
for i,(old,target) in enumerate(zip(rows,TARGETS),1):
    label=f'Fill {i}: chord tone -> connector -> target';assert old['source_payload']['printed_label']==label and page.count(label)==1
    match=re.search(re.escape(label)+r'\n(.*?)Resolve to '+target+r' on next bar 1\.',page,re.S);assert match
    block=match.group();recovered=tab.parse_tab(block);assert len(recovered['events'])==11 and all(x['fret'] is not None for x in recovered['events'])
    assert 'fill begins after beat 3' in block;parsed.append(recovered)
    matches.append({'key':old['package_key'],'base_jsonl_line':base_lines[i-1],'physical_page':8,'printed_fill_number':i,
        'label':label,'original_full_block':block,'source_target':target,'source_rows':recovered['rows']})
module='128 contacts. Begin fills on beats 1, 2, 3, 4, & of 3, and & of 4. Every fill must end before the next structural attack.'
lines=(R/txt).read_text().splitlines();assert module in lines
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'frozen_parser':pin(parser),
    'matched_cells':matches,'source_start_table':[list(x) for x in TABLE],'module_txt_instruction':module,'module_txt_line':lines.index(module)+1,
    'method':'unique original PDF text-stream label/block; no fresh rendered visual QA',
    'fill2_supplement_key_retained':KEYS[1]})
out=[]
for i,(old,recovered) in enumerate(zip(rows,parsed)):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.37';r['implementation']['events']=recovered['events']
    r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'fill_contract.py'),'class':'FillFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'LEARNER_TIMING_AND_TARGET_REGISTER_REQUIRED_FOR_FIXED_REALIZATION',
        'reason':'11TABcontacts and targetpitchclass are source facts; exactspacing/gates and targetoctave/fret remain choices. Manual contract implemented.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_SOURCE_CONTACT_AND_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities'].update({'complete_manual_response_contract':True,'actual_fret_contacts':11,
        'ordered_pitch_or_contact_slots':11,'additional_source_resolution_pitch_class_targets':1})
    r['provenance']['manual_r37']={'base_packet':pin(base),'base_jsonl_line':base_lines[i],'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','original_empty_events_were_unimplemented':True,
        'source_timing_or_target_fret_invented':False}
    out.append(r)
packet=Path('Build')/L/'fill-resolution-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
assert pin(parser)['sha256']=='b1d525636f2cb64dab519cbf1a17dbf305ebd8a9e8d34e954f466c14d51bc2c7'
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'frozen_parser':pin(parser),'model':pin(Path('Tools')/L/'fill_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':4,'source_supported_manual_contracts':4,'partial_unresolved':0,'unattempted':0,
    'recovered_source_contacts':44,'additional_source_resolution_targets':4,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
