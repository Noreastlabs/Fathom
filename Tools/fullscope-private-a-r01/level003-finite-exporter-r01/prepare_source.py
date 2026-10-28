"""Finite original Level3 source preparation; producer evidence, not independent review."""
from pathlib import Path
import hashlib, itertools, json, re, resource, time
from datetime import datetime, timezone
import pdfplumber
ROOT=Path(__file__).resolve().parents[3]
BASE='fullscope-private-a-r01/level003-finite-exporter-r01'
B=ROOT/'Build'/BASE; R=ROOT/'Results'/BASE
PACKET='Build/fullscope-private-a-r01/level003-r01/packet.jsonl'
TXT='Notes/music/guitar project/TXT version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.txt'
PDF='Notes/music/guitar project/PDF version/108_Finger_Permutations_Level_3_Odd_Count_String_Transfer.pdf'
PINS={PACKET:('17a6b272e593717b6eebca6f8f5f0affb58b04df3f3f2da145065f7243330af4',6847367),TXT:('1bb8d5225f2db8df2b3ce518f10f28e11158592e0b5cbbb4c28af2742c861b4f',140780),PDF:('f04c1e49ce939ec83e5c80f9ad8cc81fd49da62e2039c25cac5367cea0fa6234',86935)}
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
txt=(ROOT/TXT).read_text().splitlines();units=[];mode=None;setno=None
for i,line in enumerate(txt):
 m=re.match(r'SET (\d) OF 9',line)
 if m:setno=int(m[1])
 m=re.match(r'MODE ([AB]) -',line)
 if m:mode=m[1]
 m=re.fullmatch(r'Exercise (\d{3}): ([1-4]{4})',line)
 if m:units.append(dict(ordinal=int(m[1]),code=m[2],mode=mode,set=setno,line=i+1,unit=txt[i:i+15]))
ck(len(units)==len(rows)==216,'216 units')
codes=[''.join(c) for c in itertools.product('1234',repeat=4) if all(c[i]!=c[i+1] for i in range(3))]
expected_order=[(s,m,i+1,codes[i]) for s in range(1,10) for m in 'AB' for i in range((s-1)*12,s*12)]
ck([(u['set'],u['mode'],u['ordinal'],u['code']) for u in units]==expected_order,'complete ordered printed family')
bindings=[];lookup={}
for line,(u,r) in enumerate(zip(units,rows),1):
 expected_id=f"printed:l003:set-{u['set']}-of-9-exercises-{(u['set']-1)*12+1:03}-{u['set']*12:03}:mode-"+('a-3-1-late-transfer' if u['mode']=='A' else 'b-1-3-early-transfer')+f":exercise-{u['ordinal']:03}-{u['code']}"
 ck(r['source_identity']==expected_id and r['package_key']=='proposed-'+expected_id.replace(':','-'),'exact key')
 ck(r['source_payload']['exact_unit_lines']==u['unit'],'TXT full unit')
 page=2*u['set']+(u['mode']=='B')
 ck(r['source_refs'][1]['locator']['physical_pages']==[page],'PDF page join')
 tokens=[]
 for block,offset in enumerate([2,9],1):
  group=[]
  for row_index,s in enumerate(u['unit'][offset:offset+6]):
   m=re.fullmatch(r'([eBGDAE])\|([5-8|\-]+)',s);ck(m is not None,'TXT staff')
   group.extend((t.start(),m[1],int(t[0]),u['line']+offset+row_index,t.start()+3,block) for t in re.finditer('[5-8]',m[2]))
  ck(len(group)==20 and len({x[0] for x in group})==20,'20 ordered contacts')
  tokens.extend(sorted(group))
 pairs=list(zip('EADGB','ADGBe'))+list(zip('eBGDA','BGDAE'))
 split=3 if u['mode']=='A' else 1
 route=[(s,int(f)+4,int(f)) for pair in pairs for s,f in zip([pair[0]]*split+[pair[1]]*(4-split),u['code'])]
 ck([(t[1],t[2]) for t in tokens]==[(s,f) for s,f,_ in route],'source split/route')
 contacts=r['implementation']['ordered_contacts'];ck(len(contacts)==40,'packet count')
 for n,(t,(s,f,finger),c) in enumerate(zip(tokens,route,contacts)):
  ck((c['string_label'],c['fret'],c['finger'],c['source_line'],c['source_column_1based'],c['block_index'])==(s,f,finger,t[3],t[4],t[5]),'literal packet contact')
  ck(c['midi']==dict(zip('EADGBe',[40,45,50,55,59,64]))[s]+f,'pitch')
  ck(c['onset_q']==n/4 and c['duration_q']==0.25,'selected original relative timing')
 ck(r['unresolved_reasons']==[],'no unresolved')
 for v,startstroke in zip(r['implementation']['relative_variants'],'DU'):
  ck(v['start_stroke']==startstroke and v['contact_ordinals']==list(range(1,41)) and v['strokes']==[startstroke if n%2==0 else ('U' if startstroke=='D' else 'D') for n in range(40)] and v['end_q']==10,'source alternate starts')
 binding={'package_key':r['package_key'],'source_identity':r['source_identity'],'packet_line':line,'record_sha256_sorted_keys':sha(canon(r)),'set':u['set'],'mode':u['mode'],'exercise_ordinal':u['ordinal'],'code':u['code'],'pdf_page':page,'txt_first_line':u['line'],'txt_last_line':u['line']+14}
 bindings.append(binding);lookup[(page,u['ordinal'])]=u
with pdfplumber.open(ROOT/PDF) as pdf:
 ck(len(pdf.pages)==19,'original 19 pages')
 page1=pdf.pages[0].extract_text()
 (B/'original-pdf-page1.txt').write_text(page1+'\n')
 for page_no,page in enumerate(pdf.pages[1:],2):
  lines=page.extract_text().splitlines();seen=[]
  for i,line in enumerate(lines):
   heads=re.findall(r'\b(\d{3}) ([1-4]{4}) (?:3\+1 LATE|1\+3 EARLY) TRANSFER',line)
   if not heads:continue
   ck(len(heads)==3,'three original cards across PDF')
   staff=[re.findall(r'[eBGDAE]\|[5-8|\-]+',s) for s in lines[i+1:i+13]]
   ck(len(staff)==12 and all(len(x)==3 for x in staff),'12 staff rows x3cards')
   for col,(ordinal,code) in enumerate(heads):
    u=lookup[(page_no,int(ordinal))];seen.append(int(ordinal))
    ck(code==u['code'],'PDF code')
    ck([x[col] for x in staff]==u['unit'][2:8]+u['unit'][9:15],'all original PDF/TXT card rows')
  ck(len(seen)==len(set(seen))==12,'12 distinct PDF cards')
 guidance={'schema':'fathom-private-level003-source-guidance.1','status':'NOT_ADMITTED','source_pdf':{'path':PDF,'sha256':PINS[PDF][0],'physical_page':1},'source_txt':{'path':TXT,'sha256':PINS[TXT][0],'first_line':1,'last_line':21},'original_pdf_page1_text':page1,'original_txt_intro':txt[:21],
 'obligations':[
 {'key':'fixed_foundation','text':'Standard tuning; fifth position fingers1–4 at frets5–8; no position shift or string skip.','basis':'PDFp1, TXT2–3'},
 {'key':'mode_split','text':'ModeA3+1 crosses after note3; ModeB1+3 crosses after note1; original four-digit order never changes.','basis':'PDFp1, TXT5–9'},
 {'key':'adjacent_route','text':'Five adjacent pairs ascending E/A A/D D/G G/B B/e and descending e/B B/G G/D D/A A/E.','basis':'TXT8'},
 {'key':'alternate_pick_starts','text':'Strict alternate picking, once beginning downstroke and once upstroke; continuous emitted alternation over full40contacts.','basis':'TXT12–13,17; PDFp1'},
 {'key':'session_scope','text':'One12-code set and one mode per session; SessionA ModeA then SessionB same set ModeB.','basis':'TXT16; PDFp1 session2'},
 {'key':'first_pass','text':'First pass lightly accent the first landing after each crossing: note4 of each ModeA group, note2 of each ModeB group.','basis':'TXT18; PDFp1 examples'},
 {'key':'second_pass','text':'Second pass remove the accent and make all four notes equal in volume.','basis':'TXT18; PDFp1 examples'},
 {'key':'grouping_rotation','text':'Rotate existing straight16th, triplet and quintuplet groupings across sessions.','basis':'TXT19'},
 {'key':'starting_tempo','text':'Begin8–12BPM below your clean Level2 tempo; no fixed BPM or observed baseline supplied.','basis':'TXT16; PDFp1 session1'},
 {'key':'tempo_advance','text':'After three clean loops add2BPM next time.','basis':'TXT20; PDFp1 session4'},
 {'key':'tempo_reduce','text':'After two errors or rising tension reduce4–6BPM.','basis':'TXT20; PDFp1 session4'},
 {'key':'progression','text':'Advance when both mode pages of the set are clean on two separate days; then try alternating3+1/1+3 between successive string pairs.','basis':'TXT21; PDFp1 session5'},
 {'key':'quality','text':'Combine only after each mode is clean; even tone matters more than top speed.','basis':'PDFp1 foundation3'}],
 'selected_realization':{'rhythm':'straight_sixteenth','pass':'second_equal_volume','start_variants':['D','U'],'additional_pass_variant_axis':False},
 'unselected_required_semantics':{'first_pass_landing_accents':{'A':4,'B':2},'accent_is_qualitative':True,'numeric_velocity':None,'other_rhythms':['triplet','quintuplet'],'completion_claimed':False,'optional_after_progression':'alternate modes between successive pairs; not generated'},
 'limits':{'automatic_credit':False,'observed_clean_loops':None,'observed_clean_days':None,'source_fixed_bpm':None,'source_acoustic_gate':None,'performed_velocity':None,'runtime_admitted':False,'independent_review':'PENDING'}}
 for phrase in ['Lightly accent the landing note 4','Lightly accent the landing note 2','No position shift or string skip yet.','both mode pages are clean on two separate days; then','try alternating 3+1 and 1+3 between successive string pairs.']:
  ck(phrase in page1,'exact PDF guidance '+phrase)
(B/'trusted-bindings.json').write_bytes(canon({'schema':'fathom-private-level003-bindings.1','status':'PRODUCER_BOUND_NOT_INDEPENDENTLY_ACCEPTED','source_packet':{'path':PACKET,'sha256':PINS[PACKET][0]},'records':bindings})+b'\n')
(B/'source-guidance.json').write_bytes(canon(guidance)+b'\n')
result={'status':'PASS','utc':datetime.now(timezone.utc).isoformat(),'started_utc':utc,'assertions':checks,'source_units':216,'source_contacts':8640,'variants':432,'variant_memberships':17280,'pdf_pages_checked':19,'pdf_cards_checked':216,'evidence_kind':'producer original PDF text/vector and TXT source checks; no independent/raster/native/installed acceptance','elapsed_seconds':round(time.monotonic()-start,4),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
(R/'original-source-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
