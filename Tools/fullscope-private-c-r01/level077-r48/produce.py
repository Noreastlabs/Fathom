from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from dictation_contract import KEYS,CARD,RAW,FOOTER,NO_SEARCH,contract,delta,PC
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r48');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
rows=[json.loads(x) for x in (R/base).read_text().splitlines()][12:34];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[2].extract_text();lines=page.splitlines();t=(R/txt).read_text();matches=[]
for i,r in enumerate(rows):
    fields=[str(CARD[i]),*RAW[i]];block='\n'.join(fields);assert page.count(block)==1
    assert r['implementation']['task']['table_fields'][0]['values']==fields
    assert ((PC[RAW[i][0]]+delta(i))%12==PC[RAW[i][1]]) is (i!=19)
    matches.append({'key':KEYS[i],'base_jsonl_line':13+i,'printed_card':CARD[i],'original_pdf_fields':fields,
      'pdf_block_text':block,'pdf_block_first_text_line':lines.index(str(CARD[i]))+1,'derived_signed_semitones':delta(i)})
assert FOOTER in ' '.join(page.split()) and NO_SEARCH in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':3,
    'original_page_text':page,'matched_rows':matches,'full_fretboard_footer':FOOTER,'no_search_rule':NO_SEARCH,
    'no_search_txt_line':t.splitlines().index(NO_SEARCH)+1,'outside_child_printed_cards_not_created':[22,23],
    'card20_source_reconciliation':{'key':KEYS[19],'printed_signed_semitones':-8,'pair_descending_semitones':9,'status':'Pending separate Curriculum disposition'},'card24_official_key':KEYS[-1],'method':'original PDF text stream; no fresh rendered visual review'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i)
    r['schema_version']='fathom-private-source-implementation.48';r['implementation']['task']['contract']=c
    if i!=19:
        r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],
          'learner_response':None,'completion_claim':None,'automatic_score':False}
        r['implementation']['manual_model']={'path':str(Path('Tools')/L/'dictation_contract.py'),'class':'DictationFlow','pure_python_reference':True}
        r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
        r['unresolved_reasons']=[{'disposition':'EXTERNAL_SOURCE_AND_CHOSEN_REGISTER_REQUIRED','reason':'Exact source pitch classes/direction/interval with full manual two-pass contract. Actual sound/named prompts, chosen register/string and performance reports remain external, unverified and not native timed.'}]
    else:
        r['contract_category']='IMPLEMENTATION_OR_INTERPRETATION_PENDING';r['status']='SOURCE_RECONCILIATION_PENDING'
        r['contract_capabilities']['complete_manual_response_contract']=False
        r['implementation']['private_workflow_refusal']={'reason':'Printed B to D down spans9semitones, while m6 is8. No source correction adopted.','key':KEYS[i]}
        r['unresolved_reasons']=[{'disposition':'SOURCE_RECONCILIATION_PENDING','printed_row':list(RAW[i]),'printed_signed_semitones':-8,'pair_descending_semitones':9,'source_correction_adopted':False}]
    r['provenance']['manual_r48']={'base_packet':pin(base),'base_jsonl_line':i+13,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    out.append(r)
packet=Path('Build')/L/'interval-dictation-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'dictation_contract.py'),
    'exact_replaced_keys':list(KEYS),'attempted':22,'source_supported_manual_contracts':21,'partial_unresolved':1,'unattempted':0,
    'source_pitch_classes_preserved':44,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'card020-source-referral.json',{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'source_check':pin(source),'overlay':pin(packet),'key':KEYS[19],'base_jsonl_line':32,'overlay_jsonl_line':20,'physical_page':3,'printed_row':['20',*RAW[19]],'printed_interval_semitones':8,'descending_pitch_pair_semitones':9,'disposition':'Pending separate Curriculum/source reconciliation; no relabel/pitch/key correction; private workflow refuses','source_conflict_count_increment':0})
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
