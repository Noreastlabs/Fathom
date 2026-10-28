from pathlib import Path
from copy import deepcopy
from pypdf import PdfReader
import datetime,hashlib,json,resource,time
from rhythm_contract import KEYS,DEGREES,PITCHES,LABELS,FOOTER,contract
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r56');tick=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
base=Path('Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl');assert pin(base)['sha256']=='e8b2221c7bbb8389f2c20892ae6f08b34379bb5e88ead50c971819740b0a3791'
allrows=[json.loads(x) for x in (R/base).read_text().splitlines()];old=allrows[86:88];assert [r['package_key'] for r in old]==list(KEYS)
pdf=Path(old[0]['source_refs'][0]['path']);txt=Path(old[0]['source_refs'][1]['path'])
assert pin(pdf)['sha256']=='bfeaab5b0ddd52ac55063e0552b8c451d8a8029ddb073b744d8f0e76186aedce'
assert pin(txt)['sha256']=='54ab2490448e1fa6391ead275fe22e2fbec9be23d6e83c88001293b4be7e7236'
page=PdfReader(R/pdf).pages[9].extract_text();joined=' '.join(page.split());txtlines=(R/txt).read_text().splitlines();assert FOOTER in joined
assert '8 TWO-BAR CELLS | 64 TONES' in joined and 'PITCH AND RHYTHM ARE TRANSCRIBED SEPARATELY, THEN RECOMBINED' in joined
joins=[]
for i,r in enumerate(old):
    components=[str(i+1),'C major','-'.join(DEGREES[i]),LABELS[i],''];assert r['implementation']['task']['printed_components']==components
    assert ' '.join(components).strip() in joined and r['implementation']['events']==[] and r['contract_category']=='IMPLEMENTATION_OR_INTERPRETATION_PENDING'
    literal='C major: degrees '+'-'.join(DEGREES[i])+'; pitches '+'-'.join(PITCHES[i]);line=[j+1 for j,v in enumerate(txtlines) if v==literal];assert len(line)==1
    joins.append({'key':KEYS[i],'base_jsonl_line':87+i,'physical_page':10,'printed_components':components,'paired_txt_pitch_confirmation_line':line[0],
      'derived_pitches':list(PITCHES[i]),'derivation':'C-major scale-degree mapping, confirmed by the exact paired TXT degree/pitch row; not a printed p10 pitch-name field'})
other=[{'base_jsonl_line':j+1,'key':r['package_key'],'components':r['implementation']['task']['printed_components'],'disposition':'unchanged implementation Pending; no source-conflict conclusion'} for j,r in enumerate(allrows) if 88<=j<=93]
assert len(other)==6 and sum(len(r['implementation']['task']['printed_components'][2].split('-')) for r in allrows[86:94])==53
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'base_packet':pin(base),'physical_page':10,
 'original_page_text':page,'full_footer':FOOTER,'exact_selected_joins':joins,'remaining_six_intake_only':other,
 'extent':{'literal_header':'8 TWO-BAR CELLS | 64 TONES','actual_rows':8,'actual_degree_tokens':53,'selected_rows':2,'selected_degree_tokens':13,'extra_notes_manufactured':0},
 'method':'original PDF text stream and paired TXT degree/pitch confirmation; no fresh rendered visual review'})
rows=[]
for i,o in enumerate(old):
    r=deepcopy(o);c=contract(i);r['schema_version']='fathom-private-source-implementation.56';r['implementation']['task']['contract']=c
    r['implementation']['task']['response_contract']={'mode':'manual_user_response','response_fields':c['response_schema'],'source_player_choice_fields':c['plan_schema'],'learner_response':None,'completion_claim':None,'automatic_score':False}
    r['implementation']['manual_model']={'path':str(Path('Tools')/L/'rhythm_contract.py'),'class':'RhythmFlow','pure_python_reference':True}
    r['implementation']['task']['source_sequence_recovery']={'source_check':pin(source),'original_raw_retained':True,'identity_changed':False}
    r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['status']='PRIVATE_MANUAL_CONTRACT_PENDING_REVIEW';r['contract_capabilities']['complete_manual_response_contract']=True
    r['unresolved_reasons']=[{'disposition':'EXTERNAL_SOURCE_AND_CHOSEN_RHYTHM_REALIZATION_REQUIRED','reason':'Complete manual separate-layer dictation, clap, unmetered singing and vocal recombination. Source fixes quarter/eighth note class; external performer chooses meter/rest/register map. No source-fixed complete pulse map, app audio or native admission.'}]
    r['provenance']['manual_r56']={'base_packet':pin(base),'base_jsonl_line':87+i,'source_check':pin(source),'author':'private producer C','independent_source_review':'Pending','source_note_events_added':False}
    rows.append(r)
packet=Path('Build')/L/'rhythm-pitch-dictation-overlay.jsonl';p=R/packet;assert not p.exists();p.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'utc':start,'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'base_packet':pin(base),'overlay':pin(packet),'source_check':pin(source),'model':pin(Path('Tools')/L/'rhythm_contract.py'),
 'exact_replaced_keys':list(KEYS),'attempted':2,'source_supported_manual_contracts':2,'partial_unresolved':0,'unattempted_selected_keys':0,'other_page_rows_intake_only':6,
 'selected_degree_tokens':13,'source_note_events_added':0,'outside_child_keys_created':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
