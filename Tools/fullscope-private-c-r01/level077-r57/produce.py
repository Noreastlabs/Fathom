from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from motif_contract import KEYS,DEGREES,PITCHES,FOOTER,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r57');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
o=json.loads((R/base).read_text().splitlines()[88]);assert o['package_key']==KEYS[0] and o['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
pdf=Path(o['source_refs'][0]['path']);txt=Path(o['source_refs'][1]['path']);assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[9].extract_text();joined=' '.join(page.split());assert FOOTER in joined
parts=['3','G major','1-3-2-5-4-3-2-1','q q 2eighths',''];assert o['implementation']['task']['printed_components']==parts and ' '.join(parts).strip() in joined
literal='G major: degrees 1-3-2-5-4-3-2-1; pitches G-B-A-D-C-B-A-G';matches=[i+1 for i,x in enumerate((R/txt).read_text().splitlines()) if x==literal];assert len(matches)==1
reuse=json.loads((R/'Results'/L/'model-reuse-input.json').read_text());assert pin(reuse['path'])['sha256']==reuse['sha256']
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'base_jsonl_line':89,'physical_page':10,
 'original_page_text':page,'selected_key':KEYS[0],'original_components':parts,'txt_confirmation_line':matches[0],'txt_confirmation':literal,
 'full_footer':FOOTER,'chosen_interpretation':'Explicit two contiguous repetitions of q/q/eighth/eighth; only rests around/between complete motifs. Source supplies shorthand, not complete repeat/meter/rest/register mapping.',
 'method':'original PDF text and exact paired TXT degree/pitch confirmation; no new rendered visual review'})
r=deepcopy(o);c=contract(0);assert r['implementation']['events']==[];r['schema_version']='fathom-private-source-implementation.57';r['implementation']['task']['contract']=c
r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'source_player_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
r['implementation']['manual_model']={'path':str(Path('Tools')/L/'motif_contract.py'),'class':'MotifFlow','pure_python_reference':True}
r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'original_raw_retained':True,'identity_changed':False}
r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
r['unresolved_reasons']=[{'disposition':'EXPLICIT_PERFORMER_MOTIF_CHOICE_AND_EXTERNAL_SOURCE_REQUIRED','reason':'Complete manual contract under explicit two-repeat q/q/eighth/eighth choice; octave/meter/rest placement remain authored, no source-fixed full timing or native admission. Other interpretations are outside this finite adapter, not declared invalid.'}]
r['provenance']['manual_r57']={'base_packet':pin(base),'base_jsonl_line':89,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
packet=Path('Build')/L/'qqee-dictation-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'motif_contract.py'),'reused_model_input':pin(reuse['path']),
 'exact_replaced_keys':list(KEYS),'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,'selected_degree_tokens':8,
 'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
