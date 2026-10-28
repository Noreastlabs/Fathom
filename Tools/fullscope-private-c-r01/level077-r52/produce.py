from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from guide_contract import KEYS,RAW,SPEC,HEADINGS,NO_SEARCH,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r52');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
allrows=[json.loads(x) for x in (R/base).read_text().splitlines()];rows=[allrows[s[3]-1] for s in SPEC];assert tuple(r['package_key'] for r in rows)==KEYS
pdf=Path(rows[0]['source_refs'][0]['path']);txt=Path(rows[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
reader=PdfReader(R/pdf);pages={n:reader.pages[n-1].extract_text() for n in (7,8)};t=(R/txt).read_text();matches=[]
for i,r in enumerate(rows):
    p,row,_,line=SPEC[i];values=[*RAW[i],'sing both -> play shell'];block='\n'.join(values);page=pages[p];lines=page.splitlines();assert page.count(block)==1
    if row!=6:assert r['implementation']['task']['table_fields'][0]['values']==values+['']
    txtline=f'{RAW[i][0]}: {RAW[i][1]}({RAW[i][2]}) + {RAW[i][3]}({RAW[i][4]})';assert txtline in t
    matches.append({'key':KEYS[i],'base_jsonl_line':line,'physical_page':p,'official_table_row':row,'full_pdf_fields':values,
      'pdf_block_text':block,'pdf_block_first_text_line':next(n+1 for n in range(len(lines)-5) if lines[n:n+6]==values),
      'txt_line':txtline,'txt_line_number':t.splitlines().index(txtline)+1,'prior_extracted_values':r['implementation']['task']['table_fields'][0]['values'],
      'recovered_after_annotation_overlap':row==6,'identity_changed':False})
assert all(HEADINGS[j] in pages[j+7] for j in (0,1)) and NO_SEARCH in t
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),
  'original_page_text':pages,'matched_rows':matches,'no_search':NO_SEARCH,'excluded_official_quarantines':['exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7'],
  'separate_voice_leading_supplements_untouched':True,'method':'original PDF text stream plus exact TXT corroboration; no new rendered visual review'})
out=[]
for i,old in enumerate(rows):
    r=deepcopy(old);assert r['implementation']['events']==[];c=contract(i);r['schema_version']='fathom-private-source-implementation.52';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'learner_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'guide_contract.py'),'class':'GuideFlow','pure_python_reference':True}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'CHOSEN_SHELL_AND_MANUAL_PERFORMANCE_REQUIRED','reason':'Full row contract, selected root/third/seventh realization; actual sung/played correctness unverified. Chosen shell omits fifth and does not verify full chord quality; no fixed source events/timing.'}]
    r['provenance']['manual_r52']={'base_packet':pin(base),'base_jsonl_line':SPEC[i][3],'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    if SPEC[i][1]==6:r['implementation']['task']['source_field_recovery']={'original_raw_fields_retained':True,'recovered_fields':c['source_fields'],'source_check':pin(source),'identity_changed':False}
    out.append(r)
packet=Path('Build')/L/'sung-guide-shell-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in out))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
  'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'guide_contract.py'),
  'exact_replaced_keys':list(KEYS),'attempted':8,'source_supported_manual_contracts':8,'partial_unresolved':0,'unattempted':0,
  'printed_guide_pitch_class_targets':16,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
