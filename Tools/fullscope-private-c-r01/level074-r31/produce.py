from pathlib import Path
from pypdf import PdfReader
import datetime,hashlib,json,time,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r31')
started=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='cbf7e70fa609ca75aa8e5de13ffbf0cfb636c12d2a978a30c9481b9d72dfe247'
row=[json.loads(x) for x in (R/base).read_text().splitlines()][45];refs=row['source_refs']
for ref in refs:assert pin(ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')}
pdf,txt=Path(refs[0]['path']),Path(refs[1]['path']);text=PdfReader(R/pdf).pages[18].extract_text();norm=' '.join(text.split());lines=(R/txt).read_text().splitlines()
instructions=['Clap full group-of-3 cycle.','Clap full group-of-5 cycle.','Clap full group-of-7 cycle.',
 'Add pitch cells without changing accents.','Complete eight metric displacements.','Play quintuplet and septuplet cells.',
 'Separate and combine 3:2 voices.','Separate and combine 4:3 voices.','Perform 5/4 and 7/8 studies.','Record the sixteen-bar capstone.']
fields=[['full_three_bar_group3'],['full_five_bar_group5'],['full_seven_bar_group7'],
 ['group3_pitch_cells','group5_pitch_cells','group7_pitch_cells','unchanged_accents'],
 [f'displacement_{i}' for i in range(1,9)],['printed_quintuplet_cells','printed_septuplet_cells'],
 ['lower_3_to_2_alone','upper_3_to_2_alone','combined_3_to_2'],
 ['lower_4_to_3_alone','upper_4_to_3_alone','combined_4_to_3'],
 ['four_five_four_studies','four_seven_eight_studies'],['complete_sixteen_bar_form','recorded_source_capstone']]
pages=[[3],[4],[5],[3,4,5],[6,7],[8,9],[10],[11],[12,13],[17,18]]
phases=[]
for i,(instruction,obligations,pp) in enumerate(zip(instructions,fields,pages),1):
    assert f'{i}. '+instruction in norm and f'{i}. {i}. '+instruction in lines
    phases.append({'phase':i,'source_instruction':instruction,'obligation_fields':obligations,
                   'source_task_reference':{'original_pdf_pages':pp,'canonical_binding':None,
                    'prerequisite':'learner uses original printed task with instrument and external resources as needed'},
                   'cycle_scope':'complete source scope represented by this phase, not one bar or diagnostic excerpt',
                   'authored_scope_note':'Typed phase-wide obligation fields are authored interface coverage; they do not allocate or accept referenced exercise child identities.'})
repairs={'ACCENT ADDS A NOTE':'return to even attacks and change volume only',
 'BARLINE MOVES':'tap quarters and speak bar numbers','GROUP RESTARTS':'continue global event count across the barline',
 'QUINTUPLET RUSHES':'practice one beat and land the next click','SEPTUPLET COLLAPSES':'reduce tempo and accent only note 1',
 'POLYRHYTHM MERGES':'play each voice alone, then alternate','ODD METER FEELS SHORT':'count large groups, not imaginary 4/4',
 'DISPLACED MOTIF LOST':'sing the motif before moving its onset'}
for k,v in repairs.items():assert k+' '+v in norm and k+': '+v+'.' in lines
advance='Add 2 BPM after three clean complete cycles, not after one clean bar. For 5- and 7-group cycles, shorten to two bars only for diagnosis, then return to the full cycle. Increase quintuplet or septuplet tempo only when the next quarter-note click remains exact.'
physical='Odd rhythm is not permission to tense the picking hand or over-accent every group. Use a small dynamic difference, preserve note length, and stop if the subdivision causes gripping or breath-holding.'
assert advance in norm and physical in norm
model=Path('Tools')/L/'practice_contract.py'
c={'schema_version':'fathom-private-practice-repair-manual-contract.1','package_key':row['package_key'],
 'complete_manual_contract':True,'source_heading':'REPAIR THE EARLIEST RHYTHMIC LAYER THAT FAILED','phases':phases,
 'error_repairs':repairs,'source_advancement_instruction':advance,'source_physical_instruction':physical,
 'manual_prerequisites':{'own_instrument':True,'original_workbook':True,'external_quarter_click_for_subdivision_phase':True,
                         'external_recording_capability_for_final_phase':True,'app_supplies_audio_or_capture':False,
                         'unresolved_source_child_scope':'Referenced original exercises remain at their own current status. Four L74outside-child ambiguities remain pending; this workflow neither allocates nor adopts them.'},
 'tempo_policy':{'increment_bpm':2,'minimum_clean_full_cycles':3,'scope':'same current phase and chosen tempo',
                 'consecutive_requirement_printed':False,'partial_or_diagnostic_counts':False,'changed_phase_or_tempo_resets_counter':True,
                 'subdivision_phase_extra_gate':'latest next-quarter click exact self-report',
                 'applies_to':'private chosen external BPM only after explicit acknowledgment; never host clock',
                 'representation_limit':'refuse unrepresentable exact+2 numeric suggestion'},
 'diagnostic_policy':{'phases':[2,3],'excerpt_bars':2,'counts_for_completion_or_tempo':False,'return_full_required':True},
 'manual_response_schema':{'common':['complete_scope','clean','small_dynamic_difference','note_length_preserved','no_gripping_or_breath_holding'],
                          'source_obligations':'all current phase named fields yes/no/uncertain',
                          'quarter_click_exact':'phase6 yes/no/uncertain; otherwise null',
                          'recording':'phase10 recorded yes/no/uncertain, external_reference/self_report, nonempty reference_or_statement; otherwise null',
                          'notes':'optional text'},
 'state_policy':{'full_cycle':'perform→manualrelease→report→cycle_complete orrepair/physicalstop',
                 'tempo':'suggestion only after qualifyingthreecycles; explicitexternalack; no automaticchange',
                 'repair':'learner selects earliest error oruncertain; exactrepair guidance exposed; explicitperformed/release before retry',
                 'physical_stop':'interrupt currentmanualcycle; release/resolvedselfreport before retry; never counted complete',
                 'diagnosis':'two-bar report cannotadvance; explicitreturn-full fence',
                 'phase_advancement':'after complete satisfied currentcycle; does not require tempo-increase eligibility',
                 'cancel_reopen':'preserve phase/choices/response/history, invalidate tokens and requiremanualrelease',
                 'token':'instance/key/generation/phase/cycle/action/stage'},
 'authored_interface_policy':'Phase-wide fields/counters and state ownership are authored interface decisions around source instructions. All performance, repair, quarter-click, recording and external tempo replies are manual self-report. No automatic diagnosis, scoring, mastery or native task binding. Uncertain physical symptom report conservatively requires stop/release.',
 'source_locators':{'pdf_page':19,'txt_progression_lines':[395,406],'txt_error_lines':[408,416]},
 'state_engine_ref':pin(model),'performance_observed':False,'audio_supplied':False,'host_tempo_changed':False,
 'recording_inspected':False,'Attempt_credit':False,'mastery_awarded':False}
row['implementation']['task']['contract']=c;row['schema_version']='fathom-private-source-implementation.31'
row['provenance']['previous_private_packet']=pin(base);row['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
row['status']='SOURCE_SUPPORTED_MANUAL_TASK';row['contract_capabilities']['complete_manual_response_contract']=True
row['unresolved_reasons']=[];row['field_limitations']=[{'field':'practice_availability','status':'requires original source tasks, actualinstrument/externalclick/recording; not app-supplied'},
 {'field':'referenced_tasks','status':'no canonical binding or underlying child-status promotion'},
 {'field':'outcome','status':'manual reports only, no acoustic verification, credit or mastery'}]
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'previous_packet_line':46,
 'pdf_page':19,'pdf_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'phases':10,'repairs':8,
 'source_advancement':advance,'source_physical_boundary':physical,'txt_progression':lines[394:406],'txt_errors':lines[407:416],
 'method':'original PDF text stream and originalTXT; no rendered/app/native qualification'})
out=Path('Build')/L/'practice-repair-overlay.jsonl';assert not(R/out).exists();(R/out).write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(model),'source_check':pin(source),
 'exact_replaced_keys':[row['package_key']],'attempted':1,'source_supported_manual_contracts':1,
 'partial_unresolved':0,'unattempted':0,'source_contacts_retained_exact':len(row['implementation']['events']),
 'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
