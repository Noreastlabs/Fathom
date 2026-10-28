"""Source conversion extensions, explicit ordered data and non-playback contracts."""
import copy,re
STRINGS={'E':6,'A':5,'D':4,'G':3,'B':2,'e':1}
def event(i,kind,**kw):return {'order':i,'kind':kind,'onset_q':None,'duration_q':None,**kw}
def qpair(v):
 from fractions import Fraction
 f=Fraction(v);return [f.numerator,f.denominator]
def scalar_tokens(s):return re.findall(r'[^|\s-]+',s)
def pipe_rows(text):
 result=[]
 for line in text.splitlines():
  m=re.match(r'^\s*([A-Za-z][A-Za-z0-9 ]{0,10})\|(.+)',line)
  if m:result.append((m[1].strip(),m[2]))
 return result

def inline_shapes(lines):
 out={}
 for i,line in enumerate(lines):
  m=re.match(r'([^:]+): frets ([^|]+)\| fingers ([^|]+)',line)
  if not m:continue
  frets=m[2].split();fingers=m[3].split();
  if len(frets)!=6 or len(fingers)!=6:continue
  family='A' if 'A-SHAPE' in '\n'.join(lines[max(0,i-35):i]).upper() and all(x.lower()=='x' for x in frets[:1]) else 'E'
  notes=[]
  if i+2<len(lines) and lines[i+2].startswith('Notes:'):notes=lines[i+2].split(':',1)[1].split()
  data={'strings':[6,5,4,3,2,1],'frets':[None if f.lower()=='x' else int(f) for f in frets],'muted':[f.lower()=='x' for f in frets],'fingers':fingers,'printed_notes':notes,'txt_line':i+1}
  out[m[1]]=data;out[(family,m[1])]=data
 return out

def fifty(r,text,lines,pages):
 parent=r['parent_path'][-1];label=r['printed_label'];unknown=[];shapes=inline_shapes(lines);page='\n'.join(pages[i-1] for i in r['pdf_locator']['physical_pages'])
 impl={'kind':'ordered_chord_practice','events':[],'instructions':text.splitlines(),'chord_shapes':{}}
 if 'MODULE A' in parent:
  pair=label.split(':')[0];steps=[]
  for n in range(8):
   for count,job in enumerate(['hold current shape','release pressure preserving anchors','move guide and remaining fingers','land and inspect new shape']):steps.append({'order':len(steps)+1,'landing':n+1,'count':count+1,'direction':'forward' if n%2==0 else 'reverse','instruction':job})
  impl={'kind':'silent_transition_task','events':[],'ordered_steps':steps,'pair':pair,'printed_landings':8,'passes':['eyes open','eyes on destination only','eyes closed after first chord formed'],'instructions':[label],'sound_generation':False}
 elif r['kind']=='timed_assessment':
  impl={'kind':'manual_assessment','events':[],'task':{'pair':label,'windows':[{'division':'quarter','duration_seconds':60},{'division':'anticipated','duration_seconds':60},{'division':'half-beat burst','duration_seconds':None,'not_endurance_test':True}],'criteria':['both chord qualities correct','proper bass string','steady beat'],'stop':'quality declines','result':None},'automated_assessment':False}
 elif r['kind']=='assessment':impl={'kind':'manual_checklist','events':[],'tasks':[{'order':i+1,'instruction':s.lstrip('- '),'completed':None} for i,s in enumerate(text.splitlines()) if s.startswith('- ')]}
 elif r['kind']=='performance_challenge' and not pipe_rows(text):
  impl={'kind':'manual_performance_challenge','events':[],'task':{'instruction':label,'source_page_instructions':page,'result':None},'automated_assessment':False}
 else:
  if 'MODULE H' in parent:
   m=re.search(r'Atk\|([^|]+)',text);assert m
   rhythm=scalar_tokens(m[1]);assert len(rhythm)==4
   for ch in ['Am','C','G','Em']:
    for token in rhythm:
     e=event(len(impl['events'])+1,'muted_strum' if token=='x' else 'bass_contact' if token=='B' else 'chord_attack',chord=ch,pick='D' if token=='D' else None)
     if token=='B':
      active=[(st,fr) for st,fr in zip(shapes[ch]['strings'],shapes[ch]['frets']) if fr is not None];e['string'],e['fret']=active[0]
     impl['events'].append(e)
  else:
   blocks=[];block=[]
   for k,v in pipe_rows(text):
    if k=='Cnt' and block:blocks.append(dict(block));block=[]
    block.append((k,v))
   if block:blocks.append(dict(block))
   offset=0
   for b in blocks:
    if 'Chd' not in b:continue
    chordraw=b['Chd'].replace('|','');counter=b.get('Cnt','').replace('|','');stroke=b.get('Str',b.get('Atk','')).replace('|','')
    cpositions=[m.start() for m in re.finditer(r'[^-\s]+',counter)];unit=min([j-i for i,j in zip(cpositions,cpositions[1:])] or [1])
    division=.5 if '&' in counter else 1
    for m in re.finditer(r'[^-\s]+',chordraw):
     ch=m[0];tok=stroke[m.start():].split('-')[0] if len(stroke)>m.start() else None
     e=event(len(impl['events'])+1,'muted_strum' if ch=='MUTE' else 'chord_attack',chord=ch if ch!='MUTE' else label.split()[0],pick=tok if tok in ['D','U'] else None,printed_grid_column=m.start())
     e['onset_q']=qpair(offset+m.start()/unit*division);e['duration_q']=None;impl['events'].append(e)
    offset+=len(cpositions)*division
   if 'MODULE E' in parent:
    impl['passes']=[{'name':'printed','event_orders':list(range(1,len(impl['events'])+1))},{'name':'sustain anticipated chord through beat1; resume beat2','omit_attacks_on_following_bar_beat_one':True,'retain_chord_sustain':True,'source':'Pass 2: let the anticipated chord ring through beat 1 and resume on beat 2.'}]
   if 'MODULE I' in parent:impl['passes']=[{'name':'sustained quarters'},{'name':'clip beat4','release_offset_q':None},{'name':'anticipate bars5 and8','anticipated_onset_before_bar_q':[1,2]}]
   if 'MODULE J' in parent:impl['additional_page_contract']=page
  for i,e in enumerate(impl['events']):
   if 'MODULE H' in parent:e['onset_q']=[i,1];e['duration_q']=[1,1]
   ch=e.get('chord')
   if ch in shapes:impl['chord_shapes'][ch]=shapes[ch]
  if 'Em' in impl['chord_shapes'] and ('G' in impl['chord_shapes'] or 'C' in impl['chord_shapes']):impl['chord_shapes']['Em']=shapes['Em-alt']
  if not impl['events']:raise AssertionError(label)
 return impl,unknown,{'fixed_bpm':None,'metric_authority':'printed count grid; quarter beats and & subdivisions. Manual tests explicitly distinguished. Release instants remain qualitative where source is qualitative.','acoustic_gate':None}

def members(strings,frets,notes=None,fingers=None,degrees=None):
 return [{'string':st,'fret':int(fr) if str(fr).isdigit() else None,'muted':str(fr).lower()=='x',**({'printed_note':notes[i]} if notes and i<len(notes) else {}),**({'finger':fingers[i]} if fingers and i<len(fingers) else {}),**({'degree':degrees[i]} if degrees and i<len(degrees) else {})} for i,(st,fr) in enumerate(zip(strings,frets))]
def field(text,label):
 m=re.search(r'^'+re.escape(label)+r':\s*(.+)',text,re.M);return m[1] if m else ''
def fiftyone(r,text,lines,pages):
 parent=r['parent_path'][-1];label=r['printed_label'];page='\n'.join(pages[i-1] for i in r['pdf_locator']['physical_pages']);unknown=[];shapes=inline_shapes(lines)
 impl={'kind':'ordered_manual_chord_practice','events':[],'instructions':text.splitlines(),'page_contract':page}
 if parent.startswith('MODULE A') and 'Random-root' in label:
  impl={'kind':'manual_random_root_extension','events':[],'task':{'instructions':['Write twelve chromatic root names on cards.','Draw one card, choose E-shape or A-shape, announce major/minor before touching the neck.','Form within four silent counts, no strum and no fret-by-fret search.'],'selected_root':None,'selected_family':None,'selected_quality':None,'result':None},'page_contract':page}
 elif parent.startswith('MODULE A'):
  family='E' if 'E-shape' in label else 'A';roots=['F','G','A','B','C','D','E'] if family=='E' else ['B','C','D','E','F','G','A'];frets=[1,3,5,7,8,10,12] if family=='E' else [2,3,5,7,8,10,12]
  steps=[]
  for root,fr in zip(roots,frets):
   for quality in ['major','minor']:
    for voicing in ['full','upper-four partial' if family=='E' else 'inner-four partial']:steps.append({'order':len(steps)+1,'root':root,'root_fret':fr,'quality':quality,'family':family,'voicing':voicing,'instruction':'form silently within four counts, release and inspect; no strum'})
  impl={'kind':'silent_formation','events':[],'ordered_steps':steps,'sound_generation':False,'page_contract':page}
 elif 'MODULE B' in parent:
  if '-string barre' in label:
   n=int(label[0]);
   for fr in [5,7]:
    for st in range(n,0,-1):impl['events'].append(event(len(impl['events'])+1,'string_contact',string=st,fret=fr,finger=1))
  elif 'Pressure-fade' in label:
   impl={'kind':'manual_pressure_task','events':[],'ordered_steps':[{'order':i+1,'count':i+1,'instruction':j} for i,j in enumerate(['press','fade','first buzz','restore only necessary pressure'])],'task':{'first_fret':5,'first_strings':[2,1],'then':'remaining strings','contact':'pick one selected string on every count','selection':'player selects one test string; fixed playback intentionally absent'},'page_contract':page}
  else:impl={'kind':'manual_release_task','events':[],'ordered_steps':[{'order':i+1,'count':i%4+1,'pressure':'press' if i%2==0 else 'release without lifting','sound':'ring' if i%2==0 else 'mute'} for i in range(8)],'page_contract':page}
 elif ': frets ' in text:
  m=re.match(r'([^:]+): frets ([^|]+)\| fingers ([^|]+)\| spelling (.+)',text);assert m
  frets=m[2].split();notes=field(text,'Notes').split();fingers=m[3].split();impl['voicings']=[{'label':m[1],'members':members([6,5,4,3,2,1],frets,notes,fingers),'spelling':m[4].split()}]
  partial=field(text,'Partial')
  if partial:impl['voicings'].append({'label':'printed partial','members':members([6,5,4,3,2,1],partial.split())})
  impl['ordered_steps']=[{'order':1,'instruction':'form printed voicing silently; use printed full/partial workout and scan rules','source':'page_contract'}]
 elif pipe_rows(text):
  data=dict(pipe_rows(text));chords=scalar_tokens(data.get('Chd',''));strokes=scalar_tokens(data.get('Str',data.get('Atk','')));rootfrets=scalar_tokens(data.get('Fret',''))
  # Shape names containing hyphens are retained raw; root-specific member lookup is exact.
  shapefield=field(text,'Shapes');explicit=shapefield.split(' | ') if shapefield else []
  for i,ch in enumerate(chords):
   family=('A' if parent=='A-SHAPE' or 'A-SHAPE' in label else 'E')
   if explicit and i<len(explicit):family=explicit[i][0]
   if parent in ['MAJOR','MINOR']:family='E' if i%2==0 else 'A'
   sh=shapes.get((family,ch));e=event(i+1,'chord_attack',chord=ch,pick=strokes[i] if i<len(strokes) else None,shape_family=family)
   if sh:e['members']=members(sh['strings'],['x' if f is None else f for f in sh['frets']],sh['printed_notes'],sh['fingers'])
   if rootfrets and i<len(rootfrets):e['root_fret']=int(rootfrets[i])
   impl['events'].append(e)
  if 'MODULE J' in parent:
   # Four displayed chord symbols each stand for one bar; the prose supplies attack pattern.
   expanded=[]
   for e in impl['events']:
    for beat in range(4):
     e2=copy.deepcopy(e);e2['order']=len(expanded)+1;e2['onset_q']=[len(expanded),1];e2['duration_q']=None;expanded.append(e2)
   impl['events']=expanded;impl['passes_from_source']=text.splitlines()[1:2]
 elif 'MODULE K' in parent:
  for line in text.splitlines():
   if line.startswith('Bars '):
    for ch in line.split(':',1)[1].split('|'):
     impl['events'].append(event(len(impl['events'])+1,'bar_chord_contract',chord=ch.strip(),attacks_per_bar=4,division='quarter'))
  impl['shape_path']=[s.split(':',1)[1].strip() for s in text.splitlines() if s.startswith('Shapes:')]
 else:impl={'kind':'manual_checklist','events':[],'tasks':[{'order':i+1,'instruction':s.strip(),'completed':None} for i,s in enumerate(text.split(';')) if s.strip()],'page_contract':page}
 # Complete source-prescribed scans and expand the one-symbol-per-bar shorthand.
 if ': frets ' in text:
  vm=impl['voicings'][0]['members'];active=[m for m in vm if not m['muted']]
  impl['events']=[event(i+1,'string_contact',**m) for i,m in enumerate(active+active[::-1])]
 if impl['events'] and pipe_rows(text):
  data=dict(pipe_rows(text));shape_tokens=re.findall(r'[EA]\d+',data.get('Shp',''))
  if len(shape_tokens)!=len(impl['events']):shape_tokens=[]
  for i,e in enumerate(impl['events']):
   ch=e.get('chord','');family=e.get('shape_family','E');fr=e.get('root_fret')
   if shape_tokens:family=shape_tokens[i][0];fr=int(shape_tokens[i][1:])
   if fr is None and e.get('members'):
    fr=next((m['fret'] for m in e['members'] if m['string']==(6 if family=='E' else 5)),None)
   if fr is not None:
    minor=ch.endswith('m');fs=[fr,fr+2,fr+2,fr if minor else fr+1,fr,fr] if family=='E' else ['x',fr,fr+2,fr+2,fr+1 if minor else fr+2,fr]
    e['members']=members([6,5,4,3,2,1],fs);e['member_authority']='Printed E/A movable-shape formula at printed root fret.'
   if 'MODULE J' in parent and e.get('members'):
    e['members']=[m for m in e['members'] if m['string'] in ([4,3,2,1] if family=='E' else [5,4,3,2])]
    if label.startswith('J4'):
     e['kind']='selected_partial_string_contact';e['string']=None;e['pick']=None
  if any(x in parent for x in ['MODULE H','MODULE I']):
   impl['events']=[{**copy.deepcopy(e),'order':i*4+b+1,'onset_q':[(i*4+b),1],'duration_q':[1,1]} for i,e in enumerate(impl['events']) for b in range(4)]
  elif parent in ['E-SHAPE','A-SHAPE','MAJOR','MINOR']:
   for i,e in enumerate(impl['events']):e['onset_q']=[i,1];e['duration_q']=[1,1]
  if label.startswith('J4'):unknown.append({'field':'events[].string','reason':'Source specifies four active partial-chord strings per bar without an exact picking order; retained symbolic contacts and exact four-string member set, no fixed string sequence invented.'})
 if 'MODULE K' in parent:
  contracts=impl['events'];impl['events']=[];path=[x.strip() for st in impl['shape_path'] for x in st.split('|')]
  for i,e in enumerate(contracts):
   match=re.fullmatch(r'([EA])@(\d+)',path[i]);family,fr=match[1],int(match[2]);minor=e['chord'].endswith('m');fs=[fr,fr+2,fr+2,fr if minor else fr+1,fr,fr] if family=='E' else ['x',fr,fr+2,fr+2,fr+1 if minor else fr+2,fr]
   for b in range(4):impl['events'].append(event(len(impl['events'])+1,'chord_attack',chord=e['chord'],members=members([6,5,4,3,2,1],fs),onset_q=[i*4+b,1],duration_q=[1,1],member_authority='Printed movable-shape formula at printed shape/root fret.'))
 return impl,unknown,{'fixed_bpm':None,'clock':'manual/source divisions; no acoustic duration invented' ,'printed_timing_context':page.splitlines()[:6]}

def fiftytwo(r,text,lines,pages):
 parent=r['parent_path'][-1];label=r['printed_label'];page='\n'.join(pages[i-1] for i in r['pdf_locator']['physical_pages']);impl={'kind':'ordered_manual_triad_practice','events':[],'instructions':text.splitlines(),'page_contract':page};unknown=[]
 if parent=='MODULE A - TRIAD SPELLING, INVERSION ROLES, AND SILENT FORMATION':
  impl={'kind':'silent_formation','events':[],'ordered_steps':[{'order':i*6+j*3+k+1,'root':root,'quality':quality,'inversion':inv,'instruction':'form silently before the first attack'} for i,root in enumerate(['C','D','E','F','G','A','B']) for j,quality in enumerate(['major','minor']) for k,inv in enumerate(['root','first','second'])],'sound_generation':False,'page_contract':page}
 elif 'G-B-e frets:' in text:
  frets=field(text,'G-B-e frets').split('-');notes=field(text,'Notes').split();fingers=field(text,'Fingers').split();degrees=field(text,'Degrees').split();m=members([3,2,1],frets,notes,fingers,degrees)
  for _ in range(4):impl['events'].append(event(len(impl['events'])+1,'blocked_triad',members=m))
  for idx in [0,1,2,2,1,0]:impl['events'].append(event(len(impl['events'])+1,'string_contact',**m[idx]))
 elif 'MODULE D' in parent:
  for inv,shape in re.findall(r'([R12])\((\d+-\d+-\d+)\)',text):impl['events'].append(event(len(impl['events'])+1,'blocked_triad',inversion=inv,members=members([3,2,1],shape.split('-'))))
 elif '<->' in text and 'repeated to 8' in text:
  pairs=re.findall(r'([A-G][bm#]*) \((\d+, \d+, \d+)\)',text);assert len(pairs)==2
  for i in range(8):ch,fr=pairs[i%2];impl['events'].append(event(i+1,'blocked_triad',chord=ch,members=members([3,2,1],fr.split(', '))))
 elif any(x in parent for x in ['MODULE G','MODULE H']):
  chords=field(text,'Chords').split(' | ');inv=field(text,'Inversions').split(' | ');frets=field(text,'G-B-e').split(' | ')
  for i in range(16):j=i%4;impl['events'].append(event(i+1,'blocked_triad',chord=chords[j],inversion=inv[j],members=members([3,2,1],frets[j].split('-')),onset_q=[i,1],duration_q=[1,1]))
 elif 'MODULE I' in parent:
  chordblocks=[s.split(':',1)[1].strip().split(' | ') for s in text.splitlines() if s.startswith('Bars ')];shape_blocks=[s.split(':',1)[1].strip().split(' | ') for s in text.splitlines() if s.startswith('Shapes:')]
  for chs,frs in zip(chordblocks,shape_blocks):
   for ch,fr in zip(chs,frs):
    for _ in range(4):i=len(impl['events']);impl['events'].append(event(i+1,'blocked_triad',chord=ch,members=members([3,2,1],fr.split('-')),onset_q=[i,1],duration_q=[1,1]))
 elif 'MODULE F' in parent and re.match('F[1-6]',label):
  n=int(label[1]);shape={1:[5,5,3],2:[5,5,5],3:[4,5,4],4:[4,3,3],5:[7,6,5],6:[5,6,5]}[n];mm=members([3,2,1],shape)
  seq={1:['BLOCK']*8,2:[3,2,1,1,2,3,3,2],3:[1,2,3,3,2,1,1,2],4:[3,1,2,1,3,1,2,1],5:['BLOCK',3,2,1,'BLOCK',1,2,3],6:['BLOCK','mute']*4}[n]
  for i,t in enumerate(seq):
   e=event(i+1,'muted_strum' if t=='mute' else 'blocked_triad' if t=='BLOCK' else 'string_contact')
   if isinstance(t,int):e.update(mm[3-t])
   else:e['members']=mm
   if n==1:e['onset_q']=[i,1];e['duration_q']=[1,1]
   impl['events'].append(e)
  impl['representative_shape_authority']='Exact same workbook natural-root triad family map; G-B-e.'
  impl['extension_contract']='Apply same pattern to one major and one minor triad in every inversion; selected further roots are learner choice.'
 else:
  impl={'kind':'manual_curriculum_task','events':[],'task':{'label':label,'instructions':text if text else page,'selection_contract':'Printed random-root, ear-training, recognition or audit task; no chosen response or achieved result supplied','result':None},'automated_assessment':False}
  response={'completed':{'type':['boolean','null'],'default':None},'notes':{'type':['string','null'],'default':None}}
  root_field={'type':['string','null'],'enum':['C','D','E','F','G','A','B',None],'default':None};quality_field={'type':['string','null'],'enum':['major','minor',None],'default':None};inversion_field={'type':['string','null'],'enum':['root','first','second',None],'default':None}
  if 'inversion-recognition' in r['source_identity']:
   answer={'1-3-5':['major','root'],'3-5-1':['major','first'],'5-1-3':['major','second'],'1-b3-5':['minor','root'],'b3-5-1':['minor','first'],'5-1-b3':['minor','second']}[label]
   response.update(quality=quality_field,inversion=inversion_field,spoken_degree_order={'type':['array','null'],'items':{'type':'string'},'default':None});impl['task']['printed_answer']={'quality':answer[0],'inversion':answer[1],'degree_order':label.split('-')};impl['task']['instructions']='Name the quality and inversion for the printed degree order '+label+'.'
  elif 'random-root' in r['source_identity'] or 'silent-formation-audit' in r['source_identity']:
   response.update(selected_root=root_field,quality=quality_field,inversion=inversion_field,spelling={'type':['array','null'],'items':{'type':'string'},'default':None},gbE_frets={'type':['array','null'],'items':{'type':'integer','minimum':0,'maximum':24},'minItems':3,'maxItems':3,'default':None},bass_role={'type':['string','null'],'enum':['root','third','fifth',None],'default':None})
   if 'random-root' in r['source_identity']:impl['task']['instructions']=label
  elif 'ear-training' in r['source_identity']:
   response.update(selected_root=root_field,quality=quality_field,inversion_order={'type':['array','null'],'items':inversion_field,'default':None},bass_role={'type':['string','null'],'default':None},moving_or_melody_string={'type':['integer','null'],'enum':[3,2,1,None],'default':None},heard_degree_or_quality={'type':['string','null'],'default':None},recording_reference={'type':['string','null'],'default':None})
   prefix=label.split('.',1)[0]+'.';exact=next((s for s in page.splitlines() if s.startswith(prefix)),label);impl['task']['instructions']=exact
  impl['interaction_contract']={'mode':'explicit learner response; offline manual exercise','prompt':impl['task']['instructions'],'response_schema':response,'advance':'explicit submit or acknowledge; never auto-complete','assessment':'No automatic assessment, acceptance, mastery, acoustic verdict or credit. Printed answer/prerequisite remains source content.','design_provenance':'Private producer response schema; not a printed UI or grading implementation.'}
 return impl,unknown,{'fixed_bpm':None,'metric_authority':'explicit quarter-note grids only; manual/non-playback tasks retain instructions','acoustic_gate':None}

def postprocess_fiftytwo(records):
 for r in records:
  label=r['source_payload']['label']
  if label not in ['TOP-VOICE TEST','BASS-VOICE TEST']:continue
  impl=r['implementation'];events=[];links=[];st=1 if label=='TOP-VOICE TEST' else 3
  for number in [2,3,4,5]:
   src=next(x for x in records if re.match('F'+str(number)+r'\.',x['source_payload']['label']))
   for e in src['implementation']['events']:
    e=copy.deepcopy(e);e.update(order=len(events)+1,accent_string=st,accent_instruction='Accent only the printed high e' if st==1 else 'Accent only G; name bass role');events.append(e)
   links.append({'source_identity':src['source_identity'],'reason':'Source p14 explicitly repeats F2–F5 under the top/bass voice test.'})
  assert len(events)==32
  impl['events']=events;impl['kind']='ordered_voice_emphasis_contacts';impl['source_links']=links;impl['task']['instructions']='Repeat F2–F5, accenting only '+('high e.' if st==1 else 'G. Name whether the bass is root, third, or fifth.');impl['interaction_contract']['prompt']=impl['task']['instructions']

def governing_tasks(r,pages):
 """Scoped visible governing text, retained as executable manual instructions, not an acoustic gate."""
 tasks=[]
 if not r.get('pdf_locator'):return tasks
 for pg in r['pdf_locator']['physical_pages']:
  ls=pages[pg-1].splitlines()
  for s in ls[2:5]:
   if s and not re.match(r'^(Str|Frt|Nte|Cnt|Chd|e|B|G|D|A|E)\|',s):tasks.append({'order':len(tasks)+1,'instruction':s,'source':{'physical_page':pg,'location':'module heading, rule and governing paragraph before local cards'},'response':'manual practice instruction; not measured or credited'})
  for s in ls:
   if re.match(r'^(PASS |REPAIR |ADVANCE |LIMIT |RULE |AUDIT |FREEZE |CHANGE |PULSE |MUTING |COUNT |EXERCISE |SCAN |REST |ENDING TEST |TRANSITIONS |SILENT SPELLING )',s):tasks.append({'order':len(tasks)+1,'instruction':s,'source':{'physical_page':pg,'location':'printed named instruction block'},'response':'manual practice instruction; not measured or credited'})
 return tasks
