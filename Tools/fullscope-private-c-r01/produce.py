#!/usr/bin/env python3
"""Private, nonadmitted source payloads. No canonical allocation; one level per invocation."""
from pathlib import Path
import sys,json,re,hashlib,datetime,resource,collections
import pdfplumber
ROOT=Path(__file__).resolve().parents[2]
LANE='fullscope-private-c-r01'
COVERAGE='Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/coverage-matrix.json'
BASE='Results/level-oracle/exercise-completeness-r01/reviewed-handoff-r01/wbs-annex-candidate.jsonl'
PINS={COVERAGE:'7f7ec0d8225a789bd6e738010c78eac9535d31016479e0fba22eb6f249e83c12',BASE:'dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c'}
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def pin(path,expected=None):
 p=ROOT/path;d={'path':path,'bytes':p.stat().st_size,'sha256':digest(p)}
 if expected and d['sha256']!=expected:raise ValueError('PIN_DRIFT '+path)
 return d
def write(p,obj):
 assert not p.exists(),str(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def norm(s):return re.sub(r'\s+','',s)
def extract_region(page,row,ph):
 loc=row['pdf_locator'];box=loc.get('bbox');identity=row['source_identity'];regions=[];table=None
 mt=re.search(r'-t(\d+)-r(\d+)/',identity)
 if mt:
  table=ph['tables'][int(mt[1])-1];rn=int(mt[2]);table={'columns':table['column_labels'],'row_number_excluding_header':rn,'values':table['rows'][rn],'table_bbox':table['bbox']}
  return page.crop(tuple(box)).extract_text(x_tolerance=1,y_tolerance=2) or '',box,table
 if box:
  # The source's enclosing drawn card, not a guessed equal grid.
  shapes=[c for c in page.curves+page.rects if c['x0']<=box[0]+.1 and c['x1']>=box[2]-.1 and c['top']<=box[1]+.1 and c['bottom']>=box[3]-.1 and c['bottom']-c['top']>30]
  if shapes:
   c=min(shapes,key=lambda c:(c['x1']-c['x0'])*(c['bottom']-c['top']));box=[c['x0'],c['top'],c['x1'],c['bottom']]
  else:
   # Keep exact label region; absence of full card boundary is explicit below.
   return page.crop(tuple(box)).extract_text(x_tolerance=1,y_tolerance=2) or '',box,None
 else:box=[0,0,page.width,page.height]
 return page.crop(tuple(box)).extract_text(x_tolerance=1,y_tolerance=2) or '',box,table
STRINGS={'e':1,'B':2,'G':3,'D':4,'A':5,'E':6}
def parse_tabs(text):
 lines=text.splitlines();events=[];blocks=[];problems=[]
 for i,line in enumerate(lines):
  m=re.match(r'^(Nte|V[1-9]N)\s*\|(.*)$',line.strip())
  if not m:continue
  voice=m[1][1] if m[1].startswith('V') else None
  raw=[line];rows=[];roles=None
  for follow in lines[i+1:]:
   f=follow.strip();q=re.match(r'^([A-Za-z0-9]+)\s*\|(.*)$',f)
   if not q:break
   lab,grid=q.groups()
   if lab=='Nte' or re.match(r'V[1-9]N',lab):break
   raw.append(follow)
   if lab in ['Rol','V'+str(voice)+'R']:roles=grid
   string=lab if lab in STRINGS else lab[2:] if voice and lab.startswith('V'+voice) else None
   if string in STRINGS:rows.append((string,grid))
  notes={}
  for bar,seg in enumerate(m[2].split('|'),1):
   for note in re.finditer(r'[A-G](?:#{1,2}|b{1,2})?',seg):notes[(bar,note.start())]=note.group()
  contacts=[]
  for string,grid in rows:
   for bar,seg in enumerate(grid.split('|'),1):
    for hit in re.finditer(r'\d+|[xX]',seg):
     note=notes.get((bar,hit.start()));is_mute=hit.group().lower()=='x'
     contacts.append({'bar_in_block':bar,'printed_column':hit.start(),'string_name':string,'string_number':STRINGS[string],'fret':None if is_mute else int(hit.group()),'printed_note':note,'kind':'muted_contact' if is_mute else 'fretted_contact','voice':voice,'onset_q':None,'duration_q':None,'finger':None})
  contacts.sort(key=lambda e:(e['bar_in_block'],e['printed_column'],e['string_number']))
  if not rows:problems.append({'field':'contacts','reason':'Printed note row has no unambiguously associated string/fret row','source_line':line})
  if contacts and any(c['printed_note'] is None and c['kind']!='muted_contact' for c in contacts):problems.append({'field':'note_to_contact_alignment','reason':'Some literal TAB columns lack exact matching Nte column; retained contact without inferred pitch label','source_line':line})
  blocks.append({'block_ordinal':len(blocks)+1,'voice':voice,'raw_lines':raw,'printed_note_slots':len(notes),'contact_count':len(contacts)})
  for c in contacts:c['block_ordinal']=len(blocks);c['source_order']=len(events)+1;events.append(c)
 return events,blocks,problems

def produce(level):
 started=utc();pins=[pin(k,v) for k,v in PINS.items()];matrix=json.loads((ROOT/COVERAGE).read_text());entry=next(x for x in matrix['levels'] if x['level']==level)
 assert 73<=level<=105
 pins += [pin(entry['hierarchy'],entry['hierarchy_sha256']),pin(entry['exercises'],entry['exercises_sha256'])]
 for s in entry['originals'].values():
  if isinstance(s,dict):pins.append(pin(s['path'],s['sha256']));assert pins[-1]['bytes']==s['bytes']
 hierarchy=json.loads((ROOT/entry['hierarchy']).read_text());rows=[json.loads(s) for s in (ROOT/entry['exercises']).read_text().splitlines()]
 official={};all_assigned=[]
 with (ROOT/BASE).open() as f:
  for line in f:
   r=json.loads(line);l=r['exercise']['level']
   if 73<=l<=105:all_assigned.append([r['package_key'],r['exercise']['source_identity']])
   if l==level:official[r['exercise']['source_identity']]=r
 # Verify exact assignment order against published per-level source order.
 assigned_map={identity:key for key,identity in all_assigned};ordered=[]
 for x in matrix['levels']:
  if 73<=x['level']<=105:
   for line in (ROOT/x['exercises']).open():
    r=json.loads(line)
    if r['source_identity'] in assigned_map:ordered.append([assigned_map[r['source_identity']],r['source_identity']])
 assert len(ordered)==2411 and hashlib.sha256(json.dumps(ordered,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()=='d3519f077d572a44afa7cfb885482a121cd0d3164ce6f0cb1ef365ef2837581b'
 old=[]
 for ref in hierarchy.get('prepared_sources_considered',[]):
  pins.append(pin(ref['path'],ref['sha256']));d=json.loads((ROOT/ref['path']).read_text());old.append((ref,d))
  # Old preparation is reference-only until its exact source pins and field join agree.
  serialized=json.dumps(d)
  assert entry['originals']['txt']['sha256'] in serialized and entry['originals']['pdf']['sha256'] in serialized
 pdfref=entry['originals']['pdf'];txtref=entry['originals']['txt'];txtlines=(ROOT/txtref['path']).read_text().splitlines()
 output=[];ambiguous=[];support_cache={}
 with pdfplumber.open(ROOT/pdfref['path']) as pdf:
  for row in rows:
   identity=row['source_identity'];loc=row['pdf_locator'];pages=loc.get('physical_pages') or [loc['physical_page']];chunks=[];boxes=[];tables=[];contexts=[]
   for pn in pages:
    page=pdf.pages[pn-1];ph=hierarchy['pdf_pages'][pn-1];body,box,table=extract_region(page,row,ph);chunks.append(body);boxes.append({'physical_page':pn,'bbox':box});
    if table:tables.append(table)
    # Page context binds shared timing and instructions separately from unit body.
    if pn not in support_cache:support_cache[pn]={'physical_page':pn,'text':page.extract_text(x_tolerance=1,y_tolerance=2) or ''}
    contexts.append(pn)
   text='\n\n'.join(chunks);events,blocks,problems=parse_tabs(text)
   rawctx='\n'.join(support_cache[p]['text'] for p in pages)
   instructions=[s for s in rawctx.splitlines() if re.search(r'quarter|eighth|sixteenth|tempo|BPM|sustain|rest|silence|pause|beat|barline|duration|hold',s,re.I) and not re.match(r'^(Nte|Rol|[eBGDAE]|V\d)\s*\|',s)]
   # Printed row/task fields remain data; no pitches are guessed from chord symbols.
   task={'type':row['kind'],'label':row['printed_label'],'instructions':[{'source_line_in_region':i+1,'text':s} for i,s in enumerate(text.splitlines()) if s.strip() and not re.match(r'^(Nte|Rol|[eBGDAE]|V\d)\s*\|',s.strip())],'table_fields':tables,'printed_components':row['printed_components']}
   source_refs=[dict(pdfref,locator={'physical_pages':pages,'regions':boxes,'within_page_label':row['printed_label']}),dict(txtref,locator=row.get('txt_locator') or {'scope':'original paired TXT retained; no exact standalone boundary was established by inventory'})]
   txtpayload=None
   if row.get('txt_locator'):
    t=row['txt_locator'];txtpayload={'line_start':t['line_start'],'line_end':t['line_end'],'text':'\n'.join(txtlines[t['line_start']-1:t['line_end']])}
   lineage=[]
   for ref,d in old:
    for rec in d.get('records',[]):
     oldunit=rec.get('source_unit',{});raw=oldunit.get('raw_lines',[])
     nterows=[s.strip() for s in raw if s.strip().startswith('Nte|')]
     if nterows and all(norm(s) in norm(text) for s in nterows):
      # This is a source-row match only, never an accepted whole-unit alias.
      lineage.append({'path':ref['path'],'sha256':ref['sha256'],'source_local_key':rec.get('source_local_key'),'match':'all retained literal Nte rows occur in this exact PDF unit region','scope':'source-contact lineage only; identity/scope and timing not imported'})
   nonplayback=row['kind'] in ['assessment','written','reflection'] or (not events and bool(re.search(r'ear.training|completion log|diagnosis|self.assess|practice progression',row['printed_label'],re.I)))
   unresolved=list(problems)
   if not nonplayback:
    if not events:unresolved.append({'field':'complete_ordered_contacts','reason':'This retained unit is a task/table prescription rather than a fully specified monophonic TAB route; no concrete execution contacts are invented.'})
    else:unresolved.append({'field':'performance_timing','reason':'Exact onset/duration interpretation and articulation must be selected against retained printed timing instructions before native conversion; printed contacts are not silently quantized.'})
    unresolved.append({'field':'BPM_and_fingering','reason':'No fixed BPM or complete finger assignment is asserted from the available unit payload; source instructions and fields are retained verbatim.'})
   if identity not in official:unresolved.append({'field':'source_identity','reason':'Explicit inventory ambiguity has no official child; retained separately without allocating a child.','inventory_discrepancies':row['source_discrepancy']})
   obj={'schema_version':'fathom-private-source-implementation.1','package_key':official.get(identity,{}).get('package_key'),'source_identity':identity,'level':level,'existing_parent_id':row['wbs_parent'],'source_refs':source_refs,'source_payload':{'pdf_region_text':text,'page_context_refs':contexts,'txt_excerpt':txtpayload,'printed_label':row['printed_label'],'parent_path':row['parent_path'],'source_discrepancies':row['source_discrepancy']},'implementation':{'kind':'non_playback_task' if nonplayback else 'ordered_source_contacts' if events else 'structured_source_prescription','events':events,'tab_blocks':blocks,'task':task,'canonical_ids_allocated':False,'playback_admitted':False},'timing_authority':{'printed_instruction_lines':instructions,'fixed_bpm':None,'onset_duration_resolved':False,'source_contacts_are_performance_observations':False},'unresolved_reasons':unresolved,'provenance':{'producer':'private producer C','original_hashes_verified':True,'inventory_ref':entry['exercises'],'inventory_sha256':entry['exercises_sha256'],'matched_prior_conversions':lineage,'canonical_allocation':False},'status':'SOURCE_SUPPORTED_NONPLAYBACK' if nonplayback and not unresolved else 'SOURCE_UNRESOLVED'}
   assert text.strip(),identity
   (output if identity in official else ambiguous).append(obj)
 assert len(output)==entry['pending_proposals'] and {r['source_identity'] for r in output}==set(official)
 dest=ROOT/'Build'/LANE/f'level{level:03d}';dest.mkdir(parents=True,exist_ok=True);packet=dest/'implementation-packet.jsonl';assert not packet.exists();packet.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in output));write(dest/'source-ambiguities.json',ambiguous);write(dest/'page-context.json',{'schema_version':'fathom-private-page-context.1','source':pdfref,'pages':list(support_cache.values())})
 resultdir=ROOT/'Results'/LANE/f'level{level:03d}';resultdir.mkdir(parents=True,exist_ok=True)
 pins.extend(pin(str(p.relative_to(ROOT))) for p in [packet,dest/'source-ambiguities.json',dest/'page-context.json'])
 counts={'attempted':len(output),'source_supported_implemented':sum(r['status']=='SOURCE_SUPPORTED_NONPLAYBACK' for r in output),'partial_source_unresolved':sum(r['status']=='SOURCE_UNRESOLVED' for r in output),'unattempted_in_level':0,'ordered_contacts_retained':sum(len(r['implementation']['events']) for r in output),'explicit_ambiguities_without_children':len(ambiguous),'native_valid':0,'integrated':0,'independently_reviewed':0,'Accepted':0}
 seal={'schema_version':'fathom-private-level-seal.1','started_utc':started,'ended_utc':utc(),'level':level,'counts':counts,'exact_attempted_keys':[r['package_key'] for r in output],'exact_unresolved_keys':[r['package_key'] for r in output if r['status']=='SOURCE_UNRESOLVED'],'exact_unattempted_keys':[],'remaining_partition_keys':[key for key,identity in ordered if int(identity.split('/')[0].replace('level',''))>level],'input_and_output_pins':pins,'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'packet_bytes':packet.stat().st_size,'queue_admission':'not selected; private packet consumes no canonical queue place','producer_elapsed_scope':'this one-level invocation only; excludes tool authoring/intake'}
 write(resultdir/'seal.json',seal)
 handoff=f'# Level {level} private implementation packet\n\nStarted {started}; ended {seal["ended_utc"]}. {len(output)} exact official children attempted; {counts["source_supported_implemented"]} complete non-playback source tasks; {counts["partial_source_unresolved"]} partial/source-unresolved payloads retain {counts["ordered_contacts_retained"]} ordered printed contacts plus complete captured task prescriptions. {len(ambiguous)} explicit source ambiguities are separate, with no invented child. Zero native-valid, integrated, independently reviewed or Accepted new units.\n\nPacket `{packet.relative_to(ROOT)}` SHA256 `{digest(packet)}` ({packet.stat().st_size} bytes). Page-context and ambiguity payloads are separately pinned. Original TXT/PDF hashes and exact locators are in every record; prior conversion matches are source-contact lineage, never a whole-unit readiness claim. Literal source order, bars, voices, notes, strings and frets are retained where supported; timing/BPM/fingering and execution choices remain explicit. Playback, learner performance and credit are not inferred.\n\nPeak process RSS {seal["process_peak_rss_bytes"]} bytes. Remaining assigned keys are explicit in seal.json. Private standard-library integrity checks follow; downstream Curriculum/native/integration/installed review remains pending.\n'
 (resultdir/'handoff.md').write_text(handoff);print(json.dumps({'level':level,'counts':counts,'packet':str(packet.relative_to(ROOT)),'sha256':digest(packet),'packet_bytes':packet.stat().st_size,'handoff_bytes':(resultdir/'handoff.md').stat().st_size,'started_utc':started,'ended_utc':seal['ended_utc'],'peak_rss':seal['process_peak_rss_bytes']}))
if __name__=='__main__':produce(int(sys.argv[1]))
