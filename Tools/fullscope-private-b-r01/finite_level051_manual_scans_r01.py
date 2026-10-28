"""Finite source-directed, untimed manual contracts for 28 full chord scans."""
import copy, hashlib, json, re, resource, time
from pathlib import Path
from datetime import datetime, timezone
import pdfplumber

ROOT=Path(__file__).resolve().parents[2]
RES=ROOT/'Results/fullscope-private-b-r01/finite-level051-manual-scans-r01'
OUT=ROOT/'Build/fullscope-private-b-r01/finite-level051-manual-scans-r01'
BASE=ROOT/'Results/fullscope-private-b-r01/checkpoint-r03/range-index.json'
PREV=ROOT/'Results/fullscope-private-b-r01/finite-level057-reason-r01/handoff.json'
PACKET=ROOT/'Build/fullscope-private-b-r01/level051/implementation.jsonl'
def compact(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def rh(x):return hashlib.sha256(compact(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)}
def checkpin(r):assert pin(ROOT/r['path'])=={k:r[k] for k in ['path','bytes','sha256']},'INPUT_DRIFT'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(s):return re.sub(r'\s+',' ',s).strip()
RULES={
 5:[('place_chord_fingers','Construction order: chord fingers -> index barre -> thumb support -> scan.'),('add_index_barre','Construction order: chord fingers -> index barre -> thumb support -> scan.'),('add_thumb_support','Construction order: chord fingers -> index barre -> thumb support -> scan.')],
 6:[('form_minor_barre','The G string is part of the index barre. Do not let the ring finger touch it.')],
 7:[('form_index_and_ring_barres','Finger 1 barres A through high e. Finger 3 mini-barres D-G-B.'),('clear_high_e_full_shape','For the full version, roll the ring finger so high e remains clear.')],
 8:[('place_three_chord_fingers','Build the three chord fingers first; add only enough index pressure to sound A and high e.'),('add_minimal_index_pressure','Build the three chord fingers first; add only enough index pressure to sound A and high e.')],
}
REGIONS={}
def source_rule(page,literal,pages):
    if norm(literal) in norm(pages[page]):return {'physical_page':page,'exact_text':literal}
    for bbox,text in REGIONS.get(page,[]):
        if norm(literal) in norm(text):return {'physical_page':page,'bbox':bbox,'exact_text':literal}
    raise AssertionError('ORIGINAL_PDF_RULE '+literal)
def response_state(contract,responses):
    assert isinstance(responses,list),'RESPONSE_TYPE'
    assert len(responses)<=len(contract['steps']),'RESPONSE_OVERFLOW'
    terminal=False
    for i,r in enumerate(responses):
        assert isinstance(r,dict) and set(r)=={'step','response'},'RESPONSE_FIELDS'
        assert type(r['step']) is int and r['step']==i+1,'RESPONSE_ORDER'
        assert not terminal,'AFTER_TERMINAL'
        assert r['response'] in ['acknowledged','needs_retry','stopped'],'RESPONSE_VALUE'
        terminal=r['response']!='acknowledged'
    if responses and responses[-1]['response']=='stopped':return 'STOPPED'
    if responses and responses[-1]['response']=='needs_retry':return 'NEEDS_RETRY'
    return 'USER_REPORTED_STEPS_FINISHED' if len(responses)==len(contract['steps']) else 'IN_PROGRESS'
def validate(old,new):
    expected=copy.deepcopy(new);expected['implementation'].pop('manual_execution_contract');expected['implementation']['kind']=old['implementation']['kind']
    assert expected==old,'UNRELATED_MUTATION'
    c=new['implementation']['manual_execution_contract'];events=old['implementation']['events']
    assert c['mode']=='manual_nonplayback' and c['automated_assessment'] is False and c['grants_credit'] is False,'AUTHORITY'
    assert c['clock']=={'onset_q':None,'duration_q':None,'fixed_bpm':None,'acoustic_gate_q':None},'INVENTED_CLOCK'
    assert all(e['onset_q'] is None and e['duration_q'] is None for e in events),'SOURCE_CLOCK'
    picks=[s for s in c['steps'] if s['action']=='pick_printed_string']
    assert [s['event_order'] for s in picks]==list(range(1,len(events)+1)),'CONTACT_COVERAGE'
    assert [s['order'] for s in c['steps']]==list(range(1,len(c['steps'])+1)),'STEP_ORDER'
    for s,e in zip(picks,events):
        assert s['string']==e['string'] and s['fret']==e['fret'] and s['finger']==e['finger'] and s['printed_note']==e['printed_note'],'CONTACT_BINDING'
    assert c['steps'][0]['action']=='name_root' and c['steps'][-1]['action']=='release_pressure','BOUNDARIES'
    family='E' if ':module-c-' in old['source_identity'] else 'A'
    strings=list(range(6 if family=='E' else 5,0,-1))
    assert [e['string'] for e in events]==strings+strings[::-1],'PRINTED_SCAN_ORDER'
    assert c['muted_strings']==([] if family=='E' else [6]),'MUTING'
    assert c['sound_contact_count']==len(events) and c['selected_voicing_index']==0,'FULL_VOICING'
    assert c['family_rules']['rest_after_every_full_barre_cells']==4,'REST_RULE'
    assert c['family_rules']['new_full_barre_cells_since_rest_initial'] is None,'UNKNOWN_HISTORY'
    assert c['response_contract']['meaning']=='User-reported workflow only; not observed playing, correctness, mastery, credit or a saved Attempt.','RESPONSE_MEANING'

def main():
    started=datetime.now(timezone.utc).isoformat();t=time.monotonic()
    for p,h in [(BASE,'3a367221ea2f831c7774720730a9876eb59bb2656766336047270c8e0ae22ce8'),(PREV,'7d3813ffcd19c0cdd8c40261b7698739e29820a9d185e656e66eb8d1fde73470'),(PACKET,'fc77c9f01988c46108e80d50c367ae79e89739d2585f70e00b6ac9d88ca070d6')]:assert sha(p)==h,'FROZEN_PIN'
    assert not (RES/'handoff.json').exists() and not (OUT/'implementation-overlay.jsonl').exists(),'OUTPUT_EXISTS'
    index=json.loads(BASE.read_text());prior=json.loads(PREV.read_text());rr=[json.loads(s) for s in PACKET.read_text().splitlines()]
    selected=[e for e in index['children'] if e['level']==51 and (':module-c-' in e['source_identity'] or ':module-d-' in e['source_identity'])]
    assert len(selected)==28 and all(e['category']=='implementation_or_interpretation_pending' for e in selected),'SCOPE'
    refs=rr[selected[0]['line']-1]['source_refs']
    for r in refs:checkpin(r)
    txt=(ROOT/refs[0]['path']).read_text().splitlines()
    scan_rules={}
    for family,literal in [('E','Scan every chord low-to-high and high-to-low. 168 attacks total.'),('A','Scan every chord A-to-e and e-to-A. 140 attacks total.')]:
        found=[i+1 for i,s in enumerate(txt) if s==literal];assert len(found)==1
        scan_rules[family]={'path':refs[0]['path'],'line':found[0],'exact_text':literal}
    with pdfplumber.open(ROOT/refs[1]['path']) as pdf:
        pages={p:pdf.pages[p-1].extract_text() for p in [1,5,6,7,8]}
        REGIONS[1]=[(box,pdf.pages[0].crop(box).extract_text()) for box in [(40,145,285,200),(545,145,760,200)]]
    context=json.loads((ROOT/refs[2]['path']).read_text())
    for p in pages:assert norm(pages[p])==norm(next(x['text'] for x in context['pdf_pages'] if x['physical_page']==p)),'SOURCE_CONTEXT_DRIFT'
    general={
      'root':source_rule(1,'Name the note before forming the grip.',pages),
      'release':source_rule(1,'Press for the sound, release when silent, and rest before fatigue becomes pain.',pages),
      'rest':source_rule(1,'Rest after every four full-barre cells.',pages),
      'stop':source_rule(1,'Stop for pain, numbness, tingling, or a hand position that cannot relax after release.',pages),
      'pressure':source_rule(1,'Move the index placement before increasing whole-hand pressure.',pages),
      'start':source_rule(1,'Start near frets 5-7, where the fret spacing and string tension are manageable. Add the fret-1 F chord last.',pages),
    }
    rows=[];delta=[];oldrows=[];contacttotal=0
    for e in selected:
        old=rr[e['line']-1];assert rh(old)==e['record_sha256'],'BASE_RECORD'
        assert old['source_refs']==refs or all({k:r[k] for k in ['path','bytes','sha256']}=={k:base[k] for k in ['path','bytes','sha256']} for r,base in zip(old['source_refs'],refs)),'SOURCE_INPUT'
        page=old['source_refs'][1]['locator']['physical_pages'][0];assert page in RULES
        family='E' if ':module-c-' in old['source_identity'] else 'A';ev=old['implementation']['events'];voicing=old['implementation']['voicings'][0]
        expected=[m for m in voicing['members'] if not m['muted']];assert len(expected)==(6 if family=='E' else 5)
        actual=[{k:v for k,v in x.items() if k not in ['order','kind','onset_q','duration_q']} for x in ev]
        assert actual==expected+expected[::-1],'VOICING_SCAN_BINDING'
        source_line=old['source_refs'][0]['locator']['line_start'];literal=txt[source_line-1]
        assert old['source_payload']['label'] in literal or literal in old['source_payload']['label'],'TXT_CARD_LOCATOR'
        # The printed label includes exact frets/fingers/spelling; parse them independently.
        mm=re.search(r'frets (.*?) \| fingers (.*?) \| spelling (.*)$',literal);assert mm,'TXT_FULL_SHAPE'
        frets=mm[1].split();fingers=mm[2].split();assert len(frets)==len(fingers)==6
        for m,f,fi in zip(voicing['members'],frets,fingers):
            assert m['fret']==(None if f=='x' else int(f)) and m['muted']==(f=='x') and m['finger']==fi,'PRINTED_VOICING'
        assert voicing['spelling']==mm[3].split(),'PRINTED_SPELLING'
        def step(action,**fields):return {'order':len(steps)+1,'action':action,**fields}
        steps=[];steps.append(step('name_root',root=voicing['label'].removesuffix('m'),source=general['root']))
        for action,literal_rule in RULES[page]:steps.append(step(action,selected_voicing_index=0,source=source_rule(page,literal_rule,pages)))
        if family=='A':steps.append(step('mute_low_e',string=6,source=source_rule(7,'Low E remains muted.',pages)))
        for event in ev:
            steps.append(step('pick_printed_string',event_order=event['order'],string=event['string'],fret=event['fret'],finger=event['finger'],printed_note=event['printed_note'],source=scan_rules[family]))
        release=source_rule(8,'After the scan, release the index and thumb completely before moving to the next root.',pages) if page==8 else general['release']
        steps.append(step('release_pressure',source=release))
        contract={'schema':'fathom.private-manual-chord-scan.v1','mode':'manual_nonplayback','selected_voicing_index':0,'selected_scope':'Printed full chord scan; partial alternative is retained as reference, not substituted or sounded in this scan.','sound_contact_count':len(ev),'clock':{'onset_q':None,'duration_q':None,'fixed_bpm':None,'acoustic_gate_q':None},'muted_strings':[] if family=='E' else [6],'steps':steps,'family_rules':{'rest_after_every_full_barre_cells':4,'new_full_barre_cells_since_rest_initial':None,'rest_source':general['rest'],'start_and_fret1_order_source':general['start'],'stop_source':general['stop'],'pressure_source':general['pressure'],'dead_G_correction':source_rule(6,'If G string is dead, move the index or ring finger. Do not add pressure to the entire grip.',pages) if page==6 else None},'response_contract':{'author':'B producer-authored manual interaction schema; musical actions are separately source-located.','fields':{'step':'integer, 1-based contiguous prefix of steps','response':['acknowledged','needs_retry','stopped']},'additional_fields':False,'initial_responses':[],'advance':'Only explicit acknowledged advances to the next step. A terminal needs_retry or stopped ends this response sequence. Restart requires a fresh explicit sequence; no automatic retry.','completion':'Only all ordered steps acknowledged yields USER_REPORTED_STEPS_FINISHED; shorter prefixes remain IN_PROGRESS.','meaning':'User-reported workflow only; not observed playing, correctness, mastery, credit or a saved Attempt.'},'automated_assessment':False,'grants_credit':False}
        new=copy.deepcopy(old);new['implementation']['kind']='manual_chord_scan_contract';new['implementation']['manual_execution_contract']=contract
        validate(old,new);rows.append(new);oldrows.append(old);contacttotal+=len(ev)
        responses=[{'step':i+1,'response':'acknowledged'} for i in range(len(steps))]
        assert response_state(contract,responses)=='USER_REPORTED_STEPS_FINISHED'
        assert response_state(contract,responses[:-1])=='IN_PROGRESS'
        assert response_state(contract,[{'step':1,'response':'stopped'}])=='STOPPED'
        assert response_state(contract,[{'step':1,'response':'needs_retry'}])=='NEEDS_RETRY'
        delta.append({'package_key':new['package_key'],'source_identity':new['source_identity'],'base_record_sha256':e['record_sha256'],'overlay_line':len(rows),'overlay_record_sha256':rh(new),'old_category':e['category'],'new_category':'complete_manual_nonplayback_contract'})
    assert contacttotal==308
    refused=[]
    def reject(name,fn):
        try:fn()
        except AssertionError:refused.append(name)
        else:raise AssertionError('CORRUPTION_ACCEPTED '+name)
    mutations=[('contact_fret',lambda x:x['implementation']['events'][0].update(fret=99)),('remove_contact_step',lambda x:x['implementation']['manual_execution_contract']['steps'].pop(5)),('duplicate_contact_ref',lambda x:x['implementation']['manual_execution_contract']['steps'][5].update(event_order=1)),('invent_clock',lambda x:x['implementation']['manual_execution_contract']['clock'].update(fixed_bpm=60)),('automatic_credit',lambda x:x['implementation']['manual_execution_contract'].update(grants_credit=True)),('remove_release',lambda x:x['implementation']['manual_execution_contract']['steps'].pop()),('muting_regression',lambda x:x['implementation']['manual_execution_contract'].update(muted_strings=[1]))]
    for name,mut in mutations:
        bad=copy.deepcopy(rows[0]);mut(bad);reject(name,lambda bad=bad:validate(oldrows[0],bad))
    c=rows[0]['implementation']['manual_execution_contract']
    for name,rrr in [('out_of_order_response',[{'step':2,'response':'acknowledged'}]),('boolean_step',[{'step':True,'response':'acknowledged'}]),('unknown_response',[{'step':1,'response':'passed'}]),('extra_grade',[{'step':1,'response':'acknowledged','grade':100}]),('after_stop',[{'step':1,'response':'stopped'},{'step':2,'response':'acknowledged'}])]:reject(name,lambda rrr=rrr:response_state(c,rrr))
    # Strict full-range fold by references; no regenerated range copy.
    effective={};used=set()
    for ref in index['packets']:
        checkpin(ref)
        for row in map(json.loads,(ROOT/ref['path']).read_text().splitlines()):
            assert row['package_key'] not in effective,'BASE_DUPLICATE';effective[row['package_key']]=row
    chain=['finite-metric-grid-r01','finite-quarter-voicings-r01','finite-level057-reason-r01']
    for name in chain:
        h=json.loads((ROOT/f'Results/fullscope-private-b-r01/{name}/handoff.json').read_text());checkpin(h['overlay']);overlay=[json.loads(s) for s in (ROOT/h['overlay']['path']).read_text().splitlines()]
        for d in h['changes']:
            key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'],'PRIOR_BASE'
            row=overlay[d['overlay_line']-1];assert rh(row)==d['overlay_record_sha256'] and row['package_key']==key,'PRIOR_OVERLAY';effective[key]=row;used.add(key)
    for d,row in zip(delta,rows):
        key=d['package_key'];assert key not in used and rh(effective[key])==d['base_record_sha256'],'TARGET_OVERLAP';effective[key]=row;used.add(key)
    identity=[[e['package_key'],effective[e['package_key']]['source_identity']] for e in index['children']]
    assert len(effective)==2133 and len(used)==93 and rh(identity)==index['ordered_identity_sha256'],'IDENTITY'
    packet=OUT/'implementation-overlay.jsonl';packet.write_text(''.join(compact(x)+'\n' for x in rows))
    cats=copy.deepcopy(prior['effective_categories']);cats['implementation_or_interpretation_pending']-=28;cats['complete_manual_nonplayback_contract']+=28
    save(RES/'targeted-validation.json',{'result':'PASS','records':28,'source_contacts':308,'original_pdf_rule_pages':[1,5,6,7,8],'original_txt_full_shapes_and_scan_rules_verified':True,'events_source_and_status_unchanged':True,'complete_prefix_stop_retry_checks':112,'causal_refusals':refused,'identity_sha256':rh(identity),'native_compiler_gui_broad_qa':'NOT_RUN'})
    handoff={'schema_version':1,'status':'Private manual execution contracts; overall B range IN_PROGRESS','start_utc':started,'end_utc':datetime.now(timezone.utc).isoformat(),'converter_seconds':round(time.monotonic()-t,3),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'base_index':pin(BASE),'prior_overlay_handoff':pin(PREV),'overlay':pin(packet),'changes':delta,'strict_semantics':'Fold checkpoint-r03 then the prior65 disjoint replacements, then these28 exact-key replacements. All old/new record and file hashes must match; no append or missing/duplicate key. Manual response contract is authoritative for this finite untimed task; original copied instructions remain source context.','effective_categories':cats,'effective_child_count':2133,'effective_overlay_record_count':93,'ordered_identity_sha256':rh(identity),'outside_child_ambiguities_unchanged':6,'level57_unresolved_records_unchanged':6,'source_inputs':[pin(ROOT/r['path']) for r in refs],'producer_script':pin(Path(__file__)),'new_native_valid':0,'new_integrated':0,'new_independently_reviewed':0,'new_accepted':0}
    save(RES/'handoff.json',handoff);print(compact({'handoff':pin(RES/'handoff.json'),'overlay':pin(packet),'categories':cats,'refusals':len(refused)}))
if __name__=='__main__':main()
