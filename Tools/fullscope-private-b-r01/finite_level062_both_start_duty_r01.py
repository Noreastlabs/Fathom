"""Explicit fourteen-key producer source-duty correction; controlled effective-row revisions."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,importlib.util,json,re,resource,time
import pdfplumber
ROOT=Path(__file__).resolve().parents[2];NAME='finite-level062-both-start-duty-r01';RES=ROOT/'Results/fullscope-private-b-r01'/NAME;OUT=ROOT/'Build/fullscope-private-b-r01'/NAME
BASE=ROOT/'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json';PREV=ROOT/'Results/fullscope-private-b-r01/finite-level062-inversion-quarter-r01/handoff.json'
QUOTE='Complete all eight diagonal triad fragments and six seventh-chord routes with both pick starts.'
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rh(x):return hashlib.sha256(compact(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def checkpin(r):assert pin(ROOT/r['path'])=={k:r[k] for k in ['path','bytes','sha256']},'INPUT_DRIFT'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(x):return re.sub(r'\s+',' ',x).strip()
def fold_chain(base,previous):
 index=json.loads(base.read_text());prior=json.loads(previous.read_text());effective={};categories={e['package_key']:e['category'] for e in index['children']};seen=set();operations=0;chain=[];h=prior;walk=set()
 for ref in index['packets']:
  checkpin(ref)
  for row in map(json.loads,(ROOT/ref['path']).read_text().splitlines()):assert row['package_key'] not in effective;effective[row['package_key']]=row
 while True:
  digest=rh(h);assert digest not in walk,'CHAIN_CYCLE';walk.add(digest);chain.append(h)
  if 'prior_overlay_handoff' not in h:break
  checkpin(h['prior_overlay_handoff']);h=json.loads((ROOT/h['prior_overlay_handoff']['path']).read_text())
 for h in reversed(chain):
  checkpin(h['overlay']);rows=list(map(json.loads,(ROOT/h['overlay']['path']).read_text().splitlines()));batch=set();assert len(rows)==len(h['changes']),'OVERLAY_COVERAGE'
  for change in h['changes']:
   key=change['package_key'];assert key in effective and key not in batch,'MISSING_OR_DUPLICATE_BATCH_KEY';batch.add(key)
   if key in seen:assert h.get('revision_of_existing_overlay') is True and change.get('replacement_basis')=='previous_effective_record','UNDECLARED_REPEATED_KEY'
   else:assert not h.get('revision_of_existing_overlay',False),'REVISION_REQUIRES_EXISTING_KEY'
   assert rh(effective[key])==change['base_record_sha256'],'PREDECESSOR_EFFECTIVE_HASH';row=rows[change['overlay_line']-1];assert rh(row)==change['overlay_record_sha256'] and row['package_key']==key and row['source_identity']==effective[key]['source_identity'],'REPLACEMENT_IDENTITY_HASH';assert categories[key]==change['old_category'];categories[key]=change['new_category'];effective[key]=row;seen.add(key);operations+=1
 identity=[[entry['package_key'],effective[entry['package_key']]['source_identity']] for entry in index['children']];assert len(effective)==2133 and rh(identity)==index['ordered_identity_sha256'],'IDENTITY_DIGEST'
 return index,prior,effective,categories,seen,operations
def correction(old,source):
 new=copy.deepcopy(old);c=new['implementation']['selected_quarter_contract'];assert c['both_starts_required_by_source'] is False,'EXPECTED_OLD_ERROR';c['both_starts_required_by_source']=True;c['source_rules']['both_start_mastery_duty']=source
 c['unselected_source_obligations'].append({'source_page':20,'instruction':QUOTE,'required_starts':['D','U'],'status':'Required full mastery practice duty; this one explicitly selected start/pass does not complete both starts or the full gate.','completion_observed':False,'full_mastery_gate_txt_lines':source['full_mastery_gate_txt_lines']})
 return new
def verify(old,new,source):assert new==correction(old,source),'EXACT_SOURCE_DUTY_ONLY_CORRECTION'
def main():
 start=datetime.now(timezone.utc).isoformat();timer=time.monotonic();assert sha(BASE)=='3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8';assert sha(PREV)=='5ad629f769616793b2127f460c8a28cd3ebc6cfc26ca07371c27006b618e84d5';assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS';RES.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 index,prior,effective,categories,seen,operations=fold_chain(BASE,PREV);assert len(seen)==operations==292
 entries=[e for e in index['children'] if e['level']==62 and ('/modulea/' in e['source_identity'] or '/moduleb/' in e['source_identity'])];assert len(entries)==14;refs=effective[entries[0]['package_key']]['source_refs']
 for r in refs:checkpin(r)
 txt=(ROOT/refs[0]['path']).read_text().splitlines();context=json.loads((ROOT/refs[2]['path']).read_text());line=[i+1 for i,s in enumerate(txt) if s=='- '+QUOTE];assert len(line)==1;gate_start=txt.index('MASTERY GATE')+1;gate_end=gate_start+7;assert len([s for s in txt[gate_start:gate_end] if s.startswith('- ')])==7
 pattern=re.compile(r'\bboth\b|pick starts?|starting.*stroke|\bD/U\b|alternate picking|pick cycle|opposite.*stroke',re.I);pdf_scan=[];page_hashes=[]
 with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
  assert len(pdf.pages)==20
  for n,p in enumerate(pdf.pages,1):
   text=p.extract_text(x_tolerance=1);assert norm(text)==norm(next(x['text'] for x in context['pdf_pages'] if x['physical_page']==n)),'FULL_BOOK_CONTEXT';page_hashes.append({'physical_page':n,'normalized_text_sha256':rh(norm(text))});pdf_scan.extend({'physical_page':n,'line':i+1,'text':s} for i,s in enumerate(text.splitlines()) if pattern.search(s))
   if n==20:assert QUOTE in norm(text),'EXACT_P20_QUOTE'
 source={'physical_page':20,'heading':'Mastery gate before Level 63','exact_text':QUOTE,'txt_path':refs[0]['path'],'txt_line':line[0],'full_mastery_gate_txt_lines':[gate_start,gate_end],'completion_observed':False,'numeric_assessment':None}
 helper_paths=[('Tools/fullscope-private-b-r01/finite_level062_triad_quarter_r01.py','b61217a335339a9e37910c83231d84e83b8410a51633f2842035f13aa53669cf'),('Tools/fullscope-private-b-r01/finite_level062_seventh_quarter_r01.py',None)];modules=[]
 # Seventh selector is pinned by its immutable manifest, not a newly inferred self-identity.
 frozen_manifest=json.loads((ROOT/'Results/fullscope-private-b-r01/finite-level062-seventh-quarter-r01/artifact-manifest.json').read_text())
 helper_paths[1]=(helper_paths[1][0],next(x['sha256'] for x in frozen_manifest['artifacts'] if x['path']==helper_paths[1][0]))
 for path,digest in helper_paths:
  assert sha(ROOT/path)==digest;spec=importlib.util.spec_from_file_location('select_'+str(len(modules)),ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);modules.append(m)
 rows=[];changes=[];selection_checks=stale_refusals=0
 for e in entries:
  key=e['package_key'];old=effective[key];new=correction(old,source);verify(old,new,source);selector=modules[0 if '/modulea/' in e['source_identity'] else 1].selection;before=old['implementation']['selected_quarter_contract'];after=new['implementation']['selected_quarter_contract']
  for start_stroke in ['D','U']:
   request={'package_key':key,'contract_sha256':rh(after),'start_stroke':start_stroke};actual=selector(after,request);old_actual=selector(before,{**request,'contract_sha256':rh(before)});assert actual['event_picks']==old_actual['event_picks'] and actual['repeat_count']==1 and actual['grants_credit'] is False;selection_checks+=1
   try:selector(after,{**request,'contract_sha256':rh(before)})
   except AssertionError:stale_refusals+=1
   else:raise AssertionError('STALE_PREIMAGE_ACCEPTED')
  rows.append(new);changes.append({'package_key':key,'source_identity':e['source_identity'],'base_record_sha256':rh(old),'previous_effective_record_sha256':rh(old),'original_base_record_sha256':e['record_sha256'],'replacement_basis':'previous_effective_record','overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':categories[key],'new_category':categories[key]});effective[key]=new
 refusals=[]
 for name,mut in [('false_absence',lambda r:r['implementation']['selected_quarter_contract'].update(both_starts_required_by_source=False)),('drop_required_start',lambda r:r['implementation']['selected_quarter_contract']['unselected_source_obligations'][-1].update(required_starts=['D'])),('invent_mastery',lambda r:r['implementation']['selected_quarter_contract']['unselected_source_obligations'][-1].update(completion_observed=True)),('alter_contact',lambda r:r['implementation']['events'][0].update(fret=99)),('alter_clock',lambda r:r['implementation']['events'][0].update(onset_q=[1,4])),('allocate_id',lambda r:r['provenance'].update(canonical_ids_allocated=True))]:
  bad=copy.deepcopy(rows[0]);mut(bad)
  try:assert bad==rows[0],'EXACT_SOURCE_DUTY_ONLY_CORRECTION'
  except AssertionError:refusals.append(name)
  else:raise AssertionError('CORRUPTION_ACCEPTED')
 identity=[[e['package_key'],effective[e['package_key']]['source_identity']] for e in index['children']];assert rh(identity)==index['ordered_identity_sha256'];packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(r)+'\n' for r in rows))
 others=[e for e in index['children'] if e['level']==62 and any('/'+x+'/' in e['source_identity'] for x in ['modulec','moduled','modulee'])]
 scan={'result':'PASS','original_full_book_pdf_pages_verified':20,'exact_mastery_quote':source,'txt_keyword_hits':[{'line':i+1,'text':s} for i,s in enumerate(txt) if pattern.search(s)],'pdf_keyword_hits':pdf_scan,'full_original_pdf_page_hashes':page_hashes,'other_new_L62_contracts_to_audit':[{'key':e['package_key'],'source_identity':e['source_identity'],'current_both_starts_required_by_source':effective[e['package_key']]['implementation']['selected_quarter_contract']['both_starts_required_by_source']} for e in others],'other_scope_disposition':'Page20 specifically imposes both starts on A/B. C/D/E qualitative execution duties are explicit; both-start requirement is not established for these other selected cells. Their inherited false flags will be separately changed to null with explicit source-scope disposition before progression resumes.'}
 save(RES/'full-source-start-duty-scan.json',scan)
 save(RES/'targeted-validation.json',{'result':'PASS','affected_keys':14,'musical_events_and_clocks_unchanged':True,'valid_current_choices':selection_checks,'stale_preimage_refusals':stale_refusals,'content_refusals':refusals,'other_new_L62_audited_scopes':len(others),'final_source_drift':0,'native_gui_broad_qa':'NOT_RUN'})
 for r in refs:checkpin(r)
 handoff={'schema_version':2,'status':'Producer correction of false source-duty absence; exact14 prior effective records superseded; B IN_PROGRESS','start_utc':start,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-timer,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':changes,'revision_of_existing_overlay':True,'changed_existing_overlay_keys':14,'newly_replaced_keys':0,'strict_semantics':'Fold each batch in chain order. Refuse missing/duplicate keys within a batch. Repeated keys across batches require revision_of_existing_overlay=true and replacement_basis=previous_effective_record plus exact previous effective hash. Replace, never append. base_record_sha256 here is the predecessor EFFECTIVE record; original_base_record_sha256 is separate.','effective_categories':prior['effective_categories'],'effective_child_count':2133,'effective_overlay_record_count':292,'unique_replaced_children':292,'total_replacement_operations':306,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[{k:r[k] for k in ['path','bytes','sha256']} for r in refs],'exact_mastery_source':source,'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0}
 save(RES/'handoff.json',handoff)
 # Re-read the new revision through the actual guarded folder before seal.
 _,_,again,cat,used,total=fold_chain(BASE,RES/'handoff.json');assert len(used)==292 and total==306 and all(again[r['package_key']]==r for r in rows),'REVISION_REPLAY'
 print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'quote_locator':source,'unique_replaced_children':292,'total_operations':306}))
if __name__=='__main__':main()
