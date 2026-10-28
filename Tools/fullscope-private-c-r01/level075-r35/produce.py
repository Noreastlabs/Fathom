from pathlib import Path
from pypdf import PdfReader
from copy import deepcopy
import datetime,hashlib,json,time,resource
from cue_contract import KEYS,ROWS,NOLOOK,SUPPORT,CALLS,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r35')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][18:26]
assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
book=PdfReader(R/pdf);p7=book.pages[6].extract_text();p6=book.pages[5].extract_text()
norm=lambda x:' '.join(x.split());lines=(R/txt).read_text().splitlines();contexts=[];matches=[]
assert norm(NOLOOK) in norm(p7) and norm(SUPPORT) in norm(p6)
for call in CALLS:assert norm(call) in norm(p7)
for i,(r,info) in enumerate(zip(rows,ROWS)):
    text=' '.join([info[1],'G7',info[2],info[3],'4 old attacks + 4 new attacks'])
    assert norm(text) in norm(p7) and norm(text)==norm(r['source_payload']['pdf_region_text'])
    h=lines.index(info[5]);context='\n'.join(lines[h:h+3]);assert lines[h+1].startswith('Chords: '+info[2]+' |')
    contexts.append({'source_ref':pin(txt),'line_start':h+1,'line_end':h+3,'text':context})
    matches.append({'key':r['package_key'],'base_jsonl_line':i+19,'pdf_page':7,'table_row':i+1,'literal':text,'master_context':contexts[-1]})
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),
    'method':'original pypdf text stream, not fresh rendered visual QA','matched_rows':matches,
    'full_p7_no_look_instruction':NOLOOK,'four_example_calls':list(CALLS),'full_p6_support':SUPPORT,
    'scope':'Eight existing transition row identities. No-look external requests use these row contexts; duplicateVerse labels remain separate.'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i,contexts)
    r['schema_version']='fathom-private-source-implementation.35'
    r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
        'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False,
        'source_answer_policy':'Source options remain reference; actual externalcue and learnerresponse are never prefilled or acoustically verified.'}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'cue_contract.py'),'class':'CueFlow','pure_python_reference':True}
    r['status']='PRIVATE_MANUAL_CONTRACT_IMPLEMENTED_PENDING_REVIEW';r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['contract_capabilities']['harmonic_attack_slots_without_fixed_pitch']=8
    r['unresolved_reasons']=[{'disposition':'LEARNER_REALIZATION_AND_EXTERNAL_PROVIDER_REQUIRED',
        'reason':'Fullmanualsourcecontract implemented; actualvoicings/timing and externalcue provision are not supplied or observed by this private model.'}]
    r['provenance']['manual_r35']={'base_packet':pin(base),'base_jsonl_line':i+19,'source_check':pin(source),
        'author':'private producer C','independent_source_review':'Pending','source_events_invented':False}
    out.append(r)
packet=Path('Build')/L/'section-cue-overlay.jsonl';p=R/packet;assert not p.exists()
p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':started,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'cue_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':8,'source_supported_manual_contracts':8,'partial_unresolved':0,'unattempted':0,
    'source_contacts_preserved':0,'source_harmonic_attack_slots':64,'fixed_pitches_invented':0,
    'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
