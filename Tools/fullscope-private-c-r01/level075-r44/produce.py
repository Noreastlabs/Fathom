from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from cue_contract import KEYS,TABLE,DIAGRAM,PROSE,TXT,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r44');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='0c26f74698ca130a4941637e8469d82516329a98f590d1b722f4709687f93107'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][14:18];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='2a2b6a6e2cfb04a08a7039dd1ccc79a44dbcd06565ef1d3b1d2e4052c5e9fbfd'
assert pin(txt)['sha256']=='563e18e76187e4aa7a774b335edad44e7a289603fefbb2fba04fa1409c6063fb'
page=PdfReader(R/pdf).pages[5].extract_text();lines=page.splitlines();t=(R/txt).read_text();assert TXT in t
for row in TABLE.values():assert '\n'.join(row) in page
matches=[]
for i,r in enumerate(rows):
    label=f'Cue cell {i+1}: old section -> new section';assert page.count(label)==1
    a=page.index(label);b=page.index(f'Cue cell {i+2}:') if i<3 else page.index('Level 75 - complete-performance integration.')
    block=page[a:b];assert all(d in block for d in DIAGRAM);assert PROSE in ' '.join(block.split())
    matches.append({'key':KEYS[i],'base_jsonl_line':15+i,'physical_page':6,'label_text_line':lines.index(label)+1,'original_full_block':block})
assert page.count('Cue cell ')==4 and '12 CUE CELLS | 96 CONTACTS' in page
source=Path('Build')/L/'source-check.json'
write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':6,'original_page_text':page,
    'matched_cards':matches,'txt_module_line':t.splitlines().index(TXT)+1,'txt_module':TXT,
    'method':'original PDF text stream, no fresh rendered visual inspection','all_numbered_cards':4,
    'arrow_layout_observation':{'count_symbols':DIAGRAM[0].split('|')[1],'look_symbols':DIAGRAM[2].split('|')[1],
      'look_arrow_column':12,'count_label_at_column12':'4','table_visual_preparation':TABLE['visual'][2],'interpretation':'Pending separate source disposition; layout coordinate not adopted as clock'}})
oldcontract=rows[0]['implementation']['task']['contract'];assert len(oldcontract['response_fields'])==1
write(Path('Results')/L/'prior-contract-correction.json',{'prior_packet':pin(base),'prior_jsonl_line':15,'key':KEYS[0],
    'prior_contract':oldcontract,'finding':'The prior effective response covered only neighboring cropped table text; it did not structure the full cue-cell obligations. r44 replaces the effective manual contract, preserving old source/raw/timing fields and immutable prior packet.',
    'category_before':'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT','category_after':'COMPLETE_MANUAL_NONPLAYBACK_CONTRACT','newly_complete_count_for_this_key':0})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.44';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],
      'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'cue_contract.py'),'class':'CueFlow','pure_python_reference':True}
    r['unresolved_reasons']=[{'disposition':'MANUAL_CUE_SOURCE_AND_REALIZATION_REQUIRED','reason':'Complete manual contract has external-source prerequisites and explicit chosen guitar realization; no actual performance verified.'},
      {'disposition':'SOURCE_INTERPRETATION_PENDING','reason':'Visual table beat3 versus literal Look diagram column under Count4, and12/96header versus4enumeratedcards, remain separately retained. No timed arrow projection or invented extent.'}]
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW'
    r['contract_capabilities']['complete_manual_response_contract']=True
    r['provenance']['manual_r44']={'base_packet':pin(base),'base_jsonl_line':15+i,'source_check':pin(source),'author':'private producer C',
      'independent_source_review':'Pending','source_events_or_keys_invented':False,'prior_generic_contract_replaced':i==0}
    out.append(r)
packet=Path('Build')/L/'cue-cell-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
write(Path('Results')/L/'source-interpretation-referral.json',{'pdf':pin(pdf),'txt':pin(txt),'source_check':pin(source),'overlay':pin(packet),
    'exact_keys':list(KEYS),'questions':contract(0)['source_interpretation_questions'],
    'non_resolution':'All four manual contracts expose selected table route separately; exact diagram timing and aggregate source extent remain Pending. No official key or source count correction.'})
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'cue_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':4,'source_supported_manual_contracts':4,'newly_complete':3,'strengthened_existing':1,
    'partial_unresolved_manual_contracts':0,'unattempted':0,'source_interpretation_questions_retained':2,'abstract_attack_symbols':16,'source_note_contacts_added':0,
    'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
