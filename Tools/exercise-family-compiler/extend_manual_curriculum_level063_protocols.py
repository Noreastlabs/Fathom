#!/usr/bin/env python3
"""Closed44 cached Level63 sweep/comparison/cadence/endurance graph DATA.

Reference witnesses, finite source-order projection and explicit manual loops;
no current native/table mutation, source rereading or exponential choice tables.
"""
from pathlib import Path
import argparse, collections, copy, hashlib, importlib.util, json, math, time

SELECTION='Build/manager-resume-r03/manual-procedure-level063-protocols-r01/selection.json'
SELECTION_SHA='9c0593542fc65aaa082ccece9051beb99df47856123bec3f71ece3ac0f2477ba'
OUT='Build/manager-resume-r03/manual-procedure-level063-protocols-r01/generated-r01'
NAMES={'manual_sweep_burst_rest_and_repair':'l063_triad_sweep_repair',
 'manual_seventh_sweep_release_breath_repeat':'l063_seventh_release_breath_repeat',
 'manual_four_system_comparison':'l063_four_system_comparison',
 'manual_assigned_system_cadence':'l063_assigned_cadence',
 'manual_endurance_circuit_ladder':'l063_endurance_ladder'}

def dependencies(root,s):
    result=[]
    for name in ['helper','graph_helper']:
        r=s[name];p=Path(root)/r['path'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('PREIMPORT_HELPER_PIN')
        spec=importlib.util.spec_from_file_location('protocols_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result.append(m)
    return result

def projection(source,choices,start,include_first,report_field='P_directions',value_kind='array'):
    """Closed future operator: choices in actual source P order, never defaults."""
    orders=[e['order'] for e in source if e['pick']=='P'];assert orders and len(set(orders))==len(orders)
    return {'kind':'source_order_P_directions','source_contacts':copy.deepcopy(source),
        'directions_ref':choices,'protocol_start':start,'include_first':include_first,
        'first_P_order':orders[0],'source_P_orders':orders,'report_field':report_field,'directions_value_kind':value_kind}

def resolve_projection(d,values):
    """Pure specification oracle. Native engine must implement separately."""
    assert set(d)=={'kind','source_contacts','directions_ref','protocol_start','include_first','first_P_order','source_P_orders','report_field','directions_value_kind'}
    assert d['kind']=='source_order_P_directions' and type(d['include_first']) is bool and d['protocol_start'] in ['D','U']
    cs=d['source_contacts'];orders=[e['order'] for e in cs if e['pick']=='P']
    assert orders==d['source_P_orders'] and orders and d['first_P_order']==orders[0]
    assert d['directions_value_kind'] in ['array','one_scalar']
    if d['directions_value_kind']=='one_scalar':
        assert type(values) is str and values in ['D','U'];values=[values]
    assert type(values) is list and all(type(v) is str and v in ['D','U'] for v in values)
    assert len(values)==len(orders)-(0 if d['include_first'] else 1)
    result=values if d['include_first'] else [d['protocol_start'],*values]
    assert result[0]==d['protocol_start'];return result

def numeric_guard(value,lower):
    """Finite reported seconds; bool/string/null do not become measured duration."""
    return type(value) in [int,float] and math.isfinite(value) and value>=0 and type(lower) in [int,float] and math.isfinite(lower) and lower>=0 and value>=lower

def program(h,g,o):
    impl=o['implementation'];c=impl['manual_execution_contract'];kind=impl['kind'];nodes={};domains={};name=NAMES[kind]
    if kind=='manual_assigned_system_cadence':name+='_'+c['assigned_system']
    if kind=='manual_endurance_circuit_ladder':name+='_'+str(c['circuit'])
    def ref(*path):return {'original_contract_path':list(path)}
    def add(n,fields,expected,next_node,path,*,physical=False,instruction=None,save=None):
        x=g.report(h,instruction or 'Apply the complete referenced source action and enter your own reports. Retain source safety, muting and stop duties.',fields,expected,next_node,physical=physical,save=save)
        x['source_action_ref']=ref(*path);nodes[n]=x;return x
    def acknowledge(n,next_node,path,label,physical=False):
        return add(n,g.bools(h,'source_duty_reported','no_stop_condition'),g.truths('source_duty_reported','no_stop_condition'),next_node,path,physical=physical,instruction=label)
    def fields(cs):return {'named_pitches':h.array(h.text(),len(cs)),'roles':h.array(h.text(),len(cs)),'strings':h.array(h.integer(1,6),len(cs)),'frets':h.array(h.integer(0,24),len(cs)),'source_attack_symbols':h.array(h.text(),len(cs))}
    def expected(cs):return {n:[e[k] for e in cs] for n,k in [('named_pitches','printed_note'),('roles','role'),('strings','string'),('frets','fret'),('source_attack_symbols','pick')]}
    def perform(n,cs,next_node,path,*,duties=(),project=None):
        duties=['complete_source_order','independent_attacks','source_muting_kept','no_stop_condition',*duties]
        x=add(n,{**fields(cs),**g.bools(h,*duties)},{**expected(cs),**g.truths(*duties)},next_node,path,physical=True)
        if project:
            x['schema']['properties']['P_directions']=h.array(h.menu(['D','U']),sum(e['pick']=='P' for e in cs));x['schema']['required'].append('P_directions');x['computed_expected']=project
        return x
    def trimmed(field):return g.guard('nonempty_trimmed_text',value_ref=g.ref('payload',field),minimum=1,maximum=512)
    def seconds():return {'type':['number','null'],'minimum':0,'input_role':'manual_report','source_units':'seconds','finite_required':True,'no_clock_observation':True}
    entry='setup';failure_extra={}
    if kind=='manual_sweep_burst_rest_and_repair':
        acknowledge('setup','mirror',['steps',0],'Prepare minimum pick depth, relaxed extension, muting and fret/attack/release/next-string sequence. No held mini-barre unless printed.')
        cs=c['steps'][1]['ordered_contacts'];perform('mirror',cs,'rest',['steps',1],duties=['one_continuous_motion_per_direction','release_before_next_attack','turnaround_on_source_repeated_contact'])
        acknowledge('rest','self_report',['steps',2],'Rest after the complete six-contact burst. Duration is unknown; no timed gate is inferred.')
        add('self_report',g.bools(h,'notes_separate','pick_continuous','turnaround_timely'),g.truths('notes_separate','pick_continuous','turnaround_timely'),'end',['steps',3])
        domains['one_way']=[{'selection':{'direction':d},'contacts':copy.deepcopy(cs[:3] if d=='D' else cs[3:])} for d in ['D','U']]
        nodes['repair_choice']=g.choice(h,'Only a failed post-rest final report admits the source slower one-way repair. Choose D/U explicitly, restart, or stop.',{'choice':h.menu(['one_way_repair','retry_from_entry','stop']),'direction':g.optional_menu(h,['D','U'])},{'one_way_repair':{'next':'repair_one_way','guards':[g.guard('failed_node_is',node='self_report'),g.guard('domain_lookup',domain='one_way',selection={'direction':g.ref('payload','direction')})]},'retry_from_entry':{'native_protocol':'retry_from_entry'},'stop':{'native_protocol':'stop'}},save='repair_choice')
        x=perform('repair_one_way',cs[:3],'repair_rest',['steps',3],duties=['slower_than_failed_mirror','only_selected_one_way','release_before_next_attack']);x['expected']={k:v for k,v in x['expected'].items() if k not in fields(cs[:3])};x['computed_expected']={'kind':'selected_domain_reports','domain':'one_way','selection':{'direction':g.ref('saved','repair_choice','direction')},'fields':{'named_pitches':'printed_note','roles':'role','strings':'string','frets':'fret','source_attack_symbols':'pick'}}
        acknowledge('repair_rest','restore_mirror',['steps',3],'Take an explicitly chosen conservative recovery pause; no source-fixed duration.')
        perform('restore_mirror',cs,'restore_rest',['steps',1],duties=['release_before_next_attack','restored_exact_source_mirror'])
        acknowledge('restore_rest','repair_report',['steps',2],'Rest after the restored complete mirror; source caption remains unchanged.')
        acknowledge('repair_report','repair_end',['steps',3],'Report the selected repair only. No automatically observed recovery or full source-session completion.')
        nodes['repair_end']=g.end('user_reported_source_one_way_repair_and_restore_only')
        failure_extra={'failed_node_repair_entry':{'self_report':'repair_choice'},'other_failure_repair_admitted':False}
    elif kind=='manual_seventh_sweep_release_breath_repeat':
        acknowledge('setup','mirror1',['actions','setup'],'Prepare the corrected source muting/release setup. No held mini-barre unless printed.')
        cs=c['actions']['mirror']['ordered_contacts']
        for suffix,next_repeat in [('1','mirror2'),('2','mirror2')]:
            x=perform('mirror'+suffix,cs,'breath'+suffix,['actions','mirror'],duties=['notes_separate','release_before_next_attack','short_burst_not_continuous_rake']);x['release_source_action_ref']=ref('actions','full_hand_release');x['source_release_maps_to_native_owned_release']=True
            acknowledge('breath'+suffix,'compare'+suffix,['actions','one_breath'],'After owned full hand release, take and report one breath. Its duration is unknown.')
            routes={'clean_match_repeat':{'next':next_repeat},'not_clean':{'next':'not_clean'},'stopped':{'native_protocol':'stop'}}
            if suffix=='2':routes['clean_match_finish']={'next':'end'}
            nodes['compare'+suffix]=g.choice(h,'Compare the final note with the first. Repeating requires an explicit clean match; finishing requires at least two selected repetitions.',{'choice':g.optional_menu(h,list(routes))},routes)
            nodes['compare'+suffix]['source_action_ref']=ref('actions','compare')
        nodes['not_clean']=g.end('needs_retry');nodes['not_clean']['terminal_failure']=True
        failure_extra={'minimum_selected_repetitions':c['minimum_selected_repetitions'],'source_fixed_repetition_count':c['source_fixed_repetition_count'],'minimum_selection_policy_ref':ref('minimum_selection_policy')}
    elif kind=='manual_four_system_comparison':
        choice_fields={'tempo_label':h.text(False),'tone_label':h.text(False),'D_hybrid_later_P':h.menu(['D','U']),'U_hybrid_later_P':h.menu(['D','U'])}
        x=add('setup',{**choice_fields,**g.bools(h,'shape_constant','source_muting_prepared','volume_balanced','no_stop_condition')},g.truths('shape_constant','source_muting_prepared','volume_balanced','no_stop_condition'),'source_1',['steps',0],save='choice');x['constraints']=[trimmed('tempo_label'),trimmed('tone_label'),g.guard('trimmed_text_exact',value_ref=g.ref('payload','tempo_label')),g.guard('trimmed_text_exact',value_ref=g.ref('payload','tone_label'))]
        plans={s['system']:copy.deepcopy(s['contacts']) for s in c['segments']};plans['CROSSPICK U START']=[{**e,'pick':'U' if e['pick']=='D' else 'D'} for e in plans['CROSSPICK']];plans['HYBRID U START']=copy.deepcopy(plans['HYBRID'])
        for i,s in enumerate(c['steps'][1:],1):
            nxt='source_'+str(i+1) if i+1<len(c['steps']) else 'end';node='source_'+str(i)
            if s['action']=='perform_selected_system':
                system=s['system'];cs=plans[system];start='U' if 'U START' in system else 'D';project=projection(cs,g.ref('saved','choice',start+'_hybrid_later_P'),start,False,value_kind='one_scalar') if 'HYBRID' in system else None
                # The source choice is scalar here; explicit descriptor lifts only that
                # scalar to one later-P array, preserving the original source interface.
                x=perform(node,cs,nxt,['steps',i],duties=['constant_tempo_tone_shape'],project=project)
                for field in ['tempo_label','tone_label']:
                    x['schema']['properties'][field]=h.text(False);x['schema']['required'].append(field);x['constraints'].append(g.guard('same_as_saved',left=g.ref('payload',field),right=g.ref('saved','choice',field)))
            elif s['action']=='rest_after_system':acknowledge(node,nxt,['steps',i],'Rest after this complete source system; no source-fixed duration.')
            else:
                x=add(node,{'comparison_note':h.text(False),'manual_comparison_reported':h.boolean()},{'manual_comparison_reported':True},nxt,['steps',i]);x['constraints']=[trimmed('comparison_note')]
    elif kind=='manual_assigned_system_cadence':
        system=c['assigned_system'];cs=c['steps'][1]['ordered_source_contacts'];setup=c['steps'][0];choice_fields={}
        if system=='hybrid':choice_fields={p+'_later_P':h.array(h.menu(['D','U']),5) for p in ['D','U']}
        x=add('setup',{'chords':h.array(h.text(),3),'beat_one_targets':h.array(h.text(),3),**choice_fields,**g.bools(h,'assigned_system_prepared','source_muting_prepared','no_stop_condition')},{'chords':setup['chords'],'beat_one_targets':setup['beat_one_target_notes'],**g.truths('assigned_system_prepared','source_muting_prepared','no_stop_condition')},'source_1',['steps',0],save='choice')
        for i,s in enumerate(c['steps'][1:],1):
            nxt='source_'+str(i+1) if i+1<len(c['steps']) else 'end';node='source_'+str(i)
            if 'contacts_from_selection' in s:
                start='D' if s['contacts_from_selection']=='printed' else 'U';selected=copy.deepcopy(cs)
                if system=='cross' and start=='U':selected=[{**e,'pick':'U' if e['pick']=='D' else 'D'} for e in selected]
                project=projection(selected,g.ref('saved','choice',start+'_later_P'),start,False) if system=='hybrid' else None
                perform(node,selected,nxt,['steps',i],duties=['three_bar_form_preserved','chord_spelling_and_beat_one_targets_clear','assigned_system_unchanged','no_intraphrase_added_rest',*(['minor_quality_b5_major3_b3_audible'] if 'minor_quality_duties' in setup else [])],project=project)
            else:acknowledge(node,nxt,['steps',i],'Report the complete assigned cadence spelling, targets, quality and unchanged system. Whole workbook gate remains separate debt.')
    else:
        assert kind=='manual_endurance_circuit_ladder';cs=c['source_contacts'];porders=[e['order'] for e in cs if e['pick']=='P'];choice_fields={label:h.array(h.menu(['D','U']),len(porders)) for label in ['printed_P','opposite_P']} if porders else {}
        x=add('setup',{**choice_fields,**g.bools(h,'manual_timer_available','source_muting_prepared','source_stop_duties_understood','recording_quality_duties_understood')},g.truths('manual_timer_available','source_muting_prepared','source_stop_duties_understood','recording_quality_duties_understood'),'source_1',['steps',0],save='choice')
        if porders:
            for label,start in [('printed_P','D'),('opposite_P','U')]:x['constraints'].append(g.guard('equals_literal',value_ref=g.ref('payload',label,0),literal=start))
        last_work=None
        for i,s in enumerate(c['steps'][1:],1):
            nxt='source_'+str(i+1) if i+1<len(c['steps']) else 'end';node='source_'+str(i);stepkind=s['kind']
            if stepkind=='written':
                start='D' if s['contacts_from']=='printed' else 'U';selected=copy.deepcopy(cs)
                if start=='U':
                    limit=32 if c['circuit']==1 else 8 if c['circuit']==4 else 0
                    for e in selected[:limit]:e['pick']='U' if e['pick']=='D' else 'D'
                project=projection(selected,g.ref('saved','choice','printed_P' if start=='D' else 'opposite_P'),start,True) if porders else None
                x=perform(node,selected,nxt,['steps',i],duties=['one_complete_written_circuit','clean_quality_reported'],project=project)
            elif stepkind=='work':
                x=add(node,{'reported_seconds':seconds(),'first_recording':h.text(False),'final_recording':h.text(False),**g.bools(h,'written_circuit_repeated','boundary_release_reported','no_stop_condition')},g.truths('written_circuit_repeated','boundary_release_reported','no_stop_condition'),nxt,['steps',i],physical=True,save=node)
                x['constraints']=[g.guard('reported_seconds_at_least',value_ref=g.ref('payload','reported_seconds'),lower_bound_ref=g.ref('contract','steps',i,'target_seconds')),trimmed('first_recording'),trimmed('final_recording')]
                x['source_duration_units']='seconds';x['recording_windows']={'kind':'reported_work_windows','work_ref':g.ref('saved',node,'reported_seconds'),'first':[0,10],'last_duration':10,'overlap_allowed':True,'recording_exists_observed':False};last_work=node
                x['source_contact_ref']=ref('source_contacts');x['fixed_contact_schedule']=None
            elif stepkind=='rest':
                x=add(node,{'reported_seconds':seconds(),'rest_reported':h.boolean()},{'rest_reported':True},nxt,['steps',i]);x['constraints']=[g.guard('reported_seconds_at_least',value_ref=g.ref('payload','reported_seconds'),lower_bound_ref=g.ref('saved',last_work,'reported_seconds'))]
            elif stepkind=='audit':
                dimensions=s['dimensions'];x=add(node,{'comparisons':h.obj({d:g.optional_menu(h,['same','worse']) for d in dimensions}),'clean_set_reported':h.boolean()},{'comparisons':{d:'same' for d in dimensions},'clean_set_reported':True},nxt,['steps',i]);x['source_failure_guidance_ref']=ref('source_fatigue_repairs')
            else:acknowledge(node,nxt,['steps',i],'Acknowledge only the selected duration ladder. Last60-second set is a private minimum; no two-clean-days tempo advancement, mastery, listening or whole-source-gate claim.')
        failure_extra={'source_failure_guidance_ref':ref('source_fatigue_repairs'),'fatigue_repair_execution_not_claimed':True,'tempo_advance_gate_ref':ref('tempo_advance_gate'),'tempo_advance_authorized':False}
    nodes['end']=g.end('user_reported_selected_source_program_only')
    return {'name':name,'mode':'graph','steps':[],'graph':{'schema':'fathom.manual-procedure-graph.1','entry':entry,'nodes':nodes,'domains':domains,
        'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':entry,**failure_extra},
        'call_semantics':'No inter-row calls. Every explicit repeat/repair preserves source order and requires fresh owned input.',
        'loop_semantics':'Only source seventh clean-match repetition has an explicit loop. No automatic repetitions, breath timing or timed contact scheduler.'},
        'learner_instruction_context_ref':{'original_record_paths':[['source_payload','label'],['implementation','source_scope','selected_source_text']], 'original_contract_paths':[['source_session_duties'],['source_required_practice_duty'],*([['source_rule'],['source_fatigue_repairs'],['tempo_advance_gate']] if kind=='manual_endurance_circuit_ladder' else [])]},
        'source_facts':{'original_kind':kind,'source_clock':None,'fixed_bpm':None,'printed_contact_count':c.get('printed_attacks',c.get('initial_written_attacks')),'printed_vs_chosen':'Source contacts/roles/agents/strokes/order remain facts; P directions, tempo/tone labels, comparison/recovery/recording/duration reports remain explicit choices or reports.'},
        'source_obligations_ref':{'original_contract_paths':[['source_session_duties'],['source_required_practice_duty'],*([['tempo_advance_gate'],['source_fatigue_repairs']] if kind=='manual_endurance_circuit_ladder' else [])],'full_gate_or_session_completed':False,'family_report_not_discharged_by_single_cell':True},
        'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'grants_credit':False,'automatic_mastery':False}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();raw=(root/SELECTION).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SELECTION_SHA:raise ValueError('SELECTION_PIN')
    s=json.loads(raw);h,g=dependencies(root,s);cache={}
    def pinned(r):
        p=Path(r['path']);full=root/p;h.require(not p.is_absolute() and '..' not in p.parts and full.resolve().is_relative_to(root) and not any(q.is_symlink() for q in [full,*full.parents]),'PATH_ESCAPE')
        if r['path'] not in cache:cache[r['path']]=full.read_bytes()
        raw=cache[r['path']];h.require(h.sha(raw)==r['sha256'] and len(raw)==r['bytes'],'INPUT_PIN');return raw
    for r in [s['ledger'],s['current_descriptor'],*s['cached_inputs'],*s['source_models']]:pinned(r)
    accepted={x['selection']['package_key'] for x in h.strict(cache[s['current_descriptor']['path']])['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'}
    rows=[];originals={};profiles=collections.Counter()
    for r in s['rows']:
        raw=pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);h.require(r['key'] not in accepted and h.sha(raw)==r['original_row_sha256'] and o['package_key']==r['key'] and o['source_identity']==r['source_identity'] and o['unresolved_reasons']==[],'EXACT_PENDING_SOURCE')
        p=program(h,g,o);profiles[p['name']]+=1;originals[r['key']]=o;rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':['implementation','manual_execution_contract'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'Closed44 future-native protocol DATA; no current224/future79 execution, installed or acceptance claim.'})
    h.require(len(rows)==44 and len(profiles)==10,'CLOSED44_TEN_PROFILES')
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'keys':[r['source_key'] for r in rows],'contracts':{r['source_key']:r['contract_sha256'] for r in rows},'cached_witnesses':s['cached_inputs'],'source_models':s['source_models'],'profile_counts':dict(profiles),'contexts':{r['path']:h.strict(cache[r['path']]) for r in s['cached_inputs'] if r['path'].endswith('source-context.json')},
        'operator_extensions':{'source_order_P_directions':'Closed source_contacts/source_P_orders/first_P_order/protocol_start/include_first/directions_ref/report_field/directions_value_kind. Actual source-P order; include_first binds explicit first choice to protocol start. directions_value_kind one_scalar lifts exactly one declared scalar, array requires the explicit list; no exponential domain expansion.',
            'reported_seconds_at_least':'Closed value_ref/lower_bound_ref. Finite nullable numeric manual seconds compared against exact retained contract target or saved preceding reported work. No rounding/default/coercion/clock.',
            'failed_node_is':'Closed node literal; repair admission matches retained failed source node exactly.',
            'trimmed_text_exact':'Closed value_ref; nonempty source selection label must equal its own stripped text.',
            'equals_literal':'Closed value_ref/literal; exact typed equality, no bool-number coercion.'},
        'source_release_binding':'release_source_action_ref may address actions/full_hand_release; native owned release accounts for that source duty and occurs before one_breath/compare, with no duplicate source ACK.',
        'terminal_failure_end':'needs_retry end retains source failure diagnosis/debt and cannot act as ordinary completion.',
        'new_ref_scope':'contract is exact retained manual_execution_contract, closed path to numeric source target only; saved/payload/failed references retain existing grammar.',
        'native_integration_debt':['new P projection/guards and numeric nullable form type','source actions-object refs and release alias','final-node-only triad repair admission','explicit seventh compare/repeat/minimum paths and terminal-failure end','manual reported work/rest/windows/six-dimension audit, no scheduler'],
        'native_execution':False,'runtime_admitted':False,'grants_credit':False}
    validate(rows,closure,originals,h,g);return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),'rows':44,'source_programs':10,'graph_nodes':sum(len(r['program']['graph']['nodes']) for r in rows)},originals

def validate(rows,closure,originals,h,g):
    h.require(len(rows)==44 and len(set(r['source_key'] for r in rows))==44 and [r['source_key'] for r in rows]==closure['keys'],'EXACT_KEYS')
    for r in rows:
        o=originals[r['source_key']];p=r['program'];nodes=p['graph']['nodes'];c=o['implementation']['manual_execution_contract'];h.require(p==program(h,g,o) and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'EXACT_SOURCE_PROGRAM');bound=set()
        for n in nodes.values():
            if n['kind']=='end':continue
            h.require(n['schema']['additionalProperties'] is False and set(n['schema']['properties'])==set(n['schema']['required']) and 'default' not in json.dumps(n['schema']),'CLOSED_BLANK_SCHEMA')
            paths=[n['source_action_ref']['original_contract_path']] if 'source_action_ref' in n else []
            if 'release_source_action_ref' in n:paths.append(n['release_source_action_ref']['original_contract_path'])
            for path in paths:
                target=c
                for part in path:target=target[part]
                h.require(type(target) is dict,'SOURCE_ACTION_REF');bound.add(tuple(path))
            if n['kind']=='report':h.require(n['next'] in nodes,'EDGE')
            else:
                for route in n['routes'].values():h.require(('next' in route and route['next'] in nodes) or route.get('native_protocol') in ['retry_from_entry','stop'],'ROUTE')
        expected={('steps',i) for i in range(len(c['steps']))} if 'steps' in c else {('actions',a) for a in c['actions']}
        h.require(bound==expected,'ALL_SOURCE_PHASES');h.require('original_record' not in r and p['grants_credit'] is False and p['fixed_bpm'] is None and p['performance_observed'] is False,'REFERENCE_NO_AUTHORITY')
    return True

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);s=json.loads((Path(root)/SELECTION).read_bytes());h,_=dependencies(root,s);target=Path(root)/out;h.require(not Path(out).is_absolute() and '..' not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False)
    files={'definitions.jsonl':b''.join(h.encoded(r)+b'\n' for r in rows),'family-closure.json':h.encoded(closure)+b'\n'};q=lambda x:json.dumps(x,ensure_ascii=False)
    header=['#pragma once','#include <array>','namespace fathom::tasks::manual_procedure_protocols_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+q(h.sha(h.encoded(closure)))+';','inline const std::array<Row,44> rows = {{'];header+=['{'+q(r['source_key'])+','+q(h.encoded(r).decode())+'},' for r in rows];header+=['}};','}'];files['GeneratedManualProcedureProtocols.hpp']=('\n'.join(header)+'\n').encode();pins=[]
    for name,raw in files.items():
        p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'CLOSED44_LEVEL063_PROTOCOL_DATA_PASS_FUTURE_NATIVE_PENDING','metrics':metrics,'files':pins,'source_program_profiles':closure['profile_counts'],'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
