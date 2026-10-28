from pathlib import Path
from pypdf import PdfReader
import datetime,hashlib,json,time,resource,math
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r29')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='cbf7e70fa609ca75aa8e5de13ffbf0cfb636c12d2a978a30c9481b9d72dfe247'
row=json.loads((R/base).read_text().splitlines()[0]);assert row['implementation']['events']==[]
refs=row['source_refs']
for ref in refs:assert pin(ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')}
pdf,txt=Path(refs[0]['path']),Path(refs[1]['path']);text=PdfReader(R/pdf).pages[1].extract_text();norm=' '.join(text.split())
concepts=[
 {'concept':'Odd grouping','what_changes':'accent spacing: 3, 5, or 7','what_remains_fixed':'4/4 bar and sixteenth grid','repair_cue':'tap quarters while accents drift'},
 {'concept':'Odd subdivision','what_changes':'notes per beat: 5 or 7','what_remains_fixed':'quarter-note beat length','repair_cue':'return to one beat and count evenly'},
 {'concept':'Metric displacement','what_changes':'phrase onset','what_remains_fixed':'phrase notes and duration','repair_cue':'speak the new starting slot'},
 {'concept':'Polyrhythm','what_changes':'simultaneous pulse layers','what_remains_fixed':'shared total time span','repair_cue':'play each voice alone, then combine'},
 {'concept':'Odd meter','what_changes':'number/grouping of beats','what_remains_fixed':'subdivision inside each beat','repair_cue':'count the large groups aloud'}]
for x in concepts:assert ' '.join(x.values()) in norm
heading='FOUR DIFFERENT RHYTHMIC QUESTIONS REQUIRE FOUR DIFFERENT ANSWERS';assert heading in norm
count='Count|1--e--&--a--2--e--&--a--3--e--&--a--4--e--&--a--|'
hand='Hand |D--U--D--U--D--U--D--U--D--U--D--U--D--U--D--U--|'
overlay='Accent marks sit above existing attacks; the D/U path does not restart.'
body='Keep the foot on quarter notes in 4/4. In 5/4 and 7/8, move the body pulse to the printed large grouping. The physical pulse is the reference against which displacement is heard.'
for x in (count,hand,overlay,body):assert x in norm
slots=[{'slot':i+1,'spoken_count':str(i//4+1) if i%4==0 else ['e','&','a'][i%4-1],
        'printed_hand':'D' if i%2==0 else 'U','beat_number':i//4+1,'slot_within_beat':i%4+1} for i in range(16)]
returns=[{'group':g,'bars':g,'sixteenth_slots':16*g,'accents':16} for g in (3,5,7)]
for x in returns:assert ' '.join(str(v) for v in x.values()) in norm
lines=(R/txt).read_text().splitlines()
for g in (3,5,7):assert f'Group of {g} returns after {16*g} slots = {g} bars = 16 groups.' in lines
grid={'count_literal':count,'hand_literal':hand,'slots':slots,'accent_rule':overlay,
      'source_events_allocated':0,'meaning':'reference slot labels and picking path only; no pitch/fret or runtime playback'}
bodydata={'full_instruction':body,'four_four':'quarter notes',
          'five_four_and_seven_eight':'the printed large grouping','specific_large_groups':None,
          'limit':'This atlas does not specify particular odd-meter groups; retain source exercise grouping when applied.'}
steps=[{'id':f'concept-{i+1}','kind':'concept_comparison','source_payload':x,
        'response_fields':['changes_reviewed','fixed_element_reviewed','repair_cue_reviewed']} for i,x in enumerate(concepts)]
steps += [
 {'id':'count-hand-grid','kind':'reference_grid','source_payload':grid,
  'response_fields':['count_labels_reviewed','continuous_du_path_reviewed','accents_overlay_existing_attacks_reviewed']},
 {'id':'full-cycle-returns','kind':'reference_arithmetic','source_payload':returns,
  'response_fields':['group3_return_reviewed','group5_return_reviewed','group7_return_reviewed']},
 {'id':'body-pulse','kind':'physical_reference_guidance','source_payload':bodydata,
  'response_fields':['quarter_pulse_in_four_four_reviewed','printed_large_groups_in_odd_meter_reviewed','displacement_reference_reviewed']}]
model=Path('Tools')/L/'atlas_contract.py'
c={'schema_version':'fathom-private-reference-atlas-contract.1','package_key':row['package_key'],
   'mode':'manual_source_reference_review','complete_manual_contract':True,'source_heading':heading,
   'source_label':'Grouping, subdivision, displacement, and polyrhythm reference atlas',
   'concept_comparisons':concepts,'sixteenth_grid':grid,'full_cycle_returns':returns,'body_pulse':bodydata,
   'review_steps':steps,'manual_response_schema':{'each_named_field':'yes/no/uncertain acknowledgment of review',
   'notes':'optional text; no/uncertain retained for review again'},
   'authored_interface_policy':'Eight-step order and acknowledgment fields are Fathom-authored reference-review interface. Original repair cues/body instructions are fully exposed guidance; acknowledgment does not claim those actions performed. No knowledge or performance grade.',
   'source_locators':{'pdf_physical_page':2,'txt_core_arithmetic_lines':[7,11],
                      'scope_note':'Concept table, hand grid and full body guidance are original PDF fields; paired TXT supplies core arithmetic and does not repeat all page2 table content.'},
   'state_policy':{'token':'instance/key/generation/cycle/step/action/stage',
                   'negative_uncertain':'retain all replies/notes and require explicit same-step review',
                   'repeat':'explicit new reference cycle; prior responses retained',
                   'cancel_reopen':'preserve current step/response notes and invalidate old tokens'},
   'state_engine_ref':pin(model),'source_event_count':0,'instrument_required_for_reference_review':False,
   'practice_performed':False,'app_audio_supplied':False,'knowledge_graded':False,'Attempt_credit':False,'mastery_awarded':False}
row['implementation']['task']['contract']=c;row['schema_version']='fathom-private-source-implementation.29'
row['provenance']['previous_private_packet']=pin(base);row['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
row['status']='SOURCE_SUPPORTED_MANUAL_REFERENCE_TASK';row['contract_capabilities']['complete_manual_response_contract']=True
row['unresolved_reasons']=[];row['field_limitations']=[{'field':'pitched_playback','status':'not applicable to this reference atlas; zero source contact events'},
 {'field':'reference_review','status':'not practice, acoustic observation or knowledge grade'},
 {'field':'specific_odd_meter_groups','status':'atlas delegates to the printed group in the applicable exercise; none invented'}]
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'physical_page':2,
 'pdf_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'txt_core_lines':lines[6:11],
 'previous_packet_line':1,'concept_rows':5,'review_steps':8,'slots':16,'return_rows':3,
 'method':'bounded original PDF text stream; no fresh rendered-layout QA','source_events':0})
out=Path('Build')/L/'reference-atlas-overlay.jsonl';assert not(R/out).exists();(R/out).write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(model),'source_check':pin(source),
 'exact_replaced_keys':[row['package_key']],'attempted':1,'source_supported_manual_contracts':1,
 'manual_subtype':'source_reference_review','partial_unresolved':0,'unattempted':0,'source_contacts_retained_exact':0,
 'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
