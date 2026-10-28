from pathlib import Path
from pypdf import PdfReader
import copy,datetime,hashlib,json,time,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level073-r28')
tick=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level073-r07/implementation-packet.jsonl')
assert pin(base)['sha256']=='30e05936c037a06e3258bd7bd2b5372e76755f7ac5875d3756c37013c975a127'
row=[json.loads(x) for x in (R/base).read_text().splitlines()][38]
refs=row['source_refs']
for ref in refs:assert pin(ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')}
pdf,txt=Path(refs[0]['path']),Path(refs[1]['path']);reader=PdfReader(R/pdf);lines=(R/txt).read_text().splitlines()
header='C -> G -> D -> A -> E | PIVOT CHORD, DOMINANT, DESTINATION TONIC'
instruction='Every four-bar block begins with the current tonic, reinterprets a shared diatonic chord, introduces the dominant of the next key, and confirms the new tonic. Announce the destination key on beat 4 of the pivot chord.'
passes='PERFORMANCE Pass 1 arpeggios; Pass 2 guide-tone dyads; Pass 3 free phrase with the same pivot and dominant schedule.'
pages=[]
for n in (17,18):
    text=reader.pages[n-1].extract_text();norm=' '.join(text.split())
    assert header in norm and instruction in norm and passes in norm and 'Standard tuning.' in norm
    pages.append({'physical_page':n,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'full_instruction':instruction,'pass_footer':passes})
assert lines[562:565]==['Pass 1: complete arpeggios.','Pass 2: guide-tone dyads only.','Pass 3: free phrase preserving the printed pivot and dominant schedule.']
events=row['implementation']['events'];assert len(events)==64
chords=[x.strip() for x in lines[521].split('|')[1:-1]];assert len(chords)==16
bars=[];dyads=[]
for bar,chord in enumerate(chords,1):
    es=[e for e in events if e['source_absolute_bar']==bar];assert len(es)==4
    assert all(e['harmonic_context']['chord_symbol']==chord and e['onset_q'] is None and e['duration_q'] is None for e in es)
    third=[e for e in es if e['printed_role'] in ('3','b3')];seventh=[e for e in es if e['printed_role'] in ('7','b7')]
    assert len(third)==len(seventh)==1
    selected=third+seventh;assert selected[0]['string_name']!=selected[1]['string_name']
    bars.append({'source_bar':bar,'printed_chord':chord,'source_orders':[e['source_order'] for e in es]})
    dyads.append({'source_bar':bar,'printed_chord':chord,'source_orders':[e['source_order'] for e in selected],
                  'roles':[e['printed_role'] for e in selected],
                  'positions':[{'string_name':e['string_name'],'fret':e['fret'],'printed_note':e['printed_note'],
                                'midi':e['written_pitch_theory']['midi_at_stated_standard_tuning']} for e in selected],
                  'simultaneous_manual_dyad':True,'distinct_strings':True,'onset_q':None,'duration_q':None})
keys=['C','G','D','A','E'];blocks=[]
for i in range(4):
    start=4*i+1
    blocks.append({'block':i+1,'source_key':keys[i]+' major','destination_key':keys[i+1]+' major',
                   'current_tonic':{'bar':start,'chord':chords[start-1]},
                   'shared_pivot':{'bar':start+1,'chord':chords[start]},
                   'next_dominant':{'bar':start+2,'chord':chords[start+1]},
                   'new_tonic':{'bar':start+3,'chord':chords[start+2]},
                   'spoken_destination_cue':{'bar':start+1,'beat_in_bar':4,'say':keys[i+1]+' major',
                                             'quarter_time':None,'coincident_source_order':None,
                                             'origin':'printed instruction and exact block progression; no inferred note-attack alignment'}})
model=Path('Tools')/L/'capstone_contract.py'
c={'schema_version':'fathom-private-three-pass-capstone-manual-contract.1','package_key':row['package_key'],
   'complete_manual_contract':True,'source_header':header,'full_source_instruction':instruction,
   'source_pass_footer':passes,'source_txt_pass_instructions':lines[562:565],
   'source_script':{'label':row['implementation']['task']['label'],'events':copy.deepcopy(events),
                    'bars':bars,'blocks':blocks,'route':keys,'txt_lines':[519,565],'pdf_physical_pages':[17,18]},
   'pass_contracts':[{'pass':1,'form':'complete arpeggios','source_orders':list(range(1,65)),
                      'source_contact_uses':64,'all_blocks_and_spoken_cues_required':True},
                     {'pass':2,'form':'guide-tone dyads only','guide_dyads':dyads,'source_contact_uses':32,
                      'all_blocks_and_spoken_cues_required':True,
                      'projection_provenance':'Fathom-authored manual realization of the printed guide-dyad pass using only each bar’s printed third/minor-third and seventh/minor-seventh. References existing contacts; not a new printed TAB or retimed source event.'},
                     {'pass':3,'form':'free phrase preserving printed pivot and dominant schedule',
                      'learner_choice':None,'source_contact_uses':None,'fixed_source_note_sequence':False,
                      'all_blocks_and_spoken_cues_required':True,'schedule_source_bars':list(range(1,17)),
                      'choice_schema':'nonempty learner description or local/external reference; not a prescribed file type, inspected audio or printed realization'}],
   'manual_prerequisite':{'own_instrument':True,'app_supplies_audio':False,'external_player_required':False},
   'learner_timing_choice':{'timing_plan':None,'origin':'explicit learner choice; source retains beat4 speech cue without full meter/quarter-note/gate mapping'},
   'response_schema':{'performed_pass_form':'yes/no/uncertain','sixteen_bar_schedule':'yes/no/uncertain',
                       'blocks':{'count':4,'order':[1,2,3,4],'fields':{k:'yes/no/uncertain' for k in ('current_tonic','shared_pivot','next_dominant','new_tonic','destination_announced_on_pivot_beat4')}},
                       'reflection':'optional text, empty string permitted'},
   'authored_interface_policy':'Typed choice/report fields and ordered manual release/token safeguards are authored UI policy. Replies are self-report; beat4 speech is not an acoustic measurement. Any negative/uncertain obligation requires explicit current-pass retry and preserves earlier reports.',
   'state_policy':{'passes':[1,2,3],'ready_for_pass3':'requires retained learner free-phrase choice',
                    'manual_release':'before response and explicit retry/repeat/reopen',
                    'retry':'same unsuccessful pass; successful earlier passes and history retained',
                    'repeat':'explicit complete-cycle repeat; chosen timing/phrase and all history retained',
                    'cancel_reopen':'source/script/choices/pass/response retained; callbacks invalidated',
                    'token':'exact instance/route/generation/cycle/pass/action/stage'},
   'timing_limit':{'native_quarter_projection':False,'fixed_bpm':None,'spoken_cues':'source bar+beat4 only; not note-event onset'},
   'state_engine_ref':pin(model),'performance_observed':False,'automatic_evaluation':False,
   'Attempt_credit':False,'mastery_awarded':False,'app_audio_supplied':False}
row['implementation']['task']['contract']=c;row['schema_version']='fathom-private-source-implementation.28'
row['provenance']['previous_private_packet']=pin(base);row['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT'
row['status']='SOURCE_SUPPORTED_MANUAL_TASK';row['contract_capabilities']['complete_manual_response_contract']=True
row['unresolved_reasons']=[]
row['field_limitations']=[{'field':'fixed_timed_playback','status':'not provided; retains only original source-relative speech cues'},
                          {'field':'free_phrase','status':'learner choice; not source-prescribed notes'},
                          {'field':'acoustic_result','status':'no observed performance, recording inspection, grading or credit'}]
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'pages':pages,
    'package_key':row['package_key'],'previous_packet_line':39,'events':64,'dyad_reference_uses':32,
    'new_source_events':0,'bars':bars,'blocks':blocks,'method':'bounded PDF text stream and original TXT; not fresh rendered-layout qualification'})
out=Path('Build')/L/'capstone-overlay.jsonl';assert not (R/out).exists()
(R/out).write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
      'overlay':pin(out),'base_packet':pin(base),'state_engine':pin(model),'source_check':pin(source),
      'exact_replaced_keys':[row['package_key']],'attempted':1,'source_supported_manual_contracts':1,
      'partial_unresolved':0,'unattempted':0,'source_contacts_retained_exact':64,'dyad_existing_contact_uses':32,
      'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
