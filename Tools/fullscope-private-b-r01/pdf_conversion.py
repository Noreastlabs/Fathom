"""PDF card/table conversions: original coordinates and literal printed rows retained."""
import re,copy
from fractions import Fraction
from extended import event,members,STRINGS,scalar_tokens,pipe_rows,qpair

def scope(r,rows,doc,lines):
 loc=r.get('txt_locator');p=r['pdf_locator'];
 if p is None:
  txt='\n'.join(lines[loc['line_start']-1:loc['line_end']]);return txt,'','',{'physical_page':None,'method':'exact audited TXT-only unit; no PDF substitution'}
 pg=p['physical_pages'][0];page=doc.pages[pg-1];box=p.get('bbox');clip=None
 if box and '-card' in r['source_identity']:
  anchors=[x['pdf_locator']['bbox'] for x in rows if x.get('pdf_locator') and x['pdf_locator'].get('bbox') and '-card' in x['source_identity'] and pg in x['pdf_locator']['physical_pages']]
  x0,y0=box[:2];row=sorted({b[0] for b in anchors if abs(b[1]-y0)<12});gaps=[b-a for a,b in zip(row,row[1:]) if b-a>40];width=min(gaps) if gaps else page.width-x0-32;right=min([b[0]-8 for b in anchors if b[0]>x0+40 and abs(b[1]-y0)<12] or [min(page.width-32,x0+width-8)]);bottom=min([b[1]-5 for b in anchors if b[1]>y0+15] or [page.height-35]);clip=[max(0,x0-3),max(0,y0-3),right,bottom]
 elif box and '-t' in r['source_identity']:clip=box
 if clip:pdftext=page.crop(clip).extract_text(x_tolerance=1) or ''
 else:pdftext='\n\n'.join(doc.pages[n-1].extract_text(x_tolerance=1) or '' for n in p['physical_pages'])
 txt='\n'.join(lines[loc['line_start']-1:loc['line_end']]) if loc else ''
 # An exact audited TXT boundary supplies the cell; PDF reference/crop stays beside it.
 chosen=txt if txt else pdftext
 if r['level']==53 and re.match(r'F[78]\.',r['printed_label']):chosen=pdftext
 supplemental=None
 # The audited PDF card and TXT unit can have different titles. Supplement only
 # with an exact unique source heading and retain the newly established boundary.
 if (r['level']==62 and '/modulej/' in r['source_identity'] and r['printed_label'].endswith('bridge')) or (r['level']==64 and re.match(r'J[1-6]\. ',r['printed_label'])):
  hits=[i for i,s in enumerate(lines) if s.strip()==r['printed_label']]
  if len(hits)==1:
   start=hits[0];end=next((i for i in range(start+1,len(lines)) if not lines[i].strip()),len(lines))
   chosen='\n'.join(lines[start:end]);supplemental={'line_start':start+1,'line_end':end,'method':'unique exact original TXT bridge heading; stop at first blank line'}
 if r['level']==61 and '/modulej/' in r['source_identity'] and 'capstone:' in r['printed_label']:
  title='MODULE J - SIXTEEN-BAR '+('MAJOR' if r['printed_label'].startswith('Major') else 'MINOR')+' CAPSTONE';hits=[i for i,s in enumerate(lines) if s==title]
  if len(hits)==1:
   start=hits[0];end=next((i-1 for i in range(start+2,len(lines)) if lines[i].startswith('MODULE ') or lines[i].startswith('PRACTICE PROGRESSION')),len(lines))
   chosen='\n'.join(lines[start:end]);supplemental={'line_start':start+1,'line_end':end,'method':'unique exact original TXT capstone heading through next section boundary'}
 selected=[page.crop(clip)] if clip else [doc.pages[n-1] for n in p['physical_pages']]
 score_parts=[]
 for q in selected:
  filtered=q.filter(lambda c:c.get('object_type')=='char' and 'Courier' in c.get('fontname',''))
  anchors=filtered.search(r'Nte\|') or []
  if len(anchors)>1:
   for a in sorted(anchors,key=lambda a:(round(a['top']/5),a['x0'])):
    x=a['x0'];y=a['top'];row=sorted({v['x0'] for v in anchors if abs(v['top']-y)<8});gaps=[b-a for a,b in zip(row,row[1:]) if b-a>40];width=min(gaps) if gaps else q.bbox[2]-x;xright=min([v['x0']-3 for v in anchors if v['x0']>x+40 and abs(v['top']-y)<8] or [min(q.bbox[2],x+width-3)]);ybottom=min([v['top']-1 for v in anchors if v['top']>y+10] or [q.bbox[3]])
    box=(max(q.bbox[0],x-3),max(q.bbox[1],y-1),xright,ybottom)
    if box[0]<box[2] and box[1]<box[3]:score_parts.append(filtered.within_bbox(box).extract_text(x_tolerance=1) or '')
  else:score_parts.append(filtered.extract_text(x_tolerance=1) or '')
 mono='\n\n'.join(score_parts)
 if supplemental:mono=chosen
 return chosen,pdftext,mono,{'physical_page':pg,'derived_bbox':clip,'supplemental_txt_locator':supplemental,'method':'bounded original TXT supplement with PDF identity retained' if supplemental else 'audited TXT exact boundary' if txt else 'PDF original coordinate card/row' if clip else 'PDF original full-page unit'}

def blocks(text):
 # Split horizontally adjacent score blocks without conflating their column coordinates.
 out=[];columns=[];boundaries=[]
 rx=re.compile(r'(?<!\S)(Nte|Notes?|Deg|Rol|Fng|Pck|Pick|Tag|Chd|Cnt|Snd|Hnd|[EADGBe])\s*\|')
 for line in text.splitlines():
  matches=list(rx.finditer(line))
  if not matches:continue
  chunks=[(m[1],line[m.end():matches[i+1].start() if i+1<len(matches) else len(line)].rstrip(),m.start()) for i,m in enumerate(matches)]
  if chunks[0][0] in ['Nte','Note','Notes','Cnt']:
   if columns:out.extend(columns)
   columns=[[] for _ in chunks];boundaries=[x[2] for x in chunks]
  if not columns:continue
  for j,(k,v,pos) in enumerate(chunks):
   col=j if len(chunks)==len(columns) else min(range(len(columns)),key=lambda i:abs(boundaries[i]-pos))
   columns[col].append((k,v))
 if columns:out.extend(columns)
 return out

def tab_events(text):
 events=[];problems=[];sourcegrids=[]
 for block in blocks(text):
  d=dict(block);note_key=next((k for k in ['Nte','Note','Notes'] if k in d),None)
  strings=[k for k in STRINGS if k in d]
  if not note_key or not strings:continue
  note=d[note_key].replace('|','');ns=[(m.start(),m.group()) for m in re.finditer(r'[^\s-]+',note)]
  smap={}
  for k in strings:
   for m in re.finditer(r'\d+|[xX]',d[k].replace('|','')[:len(note)]):smap.setdefault(m.start(),[]).append({'string':STRINGS[k],'fret':int(m[0]) if m[0].isdigit() else None,'muted':m[0].lower()=='x'})
  aux={k:{m.start():m[0] for m in re.finditer(r'[^\s-]+',v.replace('|',''))} for k,v in block if k not in strings+[note_key]}
  for pos,n in ns:
   contact=smap.get(pos,[]);e=event(len(events)+1,'note_contact' if len(contact)==1 else 'chord_contact' if contact else 'unresolved_note_contact',printed_note=n,printed_column=pos)
   if len(contact)==1:e.update(contact[0])
   elif contact:e['members']=contact
   else:problems.append({'field':f'events[{len(events)}].string/fret','reason':f'Printed note {n} at column{pos} has no aligned TAB contact within the exact card; no position inferred.'})
   for k,name in [('Deg','degree'),('Rol','role'),('Fng','finger'),('Pck','pick'),('Pick','pick'),('Tag','tag')]:
    if pos in aux.get(k,{}):e[name]=aux[k][pos]
   events.append(e)
  unexpected=set(smap)-set(p for p,n in ns)
  if unexpected:problems.append({'field':'TAB alignment','reason':'Additional printed TAB positions do not align with the extracted Nte grid: '+str(sorted(unexpected))+'. Source rows preserved for exact repair.'})
  sourcegrids.append({'rows':[{'label':k,'literal':v} for k,v in block]})
 return events,problems,sourcegrids

def mask_events(text):
 events=[];raw=[]
 for b in blocks(text):
  d=dict(b)
  if 'Snd' not in d:continue
  snd=d['Snd'].replace('|','').replace(' ','');hnd=d.get('Hnd','').replace('|','').replace(' ','');raw.append(d)
  if not all(c in 'PpxX-~.Rr' for c in snd):continue
  for i,c in enumerate(snd):
   # A '-' is an air-stroke/non-contact, never an invented pitched attack.
   e=event(len(events)+1,'pitched_chord_contact' if c.upper()=='P' else 'dead_stroke' if c.lower()=='x' else 'release' if c.upper()=='R' else 'air_stroke' if c in '-.' else 'hold',source_token=c,subdivision_index=i,pick=hnd[i] if i<len(hnd) else None,onset_q=[i,4],duration_q=[1,4]);events.append(e)
 return events,raw

def fixed_voicing(text):
 d=dict(pipe_rows(text));fr=d.get('Frt',d.get('Val'));st=d.get('Str')
 if not fr or not st:return None
 strings=scalar_tokens(st);frets=scalar_tokens(fr)
 if len(strings)!=len(frets) or not all(s in STRINGS for s in strings):return None
 return members([STRINGS[s] for s in strings],frets,scalar_tokens(d.get('Nte','')),scalar_tokens(d.get('Fng','')),scalar_tokens(d.get('Deg','')))

def triad_table(r,text,page):
 cp=r.get('printed_components') or [];level=r['level'];events=[];table={'printed_fields':cp};unknown=[]
 if level==53 and len(cp)==3 and re.fullmatch(r'\d+-\d+-\d+',cp[2]):
  stset={3:[3,2,1],4:[4,3,2],5:[5,4,3],6:[6,5,4]}[r['pdf_locator']['physical_pages'][0]];mm=members(stset,cp[2].split('-'))
  events=[event(1,'blocked_triad',members=mm)]+[event(i+2,'string_contact',**m) for i,m in enumerate(mm)]
 elif level in [55,56] and len(cp)>=7 and re.match(r'^[b#]?\d$',cp[0]):
  d=dict(pipe_rows(page));chords=[x.strip() for x in d.get('Chd','').split('|') if re.fullmatch(r'[A-G][#b]?(?:m|dim|°)?',x.strip())];frets=[x.strip() for x in d.get('Frt','').split('|') if x.strip()]
  chord=cp[3]
  if chord in chords and len(chords)==len(frets):
   fr=frets[chords.index(chord)];mm=members([4,3,2],fr.split('-'));events=[event(1,'blocked_triad',chord=chord,members=mm,onset_q=[0,1],duration_q=[1,1])]+[event(i+2,'string_contact',**m,onset_q=[i+1,1],duration_q=[1,1]) for i,m in enumerate(mm)]
  else:unknown.append({'field':'degree voicing','reason':'Table degree/spelling/function retained but the precise corresponding ladder voicing could not be isolated; original grid is retained. Do not choose a different voicing.'})
 elif len(cp)>=3 and re.fullmatch(r'(?:[xX]|\d+)(?:\s+(?:[xX]|\d+)){5}',cp[1]):
  fr=cp[1].split();fng=cp[3].split() if len(cp)>3 and len(cp[3].split())==6 else None;mm=members([6,5,4,3,2,1],fr,fingers=fng);table['members']=mm
  if 'four quarter' in page.lower() or '4 quarter' in page.lower():events=[event(i+1,'chord_attack',chord=cp[0],members=mm,onset_q=[i,1],duration_q=[1,1]) for i in range(4)]
  else:events=[event(1,'voicing_formation',chord=cp[0],members=mm)]
 else:
  # Explicit row operands are retained as a typed manual curriculum table task.
  sets=[s for s in cp if re.fullmatch(r'[EADGBe](?:-[EADGBe]){2,5}',s)]
  triples=[s for s in cp if re.fullmatch(r'\d+(?:-\d+){2}',s)]
  if sets and triples:
   mm=members([STRINGS[s] for s in sets[0].split('-')],triples[0].split('-'));table['members']=mm
   if 'one blocked attack' in page.lower() and ('low-middle-high' in page.lower() or 'arpeggio' in page.lower()):events=[event(1,'blocked_triad',members=mm)]+[event(i+2,'string_contact',**m) for i,m in enumerate(mm)]
   else:events=[event(1,'voicing_formation',members=mm)]
 return events,table,unknown

def convert(r,text,pdftext,page,mono=None):
 unknown=[];impl={'kind':'source_ordered_practice','events':[],'instructions':[]}
 level=r['level'];cp=r.get('printed_components') or [];is_table='-t' in r['source_identity'] and bool(cp)
 if is_table:
  events,table,unknown=triad_table(r,text,page);impl['events']=events;impl['table_task']=table
  if not events:impl['kind']='manual_table_curriculum_task';impl['task']={'label':r['printed_label'],'ordered_fields':cp,'instructions':text,'result':None}
 else:
  score=mono or text
  if (not re.search(r'^\s*[EADGBe]\|',score,re.M) or not re.search(r'^Nte\|',score,re.M)) and re.search(r'^\s*[EADGBe]\|',text,re.M) and re.search(r'^Nte\|',text,re.M):score=text
  events,problems,grids=tab_events(score)
  if events:
   if r['level']==59 and '1 blocked + 6 single notes' in text and len(events)==6:
    mm=[{k:e[k] for k in ['string','fret','printed_note'] if k in e} for e in events[:3]]
    events=[event(1,'blocked_triad',members=mm)]+[{**e,'order':i+2} for i,e in enumerate(events)]
   impl['events']=events;impl['source_grids']=grids;unknown+=problems
  else:
   events,mask=mask_events(text)
   if events:impl['kind']='ordered_rhythm_gesture_grid';impl['events']=events;impl['source_grids']=mask
   else:
    voice=fixed_voicing(text)
    if voice:
     impl['voicings']=[{'members':voice}];count=re.search(r'(?:WORKOUT )?(\d+) blocked attacks',text,re.I);n=int(count[1]) if count else 1
     impl['events']=[event(i+1,'blocked_chord' if count else 'voicing_formation',members=voice) for i in range(n)]
     audit=re.search(r'\+ (\d+)-string low-to-high audit',text,re.I)
     if audit:
      for m in [m for m in voice if not m['muted']]:impl['events'].append(event(len(impl['events'])+1,'string_contact',**m))
    else:
     d=dict(pipe_rows(text));sets=[x.strip() for x in d.get('Set','').split('|') if x.strip()];frts=[x.strip() for x in d.get('Fret','').split('|') if x.strip()]
     if sets and len(sets)==len(frts) and all(re.fullmatch(r'\d+-\d+-\d+',s) for s in frts):
      impl['events']=[event(i+1,'blocked_triad',members=members(sorted(map(int,ss),reverse=True),f.split('-'))) for i,(ss,f) in enumerate(zip(sets,frts))]
     elif d.get('Chd'):
      chords=scalar_tokens(d['Chd']);impl['events']=[event(i+1,'symbolic_chord_attack',chord=ch) for i,ch in enumerate(chords)];impl['source_grids']=[{'rows':[{'label':k,'literal':v} for k,v in pipe_rows(text)]}]
      unknown.append({'field':'chord members/timing','reason':'Ordered printed chord symbols retained; source voicing/time alignment still needs exact family-specific reconstruction. No generic chord shape or beat spacing substituted.'})
     else:
      plain=[s for s in text.splitlines() if s.strip() and not re.match(r'^(Guitar Exercises|Scale Exercises|Standard tuning|Major and minor triads)',s)]
      impl['kind']='manual_curriculum_task';impl['task']={'label':r['printed_label'],'source_components':cp,'result':None};impl['ordered_steps']=[{'order':i+1,'instruction':s} for i,s in enumerate(plain)];impl['automated_assessment']=False
      # Pure foundations, audits, selection and written instructions are legitimate manual tasks.
      # A fixed-score exercise not reconstructed is explicitly partial, not a ready label-only task.
      if '-card' in r['source_identity'] and (re.search(r'\b(?:Nte|Frt|Cnt|Snd|Chd|TAB)\b|\d+ (?:attacks|tones|notes)',text) or not plain):unknown.append({'field':'ordered contact reconstruction','reason':'Literal source card is retained as ordered instructions, but its fixed score/attack representation is not yet reconstructed. This unit is partial, not playback-ready.'})
  # Strip score rows from manual instructions but preserve card-local printed operations.
  impl['instructions']=[s for s in text.splitlines() if s.strip() and not re.match(r'^\s*[A-Za-z][A-Za-z0-9 ]{0,10}\|',s)]
 concrete=pattern_contract(r,text)
 if concrete:
  impl['events']=concrete;impl['kind']='ordered_triad_contacts';unknown=[]
 additional,other_unknown=additional_patterns(r,text,page)
 if additional:
  impl['events']=additional;impl['kind']='ordered_chord_or_shell_contacts';unknown=other_unknown
 finished,final_unknown=finish_patterns(r,text,page,mono)
 if finished:
  impl['events']=finished;impl['kind']='ordered_source_contacts';unknown=final_unknown
 impl=manual_contract(impl,r)
 # Exact relative clocks only where the governing source says a unique division.
 header=' '.join(page.splitlines()[:5]).lower();division=None
 if 'even eighth' in header or 'eight eighth' in header:division=Fraction(1,2)
 elif 'even quarter' in header or 'four even quarter' in header:division=Fraction(1)
 if level==61 and '/modulej/' in r['source_identity'] and 'Pass 1 uses quarter notes' in page:division=Fraction(1)
 # These exact primary passes state quarter notes; optional later variation is
 # retained separately in source tasks, never substituted into the primary grid.
 quarter_pages={61:{10,11,17,18,19},64:{13,14,15,16},65:{12,15,17},66:{16,17,18},67:{14,15,19},68:{11,12,16,17},69:{11,12,13,15,16},70:{17,18},71:{13,14,18,19},72:{13,14,17,18}}
 physical=r['pdf_locator']['physical_pages'][0] if r.get('pdf_locator') else None
 if physical in quarter_pages.get(level,set()) and re.search(r'quarter[ -]note|four quarter notes|as quarter notes',page,re.I):division=Fraction(1)
 if division and impl['events'] and all(e['kind'] in ['note_contact','chord_contact','unresolved_note_contact'] for e in impl['events']):
  for i,e in enumerate(impl['events']):e['onset_q']=qpair(i*division);e['duration_q']=qpair(division)
  if level==61 and 'hold the final target for two beats' in header:impl['events'][-1]['duration_q']=[2,1]
 if r.get('app_status')=='source_ambiguous' or r.get('gap_class')=='source_ambiguity' or not r.get('proposed_package_key'):
  unknown.append({'field':'source_ambiguity','reason':'Explicit inventory source ambiguity: no official child or corrected source interpretation is invented.','source_discrepancy':r.get('source_discrepancy')})
 return impl,unknown,{'fixed_bpm':None,'relative_clock':'explicit governing even-note rule' if division else 'printed order/gesture grid; onset and duration remain null unless locally explicit','acoustic_gate':None,'printed_context':page.splitlines()[:5]}

def pattern_contract(r,text):
 """Return complete literal triad/pattern contacts when the operands are printed."""
 events=[];d=dict(pipe_rows(text));ss=re.search(r'\b([EADGBe](?:-[EADGBe]){2,5})\b',text);strings=[STRINGS[s] for s in ss[1].split('-')] if ss else None
 if strings and 'MAJ' in d and 'MIN' in d:
  fr1=re.search(r'\d+-\d+-\d+',d['MAJ']);fr2=re.search(r'\d+-\d+-\d+',d['MIN'])
  if fr1 and fr2:
   for i in range(8):events.append(event(i+1,'blocked_triad',quality='major' if i%2==0 else 'minor',members=members(strings,(fr1[0] if i%2==0 else fr2[0]).split('-'))))
 elif strings and 'Chd' in d and ('Fret' in d or 'Frt' in d):
  cs=[s.strip() for s in d['Chd'].split('|') if s.strip()] if ' |' in d['Chd'] or '| ' in d['Chd'] else scalar_tokens(d['Chd']);fs=re.findall(r'\d+-\d+-\d+',d.get('Fret',d.get('Frt','')))
  if len(cs)==len(fs) and all(re.fullmatch(r'\d+-\d+-\d+',s) for s in fs):
   repeat=4 if 'repeated four times' in text else 1
   for _ in range(repeat):
    for ch,fr in zip(cs,fs):
     mm=members(strings,fr.split('-'));events.append(event(len(events)+1,'blocked_triad',chord=ch,members=mm))
     if 'B-L-M-H' in text or 'BLOCK+ARP' in text:
      for m in mm:events.append(event(len(events)+1,'string_contact',chord=ch,**m))
 elif strings:
  fr=re.search(r'(?:Frets?|Fret)\s+(\d+-\d+-\d+)',text)
  if fr:
   mm=members(strings,fr[1].split('-'));pattern=None
   if 'BLOCK x8' in text:pattern=['BLOCK']*8
   elif re.search(r'^Play ',text,re.M):pattern=re.split(r'[|\s-]+',re.search(r'^Play (.+)',text,re.M)[1].strip())
   else:
    for line in text.splitlines():
     if re.fullmatch(r'(?:BLOCK|CHORD|mute|[EADGBe]|[ |\-])+',line.strip()) and ('|' in line or 'mute' in line):pattern=re.split(r'[|\s-]+',line.strip());break
   if pattern:
    for tok in [x for x in pattern if x]:
     if tok in ['BLOCK','CHORD']:events.append(event(len(events)+1,'blocked_triad',members=mm))
     elif tok=='mute':events.append(event(len(events)+1,'muted_contact',members=mm))
     elif tok in STRINGS and STRINGS[tok] in strings:events.append(event(len(events)+1,'string_contact',**mm[strings.index(STRINGS[tok])]))
 # A CAGED multi-block capstone uses local string-set headings for each block.
 if not events and r['level']==54 and '/modulej/' in r['source_identity']:
  for chunk in re.split(r'(?=Bars \d+-\d+ -)',text)[1:]:
   found=pattern_contract({**r,'source_identity':'local-block'},chunk)
   for e in found:e['order']=len(events)+1;events.append(e)
 # A capstone page can contain four horizontally aligned bar cards, across multiple pages.
 if not events and 'Bar 1:' in text and 'Fret|' in text:
  ls=text.splitlines()
  for i,line in enumerate(ls):
   bars=re.findall(r'Bar (\d+): ([A-G][#bm0-9]*)',line)
   if not bars:continue
   block='\n'.join(ls[i+1:i+7]);set_names=re.findall(r'\b([EADGBe](?:-[EADGBe]){2})\b',ls[i+1]);frets=re.findall(r'Fret\|([\d-]+)\|',block)
   if len(bars)==len(set_names)==len(frets):
    for (bar,ch),ss,fr in zip(bars,set_names,frets):
     mm=members([STRINGS[x] for x in ss.split('-')],fr.split('-'));events.append(event(len(events)+1,'blocked_triad',bar=int(bar),chord=ch,members=mm))
     for m in mm:events.append(event(len(events)+1,'string_contact',bar=int(bar),chord=ch,**m))
 return events

def additional_patterns(r,text,page):
 events=[];unknown=[];level=r['level'];d=dict(pipe_rows(text));label=r['printed_label']
 # CAGED fragment rows have three independent, explicitly printed triad operands.
 if level==54 and '/modulec/' in r['source_identity']:
  for inv,ss,fr in re.findall(r'(RP|1st|2nd) ([EADGBe](?:-[EADGBe]){2}) (\d+-\d+-\d+)',text):
   mm=members([STRINGS[x] for x in ss.split('-')],fr.split('-'));events.append(event(len(events)+1,'blocked_triad',inversion=inv,members=mm))
   for m in mm:events.append(event(len(events)+1,'string_contact',**m))
 elif level==54 and '/moduleg/' in r['source_identity']:
  ss=re.search(r'^([EADGBe](?:-[EADGBe]){3})$',text,re.M);fr=d.get('Frt')
  if ss and fr:
   mm=members([STRINGS[x] for x in ss[1].split('-')],scalar_tokens(fr));events=[event(i+1,'string_contact',**m) for i,m in enumerate(mm)]
 elif level in [55,56] and d.get('Chd') and ('4 downstrokes per bar' in text or 'four quarter-note' in text.lower()):
  # Preserve exact chronological chord grid even when the player's voicing is intentionally open.
  for line in text.splitlines():
   if not line.startswith('Chd|'):continue
   for segment in re.split(r'Chd\|',line)[1:]:
    chords=[x.strip() for x in segment.split('|') if re.fullmatch(r'[A-G][#b]?(?:m|dim|7|maj7|m7|m7b5)?',x.strip())]
    for ch in chords:
     for b in range(4):i=len(events);events.append(event(i+1,'chord_attack',chord=ch,pick='D',members=None,onset_q=[i,1],duration_q=[1,1]))
  unknown=[{'field':'chord members/fingering','reason':'Source names open/barre/triad or alternative dominant voicing choices, without a unique complete numeric fingering for this progression. All ordered quarter-note chord attacks and printed choice instructions are retained; a fixed playback voicing requires a reviewed authored choice.'}]
 elif level==57 and 'quality ladder' in label.lower():
  shapes=[]
  for line in text.splitlines():
   m=re.fullmatch(r'(maj7|7|m7|m7b5) ((?:\d+|x)(?: (?:\d+|x)){5})',line)
   if m:shapes.append((m[1],members([6,5,4,3,2,1],m[2].split())))
  if len(shapes)==7:
   for _ in range(4):
    for quality,mm in shapes:events.append(event(len(events)+1,'chord_attack',quality=quality,members=mm))
 elif level==57 and 'LOWER VOICE' in text:
  main=text.split('LOWER VOICE')[0];rows=dict(pipe_rows(main));chs=scalar_tokens(rows.get('Chd',''));lo=scalar_tokens(rows.get('D',''));hi=scalar_tokens(rows.get('G',''))
  if len(chs)==len(lo)==len(hi):
   for ch,a,b in zip(chs,lo,hi):
    for _ in range(4):events.append(event(len(events)+1,'shell_attack',chord=ch,members=members([4,3],[a,b])))
   for st,vals in [(4,lo),(3,hi)]:
    for fr in vals:events.append(event(len(events)+1,'string_contact',string=st,fret=int(fr)))
   if 'play full' in text.lower():unknown.append({'field':'prelude count','reason':'Printed instruction adds one full iiø attack to the 18 shell/voice-line attacks but caption still says18. Full-quality-check voicing is retained in instructions; count conflict not silently normalized.'})
 elif level==57 and '/modulei/' in r['source_identity']:
  for line in text.splitlines():
   if line.startswith('Bars ') and 'D/G:' in line:
    chs=[x.strip() for x in line.split(':',1)[1].split('D/G:')[0].split('|')];fs=[s.strip() for s in line.split('D/G:')[1].split('|')]
    if len(chs)==len(fs):
     for ch,fr in zip(chs,fs):
      for b in range(4):i=len(events);events.append(event(i+1,'shell_attack',chord=ch,members=members([4,3],fr.split('-')),onset_q=[i,1],duration_q=[1,1]))
 return events,unknown

def finish_patterns(r,text,page,mono):
 events=[];unknown=[];lv=r['level'];label=r['printed_label'];ss=re.search(r'\b([EADGBe](?:-[EADGBe]){2})\b',text)
 strings=[STRINGS[s] for s in ss[1].split('-')] if ss else []
 if lv==53 and re.match(r'F[78]\.',label) and strings:
  d=dict(pipe_rows(text));chs=scalar_tokens(d['Chd']);frets=re.findall(r'\d+-\d+-\d+',d['Fret']);assert len(chs)==len(frets)==4
  for ch,fr in zip(chs,frets):
   mm=members(strings,fr.split('-'));voice=mm[-1] if label.startswith('F7') else mm[0]
   for kind in (['blocked_triad','string_contact'] if label.startswith('F7') else ['string_contact','blocked_triad']):events.append(event(len(events)+1,kind,chord=ch,**({'members':mm} if kind=='blocked_triad' else voice)))
 elif lv==59 and '/moduled/' in r['source_identity']:
  pos=re.findall(r'\b([EADGBe])(\d+)\b',text.splitlines()[0]);ns=scalar_tokens(dict(pipe_rows(text)).get('Nte',''))
  if len(pos)==3 and len(ns)==6:
   mm=members([STRINGS[s] for s,f in pos],[f for s,f in pos]);index=[0,1,2,2,1,0]
   for system,picks in [('ALT','DUDUDU'),('ECO','DDDUUU')]:
    for j,k in enumerate(index):events.append(event(len(events)+1,'string_contact',**mm[k],printed_note=ns[j],pick=picks[j],system=system))
 elif lv==59 and '/modulef/' in r['source_identity'] and strings:
  triples=re.findall(r'(?<![\d-])\d+-\d+-\d+(?![\d-])',text)
  if len(triples)>=3:
   for fr in triples[:3]:
    mm=members(strings,fr.split('-'))
    for j,k in enumerate([0,1,2,2,1,0]):events.append(event(len(events)+1,'string_contact',**mm[k],pick='D' if j%2==0 else 'U'))
 elif lv==59 and '/modulej/' in r['source_identity'] and strings:
  triples=re.findall(r'(?<![\d-])\d+-\d+-\d+(?![\d-])',text)
  if len(triples)>=4:
   for fr in triples[:4]:
    mm=members(strings,fr.split('-'));events.append(event(len(events)+1,'blocked_triad',members=mm))
    for m in mm:events.append(event(len(events)+1,'string_contact',**m))
 elif lv==60 and '/moduled/' in r['source_identity']:
  m=re.search(r'([EA])-root family - frets (\d+-\d+-\d+-\d+)',label)
  if m:
   mm=members([6,5,4,3] if m[1]=='E' else [5,4,3,2],m[2].split('-'))
   for system,seq,picks in [('ALT',[0,1,2,3,3,2,1,0],'DUDUDUDU'),('ECO',[0,1,2,3,3,2,1,0],'DDDDUUUU'),('7-NT',[0,1,2,3,2,1,0]*2,'DUDUDUDUDUDUDU')]:
    for j,k in enumerate(seq):events.append(event(len(events)+1,'string_contact',**mm[k],pick=picks[j],system=system))
 elif lv==66 and '/moduleb/' in r['source_identity']:
  for line in text.splitlines():
   m=re.match(r'^([EADGBe]) ([\d-]+) ([A-G#b-]+) ([\d#b-]+)',line)
   if m:
    frets=m[2].split('-');notes=m[3].split('-');degrees=m[4].split('-');assert len(frets)==len(notes)==len(degrees)==7
    for fr,n,d in zip(frets,notes,degrees):events.append(event(len(events)+1,'string_contact',string=STRINGS[m[1]],fret=int(fr),printed_note=n,degree=d))
 elif lv==70 and '/moduleb/' in r['source_identity']:
  d=dict(pipe_rows(mono or text));deg=d.get('Deg','').replace('|','');finger=d.get('Fng','').replace('|','');bypos={}
  for st in STRINGS:
   for m in re.finditer(r'\d+',d.get(st,'').replace('|','')):bypos[m.start()]={'string':STRINGS[st],'fret':int(m[0])}
  for pos,contact in sorted(bypos.items()):
   gd=re.match(r'[^- ]+',deg[pos:]);f=re.match(r'[^- ]+',finger[pos:]);events.append(event(len(events)+1,'string_contact',**contact,degree=gd[0] if gd else None,finger=f[0] if f else None))
 # Source-authored recovery pairs: preserve pitches even where the player chooses location.
 if not events and re.search(r': [A-G][#b]? -> [A-G][#b]?$',label):
  pair=re.search(r': ([A-G][#b]?) -> ([A-G][#b]?)$',label);poss=re.findall(r'\b([EADGBe])(\d+)\b','\n'.join(text.splitlines()[1:]))
  if len(poss)!=2:
   poss=[(k,m[0]) for k,v in pipe_rows(mono or text) if k in STRINGS for m in re.finditer(r'\d+',v)]
  for i,n in enumerate(pair.groups()):events.append(event(i+1,'recovery_note_contact',printed_note=n,**({'string':STRINGS[poss[i][0]],'fret':int(poss[i][1])} if len(poss)==2 else {'string':None,'fret':None})))
  if len(poss)!=2:unknown.append({'field':'recovery-pair position','reason':'Original recovery prompt specifies two pitches/roles without a fixed string/fret or octave. Retain player-selected position; no fixed realization invented.'})
 if lv==67 and label=='Dominant release':
  events=[event(i+1,'recovery_note_contact',printed_note=n,string=None,fret=None) for i,n in enumerate(['G#','A'])]
  unknown=[{'field':'recovery-pair position','reason':'Source requires G#-A after each cell without a fixed string/fret or octave. Retain player-selected position; no fixed realization invented.'}]
 return events,unknown

def manual_contract(impl,r):
 if not impl.get('events'):
  impl['interaction_contract']={'mode':'offline manual/reference exercise','source_task_kind':r['kind'],'prompt':r['printed_label'],'steps':[x['order'] for x in impl.get('ordered_steps',[])],'response_schema':{'learner_marked_done':{'type':'boolean','default':None},'selected_prompt_or_option':{'type':['string','null'],'default':None},'written_or_spoken_response_note':{'type':['string','null'],'default':None}},'grading':'no automatic assessment, acceptance, mastery or credit','performance_observation':None,'advance':'explicit learner acknowledgment only','design_provenance':'Private producer UI-neutral manual contract; not printed scoring authority or runtime admission.'}
 return impl

def postprocess(records):
 if not records:return
 lv=records[0]['level']
 for r in records:
  impl=r['implementation'];text=impl.get('source_scope',{}).get('selected_source_text','');sid=r['source_identity']
  if lv==60 and '/moduleef/p012-' in sid and re.fullmatch(r'\S+ [EA]-root',r['source_payload']['label']):
   label=r['source_payload']['label'];chord,family=label.split(' ');prefix=chord+' - '+('LOW-E-ROOT' if family=='E-root' else 'A-STRING-ROOT')+' fret '
   found=[x for x in records if x['source_payload']['label'].startswith(prefix)];assert len(found)==1
   src=found[0];events=copy.deepcopy(src['implementation']['events']);d=dict(pipe_rows(text));roles=scalar_tokens(d['Rol']);assert len(events)==len(roles)==8
   acc=d['Acc'].replace('|','');positions=[m.start() for m in re.finditer(r'[^\s-]+',d['Rol'].replace('|',''))]
   for e,role,pos in zip(events,roles,positions):assert e.get('role')==role;e['accent']=acc[pos:pos+1]=='>'
   impl['events']=events;impl['kind']='ordered_guide_tone_accent_contacts';impl['source_links']=[{'source_identity':src['source_identity'],'reason':'Exact chord/root-family mirror and identical eight-role schedule; accent positions read from this local Acc grid.'}];r['unresolved_reasons']=[]
  if lv==58 and '/moduleg/' in sid:
   progression=re.search(r'^Progression: (.+)$',text,re.M);chords=[x.strip() for x in progression[1].split('|') if x.strip()];assert len(chords)==4
   template=copy.deepcopy(impl['events']);assert len(template)==16
   impl['events']=[]
   for bar,ch in enumerate(chords):
    for e in template:
     e=copy.deepcopy(e);e.update(order=len(impl['events'])+1,chord=ch,bar=bar+1,onset_q=[bar*16+e['subdivision_index'],4]);impl['events'].append(e)
   impl['form_contract']={'bars':4,'printed_progression':chords,'pattern_repeats_per_bar':1,'physical_page':impl['source_scope']['locator']['physical_page']}
  if lv==58 and '/modulei/p016-' in sid:
   grids=impl['source_grids'];assert len(grids)==6
   forms=[('INTRO',['G','D','Em','C']),('VERSE A',['G','D','Em','C','G','D','C','D']),('PRE-CHORUS',['Am','C','D','D']),('CHORUS',['G','C','Em','D','G','C','D','D']),('BRIDGE',['Em','C','G','D']),('OUTRO',['G','D','C'])];events=[];bar=0
   for (section,chords),grid in zip(forms,grids):
    source='Cnt|'+grid['Cnt']+'\nHnd|'+grid['Hnd']+'\nSnd|'+grid['Snd'];template,_=mask_events(source);assert len(template)==16
    for ch in chords:
     for e in template:
      e=copy.deepcopy(e);e.update(order=len(events)+1,chord=ch,bar=bar+1,section=section,onset_q=[bar*16+e['subdivision_index'],4]);events.append(e)
     bar+=1
   assert bar==31 and 'FINAL|P~~~|~~~~|~~~~|~~~~|' in text
   final,_=mask_events('Cnt|1e&a|2e&a|3e&a|4e&a|\nHnd|DUDU|DUDU|DUDU|DUDU|\nSnd|P~~~|~~~~|~~~~|~~~~|')
   for e in final:e.update(order=len(events)+1,chord='G',bar=32,section='FINAL G',onset_q=[31*16+e['subdivision_index'],4]);events.append(e)
   assert len(events)==512 and sum(e['kind'] in ['pitched_chord_contact','dead_stroke'] for e in events)==209
   impl['events']=events;impl['form_contract']={'bars':32,'quarter_extent':128,'grid_slots':512,'notated_contacts':209,'source_pages':[16,17,18,19],'final_bar':'One G attack then15 hold slots; no repeated final attacks.'}
  if lv==60 and '/modulej/' in sid and 'capstone:' in r['source_payload']['label']:
   events=[];links=[]
   for line in text.splitlines():
    match=re.match(r'^(\d+)-(\d+) [A-G][#b]? (?:major|minor) (\S+) ([EA]\d+ \| [EA]\d+ \| [EA]\d+ \| [EA]\d+) 16$',line)
    if not match:continue
    chords=match[3].split('-');routes=match[4].split(' | ')
    for ch,route in zip(chords,routes):
     title=ch+' - '+('LOW-E-ROOT' if route[0]=='E' else 'A-STRING-ROOT')+' fret '+route[1:]
     src=next((x for x in records if x['source_payload']['label']==title),None)
     source_events=src['implementation']['events'][:4] if src else None;source_offset=0
     if src is None:
      for candidate in records:
       if not any('/module'+m+'/' in candidate['source_identity'] for m in ['g','h']):continue
       progression=candidate['source_payload']['label'].split(': ',1)[-1].split(' -> ')
       for j,printed_chord in enumerate(progression):
        part=candidate['implementation']['events'][j*8:j*8+4]
        if printed_chord==ch and len(part)==4 and part[0].get('string')==STRINGS[route[0]] and part[0].get('fret')==int(route[1:]):src=candidate;source_events=part;source_offset=j*8;break
       if src:break
     assert src is not None and len(source_events)==4,('CAPSTONE_SOURCE_SHAPE',title)
     links.append({'source_identity':src['source_identity'],'event_orders':[source_offset+1,source_offset+4],'reason':'Exact printed capstone chord and root-family/fret route; four ascending source arpeggio tones, including sharp-root cadence operands.'})
     for e in source_events:
      e=copy.deepcopy(e);e.update(order=len(events)+1,chord=ch,bar=len(events)//4+1,onset_q=[len(events),1],duration_q=[1,1]);events.append(e)
   assert len(events)==64,('CAPSTONE_CARDINALITY',sid,len(events))
   impl['events']=events;impl['kind']='ordered_source_capstone';impl['source_links']=links;impl['passes']=[{'name':'alternate','picking':'D/U alternating across complete sequence'},{'name':'economy','picking':'source ascending adjacent-string motion; reset between arpeggios'},{'name':'guide-tone accents','instruction':'Printed Pass3 quality-specific roles; no invented numeric velocity.'}];r['unresolved_reasons']=[]
  if lv==54 and '/modulei/' in sid:
   form=r['source_payload']['label'][0];d=dict(pipe_rows(text));sm=re.search(r'Strings: ([EADGBe](?:-[EADGBe]){3})',text);scale=next((x for x in records if '/modulef/' in x['source_identity'] and x['source_payload']['label'][0].upper()==form.upper()),None)
   wanted=scalar_tokens(d.get('Nte',''))
   if sm and scale and [e.get('printed_note') for e in scale['implementation']['events'][:8]]==wanted:
    block=members([STRINGS[x] for x in sm[1].split('-')],scalar_tokens(d['BLK']));triad_sets={'C':[5,4,3],'A':[3,2,1],'G':[5,4,3],'E':[4,3,2],'D':[3,2,1]};tri=members(triad_sets[form],scalar_tokens(d['TRI']));events=[event(1,'blocked_chord',members=block)]+[event(i+2,'string_contact',**m) for i,m in enumerate(tri)]
    for e in scale['implementation']['events'][:8]:e=copy.deepcopy(e);e['order']=len(events)+1;events.append(e)
    impl['events']=events;impl['kind']='ordered_synthesis_contacts';impl['source_links']=[{'source_identity':scale['source_identity'],'reason':'Same form local scale; all eight literal printed note names exactly match synthesis Nte row.'}];r['unresolved_reasons']=[]
  if lv==63 and '/moduleg/' in sid:
   src=next((x for x in records if '/modulea/' in x['source_identity'] and x['source_payload']['label']==r['source_payload']['label']),None)
   if src:
    lookup={};ambiguous=False
    for e in src['implementation']['events']:
     note=e.get('printed_note');value={k:e[k] for k in ['string','fret'] if k in e}
     if note in lookup and lookup[note]!=value:ambiguous=True
     lookup[note]=value
    if not ambiguous:
     events=[]
     for block in blocks(impl['source_scope'].get('pdf_monospace_score') or text):
      d=dict(block);ns=scalar_tokens(d.get('Nte',''));roles=scalar_tokens(d.get('Rol',''));picks=scalar_tokens(d.get('Pck',''))
      if not ns:continue
      for i,n in enumerate(ns):events.append(event(len(events)+1,'string_contact',printed_note=n,**lookup[n],pick=picks[i] if i<len(picks) else None,role=roles[i] if i<len(roles) else None))
     if len(events)==28:impl['events']=events;impl['kind']='ordered_picking_system_contacts';impl['source_links']=[{'source_identity':src['source_identity'],'reason':'Exact same printed triad/root-shape label; each printed pitch has one identical source contact.'}];r['unresolved_reasons']=[]
  if lv==57 and '/moduleg/p016-card' in sid:
   num=int(re.search(r'Pass (\d)',r['source_payload']['label'])[1]);chords=['A7']*4+['D7']*2+['A7']*2+['E7','D7','A7','E7'];low={'A7':[5,'x',5,6,'x','x'],'D7':['x',5,'x',5,7,'x'],'E7':['x',7,'x',7,9,'x']};middle={'A7':[11,12],'D7':[10,11],'E7':[12,13]};high={'A7':[14,15],'D7':[13,14],'E7':[15,16]};events=[]
   for bar,ch in enumerate(chords):
    register='low' if num==1 else 'middle' if num==2 else 'high' if num==3 else 'low' if bar<4 else 'middle' if bar<8 else 'high';mm=members([6,5,4,3,2,1],low[ch]) if register=='low' else members([4,3] if register=='middle' else [2,1],(middle if register=='middle' else high)[ch]);mm=[m for m in mm if not m['muted']]
    for k in range(1 if num==1 else 2 if num in [2,3] else 4):
     e=event(len(events)+1,'shell_attack' if num<4 or k==0 else 'source_unspecified_arpeggio_contact',chord=ch,bar=bar+1,register=register,members=mm)
     if num==1:e['onset_q']=[bar*4,1];e['duration_q']=[4,1]
     if num==2:e['onset_q']=[bar*4+1+k*2,1];e['duration_q']=[2,1]
     events.append(e)
   impl['events']=events;impl['kind']='ordered_blues_shell_contract';impl['source_links']=[{'physical_page':15,'scope':'exact low/middle/high shell map'},{'physical_page':16,'scope':'12-bar form and pass grid'}]
   r['unresolved_reasons']=[] if num<=2 else [{'field':'source performance pattern','reason':'Source says shuffle pair on beats2and4 but caption counts24 contacts across12bars; exact within-pair timing/contact semantics need Curriculum interpretation.'}] if num==3 else [{'field':'source arpeggio order','reason':'Source requests three-note arpeggio over middle/high dyads containing two printed notes. The 48 symbolic attack slots and exact shell members are retained; source does not choose the repeated member or exact picking order.'}]
  # Source-authored alternate starts remain explicit variants of the same child, never new IDs.
  if 'opposite starting stroke' in text.lower() or ('both d-start and u-start' in text.lower()):impl['source_passes']=[{'type':'printed'},{'type':'opposite_start','transform':'swap D and U for source-specified alternate picking; all contacts unchanged','canonical_variant_id':None}]
  r['status']='PARTIAL_SOURCE_UNRESOLVED' if r['unresolved_reasons'] else 'SOURCE_SUPPORTED_IMPLEMENTED'
