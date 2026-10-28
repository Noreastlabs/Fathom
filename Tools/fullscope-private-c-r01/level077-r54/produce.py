from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from minor_contract import KEY,CRITICAL,DOMINANT,NO_SEARCH,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r54');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
old=json.loads((R/base).read_text().splitlines()[77]);assert old['package_key']==KEY and old['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
pdf=Path(old['source_refs'][0]['path']);txt=Path(old['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[7].extract_text();lines=page.splitlines();joined=' '.join(page.split());t=(R/txt).read_text()
need=['Bm7b5 -> E7 -> Am7','D -> D -> C','A -> G# -> G',CRITICAL,DOMINANT]
assert all(x in joined for x in need) and NO_SEARCH in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':78,'physical_page':8,
  'original_page_text':page,'source_matches':[{'joined_source_text':x,'matching_text_lines':[{'line':n+1,'text':line} for n,line in enumerate(lines) if ' '.join(line.split())==x]} for x in need],
  'full_no_search_txt':NO_SEARCH,'vocal_motion_coverage_alias':'The printed upper A/G#/G also covers the identical critical descending motion, both source references retained.',
  'source_scope':'exact minor voice-leading supplement only; row5 quarantine and all table/major supplement keys untouched',
  'method':'original PDF text stream plus paired TXT no-search; no fresh rendered visual review'})
r=deepcopy(old);c=contract();assert r['implementation']['events']==[];r['schema_version']='fathom-private-source-implementation.54';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'minor_contract.py'),'class':'MinorFlow','pure_python_reference':True}
r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'original_raw_retained':True,'printed_progression':c['printed_progression'],'identity_changed':False}
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
r['unresolved_reasons']=[{'disposition':'EXTERNAL_PARTNER_AND_CHOSEN_REALIZATION_REQUIRED','reason':'Full nine-stage manual contract. Source partner sound/no-third omission and actual singing/third addition remain external and self-reported; no app audio, source-fixed note realization or native admission.'}]
r['provenance']['manual_r54']={'base_packet':pin(base),'base_jsonl_line':78,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
packet=Path('Build')/L/'minor-voiceleading-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'minor_contract.py'),
  'exact_replaced_keys':[KEY],'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
  'vocal_routes':3,'external_partner_dominant_tests':6,'explicit_E7_third_targets':1,'derived_repeat_third_targets':5,
  'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
