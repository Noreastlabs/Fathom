"""Finite original Level4 source preparation; producer evidence, not independent review."""
from pathlib import Path
import hashlib, itertools, json, re, resource, time
from datetime import datetime, timezone
import pdfplumber
ROOT=Path(__file__).resolve().parents[3]
BASE='fullscope-private-a-r01/level004-finite-exporter-r01'
B=ROOT/'Build'/BASE; R=ROOT/'Results'/BASE
PACKET='Build/fullscope-private-a-r01/level004-r01/packet.jsonl'
TXT='Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_4_Three_String_Relay.txt'
PDF='Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_4_Three_String_Relay.pdf'
PINS={PACKET:('7bea74400c5b8a645bc3320280ba7a29bf3c660fd100be5f55526ecbf036d191',2862494),TXT:('4c90d79866f42125a7aa8785e803462864dbb88b2ecfa856438bf49f922f3d9a',57886),PDF:('b24cad79148b8165b74cbd3662031c2ad0227f0e856aa955d03c88db31dbafb1',45350)}
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
checks=0;start=time.monotonic();utc=datetime.now(timezone.utc).isoformat()
def ck(v,label):
 global checks
 assert v,label
 checks+=1
for p,(h,size) in PINS.items():
 b=(ROOT/p).read_bytes();ck(len(b)==size and sha(b)==h,p)
rows=[json.loads(s) for s in (ROOT/PACKET).read_text().splitlines()]
txt=(ROOT/TXT).read_text().splitlines();units=[];setno=None;covered=set(range(22))
for i,line in enumerate(txt):
 if line=='='*96:covered.add(i)
 m=re.fullmatch(r'SET (\d) OF 9 - EXERCISES (\d{3})-(\d{3})',line)
 if m:
  setno=int(m[1]);covered.add(i)
  ck((int(m[2]),int(m[3]))==((setno-1)*12+1,setno*12),'set range')
 m=re.fullmatch(r'Exercise (\d{3}): ([1-4]{4})',line)
 if m:
  units.append(dict(ordinal=int(m[1]),code=m[2],set=setno,line=i+1,unit=txt[i:i+15]));covered.update(range(i,i+15))
ck(all(i in covered or not s.strip() for i,s in enumerate(txt)),'all nonblank TXT source lines accounted')
ck(len(units)==len(rows)==108,'108 units')
codes=[''.join(c) for c in itertools.product('1234',repeat=4) if all(c[i]!=c[i+1] for i in range(3))]
ck([(u['set'],u['ordinal'],u['code']) for u in units]==[(i//12+1,i+1,c) for i,c in enumerate(codes)],'complete ordered printed family')
triples=['EAD','ADG','DGB','GBe','eBG','BGD','GDA','DAE']
bindings=[];lookup={}
for line,(u,r) in enumerate(zip(units,rows),1):
 expected_id=f"printed:l004:set-{u['set']}-of-9-exercises-{(u['set']-1)*12+1:03}-{u['set']*12:03}:exercise-{u['ordinal']:03}-{u['code']}"
 ck(r['source_identity']==expected_id and r['package_key']=='proposed-'+expected_id.replace(':','-'),'exact key')
 ck(r['source_payload']['exact_unit_lines']==u['unit'],'TXT full unit')
 ck(u['unit'][1]=='ASCEND' and u['unit'][8]=='DESCEND','source direction labels')
 page=u['set']+1
 ck(r['source_refs'][1]['locator']['physical_pages']==[page],'PDF page join')
 tokens=[]
 for block,offset in enumerate([2,9],1):
  group=[]
  for row_index,s in enumerate(u['unit'][offset:offset+6]):
   m=re.fullmatch(r'([eBGDAE])\|([5-8|\-]+)',s);ck(m is not None,'TXT staff')
   group.extend((t.start(),m[1],int(t[0]),u['line']+offset+row_index,t.start()+3,block) for t in re.finditer('[5-8]',m[2]))
  ck(len(group)==16 and len({x[0] for x in group})==16,'16 ordered contacts')
  tokens.extend(sorted(group))
 route=[(s,int(f)+4,int(f)) for tri in triples for s,f in zip([tri[0],tri[1],tri[1],tri[2]],u['code'])]
 ck([(t[1],t[2]) for t in tokens]==[(s,f) for s,f,_ in route],'source 1+2+1 triple route')
 contacts=r['implementation']['ordered_contacts'];ck(len(contacts)==32,'packet count')
 for n,(t,(s,f,finger),c) in enumerate(zip(tokens,route,contacts)):
  ck((c['string_label'],c['fret'],c['finger'],c['source_line'],c['source_column_1based'],c['block_index'])==(s,f,finger,t[3],t[4],t[5]),'literal packet contact')
  ck(c['midi']==dict(zip('EADGBe',[40,45,50,55,59,64]))[s]+f,'pitch')
  ck(c['onset_q']==n/4 and c['duration_q']==0.25,'selected original relative timing')
 ck(r['unresolved_reasons']==[],'no unresolved')
 ck(len(r['implementation']['relative_variants'])==2,'two start variants')
 for v,startstroke in zip(r['implementation']['relative_variants'],'DU'):
  ck(v['start_stroke']==startstroke and v['contact_ordinals']==list(range(1,33)) and v['strokes']==[startstroke if n%2==0 else ('U' if startstroke=='D' else 'D') for n in range(32)] and v['end_q']==8,'source alternate starts')
 binding={'package_key':r['package_key'],'source_identity':r['source_identity'],'packet_line':line,'record_sha256_sorted_keys':sha(canon(r)),'set':u['set'],'exercise_ordinal':u['ordinal'],'code':u['code'],'pdf_page':page,'txt_first_line':u['line'],'txt_last_line':u['line']+14}
 bindings.append(binding);lookup[(page,u['ordinal'])]=u
with pdfplumber.open(ROOT/PDF) as pdf:
 ck(len(pdf.pages)==10,'original 10 pages')
 page1=pdf.pages[0].extract_text()
 for page_no,page in enumerate(pdf.pages[1:],2):
  lines=page.extract_text().splitlines();seen=[]
  ck(f'Set {page_no-1} of 9' in lines[1],'PDF set label')
  for i,line in enumerate(lines):
   heads=re.findall(r'\b(\d{3}) ([1-4]{4}) start finger ([1-4])',line)
   if not heads:continue
   ck(len(heads)==3,'three original cards across PDF')
   staff=[re.findall(r'[eBGDAE]\|[5-8|\-]+',s) for s in lines[i+1:i+13]]
   ck(len(staff)==12 and all(len(x)==3 for x in staff),'12 staff rows x3cards')
   for col,(ordinal,code,finger) in enumerate(heads):
    u=lookup[(page_no,int(ordinal))];seen.append(int(ordinal))
    ck(code==u['code'] and finger==u['code'][0],'PDF code and start finger')
    ck([x[col] for x in staff]==u['unit'][2:8]+u['unit'][9:15],'all original PDF/TXT card rows')
  ck(len(seen)==len(set(seen))==12,'12 distinct PDF cards')
 # Full page1 retained. Independently check the worked example against its printed code1234.
 examples=[re.findall(r'[eBGDAE]\|[5-8|\-]+',s) for s in page1.splitlines()]
 examples=[x for x in examples if x]
 ck(len(examples)==6 and all(len(x)==2 for x in examples),'complete worked-example two directions')
 for direction in range(2):
  grid=[]
  for row in examples:
   m=re.fullmatch(r'([eBGDAE])\|([5-8|\-]+)',row[direction])
   grid.extend((t.start(),m[1],int(t[0])) for t in re.finditer('[5-8]',m[2]))
  expected=[(s,int(f)+4) for tri in triples[direction*4:direction*4+4] for s,f in zip([tri[0],tri[1],tri[1],tri[2]],'1234')]
  ck([(s,f) for _,s,f in sorted(grid)]==expected,'PDF worked-example route')
 for phrase in ['Crossings occur after notes 1 and 3.','A downstroke start makes both landings upstrokes.','An upstroke start makes both landings downstrokes.','Keep both landings even and relaxed.','Mute every unused string.','Lightly accent landing notes 2 and 4','equal in volume and duration.','without resetting the hands or the pick.','on two separate days.']:
  ck(phrase in page1,'exact PDF guidance '+phrase)
 guidance={'schema':'fathom-private-level004-source-guidance.1','status':'NOT_ADMITTED','source_pdf':{'path':PDF,'sha256':PINS[PDF][0],'physical_page':1},'source_txt':{'path':TXT,'sha256':PINS[TXT][0],'first_line':1,'last_line':22},'original_pdf_page1_text':page1,'original_txt_intro':txt[:22],
 'obligations':[
 {'key':'fixed_foundation','text':'Standard tuning; fifth position fingers1–4 at frets5–8; no position shift or string skip.','basis':'PDFp1, TXT2–3,9'},
 {'key':'triple_split','text':'Code note1 on first string, notes2–3 on middle string, note4 on third string:1+2+1 counts, not finger numbers. Original four-digit code order never changes.','basis':'PDFp1, TXT5–9'},
 {'key':'adjacent_route','text':'Four adjacent triples ascending E/A/D A/D/G D/G/B G/B/e, then descending e/B/G B/G/D G/D/A D/A/E.','basis':'TXT8'},
 {'key':'alternate_pick_starts','text':'Repeat full ascending-to-descending traversal with opposite starting pick stroke. Continuous D/U alternation makes both landing notes2/4 upstrokes for down-start, downstrokes for up-start.','basis':'TXT13–14,18; PDFp1'},
 {'key':'continuous_turn','text':'Play ASCEND directly into DESCEND without resetting the hands or the pick; no inserted pause or position change.','basis':'TXT18; PDFp1'},
 {'key':'session_scope','text':'Use one12-exercise set per session.','basis':'TXT17; PDFp1 practice1'},
 {'key':'first_pass','text':'First pass lightly accent landing notes2 and4 of every four-note group so both crossings are deliberate.','basis':'TXT19; PDFp1 FIRST PASS'},
 {'key':'second_pass','text':'Second pass remove the accents and make all four notes equal in volume and duration.','basis':'TXT19; PDFp1 SECOND PASS'},
 {'key':'grouping_sequence','text':'Use straight16ths first. Reintroduce triplet and quintuplet groupings only after the crossings are stable.','basis':'TXT20'},
 {'key':'starting_tempo','text':'Start10–15BPM below your clean Level3 tempo; no fixed BPM or observed baseline supplied.','basis':'TXT17; PDFp1 practice2'},
 {'key':'tempo_advance','text':'After three clean loops add2BPM next session.','basis':'TXT21; PDFp1 practice6'},
 {'key':'tempo_reduce','text':'After two errors or rising tension reduce4–6BPM.','basis':'TXT21; PDFp1 practice7'},
 {'key':'progression','text':'Advance after the full12-exercise set is clean with both pick starts on two separate days. No individual-exercise completion substitutes for full-set evidence.','basis':'TXT22; PDFp1'},
 {'key':'quality_and_muting','text':'Keep both landings even and relaxed. Mute every unused string. These are unobserved physical obligations, not executable note-off times.','basis':'PDFp1 picking objective'}],
 'selected_realization':{'rhythm':'straight_sixteenth','pass':'second_equal_volume_equal_duration','start_variants':['D','U'],'additional_pass_variant_axis':False,'metric_duration_is_acoustic_gate':False},
 'unselected_required_semantics':{'first_pass_landing_accents':[2,4],'accent_is_qualitative':True,'numeric_velocity':None,'other_rhythms':['triplet','quintuplet'],'other_rhythms_condition':'only after crossings stable; stability not observed','completion_claimed':False,'opposite_start_repeat':'both variants retained; no session sequencer or observed repetition generated'},
 'limits':{'automatic_credit':False,'observed_clean_loops':None,'observed_clean_days':None,'observed_errors':None,'observed_tension':None,'observed_crossing_stability':None,'observed_clean_level3_bpm':None,'source_fixed_bpm':None,'source_acoustic_gate':None,'performed_velocity':None,'runtime_admitted':False,'independent_review':'PENDING'}}
# Fresh producer artifacts only. Source validation completes before writing them.
for name,data in {'original-pdf-page1.txt':(page1+'\n').encode(),'trusted-bindings.json':canon({'schema':'fathom-private-level004-bindings.1','status':'PRODUCER_BOUND_NOT_INDEPENDENTLY_ACCEPTED','source_packet':{'path':PACKET,'sha256':PINS[PACKET][0]},'records':bindings})+b'\n','source-guidance.json':canon(guidance)+b'\n'}.items():
 with (B/name).open('xb') as f:f.write(data)
result={'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'started_utc':utc,'assertions':checks,'source_units':108,'source_contacts':3456,'variants':216,'variant_memberships':6912,'pdf_pages_checked':10,'pdf_cards_checked':108,'pdf_worked_example_contacts_checked':32,'evidence_kind':'producer original PDF text/vector and TXT source checks; no independent/raster/native/installed acceptance','elapsed_seconds':round(time.monotonic()-start,4),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
with (R/'original-source-check.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
