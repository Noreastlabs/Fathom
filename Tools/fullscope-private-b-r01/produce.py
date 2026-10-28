#!/usr/bin/env python3
"""Private B source-grounded conversion. No IDs/runtime admission or shared writes."""
import argparse,copy,hashlib,json,re,resource,time
from pathlib import Path
from datetime import datetime,timezone
import pdfplumber
import extended
import pdf_conversion
ROOT=Path(__file__).resolve().parents[2]
LANE='fullscope-private-b-r01'
COVER=ROOT/'Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/coverage-matrix.json'
BASE=ROOT/'Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl'
EXPECTED={49:84,50:67,51:87,52:115,53:222,54:93,55:112,56:112,57:127,58:66,59:122,60:104,61:108,62:79,63:97,64:57,65:73,66:38,67:72,68:62,69:67,70:34,71:71,72:64}
def utc():return datetime.now(timezone.utc).isoformat()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):
 p=Path(p);return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
def verified(p,sha,size=None):
 p=ROOT/p;assert digest(p)==sha,(p,'SOURCE_HASH');assert size is None or p.stat().st_size==size;return p

def compact(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def tokens(s):return re.findall(r'[^|\s-]+',s)
def grid(text,name):
 m=re.search(r'^'+re.escape(name)+r'\|([^\n]+)',text,re.M);return tokens(m.group(1)) if m else []
def ev(i,kind,**kw):return {'order':i,'kind':kind,'onset_q':None,'duration_q':None,**kw}
def timed(events,q):
 for i,e in enumerate(events): e['onset_q']=[i*q,1];e['duration_q']=[q,1]
 return events

def level49(r,text,lines,pages,shapes):
 parent=r['parent_path'][-1];label=r['printed_label'];out={'kind':'ordered_manual_practice','events':[]};unresolved=[]
 sourcepage='\n'.join(pages[n-1] for n in r['pdf_locator']['physical_pages'])
 out['instructions']=[s for s in text.splitlines() if s and not set(s)=={'='}]
 out['chord_shapes']={}
 if 'MODULE A1' in parent:
  m=re.search(r'(index|middle|ring) finger: ([EADGBe])(\d+) \(([^)]+)\)',label);assert m
  for i,job in enumerate(['normal clean pressure','reduce pressure until buzz','restore minimum clean pressure','release pressure without lifting']):out['events'].append(ev(i+1,'string_contact',string={'E':6,'A':5,'D':4,'G':3,'B':2,'e':1}[m[2]],fret=int(m[3]),printed_note=m[4],finger={'index':1,'middle':2,'ring':3}[m[1]],pressure_instruction=job))
 elif 'MODULE A2' in parent or 'MODULE H' in parent:
  chord=label.split(':')[0];v=label.split(':')[1].split('|')[0].split();v=v[:6] if 'A2' in parent else v
  if 'A2' in parent:v=v+v[::-1]
  assert len(v)==12
  strings=[6,5,4,3,2,1,1,2,3,4,5,6]
  for i,(st,f) in enumerate(zip(strings,v)):out['events'].append(ev(i+1,'muted_string_test' if f.upper()=='X' else 'string_contact',string=st,fret=None if f.upper()=='X' else int(f),pick=('D' if i<6 else 'U') if 'A2' in parent else None,chord=chord))
  out['chord_shapes'][chord]=shapes[chord]
 elif 'MODULE B' in parent or 'MODULE C' in parent:
  chord=label.split()[0].rstrip(':');v=grid(text,'Val');f=grid(text,'Fng');n=grid(text,'Nte');a=grid(text,'Atk');assert len(v)==len(f)==len(n)==6 and len(a)==12
  out['chord_shapes'][chord]=shapes[chord]
  for i,t in enumerate(a):
   if t.isdigit():
    st=int(t);j=6-st;out['events'].append(ev(i+1,'muted_string_test' if v[j].upper()=='X' else 'string_contact',string=st,fret=None if v[j].upper()=='X' else int(v[j]),finger=f[j],printed_note=n[j],chord=chord))
   else:out['events'].append(ev(i+1,'muted_strum' if t=='x' else 'chord_attack',chord=chord,pick='D' if t=='D' else None,source_token=t))
 elif any('MODULE '+x in parent for x in ['D','E','F','G','I']):
  chords=grid(text,'Chd');strokes=grid(text,'Str');assert chords and len(chords)==len(strokes)
  q=4 if any('MODULE '+x in parent for x in ['D','G']) else 2 if 'MODULE E' in parent else 1
  for i,(ch,st) in enumerate(zip(chords,strokes)):out['events'].append(ev(i+1,'chord_attack',chord=ch,pick=st))
  timed(out['events'],q);out['metric_end_q']=[len(chords)*q,1]
  for ch in set(chords):out['chord_shapes'][ch]=copy.deepcopy(shapes[ch])
  if ('Em' in chords and 'G' in chords):
   out['chord_shapes']['Em']['fingers']=['O','1','2','O','O','O'];out['chord_shapes']['Em']['finger_authority']='Printed transition instruction: alternate Em uses 1 on A2 and 2 on D2.'
 elif 'MODULE J' in parent:
  passno=int(re.search(r'Pass (\d)',label)[1]);chords=['Am','C','G','Em']
  for i in range(16):
   ch=chords[i//4];kind='muted_strum' if passno==3 and i%2 else 'chord_attack';e=ev(i+1,kind,chord=ch,pick='D' if kind=='chord_attack' else None)
   if passno==2:e['pressure_release_offset_q']=[1,2]
   if passno==4:e.update(kind='learner_selected_string_contact',string=None,choice_index=i%4+1);e['pick']=None
   out['events'].append(e)
  timed(out['events'],1);out['metric_end_q']=[16,1]
  for ch in chords:out['chord_shapes'][ch]=shapes[ch]
  if passno==4:
   out['choice_contract']={'select':4,'from':'active strings of each printed chord','ordering':'stable repeating order','fixed_string_assignment':None}
   unresolved.append({'field':'events[].string/fret','reason':'Source deliberately lets the player choose four active chord strings; fixed playback needs an explicit reviewed authored choice. No choice has been invented.'})
 elif r['kind']=='timed_assessment':
  out={'kind':'manual_timed_assessment','task':{'chord_pair':label.split('-'),'primary_mechanic':{'E-Em':'add/lift finger 1','A-Am':'compact three-finger exchange','D-Dm':'finger 3 remains on B3','C-Am':'B1 and D2 remain planted','Em-G':'alternate Em fingering keeps A2 planted','G-C':'finger 2/3 guide from low E3 to A3','D-A':'finger 1 remains on G2 with printed A fingering','E-A':'move as one relaxed shape; land from bass side'}[label],'primary_mechanic_source':{'physical_page':19,'table':'One-minute change tests','row':label,'column':'Primary mechanic'},'duration_seconds':60,'initial_division':'whole notes','quarter_note_prerequisite':{'clean_whole_note_changes_in_one_minute':20},'count_only':['both chords fully formed','correct bass string struck','no required chord tone muted'],'measured_clean_changes':None,'performance_credit':None,'automated_assessment':False},'instructions':['Choose four pairs.','Use whole-note changes first; quarter-note testing begins only after a clean 20-change whole-note minute.'],'events':[]}
 elif r['kind']=='assessment':out={'kind':'manual_checklist','tasks':[{'order':i+1,'instruction':s[2:],'completed':None} for i,s in enumerate([s for s in text.splitlines() if s.startswith('- ')])],'automated_assessment':False,'events':[]}
 else:raise AssertionError(label)
 tempo=re.search(r'(?:Tempo |at )(\d+)-(\d+) BPM',sourcepage)
 timing={'fixed_bpm':None,'printed_tempo_range_bpm':list(map(int,tempo.groups())) if tempo else None,'onset_duration_authority':'printed note division and ordered attack grid' if any(e.get('onset_q') is not None for e in out['events']) else 'ordered manual task; no numeric onset or duration asserted','acoustic_gate':None,'count_in':None}
 return out,unresolved,timing

def get_shapes(lines):
 shapes={}
 for i,s in enumerate(lines):
  m=re.fullmatch(r'(\S+): frets (.+)',s)
  if m:
   frets=m[2].split();f=lines[i+2].split(':',1)[1].split();notes=lines[i+3].split(':',1)[1].split();assert len(frets)==len(f)==len(notes)==6
   shapes[m[1]]={'strings':[6,5,4,3,2,1],'frets':[None if x.lower()=='x' else int(x) for x in frets],'muted':[x.lower()=='x' for x in frets],'fingers':f,'printed_notes':notes,'txt_lines':[i+1,i+5]}
 return shapes

def produce(level,revision=None):
 start=utc();t0=time.monotonic();assert level in EXPECTED
 verified(COVER.relative_to(ROOT),'7f7ec0d8225a789bd6e738010c78eac9535d31016479e0fba22eb6f249e83c12')
 verified(BASE.relative_to(ROOT),'dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c')
 info=next(x for x in json.loads(COVER.read_text())['levels'] if x['level']==level)
 verified(info['exercises'],info['exercises_sha256']);verified(info['hierarchy'],info['hierarchy_sha256'])
 for ref in [info['originals']['txt'],info['originals']['pdf']]:verified(ref['path'],ref['sha256'],ref['bytes'])
 rows=[json.loads(s) for s in (ROOT/info['exercises']).read_text().splitlines()]
 base={}
 for line in BASE.open():
  row=json.loads(line)
  if row['exercise']['level']==level:base[row['exercise']['source_identity']]=row
 assert len(base)==EXPECTED[level]
 outdir=ROOT/'Build'/LANE/(f'level{level:03d}'+('-'+revision if revision else ''));resdir=ROOT/'Results'/LANE/(f'level{level:03d}'+('-'+revision if revision else ''))
 assert not (resdir/'handoff.json').exists(),'sealed batch cannot be overwritten'
 outdir.mkdir(parents=True,exist_ok=True);resdir.mkdir(parents=True,exist_ok=True)
 lines=(ROOT/info['originals']['txt']['path']).read_text().splitlines()
 with pdfplumber.open(ROOT/info['originals']['pdf']['path']) as doc:
  pages=[p.extract_text() or '' for p in doc.pages]
  contexts={'schema_version':1,'level':level,'originals':info['originals'],'pdf_pages':[{'physical_page':i+1,'text':s} for i,s in enumerate(pages)]}
  save(outdir/'source-context.json',contexts)
  sourcecontext=pin(outdir/'source-context.json')
  shapes=get_shapes(lines) if level==49 else {}
  packets=[];exceptions=[]
  for r in rows:
   loc=r.get('txt_locator');text='\n'.join(lines[loc['line_start']-1:loc['line_end']]) if loc else ''
   if level==49:impl,unknown,timing=level49(r,text,lines,pages,shapes)
   elif level==50:impl,unknown,timing=extended.fifty(r,text,lines,pages)
   elif level==51:impl,unknown,timing=extended.fiftyone(r,text,lines,pages)
   elif level==52:impl,unknown,timing=extended.fiftytwo(r,text,lines,pages)
   else:
    text,pdftext,mono,derived_locator=pdf_conversion.scope(r,rows,doc,lines)
    impl,unknown,timing=pdf_conversion.convert(r,text,pdftext,pages[r['pdf_locator']['physical_pages'][0]-1] if r['pdf_locator'] else '',mono)
    impl['source_scope']={'locator':derived_locator,'pdf_excerpt':pdftext,'selected_source_text':text,'pdf_monospace_score':mono}
   impl['context_tasks']=extended.governing_tasks(r,pages)
   record={'schema_version':1,'package_key':base[r['source_identity']]['package_key'] if r['source_identity'] in base else None,'source_identity':r['source_identity'],'level':level,'existing_parent_id':'2.3.1.2.1','source_refs':[{**info['originals']['txt'],'locator':loc},{**info['originals']['pdf'],'locator':r['pdf_locator']},sourcecontext],'source_payload':{'label':r['printed_label'],'parent_path':r['parent_path'],'txt_excerpt':text,'printed_components':r.get('printed_components',[]),'source_discrepancy':r.get('source_discrepancy')},'implementation':impl,'timing_authority':timing,'unresolved_reasons':unknown,'provenance':{'producer_role':'private producer B; not independent reviewer','inventory':pin(ROOT/info['exercises']),'conversion':'Tools/fullscope-private-b-r01/produce.py','canonical_ids_allocated':False,'native_validated':False,'runtime_admitted':False,'independently_reviewed':False,'accepted':False},'status':'PARTIAL_SOURCE_UNRESOLVED' if unknown else 'SOURCE_SUPPORTED_IMPLEMENTED'}
   (packets if record['package_key'] else exceptions).append(record)
  if level==52:extended.postprocess_fiftytwo(packets)
  if level>=53:pdf_conversion.postprocess(packets)
  (outdir/'conversion.py').write_bytes(Path(__file__).read_bytes())
  (outdir/'extended.py').write_bytes((Path(__file__).parent/'extended.py').read_bytes())
  (outdir/'pdf_conversion.py').write_bytes((Path(__file__).parent/'pdf_conversion.py').read_bytes())
  packet=outdir/'implementation.jsonl';packet.write_text(''.join(compact(x)+'\n' for x in packets))
  exception=outdir/'source-exceptions.jsonl';exception.write_text(''.join(compact(x)+'\n' for x in exceptions))
 ready=sum(x['status']=='SOURCE_SUPPORTED_IMPLEMENTED' for x in packets);partial=len(packets)-ready
 metadata={'schema_version':1,'level':level,'start_utc':start,'end_utc':utc(),'elapsed_seconds':round(time.monotonic()-t0,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'counts':{'source_units':len(rows),'attempted':len(packets),'source_supported_implemented':ready,'partial_source_unresolved':partial,'unattempted':0,'source_ambiguity_reconciliation_records':len(exceptions),'native_valid':0,'integrated':0,'independently_reviewed':0,'accepted':0},'packet':pin(packet),'source_context':sourcecontext,'exceptions':pin(exception),'producer':pin(outdir/'conversion.py'),'inputs':[pin(COVER),pin(BASE),pin(ROOT/info['exercises']),pin(ROOT/info['hierarchy']),info['originals']['txt'],info['originals']['pdf']],'ordered_child_identity_sha256':hashlib.sha256(compact([[x['package_key'],x['source_identity']] for x in packets]).encode()).hexdigest(),'remaining_keys_this_level':[],'unresolved_keys':[x['package_key'] for x in packets if x['unresolved_reasons']],'authority':'Private source representation only; downstream distinct Curriculum review, canonical allocation, native/admission and installed proof required.'}
 save(resdir/'handoff.json',metadata)
 print(compact({'handoff':pin(resdir/'handoff.json'),'counts':metadata['counts'],'packet':metadata['packet'],'elapsed_seconds':metadata['elapsed_seconds'],'peak_rss_bytes':metadata['process_peak_rss_bytes']}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('level',type=int);parser.add_argument('--revision');args=parser.parse_args();produce(args.level,args.revision)
