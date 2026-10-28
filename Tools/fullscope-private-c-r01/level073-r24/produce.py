from pathlib import Path
from pypdf import PdfReader
import copy,datetime,hashlib,json,resource,time
ROOT=Path(__file__).resolve().parents[3]
LANE=Path('fullscope-private-c-r01/level073-r24')
start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
 p=Path(p);return {'path':str(p),'bytes':(ROOT/p).stat().st_size,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()}
def write(p,x):
 p=ROOT/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl')
assert pin(base)['sha256']=='30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
pdf=next((ROOT/'Notes/music/guitar project/PDF version').glob('*Level_73_*')).relative_to(ROOT)
txt=next((ROOT/'Notes/music/guitar project/TXT version').glob('*Level_73_*')).relative_to(ROOT)
assert pin(pdf)['sha256']=='7cc4c0098855c8e6d4b90063fb947b763e32a4225d66b77821f9e23f763779f9'
assert pin(txt)['sha256']=='63fed22776f4fcfd61ac9b7783b456c8996f2b438c06886d585bff2ee01afd15'
page=PdfReader(ROOT/pdf).pages[11].extract_text()
header='REMOVE THE SOURCE TONIC; PRACTICE ONLY THE PIVOT, DESTINATION DOMINANT, AND NEW TONIC'
instruction='These compact cells isolate the exact harmonic bridge used inside the longer routes. Play one complete arpeggio per chord. Repeat the final tonic once before looping.'
footer='Failure sign: the bridge sounds like three unrelated arpeggios. Repair by sustaining the common or guide tone and hearing the destination dominant before replaying the full cell.'
assert all(s in ' '.join(page.split()) for s in (header,instruction,footer))
verification=Path('Build')/LANE/'source-check.json'
write(verification,{'original_pdf':pin(pdf),'original_txt':pin(txt),'physical_page':12,'extracted_text_sha256':hashlib.sha256(page.encode()).hexdigest(),
                    'method':'pypdf original PDF text stream, no fresh visual-layout qualification','header':header,'instruction':instruction,'footer':footer})
lines=(ROOT/txt).read_text().splitlines();engine=Path('Tools')/LANE/'bridge_contract.py'
rows=list(map(json.loads,(ROOT/base).read_text().splitlines()))[29:34]
assert len(rows)==5 and all('/modulef/' in r['package_key'] for r in rows)
for r in rows:
 events=r['implementation']['events'];join=r['provenance']['exact_conversion_joins'][0]
 lo,hi=join['txt_event_lines'];label,function,bridge=lines[lo-4:lo-1];chords=join['facts']['chords']
 assert label==r['source_payload']['printed_label'] and bridge=='Bridge: | '+' | '.join(chords)+' |'
 assert len(events)==12 and [e['source_order'] for e in events]==list(range(1,13))
 pcsets=[{e['written_pitch_theory']['pitch_class'] for e in events[n*4:(n+1)*4]} for n in range(3)]
 candidates=[]
 for e in events:
  bar=e['printed_bar']-1;pc=e['written_pitch_theory']['pitch_class'];bases=[]
  if e['printed_role'] in ('3','b3','7','b7'):bases.append('printed third/seventh guide-tone role')
  for adjacent in (bar-1,bar+1):
   if 0<=adjacent<3 and pc in pcsets[adjacent]:bases.append(f'common pitch class with printed chord{adjacent+1}')
  if bases:candidates.append({'source_order':e['source_order'],'basis':bases})
 segments=[{'segment_number':n,'role':role,'chord_symbol':chords[min(n-1,2)],
             'source_orders':list(range((n-1)*4+1,n*4+1)) if n<4 else [9,10,11,12],
             'origin':'printed_arpeggio' if n<4 else 'source_required_tonic_repeat_reference'}
            for n,role in enumerate(('pivot','destination_dominant','new_tonic','repeat_final_tonic_once'),1)]
 c={'schema_version':'fathom-private-pivot-bridge-contract.1','package_key':r['package_key'],'route_label':label,
    'printed_function':function,'printed_bridge':bridge,'source_header':header,'source_instruction':instruction,'source_failure_repair':footer,
    'source_page':{'pdf':pin(pdf),'physical_page':12,'verification':pin(verification)},'source_txt_lines':[lo-3,hi],
    'printed_contacts':copy.deepcopy(events),'segments':segments,'repair_candidates':candidates,
    'repair_candidate_origin':'Fathom-authored finite menu referencing only original contacts: exact adjacent-chord common pitch class or printed third/seventh role. Not new source notes, voicings, durations or canonical occurrences.',
    'prerequisites':['Learner supplies own instrument and performs/hears the source manually. No app sound or acoustic analysis.',
                     'Learner chooses pulse/articulation; the source does not print a fixed metric realization or number of loops.'],
    'response_fields':[
      {'id':'setup','fields':['own_instrument:true','pulse:text','articulation:text']},
      {'id':'each_segment','fields':['current_action_token','segment_number:1..4','complete_arpeggio:yes/no/uncertain','explanation:text']},
      {'id':'bridge_summary','fields':['connected_bridge:yes/no/uncertain','destination_dominant_heard:yes/no/uncertain','explanation:text']},
      {'id':'manual_release','fields':['current_action_token','released:true']},
      {'id':'after_release_choice','fields':['choice:loop/finish']},
      {'id':'repair_selection','fields':['source_order:existing_common_or_guide_tone','relation_and_hold_plan:text']},
      {'id':'repair_report','fields':['sustained_chosen_tone:yes/no/uncertain','heard_destination_dominant:yes/no/uncertain','explanation:text','manual_release:true']},
      {'id':'explicit_retry','fields':['reason:text','manual_release:true']}],
    'authored_interface_policy':'Fathom-authored sequencing and response fields expose printed practice/repair obligations; reports are unverified learner statements, not source-created file-format requirements.',
    'state_policy':{'order':['setup','ready','pivot','dominant','tonic','tonic_repeat','summary','release','loop_or_finish'],
                    'negative_connectedness':'Release, choose common/guide-tone source contact, sustain/hear dominant reports, release, then full replay. No bypass via generic retry.',
                    'incomplete_arpeggio':'Retain failed/uncertain reports; explicit retry and release before replay.',
                    'loop':'Explicit learner choice only after successful manual reports and tonic repeat. No fixed loop count.',
                    'cancel_reopen':'Retain context/reports/history and source position, confirm manual release; invalidate stale actions.',
                    'ownership':'Current in-memory instance/route/generation/loop/action token on every mutation; no canonical allocation or persistence.'},
    'fixed_timing_projection':{'status':'UNRESOLVED','reason':'No fixed pulse distribution, contact duration, tempo or sustain duration is printed for these bridge cells. Source order and required repeat remain explicit.',
                               'onset_q':None,'duration_q':None,'bpm':None},
    'state_engine_ref':pin(engine),'automatic_evaluation':False,'performance_observed':False,'app_audio_supplied':False,'Attempt_credit':False,'mastery_awarded':False}
 r['implementation']['task']['contract']=c
 r['schema_version']='fathom-private-source-implementation.24';r['status']='SOURCE_SUPPORTED_MANUAL_TASK'
 r['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';r['contract_capabilities']['complete_manual_response_contract']=True
 r['unresolved_reasons']=[];r['field_limitations']=[{'field':'fixed_timed_playback',**c['fixed_timing_projection']}]
 r['provenance']['previous_private_packet']=pin(base)
out=Path('Build')/LANE/'pivot-bridge-overlays.jsonl';assert not (ROOT/out).exists()
(ROOT/out).write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in rows))
seal={'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'generation_elapsed_seconds':time.monotonic()-tick,
      'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(engine),'source_check':pin(verification),
      'exact_replaced_keys':[r['package_key'] for r in rows],'attempted':5,'source_supported_manual_contracts':5,'new_manual_category_promotions':5,
      'partial_unresolved_manual_contracts':0,'fixed_timed_projection_unresolved':5,'unattempted':0,'source_contacts_retained_exact':60,
      'source_required_tonic_repeat_reference_uses':20,'new_original_or_canonical_events':0,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/LANE/'seal.json',seal);print(json.dumps(seal))
