from pathlib import Path
from pypdf import PdfReader
import copy,datetime,hashlib,json,time,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level073-r26');tick=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
 p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
 p=R/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl');assert pin(base)['sha256']=='30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
rows=list(map(json.loads,(R/base).read_text().splitlines()))[17:23];assert len(rows)==6
refs=rows[0]['source_refs'];pdf=Path(refs[0]['path']);txt=Path(refs[1]['path'])
for ref in refs:assert pin(ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')}
header='SOURCE ARPEGGIO -> COMMON TONE THROUGH FOUR REGISTERS -> DESTINATION ARPEGGIO'
instruction='No diatonic pivot chord is used. The retained pitch supplies continuity while the other chord tones change. After the printed cell, confirm the destination with its V-I cadence.'
reader=PdfReader(R/pdf);pages=[]
for n in (8,9):
 text=reader.pages[n-1].extract_text();norm=' '.join(text.split());assert header in norm and instruction in norm and 'Standard tuning.' in norm
 pages.append({'physical_page':n,'extracted_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'header':header,'full_instruction':instruction,'standard_tuning_footer':True})
lines=(R/txt).read_text().splitlines();model=Path('Tools')/L/'mediant_contract.py';questions=[];checks=[]
for r in rows:
 e=r['implementation']['events'];j=r['provenance']['exact_conversion_joins'][0];lo,hi=j['txt_event_lines'];label=lines[lo-4];bridge=j['facts']['bridge_note'];assert label==r['source_payload']['printed_label'];assert len(e)==12
 for obj in e:assert obj['onset_q'] is None and obj['duration_q'] is None and obj['finger'] is None
 bridge_events=e[4:8];midi=[x['written_pitch_theory']['midi_at_stated_standard_tuning'] for x in bridge_events];unique=len(set(midi));assert len({x%12 for x in midi})==1
 complete=unique==4;assert unique in (3,4)
 extent={'source_heading':header,'bridge_note':bridge,'source_orders':[5,6,7,8],
         'contacts':[{'string_name':x['string_name'],'fret':x['fret'],'midi_at_printed_standard_tuning':m,'source_order':x['source_order']} for x,m in zip(bridge_events,midi)],
         'printed_positions':4,'distinct_midi_pitches':unique,'status':'FOUR_DISTINCT_REGISTERS' if complete else 'REGISTER_EXTENT_RECONCILIATION_REQUIRED',
         'interpretation_limit':'Preserve four printed positions. Repeated pitch at two positions is not silently counted as two distinct pitch registers; no replacement fret/note inferred.',
         'source_refs':refs,'txt_context_lines':[lo-3,hi],'pdf_physical_page':j['pdf_physical_page'],'key':r['package_key']}
 if not complete:questions.append(extent)
 c={'schema_version':'fathom-private-chromatic-mediant-manual-contract.1','package_key':r['package_key'],'complete_manual_contract':complete,
    'source_header':header,'source_instruction':instruction,'source_script':{'route_label':label,'bridge_note':bridge,'source_arpeggio':copy.deepcopy(e[:4]),'common_tone_bridge':copy.deepcopy(e[4:8]),'destination_arpeggio':copy.deepcopy(e[8:]),'txt_context_lines':[lo-3,hi],'pdf_physical_page':j['pdf_physical_page']},
    'register_extent':extent,'source_obligations':['Play source arpeggio, common-tone bridge, then destination arpeggio in printed order.','No diatonic pivot chord is used.','Retained pitch supplies continuity while other chord tones change.','After printed cell, confirm destination with its V-I cadence.'],
    'manual_prerequisite':{'own_instrument':True,'app_supplies_audio':False,'external_player_required':False,'availability':'learner must supply actual instrument; source completeness is not live performance or app availability'},
    'cadence_choice':{'destination_reference':label.split(' -> ')[1],'source_function_label':'V-I','dominant_realization':None,'tonic_realization':None,'timing_plan':None,'destination_v_i_self_report':None,
                     'origin':'Learner supplies exact realization; printed source does not prescribe cadence voicing, notes, timing or duration. Fathom-authored text fields retain choices without claiming harmonic validation.','source_event_ids_added':0},
    'response_fields':[{'id':'setup','fields':['own_instrument:true','dominant_realization:text','tonic_realization:text','timing_plan:text','destination_v_i:yes/no/uncertain']},
      {'id':'printed_cell','fields':['played_as_printed:yes/no/uncertain','common_tone_continuity:yes/no/uncertain','no_diatonic_pivot:yes/no/uncertain','explanation:text']},
      {'id':'chosen_cadence','fields':['played_chosen_cadence:yes/no/uncertain','destination_confirmed:yes/no/uncertain','explanation:text']},
      {'id':'release','fields':['manual_instrument_released:true']},{'id':'retry','fields':['reason:text','manual_release:true']}],
    'authored_interface_policy':'Typed setup/self-report fields and phase/order/release safeguards are Fathom-authored manual interface policy, not new printed musical facts or automatic correctness checks.',
    'state_policy':{'order':['setup/choice_review','ready','perform_printed_cell','perform_chosen_cadence','manual_release','complete_manual_reports_or_retry_required'],
      'register_extent_pending':'No full task begin/completion for the three unresolved heading-versus-position cases. Original source script remains visible and cancel/reopen preserves it.',
      'token':'exact instance/route/generation/pass/current action; stale/duplicate callbacks refuse','retry':'Retain choices and complete prior reports; explicit release then reset only current pass; choices may be revised before next begin.',
      'cancel_reopen':'Retain position/choice/reports/history; invalidate stale token; require release before reopen','negative_or_uncertain':'Retain manual reports and require explicit retry/release; do not infer success.'},
    'fixed_timing_projection':{'status':'UNRESOLVED','onset_q':None,'duration_q':None,'bpm':None,'reason':'No exact fixed timing is printed here; cadence realization and timing remain learner choices.'},
    'state_engine_ref':pin(model),'performance_observed':False,'app_audio_supplied':False,'automatic_evaluation':False,'Attempt_credit':False,'mastery_awarded':False}
 r['implementation']['task']['contract']=c;r['schema_version']='fathom-private-source-implementation.26';r['provenance']['previous_private_packet']=pin(base)
 r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT' if complete else 'IMPLEMENTATION_OR_INTERPRETATION_PENDING'
 r['status']='SOURCE_SUPPORTED_MANUAL_TASK' if complete else 'REGISTER_EXTENT_RECONCILIATION_PENDING';r['contract_capabilities']['complete_manual_response_contract']=complete
 r['unresolved_reasons']=[] if complete else [{'disposition':'SOURCE_EXTENT_RECONCILIATION_REQUIRED','exact_issue':'Four-register header accompanies four printed positions but only three distinct MIDI pitches; original source formats agree. Separate disposition needed; do not retune/refret or expand quarantine.','details':extent}]
 r['field_limitations']=[{'field':'fixed_timed_playback',**c['fixed_timing_projection']},{'field':'unprinted_cadence','status':'learner-supplied manual realization; not a new source-event sequence'}]+([] if complete else [{'field':'register_extent','status':'distinct source disposition pending'}])
 checks.append({'package_key':r['package_key'],'previous_packet_line':18+len(checks),'events':12,'register_extent':extent,'complete_manual_contract':complete})
sourcecheck=Path('Build')/L/'source-check.json';write(sourcecheck,{'original_pdf':pin(pdf),'original_txt':pin(txt),'pages':pages,'rows':checks,'method':'original PDF text stream + exact original TXT and existing source join; no fresh rendered visual qualification'})
questionpath=Path('Results')/L/'register-extent-referral.json';write(questionpath,{'scope':'exact three original ModuleD cells only; not broader source defect/quarantine','source_refs':refs,'source_header':header,'source_instruction':instruction,'questions':questions,'fret_or_pitch_changes':0,'new_complete_promotions_for_questions':0,'requested_disposition':'Reconcile four-register wording versus these exact duplicated pitches; source/native/admission still Pending.'})
out=Path('Build')/L/'chromatic-mediant-overlays.jsonl';assert not(R/out).exists();(R/out).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(model),'source_check':pin(sourcecheck),'register_referral':pin(questionpath),'exact_replaced_keys':[r['package_key'] for r in rows],'attempted':6,'source_supported_manual_contracts':3,'new_manual_category_promotions':3,'partial_source_extent_unresolved':3,'unattempted':0,'source_contacts_retained_exact':72,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
