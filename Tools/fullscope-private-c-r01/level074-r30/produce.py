from pathlib import Path
from pypdf import PdfReader
from fractions import Fraction as F
import copy,datetime,hashlib,json,time,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level074-r30')
tick=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def write(p,x):
    p=R/p;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
base=Path('Build/fullscope-private-c-r01/level074-r06/implementation-packet.jsonl')
assert pin(base)['sha256']=='cbf7e70fa609ca75aa8e5de13ffbf0cfb636c12d2a978a30c9481b9d72dfe247'
row=[json.loads(x) for x in (R/base).read_text().splitlines()][44];refs=row['source_refs']
for ref in refs:assert pin(ref['path'])=={k:ref[k] for k in ('path','bytes','sha256')}
pdf,txt=Path(refs[0]['path']),Path(refs[1]['path']);reader=PdfReader(R/pdf)
texts={n:' '.join(reader.pages[n-1].extract_text().split()) for n in (2,6,10,17,18)}
passes=['Clap accents only.','Muted-string attack stream.','Written pitches.','Add chord changes.','Record the complete form without stopping.']
for s in passes:assert s in texts[17]
cue='Say "three," "five," "shift," and "three-over-two" during beat 4 before the new section. Do not pause or add a count-in between sections.'
close='After bar 16, play one whole-note Cmaj7 and stop. The final chord confirms that the rhythmic layering never changed the larger tonal destination. If the close arrives early or late, isolate bars 13-16.'
assert cue in texts[17] and close in texts[17]
rate='The pitch order, sixteenth-note rate, pick cycle, and articulation remain unchanged. Only the starting subdivision moves.'
poly='TWO QUARTER-NOTE PULSES AGAINST THREE EVEN UPPER-VOICE ATTACKS IN EACH TWO-BEAT SPAN'
assert rate in texts[6] and poly in texts[10]
lines=(R/txt).read_text().splitlines()
assert lines[387:392]==[
 'Bars 1-3: group-of-3 cycle over Cmaj7-Am7-Dm7. 48 tones.',
 'Bars 4-8: group-of-5 cycle over G7-Cmaj7-Am7-Dm7-G7. 80 tones.',
 'Bars 9-12: metric motif starts on 1, e, &, then a of beat 1. 32 tones.',
 'Bars 13-16: 3:2 polyrhythm over Cmaj7-Am7-Dm7-G7. 40 tones.',
 'Final close: whole-note Cmaj7 after bar 16; not included in the 200-tone capstone count.']
harmonies=['Cmaj7','Am7','Dm7','G7','Cmaj7','Am7','Dm7','G7','Cmaj7','Am7','Dm7','G7','Cmaj7','Am7','Dm7','G7']
cells3=[['C','E','G'],['A','C','E'],['D','F','A']]
cells5=[['G','B','D','F','A'],['C','E','G','B','D'],['A','C','E','G','B'],['D','F','A','C','E'],['G','B','D','F','A']]
motif=['C','E','G','B','A','G','E','D']
for a in cells3:assert '-'.join(a)+' repeating' in texts[18]
for a in cells5:assert '-'.join(a) in texts[18]
assert 'Motif each bar: '+'-'.join(motif) in texts[18]
assert 'Bass roots: C, A, D, G on the two-pulse. Upper thirds: E, C, F, B on the three-pulse. Ten tones per bar.' in texts[18]
slots=[]
def add(section,bar,index,pitch,onset,voice='single',accent=None):
    absolute=F(4*(bar-1))+onset
    slots.append({'section':section,'source_bar':bar,'index_in_voice_or_cell':index,'pitch_label':pitch,
                  'voice':voice,'onset_q_fraction':[absolute.numerator,absolute.denominator],
                  'duration_q':None,'accent':accent,'octave':None,'midi':None,'string_number':None,'fret':None,'finger':None,
                  'provenance':'finite authored expansion of exact condensed source rule; not preexisting TAB contact'})
for i,cell in enumerate(cells3):
    for j in range(16):add(1,i+1,j+1,cell[j%3],F(j,4),accent=(i*16+j)%3==0)
for i,cell in enumerate(cells5):
    for j in range(16):add(2,i+4,j+1,cell[j%5],F(j,4),accent=(i*16+j)%5==0)
for i in range(4):
    for j,pitch in enumerate(motif):add(3,i+9,j+1,pitch,F(i+j,4))
for i,(bass,upper) in enumerate(zip(['C','A','D','G'],['E','C','F','B'])):
    for j in range(4):add(4,i+13,j+1,bass,F(j),voice='lower_two_pulse')
    for j in range(6):add(4,i+13,j+1,upper,F(2*j,3),voice='upper_three_pulse')
slots.sort(key=lambda e:(F(*e['onset_q_fraction']),e['voice']))
for n,e in enumerate(slots,1):e['derived_order']=n
assert len(slots)==200
sections=[{'section':1,'bars':[1,2,3],'note_uses':48,'group':3,'pitch_cells':cells3,'accent_phase':'global within section; does not restart at barline'},
          {'section':2,'bars':[4,5,6,7,8],'note_uses':80,'group':5,'pitch_cells':cells5,'accent_phase':'global within section; does not restart at barline'},
          {'section':3,'bars':[9,10,11,12],'note_uses':32,'motif':motif,'offset_sixteenths':[0,1,2,3],'accents':'not specified here; learner manual accent interpretation'},
          {'section':4,'bars':[13,14,15,16],'note_uses':40,'lower_pitches':['C','A','D','G'],'upper_pitches':['E','C','F','B'],'lower_per_bar':4,'upper_per_bar':6,'accents':'not specified here; learner manual accent interpretation'}]
cueplan=[{'section':1,'word':'three','preceding_printed_bar':None,'beat':4,'position':'pre-entry; no invented bar0 or extra count-in'},
         *[{'section':n,'word':w,'preceding_printed_bar':b,'beat':4,'position':'during prior printed bar'} for n,w,b in ((2,'five',3),(3,'shift',8),(4,'three-over-two',12))]]
projection={'schema_version':'fathom-private-condensed-source-expansion.1','exact_child_key':row['package_key'],
 'sections':sections,'harmonies':[{'source_bar':i+1,'chord':x} for i,x in enumerate(harmonies)],'ordered_pitch_voice_slots':slots,
 'note_uses':200,'source_contacts':0,'canonical_ids':False,
 'basis':{'main_pdf_pages':[17,18],'supporting_grid_page':2,'same_motif_rate_page':6,'same_3_to_2_span_page':10,'txt_lines':[386,392]},
 'interpretation':'Each bar repeats its listed literal pitch cell from the first label; accent phase remains global across the section. Condensed source expansion is labeled authored, separately reviewable and not canonical/native accepted.',
 'limits':['Pitch registers/frets/fingers/gate lengths not specified by capstone; explicit learner realization required.','No fixed accent pattern is invented for later sections.','Final whole-note Cmaj7 uses chosen voicing and is not counted among200.']}
projectionpath=Path('Build')/L/'source-relative-projection.json';write(projectionpath,projection)
model=Path('Tools')/L/'rhythm_contract.py'
c={'schema_version':'fathom-private-rhythm-capstone-manual-contract.1','package_key':row['package_key'],'complete_manual_contract':True,
 'source_script':{'label':row['implementation']['task']['label'],'main_source_pages':[17,18],
                  'sections':sections,'harmonies':projection['harmonies'],'transition_instruction':cue,'cues':cueplan,
                  'close_instruction':close,'close':{'after_bar':16,'chord':'Cmaj7','duration':'whole note','stop_after':True,'included_in_200':False,'voicing':None},
                  'performance_passes':[{'pass':i+1,'instruction':x} for i,x in enumerate(passes)],'projection_ref':pin(projectionpath)},
 'manual_choices':{'own_instrument':None,'tempo_bpm':None,'register_fret_voice_plan':None,'muted_voice_plan':None,
                   'later_section_accent_plan':None,'closing_cmaj7_voicing':None,
                   'origin':'learner-chosen realizations; no unprinted source voicing/finger/gate or accent prescription'},
 'manual_response_schema':{'per_pass':['performed pass form','group3 section','group5 section','displacement section','distinct3:2voices',
                          'all4source spoken cues','no pause/extra count-in','whole-noteCmaj7close','stop','close timing'],
                          'passes4_5':'added chord changes yes/no/uncertain','pass5_recording':'recorded yes/no/uncertain; external/local artifact reference or explicit self-report statement; no file format mandated'},
 'state_policy':{'passes':[1,2,3,4,5],'advance':'all current-pass manual duties satisfied after explicit release',
                 'close_failure':'early/late/uncertain requires isolated13–16manual report before current-pass retry',
                 'retry':'successful earlier passes retained; reason/release required','repeat':'explicit fullcycle; all history retained',
                 'cancel_reopen':'preserve source/pass/choices/responses; generation invalidated and release required',
                 'token':'instance/key/generation/cycle/pass/action/stage'},
 'authored_interface_policy':'Projection procedure, typed learner choices, response/release/token guards are Fathom-authored manual interface; no automatic performance or acoustic verification. Uncertain close is conservatively reviewed through the same source13–16repair. Recordings remain uninspected external references or self-report.',
 'state_engine_ref':pin(model),'performance_observed':False,'recording_inspected':False,'audio_supplied':False,
 'automatic_evaluation':False,'Attempt_credit':False,'mastery_awarded':False}
row['implementation']['task']['contract']=c;row['implementation']['derived_source_projection_ref']=pin(projectionpath)
row['schema_version']='fathom-private-source-implementation.30';row['provenance']['previous_private_packet']=pin(base)
row['contract_category']='COMPLETE_MANUAL_NONPLAYBACK_CONTRACT';row['status']='SOURCE_SUPPORTED_MANUAL_TASK'
row['contract_capabilities']['complete_manual_response_contract']=True;row['unresolved_reasons']=[]
row['field_limitations']=[{'field':'projection','status':'200derived relative-pitch/voice slots, not canonical/native contact events'},
                        {'field':'realization','status':'unprinted octave/fret/finger/gate/close voicing/later accents remain learner choices'},
                        {'field':'recording','status':'external/self-report only; no app recording or inspection'}]
source=Path('Build')/L/'source-check.json';write(source,{'original_pdf':pin(pdf),'original_txt':pin(txt),'previous_packet_line':45,
 'source_events_retained':0,'motif_occurrences_retained':8,'main_pages':[17,18],'supporting_pages':[2,6,10],
 'page_text_sha256':{str(n):hashlib.sha256(t.encode()).hexdigest() for n,t in texts.items()},
 'joined_transition_instruction':cue,'joined_close_instruction':close,'passes':passes,'txt_capstone_lines':lines[385:392],
 'section_counts':[48,80,32,40],'projection_ref':pin(projectionpath),'method':'bounded PDF text-stream/TXT source verification; no rendered or native qualification'})
out=Path('Build')/L/'rhythm-capstone-overlay.jsonl';assert not(R/out).exists();(R/out).write_text(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
seal={'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'generation_elapsed_seconds':time.monotonic()-tick,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
 'overlay':pin(out),'projection':pin(projectionpath),'base_packet':pin(base),'state_engine':pin(model),'source_check':pin(source),
 'exact_replaced_keys':[row['package_key']],'attempted':1,'source_supported_manual_contracts':1,'partial_unresolved':0,'unattempted':0,
 'source_events_retained_exact':0,'motif_literal_occurrences_retained':8,'derived_pitch_voice_uses':200,
 'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
write(Path('Results')/L/'seal.json',seal);print(json.dumps(seal))
