#!/usr/bin/env python3
"""Twelve source-table recovery programs with explicit chosen contact geometry.

The original table prints notes/functions, not frets, clocks or a done bit.
Standard-tuning interval choices are an authored finite realization domain;
native acceptance and source/session audit remain separate obligations.
"""
from pathlib import Path
import argparse, collections, copy, hashlib, importlib.util, json, time
SELECTION='Build/manager-resume-r03/manual-procedure-recovery-table-r01/selection-r02.json'
SELECTION_SHA='7608277c4689f813046d7d34d0ba929929dac277ad05751bcd8b022dd975de96'
OUT='Build/manager-resume-r03/manual-procedure-recovery-table-r01/generated-r01'
OPEN_MIDI={1:64,2:59,3:55,4:50,5:45,6:40}
PC={'C':0,'C#':1,'D':2,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'B':11}

def dependencies(root,s):
    result=[]
    for name in ['helper','graph_helper']:
        r=s[name];p=Path(root)/r['path'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('PREIMPORT_HELPER_PIN')
        spec=importlib.util.spec_from_file_location('recovery_table_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result.append(m)
    return result

def contact_domain(fields):
    chord,weak,target,function=fields;left,right=function.split(' -> ');delta=(PC[target]-PC[weak])%12
    if delta==11:delta=-1
    assert delta in [-1,1,2],'SOURCE_LISTED_NEAREST_INTERVAL'
    domain=[]
    for ws in range(1,7):
        for wf in range(25):
            midi=OPEN_MIDI[ws]+wf
            if midi%12!=PC[weak]:continue
            for ts in range(1,7):
                tf=midi+delta-OPEN_MIDI[ts]
                if 0<=tf<=24:
                    domain.append({'selection':{'weak_string':ws,'weak_fret':wf,'target_string':ts,'target_fret':tf},'contacts':[{'order':1,'printed_note':weak,'role':left,'string':ws,'fret':wf,'pick':None},{'order':2,'printed_note':target,'role':right,'string':ts,'fret':tf,'pick':None}],'chosen_geometry':True,'absolute_delta_semitones':delta,'source_geometry':None,'source_clock':None})
    assert domain;return domain

def program(h,g,o):
    fields=o['implementation']['table_task']['printed_fields'];chord,weak,target,function=fields;left,right=function.split(' -> ');domain=contact_domain(fields);nodes={}
    def add(name,fields,expected,next_node,*,physical=False,instruction=None,save=None):
        n=g.report(h,instruction,fields,expected,next_node,physical=physical,save=save);n['source_record_refs']=[['implementation','table_task'],['implementation','task'],['implementation','context_tasks']];nodes[name]=n;return n
    add('name',{'chord':h.text(),'weak_note':h.text(),'target_note':h.text(),'weak_function':h.text(),'target_function':h.text()},{'chord':chord,'weak_note':weak,'target_note':target,'weak_function':left,'target_function':right},'choose',instruction='Name the printed chord, unstable note and nearest secure target/functions. This source table has no printed fret geometry, tempo or pick directions.')
    x=add('choose',{'weak_string':h.integer(1,6),'weak_fret':h.integer(0,24),'target_string':h.integer(1,6),'target_fret':h.integer(0,24),'chosen_strokes':h.array(h.menu(['D','U']),2),'personal_reference_pace':h.text(False)}, {},'target_preview',save='choice',instruction='Choose both contact locations and strokes explicitly. The authored standard-tuning domain realizes the printed signed one- or two-semitone movement in one register; chosen contacts/strokes remain separate from source facts. Declare your own reference pace; source half-speed relation does not provide a clock.')
    x['constraints']=[g.guard('domain_lookup',domain='chosen_pair',selection={k:g.ref('payload',k) for k in ['weak_string','weak_fret','target_string','target_fret']}),g.guard('nonempty_trimmed_text',value_ref=g.ref('payload','personal_reference_pace'),minimum=1,maximum=512)]
    x=add('target_preview',{'target_note':h.text(),'target_string':h.integer(1,6),'target_fret':h.integer(0,24),**g.bools(h,'target_played_alone','target_sung','no_stop_condition')},{'target_note':target,**g.truths('target_played_alone','target_sung','no_stop_condition')},'recover',physical=True,instruction='Play the chosen target alone first and sing it, applying the retained Level61 session duty. Release through the native owner before the two-note recovery.')
    x['constraints']=[g.guard('same_as_saved',left=g.ref('payload',k),right=g.ref('saved','choice',k)) for k in ['target_string','target_fret']]
    x=add('recover',{'named_pitches':h.array(h.text(),2),'roles':h.array(h.text(),2),'strings':h.array(h.integer(1,6),2),'frets':h.array(h.integer(0,24),2),'chosen_strokes':h.array(h.menu(['D','U']),2),'personal_reference_pace':h.text(False),**g.bools(h,'unstable_then_secure_target','target_receives_harmonic_weight','half_my_reference_pace','no_stop_condition')},g.truths('unstable_then_secure_target','target_receives_harmonic_weight','half_my_reference_pace','no_stop_condition'),'self_report',physical=True,instruction='Perform only the printed weak-note→nearest-target relation on your chosen contacts. Approach at half your declared reference pace; do not invent equal resting weight, note timing, bars or a remainder phrase.')
    x['computed_expected']={'kind':'selected_domain_reports','domain':'chosen_pair','selection':{k:g.ref('saved','choice',k) for k in ['weak_string','weak_fret','target_string','target_fret']},'fields':{'named_pitches':'printed_note','roles':'role','strings':'string','frets':'fret'}}
    x['constraints']=[g.guard('same_as_saved',left=g.ref('payload',k),right=g.ref('saved','choice',k)) for k in ['chosen_strokes','personal_reference_pace']]
    add('self_report',{'nearest_secure_resolution_reported':h.boolean(),'limitations_note':h.text()},{'nearest_secure_resolution_reported':True},'end',instruction='Report this two-note source recovery only. A full session also requires a chosen progression phrase, barline continuity and space after each two-bar statement; this pair cannot discharge those duties.')
    nodes['end']=g.end('user_reported_selected_table_recovery_only')
    return {'name':'l061_table_nearest_target_recovery','mode':'graph','steps':[],'graph':{'schema':'fathom.manual-procedure-graph.1','entry':'name','nodes':nodes,'domains':{'chosen_pair':domain},'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':'name'},'call_semantics':'No inter-row calls or fabricated remainder phrase.','loop_semantics':'No automatic repetition or clock.'},'learner_instruction_context_ref':{'original_record_paths':[['source_payload','label'],['implementation','source_scope','selected_source_text'],['implementation','context_tasks']],'cached_context_pages':[1,16]},'source_facts':{'original_kind':'manual_table_curriculum_task','printed_fields':fields,'printed_contact_count':2,'printed_geometry':None,'printed_strokes':None,'source_clock':None,'fixed_bpm':None},'choice_domain_authority':{'scope':'Fathom-authored bounded standard-tuning0–24-fret realization, not printed tablature','source_note_names_and_functions_unchanged':True,'absolute_interval_semitones':domain[0]['absolute_delta_semitones'],'unreviewed_acoustic_observation':False},'source_obligations_ref':{'cached_context_pages':[1,16],'full_gate_or_session_completed':False,'two_bar_space_not_manufactured_inside_pair':True,'remaining_progression_phrase_unobserved':True},'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'grants_credit':False,'automatic_mastery':False}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();raw=(root/SELECTION).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SELECTION_SHA:raise ValueError('SELECTION_PIN')
    s=json.loads(raw);h,g=dependencies(root,s);cache={}
    def pinned(r):
        p=Path(r['path']);full=root/p;h.require(not p.is_absolute() and '..' not in p.parts and full.resolve().is_relative_to(root) and not any(q.is_symlink() for q in [full,*full.parents]),'PATH_ESCAPE')
        if r['path']not in cache:cache[r['path']]=full.read_bytes()
        raw=cache[r['path']];h.require(h.sha(raw)==r['sha256'] and len(raw)==r['bytes'],'INPUT_PIN');return raw
    for r in [s['ledger'],s['current_descriptor'],*s['cached_inputs']]:pinned(r)
    accepted={x['selection']['package_key'] for x in h.strict(cache[s['current_descriptor']['path']])['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'};rows=[];originals={}
    for r in s['rows']:
        raw=pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);h.require(r['key']not in accepted and h.sha(raw)==r['original_row_sha256'] and o['package_key']==r['key'] and o['source_identity']==r['source_identity'] and o['unresolved_reasons']==[],'EXACT_PENDING_SOURCE')
        p=program(h,g,o);originals[r['key']]=o;rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':['implementation','table_task'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'New source-program contract derived from printed table; original generic done-bit contract referenced unchanged, not claimed sufficient. Native/independent review pending.'})
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'keys':[r['source_key']for r in rows],'contracts':{r['source_key']:r['contract_sha256']for r in rows},'cached_witnesses':s['cached_inputs'],'contexts':{r['path']:h.strict(cache[r['path']])for r in s['cached_inputs']if r['path'].endswith('source-context.json')},'profile_counts':{'l061_table_nearest_target_recovery':12},'source_table_counts':{'rows':12,'printed_recovery_tones':24},'native_integration_debt':['Original manual_table_curriculum_task/source table retained path, no manual_execution_contract source-kind substitution','source_record_refs + context-page instruction projection','Finite chosen contact domain/source-vs-choice display','Distinct source/native/UI/package review'],'native_execution':False,'runtime_admitted':False,'grants_credit':False};validate(rows,closure,originals,h,g);return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),'rows':12,'source_programs':1,'graph_nodes':72,'finite_chosen_contact_pairs':sum(len(r['program']['graph']['domains']['chosen_pair'])for r in rows)},originals

def validate(rows,closure,originals,h,g):
    h.require(len(rows)==12 and len({r['source_key']for r in rows})==12 and [r['source_key']for r in rows]==closure['keys'],'EXACT12')
    for r in rows:
        p=r['program'];o=originals[r['source_key']];h.require(p==program(h,g,o)and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'EXACT_SOURCE_PROGRAM');h.require(r['retained_contract_path']==['implementation','table_task']and p['source_facts']['original_kind']=='manual_table_curriculum_task','ORIGINAL_KIND')
        for n in p['graph']['nodes'].values():
            if n['kind']=='end':continue
            h.require(n['next']in p['graph']['nodes']and n['schema']['additionalProperties']is False and set(n['schema']['properties'])==set(n['schema']['required'])and 'default'not in json.dumps(n['schema']),'CLOSED_SCHEMA')
        h.require(p['source_facts']['printed_geometry']is None and p['source_facts']['printed_strokes']is None and p['performance_observed']is False and p['grants_credit']is False,'CHOSEN_VS_PRINTED')
    return True

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);h,_=dependencies(root,json.loads((Path(root)/SELECTION).read_bytes()));target=Path(root)/out;h.require(not Path(out).is_absolute()and '..'not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False);files={'definitions.jsonl':b''.join(h.encoded(r)+b'\n'for r in rows),'family-closure.json':h.encoded(closure)+b'\n'};pins=[]
    for name,raw in files.items():p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'CLOSED12_TABLE_RECOVERY_DATA_PASS_NATIVE_PENDING','metrics':metrics,'files':pins,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
