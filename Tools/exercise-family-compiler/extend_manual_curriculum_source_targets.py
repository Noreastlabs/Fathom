#!/usr/bin/env python3
"""Closed35 source target/form programs, referenced witnesses, no current224 edits."""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.util,itertools,json,time
SELECTION='Build/manager-resume-r03/manual-procedure-source-targets-r01/selection.json'
SELECTION_SHA='64c76a5bbe1b2a7ad48634e35a28240a2026a6d328d97175e34daef162942e6b'
OUT='Build/manager-resume-r03/manual-procedure-source-targets-r01/generated-r02'
NAMES={'manual_minor_progression_workflow':'l061_minor_target_phrase','manual_source_zone_phrase':'l061_zone_target_phrase',
 'manual_source_motif_target_workflow':'l061_motif','manual_capstone_workflow':'l062_capstone',
 'manual_recovery_workflow':'l062_pulse_recovery','manual_bridge_workflow':'l062_bridge'}

def dependencies(root,s):
    result=[]
    for name in ['helper','graph_helper']:
        r=s[name];p=Path(root)/r['path'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('PREIMPORT_HELPER_PIN')
        spec=importlib.util.spec_from_file_location('targets_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result.append(m)
    return result

def program(h,g,o):
    impl=o['implementation'];c=impl['manual_execution_contract'];kind=impl['kind'];ev=impl['events'];nodes={};domains={};name=NAMES[kind]
    if kind=='manual_source_motif_target_workflow':name+='_'+('target_identity' if c['required_target_orders'] is None else 'chromatic' if c['motif_code']=='H5' else 'enclosure')
    def add(node,fields,expected,next_node,indices,*,physical=False,instruction=None):
        source=[c['steps'][i]['action'].replace('_',' ') for i in indices]
        x=g.report(h,instruction or '; then '.join(source)+'. Retain complete referenced guidance; fields are your own explicit reports.',fields,expected,next_node,physical=physical)
        x['source_action_refs']=[{'original_contract_path':['steps',i]} for i in indices];nodes[node]=x;return x
    bools=lambda *ns:g.bools(h,*ns);true=lambda *ns:g.truths(*ns)
    def contact_fields(contacts):
        return {'named_pitches':h.array(h.text(),len(contacts)),'roles':h.array(h.text(),len(contacts)),
            'strings':h.array(h.integer(1,6),len(contacts)),'frets':h.array(h.integer(0,24),len(contacts))}
    def contact_expected(contacts):
        return {n:[e[k] for e in contacts] for n,k in [('named_pitches','printed_note'),('roles','role'),('strings','string'),('frets','fret')]}
    def physical(node,contacts,next_node,indices,duties):
        return add(node,{**contact_fields(contacts),**bools(*duties)},
            {**contact_expected(contacts),**true(*duties)},next_node,indices,physical=True)
    recovery=kind=='manual_recovery_workflow';level62=o['level']==62;motif=kind=='manual_source_motif_target_workflow'
    if recovery:
        add('context',{'active_chord':h.text(),'trigger':h.menu(['missed_shift','non_chord_tone']),'existing_manual_pulse':h.boolean()},
            {'active_chord':c['active_chord'],'existing_manual_pulse':True},'choices',[0],instruction='Declare the active chord and actual recovery context. A missed shift or non-chord tone is your report; the printed initial tone is not automatically classified wrong. The existing manual pulse has no source clock here.')
        nodes['context']['save_as']='context'
    elif level62:
        groups=c['steps'][0]['chord_groups'];fields={'chords':h.array(h.text(),len(groups)),'air_picked_complete_route':h.boolean(),'no_stop_condition':h.boolean()};expected={'chords':[x['chord'] for x in groups],**true('air_picked_complete_route','no_stop_condition')}
        if kind=='manual_capstone_workflow':fields['key_order']=h.array(h.text(),4);expected['key_order']=[x['key'] for x in c['steps'][0]['key_blocks']]
        add('context',fields,expected,'choices',[0],physical=True,instruction='Name the complete printed chord/key order and air-pick every contact before sounding. This muted preview is separate from printed inventory and receives owned release before the explicit start choice.')
    elif kind=='manual_minor_progression_workflow':
        first=c['steps'][0];groups=first['chord_groups'];add('context',{'key':h.text(),'chords':h.array(h.text(),3),'functions':h.array(h.text(),3),'target_classes':h.array(h.text(),3)},
            {'key':first['key'],'chords':[x['chord'] for x in groups],'functions':[x['function'] for x in groups],'target_classes':first['target_classes']},'target_preparation',[0])
        targets=c['steps'][1]['targets'];physical('target_preparation',targets,'phrase',[1],['all_targets_played_alone','all_targets_sung','no_stop_condition'])
    elif kind=='manual_source_zone_phrase':
        first=c['steps'][0];targets=[ev[i-1] for i in first['target_event_orders']]
        x=physical('context',targets,'phrase',[0],['target_functions_named','all_targets_played_alone','all_targets_sung','no_stop_condition']);x['schema']['properties']['chords']=h.array(h.text(),4);x['schema']['required'].append('chords');x['expected']['chords']=['Dm7','G7','Cmaj7','Cmaj7']
    else:
        allowed=c['allowed_target_orders_by_chord'];required=c['required_target_orders'];sets=list(itertools.product(*allowed)) if allowed else [required]
        domains['targets']=[{'selection':{'target_orders':list(orders)},'contacts':[copy.deepcopy(ev[i-1]) for i in orders]} for orders in sets]
        fields={'target_orders':h.array(h.integer(1,8),len(sets[0]))}
        if required is not None:fields['personal_reference_pace']=h.text(False)
        x=add('context',fields,{'target_orders':required} if required else {},'target_preparation',[0],instruction='Explicitly select source targets for G7 and Cmaj7, or re-enter the fixed source target schedule on approach cards. Play each target alone and sing it before the phrase. No hidden answer or fixed source tempo is supplied.')
        x['constraints']=[g.guard('domain_lookup',domain='targets',selection={'target_orders':g.ref('payload','target_orders')})];x['save_as']='target_choice'
        targets=domains['targets'][0]['contacts'];x=add('target_preparation',{**contact_fields(targets),**bools('all_targets_played_alone','all_targets_sung','no_stop_condition')},true('all_targets_played_alone','all_targets_sung','no_stop_condition'),'identity',[0],physical=True)
        x['computed_expected']={'kind':'selected_domain_reports','domain':'targets','selection':{'target_orders':g.ref('saved','target_choice','target_orders')},'fields':{'named_pitches':'printed_note','roles':'role','strings':'string','frets':'fret'}}
        identity=c['steps'][1]
        if required is None:
            fields={'preserved_identity':h.text(),'source_reference':h.text(),'no_unprinted_contour_claim':h.boolean()};expected={'preserved_identity':identity['identity_contract']['preserved'],'source_reference':identity['identity_contract']['reference'],'no_unprinted_contour_claim':True}
            add('identity',fields,expected,'phrase',[1])
        else:
            x=physical('identity',ev,'phrase',[1],['approach_target_patterns_practiced','half_my_reference_pace','targets_receive_harmonic_weight','no_stop_condition'])
            x['schema']['properties']['personal_reference_pace']=h.text(False);x['schema']['required'].append('personal_reference_pace');x['constraints']=[g.guard('same_as_saved',left=g.ref('payload','personal_reference_pace'),right=g.ref('saved','target_choice','personal_reference_pace'))]
    if level62:
        fields={'start_stroke':h.menu(['D','U'])}
        if recovery:fields['simplified_remainder_description']={'type':'string','minLength':1,'maxLength':512,'input_role':'manual_choice_or_report'}
        x=add('choices',fields,{},'target_preview' if recovery else 'phrase',[1],instruction='Choose D or U explicitly. This selected alternate cycle is a chosen practice realization, not a claim both starts are required. For recovery, enter a nonempty simplified remainder plan; no contacts or timing are generated for it.');x['save_as']='choice'
        if recovery:x['constraints']=[g.guard('nonempty_trimmed_text',value_ref=g.ref('payload','simplified_remainder_description'),minimum=1,maximum=512)]
        domains['chosen_alternate']=[{'selection':{'start_stroke':start},'contacts':[{**copy.deepcopy(e),'chosen_pick':start if i%2==0 else ('U' if start=='D' else 'D')} for i,e in enumerate(ev)]} for start in ['D','U']]
        if recovery:
            target=c['target'];physical('target_preview',[target],'phrase',[2],['target_heard_and_named','target_previewed','unused_strings_muted','excess_pressure_released','no_unmarked_scrape','no_stop_condition'])
    duties=['complete_printed_order','target_harmonic_weight','source_barline_preserved','no_stop_condition']
    if kind=='manual_minor_progression_workflow':duties+=['half_diminished_b5_clear','dominant_major_third_clear','minor_tonic_b3_clear','no_unprinted_scale_tone']
    if kind=='manual_source_zone_phrase':duties+=['fixed_role_schedule_preserved','printed_register_route_preserved','no_invented_midphrase_rest']
    if motif:duties+=['motif_identity_preserved','no_stop_after_first_chord','selected_targets_clear']
    if level62:duties+=['existing_pulse_preserved','pick_cycle_preserved','shift_and_form_continuity']
    phrase_indices=[3,4] if recovery else [2] if kind!='manual_source_zone_phrase' else [1]
    next_node='space' if motif else 'self_report'
    x=physical('phrase',ev,next_node,phrase_indices,duties)
    if level62:
        x['schema']['properties']['chosen_pick_sequence']=h.array(h.menu(['D','U']),len(ev));x['schema']['required'].append('chosen_pick_sequence');x['computed_expected']={'kind':'selected_domain_reports','domain':'chosen_alternate','selection':{'start_stroke':g.ref('saved','choice','start_stroke')},'fields':{'chosen_pick_sequence':'chosen_pick'}}
    if recovery:
        x['schema']['properties']['simplified_remainder_description']={'type':'string','minLength':1,'maxLength':512,'input_role':'manual_report'};x['schema']['required'].append('simplified_remainder_description')
        for duty in ['continued_with_chosen_simplified_remainder','no_stop_between_recovery_and_remainder']:
            x['schema']['properties'][duty]=h.boolean();x['schema']['required'].append(duty);x['expected'][duty]=True
        x['constraints']=[g.guard('same_as_saved',left=g.ref('payload','simplified_remainder_description'),right=g.ref('saved','choice','simplified_remainder_description'))]
        x['coherent_phase']='Source recovery pair plus learner-authored remainder is one uninterrupted manual physical phase; release occurs after both. No arbitrary remainder notes generated.'
    if motif:add('space',bools('at_least_one_complete_source_beat_of_space','no_stop_condition'),true('at_least_one_complete_source_beat_of_space','no_stop_condition'),'self_report',[3],instruction='Leave at least one complete beat of space after the two-bar statement. Report this manual source duty; no beat duration, timer or scheduler is inferred.')
    last=len(c['steps'])-1;add('self_report',{'source_duties_reported':h.boolean(),'limitations_note':h.text()}, {'source_duties_reported':True},'end_cell',[last],instruction='Report only the selected complete source phrase and its target/form duties. Source repairs, family comparison and whole workbook/session gates remain separately retained debt; no listening or performance is detected.')
    nodes['end_cell']=g.end('user_reported_selected_source_extent_finished_only')
    return {'name':name,'mode':'graph','steps':[],
        'graph':{'schema':'fathom.manual-procedure-graph.1','entry':'context','nodes':nodes,'domains':domains,
            'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':'context'},
            'call_semantics':'No inter-row calls. Source recovery and chosen remainder stay one coherent physical action; no manual input/release inserted into that musical extent.',
            'loop_semantics':'No automatic repetitions or clocks.'},
        'learner_instruction_context_ref':{'original_record_paths':[['source_payload','label'],['implementation','source_scope','selected_source_text'],['implementation','context_tasks']], 'original_contract_paths':[['source_rules']] if 'source_rules' in c else [['source_rule']] if 'source_rule' in c else [['source_session_duties']]},
        'source_facts':{'original_kind':kind,'source_clock':None,'fixed_bpm':None,'printed_contact_count':len(ev),'source_contact_path':['implementation','events'],'printed_vs_chosen':'Printed pitches/roles/geometry/form remain source facts. Explicit D/U cycle, recovery context/remainder and allowed target selections are user choices; source-required both-start status remains the retained original null/false value.'},
        'source_obligations_ref':{'original_contract_paths':[['source_required_practice_duty'],*([['family_response_contract']] if kind=='manual_source_zone_phrase' else []),*([['unselected_source_obligations']] if 'unselected_source_obligations' in c else [])], 'full_gate_or_session_completed':False,'family_report_not_discharged_by_single_cell':True},
        'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'grants_credit':False,'automatic_mastery':False}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();raw=(root/SELECTION).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SELECTION_SHA:raise ValueError('SELECTION_PIN')
    s=json.loads(raw);h,g=dependencies(root,s);cache={}
    def pinned(r):
        p=Path(r['path']);full=root/p;h.require(not p.is_absolute() and '..' not in p.parts and full.resolve().is_relative_to(root) and not any(q.is_symlink() for q in [full,*full.parents]),'PATH_ESCAPE')
        if r['path'] not in cache:cache[r['path']]=full.read_bytes()
        raw=cache[r['path']];h.require(h.sha(raw)==r['sha256'] and len(raw)==r['bytes'],'INPUT_PIN');return raw
    for r in [s['ledger'],s['current_descriptor'],s['reference_helper'],*s['cached_inputs'],*s['source_models']]:pinned(r)
    accepted={x['selection']['package_key'] for x in h.strict(cache[s['current_descriptor']['path']])['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'}
    rows=[];originals={};profiles=collections.Counter()
    for r in s['rows']:
        raw=pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);h.require(r['key'] not in accepted and h.sha(raw)==r['original_row_sha256'] and o['package_key']==r['key'] and o['source_identity']==r['source_identity'] and o['unresolved_reasons']==[],'EXACT_PENDING_SOURCE')
        p=program(h,g,o);profiles[p['name']]+=1;originals[r['key']]=o;rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':['implementation','manual_execution_contract'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'Exact35 future-native source programs with witnesses by reference; no current224/native/installed/accepted/credit claim.'})
    h.require(len(rows)==35 and len(profiles)==8,'CLOSED35_EIGHT_PROGRAMS')
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'keys':[r['source_key'] for r in rows],'contracts':{r['source_key']:r['contract_sha256'] for r in rows},'cached_witnesses':s['cached_inputs'],'source_models':s['source_models'],'profile_counts':dict(profiles),'contexts':{r['path']:h.strict(cache[r['path']]) for r in s['cached_inputs'] if r['path'].endswith('source-context.json')},'operator_extension':'Reuse exact selected_domain_reports, source-defined array lengths and explicit tuple fields; chosen_pick is distinct from printed source picks.','trimmed_text_guard':{'kind':'nonempty_trimmed_text','required_fields':['kind','value_ref','minimum','maximum'],'meaning':'A typed string must have stripped length within the closed bounds; valid whitespace-only text terminates current pass with diagnosis, not a usable remainder. Never generates contacts/timing. Raw typed report/history retained. UI raw512-character bound is an authored bounded input surface, not a printed source fact.'},'source_action_refs':'Finite list of original step pointers; source recovery+continuation3/4 are one coherent phase.','native_execution':False,'runtime_admitted':False,'grants_credit':False}
    validate(rows,closure,originals,h,g);return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),'rows':35,'source_programs':8,'graph_nodes':sum(len(r['program']['graph']['nodes']) for r in rows)},originals

def validate(rows,closure,originals,h,g):
    h.require(len(rows)==35 and [r['source_key'] for r in rows]==closure['keys'],'EXACT_KEYS')
    for r in rows:
        o=originals[r['source_key']];p=r['program'];nodes=p['graph']['nodes'];h.require(p==program(h,g,o) and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'EXACT_SOURCE_PROGRAM');bound=set()
        for n in nodes.values():
            if n['kind']=='end':continue
            h.require(n['next'] in nodes and n['schema']['additionalProperties'] is False and set(n['schema']['properties'])==set(n['schema']['required']) and 'default' not in json.dumps(n['schema']),'CLOSED_BLANK_SCHEMA_EDGE')
            bound.update(x['original_contract_path'][1] for x in n['source_action_refs'])
        h.require(bound==set(range(len(o['implementation']['manual_execution_contract']['steps']))),'ALL_SOURCE_PHASES')
        h.require('original_record' not in r and p['performance_observed'] is False and p['grants_credit'] is False and p['fixed_bpm'] is None,'REFERENCE_NO_AUTHORITY')
    return True

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);s=json.loads((Path(root)/SELECTION).read_bytes());h,_=dependencies(root,s);target=Path(root)/out;h.require(not Path(out).is_absolute() and '..' not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False)
    files={'definitions.jsonl':b''.join(h.encoded(r)+b'\n' for r in rows),'family-closure.json':h.encoded(closure)+b'\n'};q=lambda x:json.dumps(x,ensure_ascii=False)
    header=['#pragma once','#include <array>','namespace fathom::tasks::manual_procedure_targets_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+q(h.sha(h.encoded(closure)))+';','inline const std::array<Row,35> rows = {{'];header+=['{'+q(r['source_key'])+','+q(h.encoded(r).decode())+'},' for r in rows];header+=['}};','}'];files['GeneratedManualProcedureTargets.hpp']=('\n'.join(header)+'\n').encode();pins=[]
    for name,raw in files.items():
        p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'CLOSED35_SOURCE_TARGET_FORM_DATA_PASS_FUTURE_NATIVE_PENDING','metrics':metrics,'files':pins,'source_program_profiles':closure['profile_counts'],'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
