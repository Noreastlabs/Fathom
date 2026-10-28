from pathlib import Path
from pypdf import PdfReader
import copy,datetime,hashlib,json,resource,time
ROOT=Path(__file__).resolve().parents[3];LANE=Path('fullscope-private-c-r01/level073-r25')
start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
 p=Path(p);return {'path':str(p),'bytes':(ROOT/p).stat().st_size,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
def write(p,x):
 p=ROOT/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl');assert pin(base)['sha256']=='30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
pdf=next((ROOT/'Notes/music/guitar project/PDF version').glob('*Level_73_*')).relative_to(ROOT)
txt=next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*')).relative_to(ROOT)
assert pin(pdf)['sha256']=='7cc4c0098855c8e6d4b90063fb947b763e32a4225d66b77821f9e23f763779f9'
assert pin(txt)['sha256']=='63fed22776f4fcfd61ac9b7783b456c8996f2b438c06886d585bff2ee01afd15'
header='PRESERVE THE SCALE-DEGREE CONTOUR WHILE THE ABSOLUTE NOTES AND FRETBOARD ROUTE CHANGE'
instruction='The source and destination motifs share an identical degree formula. Keep the rhythm, articulation, and phrase length unchanged. The listener should recognize the motif before identifying the new key.'
reader=PdfReader(ROOT/pdf);pagepins=[]
for n in (10,11):
 page=reader.pages[n-1].extract_text();assert header in ' '.join(page.split()) and instruction in ' '.join(page.split())
 pagepins.append({'physical_page':n,'extracted_text_sha256':hashlib.sha256(page.encode()).hexdigest(),'complete_instruction_matches':True})
sourcecheck=Path('Build')/LANE/'source-check.json';write(sourcecheck,{'original_pdf':pin(pdf),'original_txt':pin(txt),'pages':pagepins,'header':header,'instruction':instruction,'method':'original pypdf text stream, no fresh visual layout claim'})
lines=(ROOT/txt).read_text().splitlines();engine=Path('Tools')/LANE/'motif_contract.py'
rows=list(map(json.loads,(ROOT/base).read_text().splitlines()))[23:29]
assert len(rows)==6 and all('/modulee/' in r['package_key'] for r in rows)
for r in rows:
 e=r['implementation']['events'];j=r['provenance']['exact_conversion_joins'][0];lo,hi=j['txt_event_lines']
 label,formula=lines[lo-3:lo-1];sourcekey,destkey=label.split(' -> ');degrees=j['facts']['degree_formula']
 assert label==r['source_payload']['printed_label'] and formula=='Degree formula: '+'-'.join(degrees)
 assert len(e)==16 and [n['printed_role'] for n in e]==degrees+degrees and [n['source_order'] for n in e]==list(range(1,17))
 c={'schema_version':'fathom-private-motif-comparison-contract.1','package_key':r['package_key'],'destination_key':destkey,
    'source_header':header,'source_instruction':instruction,'source_page':{'pdf':pin(pdf),'physical_page':j['pdf_physical_page'],'verification':pin(sourcecheck)},
    'source_script':{'route_label':label,'source_key':sourcekey,'destination_key':destkey,'degree_formula':degrees,
                     'source_motif':copy.deepcopy(e[:8]),'destination_motif':copy.deepcopy(e[8:]),'txt_lines':[lo-2,hi]},
    'source_obligations':['Preserve identical scale-degree formula.','Keep rhythm unchanged.','Keep articulation unchanged.','Keep phrase length unchanged.','Listener recognizes motif before identifying new key.'],
    'selected_manual_delivery':{'performer':'Learner-supplied source player with own guitar/instrument; exact printed script remains visible.',
                                'listener':'Learner-supplied external human listener; manual responses entered in order. No app audio or recognition.',
                                'origin':'Fathom-authored two-person manual delivery, not a printed requirement for a separate person; availability is distinct from source-contract completeness.'},
    'response_fields':[
      {'id':'setup','fields':['own_instrument:true','external_listener:true','rhythm:text','articulation:text','phrase_length:text']},
      {'id':'source_performance','fields':['current_action_token','played_as_shown:yes/no/uncertain','explanation:text']},
      {'id':'destination_performance','fields':['current_action_token','played_as_shown:yes/no/uncertain','rhythm_unchanged:yes/no/uncertain','articulation_unchanged:yes/no/uncertain','phrase_length_unchanged:yes/no/uncertain','explanation:text']},
      {'id':'manual_release','fields':['current_action_token','released:true']},
      {'id':'listener_recognition','fields':['same_motif:yes/no/uncertain','explanation:text']},
      {'id':'listener_key_response','fields':['key_text:nonempty_independent_text']},
      {'id':'reference_reveal','fields':['explicit_current_action']},
      {'id':'listener_comparison','fields':['agrees_with_reference:yes/no/uncertain','explanation:text']},
      {'id':'retry','fields':['reason:text','manual_release:true']}],
    'authored_interface_policy':'Fathom-authored fields/order and listener presentation implement printed obligations; no response is extracted from source text. This is not an automatic knowledge or acoustic score.',
    'visibility_policy':{'performer':'Original source/destination script remains available, including while listener reference is withheld.',
                         'listener':'No source label, key/formula or note events before key response and explicit reveal; only the listener\'s own earlier reports may contain a key.',
                         'prior_exposure':'Keep previous reveal across retries and cancel/reopen. Never claim fresh unseen listening from resetting fields.',
                         'scope':'In-memory projection functions for a future manual adapter; not authentication or verified UI separation.'},
    'state_policy':{'order':['setup','ready','source_motif','destination_motif','manual_release','motif_recognition','key_response','explicit_reveal','manual_comparison'],
                    'failed_or_uncertain':'Retain all reports; require explicit retry/manual release. No inferred mastery or acoustic success.',
                    'retry':'Preserve full historical reports and previous answer exposure; reset current pass only.',
                    'cancel_reopen':'Preserve reports/context/source script/source position/reveal state; invalidate stale callbacks and confirm release.',
                    'ownership':'Current in-memory instance/route/generation/pass/action token; no canonical ID or persistence.'},
    'fixed_timing_projection':{'status':'UNRESOLVED','reason':'Source requires rhythm/articulation/length preservation across the pair but prints no exact timing or BPM; performer selects these manually. No numeric pulse grid or acoustic gate supplied.',
                               'onset_q':None,'duration_q':None,'bpm':None},
    'state_engine_ref':pin(engine),'automatic_evaluation':False,'performance_observed':False,'app_audio_supplied':False,'Attempt_credit':False,'mastery_awarded':False}
 r['implementation']['task']['contract']=c;r['schema_version']='fathom-private-source-implementation.25';r['status']='SOURCE_SUPPORTED_MANUAL_TASK'
 r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['contract_capabilities']['complete_manual_response_contract']=True
 r['unresolved_reasons']=[];r['field_limitations']=[{'field':'fixed_timed_playback',**c['fixed_timing_projection']},{'field':'delivery_prerequisite','status':'External manual performer/instrument and human listener required for chosen interface; no source audio provided by app.'}]
 r['provenance']['previous_private_packet']=pin(base)
out=Path('Build')/LANE/'motif-comparison-overlays.jsonl';assert not (ROOT/out).exists();(ROOT/out).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'generation_elapsed_seconds':time.monotonic()-tick,
      'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(engine),'source_check':pin(sourcecheck),
      'exact_replaced_keys':[r['package_key'] for r in rows],'attempted':6,'source_supported_manual_contracts':6,'new_manual_category_promotions':6,
      'partial_unresolved_manual_contracts':0,'fixed_timed_projection_unresolved':6,'unattempted':0,'source_contacts_retained_exact':96,'external_manual_delivery_prerequisites':6,
      'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/LANE/'seal.json',seal);print(json.dumps(seal))
