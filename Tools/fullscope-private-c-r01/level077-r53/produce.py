from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from voiceleading_contract import KEY,PRACTICE,TRANSPOSE,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r53');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
old=json.loads((R/base).read_text().splitlines()[71]);assert old['package_key']==KEY
pdf=Path(old['source_refs'][0]['path']);txt=Path(old['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[6].extract_text();lines=page.splitlines();joined=' '.join(page.split())
need=['Dm7 -> G7 -> Cmaj7','F -> F -> E lower guide voice','C -> B -> B upper guide voice',PRACTICE,TRANSPOSE]
assert all(x in joined for x in need)
assert len(old['implementation']['task']['contract']['response_fields'])==1 and old['contract_category']=='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':72,'physical_page':7,
  'original_page_text':page,'source_matches':[{'joined_source_text':x,'matching_text_lines':[{'line':n+1,'text':line} for n,line in enumerate(lines) if ' '.join(line.split())==x]} for x in need],
  'recovered_progression':['Dm7','G7','Cmaj7'],'printed_lower':['F','F','E'],'printed_upper':['C','B','B'],
  'old_overlapping_instruction':old['implementation']['task']['instructions'][10],'source_scope':'exact major voice-leading supplement only; table rows/quarantines and minor supplement untouched',
  'method':'original PDF text stream; exact full instructions, no fresh rendered visual review'})
r=deepcopy(old);c=contract();assert r['implementation']['events']==[];r['schema_version']='fathom-private-source-implementation.53';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'voiceleading_contract.py'),'class':'VoiceLeadingFlow','pure_python_reference':True}
r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'original_raw_retained':True,'printed_C':c['printed_C_reference'],'identity_changed':False}
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
r['unresolved_reasons']=[{'disposition':'CHOSEN_REALIZATION_AND_MANUAL_PERFORMANCE_REQUIRED','reason':'Complete six-key task contract; derived transpositions/selected MIDI/contact/articulation are explicit, actual hearing/coordination unverified and not native timed.'}]
r['provenance']['manual_r53']={'base_packet':pin(base),'base_jsonl_line':72,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
packet=Path('Build')/L/'major-voiceleading-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
write(Path('Results')/L/'prior-contract-correction.json',{'base_packet':pin(base),'overlay':pin(packet),'key':KEY,'base_line':72,'overlay_line':1,
  'old_contract':'One generic transposition text field; incomplete voice-line/solo/composite/key/custody contract and overlapping raw chord extraction.',
  'replacement':'Exact printed C guide lines, five requested derived transpositions and complete three-phase-per-key manual contract.',
  'manual_count_increment':0,'old_packet_unchanged':True})
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'voiceleading_contract.py'),
  'exact_replaced_keys':[KEY],'attempted':1,'source_supported_manual_contracts':1,'existing_manual_contract_corrections':1,'new_complete_manual_contracts':0,
  'partial_unresolved':0,'unattempted':0,'printed_guide_pitch_class_occurrences':6,'derived_requested_targets':30,'source_note_events_added':0,
  'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
