#!/usr/bin/env python3
"""Closed source-bound48 graph data; no frozen native/linear/table edits.

Four Level63 roll programs and one paired Level61 enclosure program share
typed reports, finite domain lookups, explicit branches and finite source calls.
All loops require a new choice. The graph is a future-native specification,
not a claim that the current96 linear owner executes these definitions.
"""
from pathlib import Path
import argparse, collections, copy, hashlib, importlib.util, json, time

SELECTION='Build/manager-resume-r03/manual-procedure-branching-r01/selection.json'
SELECTION_SHA='81d6bf864806b50ad61ffe22977a1bc85221525ef1e915273c784dfc9da0fe35'
OUT='Build/manager-resume-r03/manual-procedure-branching-r01/generated-r02'
HELPER='Tools/exercise-family-compiler/compile_manual_curriculum.py'
HELPER_SHA='eac7a92f99d1661f90953ac03d47f01b79014cf14039b57333ed00666354cf43'
PROGRAMS={'manual_crosspick_both_start_roll':'l063_crosspick_two_start_repair',
 'manual_recorded_direction_roll':'l063_direction_recording_family_repair',
 'manual_hybrid_triad_both_start_choice':'l063_hybrid_triad_choices_calibration',
 'manual_hybrid_seventh_both_start_choice':'l063_hybrid_seventh_choices_bass_release',
 'manual_enclosure_contract':'l061_paired_enclosure_choice_routes'}

def helpers(root):
    p=Path(root)/HELPER
    if hashlib.sha256(p.read_bytes()).hexdigest()!=HELPER_SHA:raise ValueError('HELPER_PREIMPORT_PIN')
    spec=importlib.util.spec_from_file_location('frozen_graph_schema_helpers',p)
    h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);return h

def ref(scope,*path):return {'scope':scope,'path':list(path)}
def report(h,instruction,fields,expected,next_node,*,physical=False,pass_tag=None,save=None):
    return {'kind':'report','action':'submit','instruction':instruction,'schema':h.obj(fields),
        'expected':expected,'constraints':[],'save_as':save,'physical':physical,
        'pass_tag':pass_tag,'next':next_node,'completion_effects':[]}
def choice(h,instruction,fields,routes,*,route_field='choice',save=None):
    return {'kind':'choice','action':'choose','instruction':instruction,'schema':h.obj(fields),
        'expected':{},'constraints':[],'route_field':route_field,'routes':routes,
        'save_as':save,'physical':False,'completion_effects':[]}
def end(status):return {'kind':'end','status':status,'grants_credit':False}
def bools(h,*names):return {n:h.boolean() for n in names}
def optional_menu(h,values,labels=None):
    s=h.menu(values);s['type']=['string','null'];s['enum']=[*values,None]
    if labels:s['enumLabels']=[*labels,'Unknown / not selected']
    return s
def truths(*names):return {n:True for n in names}
def guard(kind,**data):return {'kind':kind,**data}
def contacts(c,pass_name):
    step=c['steps'][1 if pass_name=='D' else 2]
    return step.get('ordered_contacts',step.get('source_contacts'))
def pair_domain(key,c):
    return [{'selection':{'source_key':key,'pass':p,'pair_start':n},
        'contacts':copy.deepcopy(cs[n-1:n+1]),
        'mute_skipped_strings':list(range(min(cs[n-1]['string'],cs[n]['string'])+1,max(cs[n-1]['string'],cs[n]['string']))),
        'loop_count':None,'loop_period':None,'source_clock':None}
        for p in ['D','U'] for cs in [contacts(c,p)] for n in range(1,8)
        if cs[n-1]['string']!=cs[n]['string']]

def repair_nodes(h,domain):
    pair=h.integer(1,7)
    nodes={'repair_choice':choice(h,
        'Choose only an adjacent change from the exact failed D/U pass, or restart/stop. '
        'No full-cell retry, loop count or automatic repair is inferred.',
        {'choice':h.menu(['practice_failed_pair','retry_from_entry','stop']),
         'failed_pass':optional_menu(h,['D','U']),'pair_start':pair},
        {'practice_failed_pair':{'next':'repair_pair','guards':[
            guard('same_as_failed_pass',payload_ref=ref('payload','failed_pass')),
            guard('domain_lookup',domain=domain,selection={
                'source_key':ref('failed','source_key'),'pass':ref('payload','failed_pass'),
                'pair_start':ref('payload','pair_start')})]},
         'retry_from_entry':{'native_protocol':'retry_from_entry'},
         'stop':{'native_protocol':'stop'}},save='repair_choice'),
      'repair_pair':report(h,'Practice only the chosen two source contacts, preserving their exact order/strokes and skipped-string muting. '
        'Your explicit report does not measure recovery or clear the complete-cell/family audit.',
        {'named_pitches':h.array(h.text(),2),'roles':h.array(h.text(),2),
         'picks':h.array(h.menu(['D','U']),2),
         **bools(h,'selected_pair_played','only_selected_pair','skipped_strings_muted','no_stop_condition')},
        truths('selected_pair_played','only_selected_pair','skipped_strings_muted','no_stop_condition'),
        'repair_after',physical=True),
      'repair_after':choice(h,'Another pair practice or full restart requires another explicit choice.',
        {'choice':h.menu(['practice_selected_pair_again','retry_from_entry','stop'])},
        {'practice_selected_pair_again':{'next':'repair_pair'},
         'retry_from_entry':{'native_protocol':'retry_from_entry'},'stop':{'native_protocol':'stop'}})}
    nodes['repair_pair']['computed_expected']={'kind':'selected_pair_reports','domain':domain,
        'selection':{'source_key':ref('failed','source_key'),
            'pass':ref('saved','repair_choice','failed_pass'),
            'pair_start':ref('saved','repair_choice','pair_start')},
        'fields':{'named_pitches':'printed_note','roles':'role','picks':'pick'}}
    return nodes

def roll_program(h,o,family_keys,family_labels):
    impl=o['implementation'];c=impl['manual_execution_contract'];kind=impl['kind'];key=o['package_key']
    hybrid='hybrid' in kind;seventh='seventh' in kind;recorded='recorded' in kind
    nodes={};domains={};choose_fields={}
    if hybrid:
        later=[x['order'] for x in contacts(c,'D') if x['pick']=='P' and x['order']!=1]
        choose_fields={p+'_later_P_directions':h.array(h.menu(['D','U']),len(later)) for p in ['D','U']}
        if seventh:choose_fields['conservative_release_policy_chosen']=h.boolean()
    if recorded:choose_fields['tempo_label']=h.text(False)
    nodes['choose']=report(h,'Enter explicit choices for this source contract. Source P/m/a symbols remain printed facts; '
        'later P directions and any tempo label are learner choices, with no defaults or source clock.',
        choose_fields,{'conservative_release_policy_chosen':True} if seventh else {},'setup',save='choice')
    setup=c['steps'][0];setup_fields=bools(h,'source_muting_prepared','minimum_pick_depth','relaxed_hand',
        'independent_attacks','no_stop_condition');setup_expected=truths(*setup_fields)
    if hybrid:
        setup_fields.update(bools(h,'volume_balanced_without_strain','no_string_snap','pick_volume_reduced'))
        setup_expected.update(truths('volume_balanced_without_strain','no_string_snap','pick_volume_reduced'))
    if hybrid and not seventh:
        reps=setup['representative_source_contacts']
        setup_fields.update({'calibration_agents':h.array(h.menu(['P','m','a']),3),
            'calibration_named_pitches':h.array(h.text(),3)})
        setup_expected.update({'calibration_agents':['P','m','a'],
            'calibration_named_pitches':[x['printed_note'] for x in reps]})
    if seventh:
        setup_fields.update({'named_roles':h.array(h.text(),8),
            **bools(h,'bass_shorter_than_upper','bass_released_before_upper')})
        setup_expected.update({'named_roles':setup['named_roles_in_order'],
            **truths('bass_shorter_than_upper','bass_released_before_upper')})
    nodes['setup']=report(h,'Apply the retained setup/calibration, source muting and stop conditions. '
        'For hybrid triads, isolate P, then m, then a and balance volume before both passes. '
        'Seventh bass release is the retained conservative chosen policy, not a universal ban on printed pedals.',
        setup_fields,setup_expected,'D_pass',physical=hybrid and not seventh)
    nodes['setup']['source_action_binding']=copy.deepcopy(setup)
    for p,next_node in [('D','U_pass'),('U','cell_report')]:
        cs=contacts(c,p);fields={'named_pitches':h.array(h.text(),8),'roles':h.array(h.text(),8),
            'source_attack_symbols':h.array(h.text(),8),
            **bools(h,'same_source_contacts','equal_tone','source_muting_kept','chord_identity_kept','no_stop_condition')}
        expected={'named_pitches':[x['printed_note'] for x in cs],'roles':[x['role'] for x in cs],
            'source_attack_symbols':[x['pick'] for x in cs],
            **truths('same_source_contacts','equal_tone','source_muting_kept','chord_identity_kept','no_stop_condition')}
        if hybrid:
            fields['P_directions']=h.array(h.menu(['D','U']),sum(x['pick']=='P' for x in cs))
            if seventh:
                fields.update(bools(h,'bass_shorter_than_upper','bass_released_before_upper','roles_named_while_playing'))
                expected.update(truths('bass_shorter_than_upper','bass_released_before_upper','roles_named_while_playing'))
        if recorded:
            fields.update({'tempo_label':h.text(False),'recording_locator':h.text(False),
                **bools(h,'recorded_this_pass','accent_event_one_only','skipped_strings_muted')})
            expected.update(truths('recorded_this_pass','accent_event_one_only','skipped_strings_muted'))
        nodes[p+'_pass']=report(h,'Perform and report the exact eight-contact '+p+' start pass. '
            'U is additional required practice, not another printed inventory unit. '
            'Recordings are your actual take/segment declarations; their existence/audio is unobserved.',
            fields,expected,next_node,physical=True,pass_tag=p,save=p+'_report')
        nodes[p+'_pass']['source_action_binding']=copy.deepcopy(c['steps'][1 if p=='D' else 2])
        if hybrid:nodes[p+'_pass']['computed_expected']={'kind':'selected_direction_bindings','pass':p,
            'directions_ref':ref('saved','choice',p+'_later_P_directions'),
            'source_contacts':cs,'report_field':'P_directions'}
        if recorded:nodes[p+'_pass']['constraints']=[guard('same_as_saved',
            left=ref('payload','tempo_label'),right=ref('saved','choice','tempo_label'))]
    report_fields=bools(h,'both_starts_reported','equal_tone_reported','chord_identity_reported',
        'source_muting_reported');report_fields['limitations_note']=h.text()
    nodes['cell_report']=report(h,'Report both source passes and their retained quality/control duties. '
        'Whole practice and any family recording audit remain separate debt.',
        report_fields,truths('both_starts_reported','equal_tone_reported','chord_identity_reported','source_muting_reported'),
        'finish_choice' if recorded else 'end_cell')
    nodes['cell_report']['source_action_binding']=copy.deepcopy(c['steps'][3])
    nodes['end_cell']=end('user_reported_cell_finished_only')
    if not hybrid:
        domains['failed_pass_pairs']=pair_domain(key,c)
        nodes.update(repair_nodes(h,'failed_pass_pairs'))
    if recorded:
        family_item=h.obj({'case_key':{'type':'string','enum':family_keys,'enumLabels':family_labels,
                'input_role':'explicit_source_case_selection'},'tempo_label':h.text(False),
            'responses':h.array(h.menu(['acknowledged','needs_retry','stopped']),4),
            'D_recording_locator':h.text(False),'U_recording_locator':h.text(False),
            'judgments':h.obj({p:h.obj({'result':h.menu(['consistent','louder','later']),
                'pair_start':h.integer(1,7)}) for p in ['D','U']})})
        nodes['finish_choice']=choice(h,'Finish this cell or explicitly submit the eight-case/two-pass source family audit. '
            'A finished cell never supplies sibling recordings/completion by itself.',
            {'choice':h.menu(['complete_cell','audit_family','stop'])},
            {'complete_cell':{'next':'end_cell'},'audit_family':{'next':'family_audit'},
             'stop':{'native_protocol':'stop'}})
        nodes['family_audit']=choice(h,'Supply every source case, its two recording locators and your source-step reports at the same chosen tempo. '
            'Judge each D/U direction; louder/later selects only its exact crossing pair. No audio or file check is implied.',
            {'audit_result':h.menu(['consistent','repair_required']),
             'submissions':h.array(family_item,8)},
            {'consistent':{'next':'end_family','guards':[guard('audit_outcome',value='consistent',array_ref=ref('payload','submissions'),judgments_field='judgments',passes=['D','U'])]},
             'repair_required':{'next':'family_repair_choice','guards':[guard('audit_outcome',value='repair_required',array_ref=ref('payload','submissions'),judgments_field='judgments',passes=['D','U'])]}},
            route_field='audit_result',save='family_audit')
        nodes['family_audit']['constraints']=[
            guard('exact_unique_case_set',array_ref=ref('payload','submissions'),key_field='case_key',expected_keys=family_keys),
            guard('complete_source_response_prefix',array_ref=ref('payload','submissions'),response_field='responses',steps=4),
            guard('same_family_tempo',array_ref=ref('payload','submissions'),tempo_field='tempo_label',saved_ref=ref('saved','choice','tempo_label')),
            guard('conditional_pair',array_ref=ref('payload','submissions'),case_field='case_key',
                judgments_field='judgments',passes=['D','U'],domain='direction_family_pairs')]
        nodes['family_repair_choice']=choice(h,'Choose one exact reported louder/later source case/pass/pair; practice only that pair.',
            {'choice':h.menu(['practice_reported_pair','resubmit_family_audit','stop']),
             'case_key':optional_menu(h,family_keys,family_labels),
             'pass':optional_menu(h,['D','U']),'pair_start':h.integer(1,7)},
            {'practice_reported_pair':{'next':'family_repair_pair','guards':[
                guard('reported_issue_binding',saved_ref=ref('saved','family_audit','submissions'),
                    case_ref=ref('payload','case_key'),pass_ref=ref('payload','pass'),pair_ref=ref('payload','pair_start'))]},
             'resubmit_family_audit':{'next':'family_audit'},'stop':{'native_protocol':'stop'}},save='family_repair_choice')
        nodes['family_repair_pair']=copy.deepcopy(nodes['repair_pair'])
        nodes['family_repair_pair']['next']='family_repair_choice'
        nodes['family_repair_pair']['computed_expected']={'kind':'selected_pair_reports','domain':'direction_family_pairs',
            'selection':{'source_key':ref('saved','family_repair_choice','case_key'),
                'pass':ref('saved','family_repair_choice','pass'),
                'pair_start':ref('saved','family_repair_choice','pair_start')},
            'fields':{'named_pitches':'printed_note','roles':'role','picks':'pick'}}
        nodes['end_family']=end('user_reported_family_audit_finished_no_recording_or_audio_verified')
    return common_program(o,nodes,domains,'choose',
        {'source_required_practice_duty':c['source_required_practice_duty'],
         'source_session_duties':c['source_session_duties'],
         'family_audit_ref':c.get('family_audit'),'family_audit_performed':False},
        {'failed_pass_repair_entry':'repair_choice' if not hybrid else None,
         'explicit_restart_entry':'choose','hybrid_restart_restores_calibration':hybrid})

def enclosure_program(h,o):
    impl=o['implementation'];c=impl['manual_execution_contract'];key=o['package_key'];mate=c['paired_cell']['package_key'];nodes={}
    for i,s in enumerate(c['steps']):
        name='cell_setup' if i==0 else 'source_'+str(i+1)
        next_node='source_'+str(i+2) if i+1<len(c['steps']) else 'followup'
        if i==len(c['steps'])-1:name='separate_report'
        if i==len(c['steps'])-2:next_node='separate_report'
        action=s['action'];fields={};expected={};physical=False
        if action=='name_destination_and_enclosure_order':
            fields={n:h.text() for n in ['printed_target','target_role','enclosure_order']}
            expected={n:s[n] for n in fields}
        elif action=='establish_personal_reference_pace':
            fields={'personal_reference_pace':h.text(),'pace_explicitly_chosen':h.boolean()};expected={'pace_explicitly_chosen':True}
        elif action=='play_reference_target_before_cell':
            fields={'named_pitch':h.text(),**bools(h,'target_alone_played','no_stop_condition')}
            expected={'named_pitch':s['printed_note'],**truths('target_alone_played','no_stop_condition')};physical=True
        elif action=='sing_target':
            fields={'named_pitch':h.text(),**bools(h,'target_sung','no_stop_condition')}
            expected={'named_pitch':s['printed_note'],**truths('target_sung','no_stop_condition')};physical=True
        elif action=='prepare_enclosure_half_reference_speed':
            fields=bools(h,'half_my_reference_pace_prepared');expected=truths('half_my_reference_pace_prepared')
        elif action=='play_source_contact':
            event=impl['events'][s['event_order']-1]
            fields={'named_pitch':h.text(),'role':h.text(),'tag':h.text(),
                'string':h.integer(1,6),'fret':h.integer(0,24),**bools(h,'printed_order_played','no_stop_condition')}
            expected={**{n:event[n] for n in ['role','tag','string','fret']},
                'named_pitch':event['printed_note'],**truths('printed_order_played','no_stop_condition')};physical=True
        elif action=='self_report_separate_practice':
            fields={**bools(h,'this_exact_order_separately_practiced'),'limitations_note':h.text()};expected=truths('this_exact_order_separately_practiced')
        else:raise ValueError('ENCLOSURE_ACTION')
        instruction=s.get('meaning',s.get('source',{}).get('exact_text',action.replace('_',' ')))
        nodes[name]=report(h,instruction,fields,expected,next_node,physical=physical)
        nodes[name]['source_action_binding']=copy.deepcopy(s)
    nodes['separate_report']['completion_effects']=[{'kind':'write_readiness','source_key':key,
        'report_ref':ref('payload','this_exact_order_separately_practiced'),'report_only':True}]
    routes={'repeat_current':{'next':'followup','calls':[{'source_key':key,'entry':'cell_setup','exit':'separate_report'}]},
        'practice_other_order':{'next':'followup','calls':[{'source_key':mate,'entry':'cell_setup','exit':'separate_report'}]},
        'alternate_one_pair':{'next':'followup','guards':[guard('all_true',refs=[ref('payload','current_separate'),ref('payload','other_separate')])],
            'calls':[{'source_key':k,'entry':'cell_setup','exit':'separate_report'} for k in [key,mate]]},
        'stop':{'native_protocol':'stop'}}
    nodes['followup']=choice(h,'Explicitly report readiness for both exact orders, then choose one finite route. '
        'Practice both orders separately before alternating. Each pair needs another explicit choice; no automatic repetition.',
        {'choice':h.menu(c['followup_choice']['allowed']),
         'current_separate':h.boolean(),'other_separate':h.boolean()},routes,save='followup')
    nodes['followup']['constraints']=[guard('known_boolean_reports',refs=[ref('payload','current_separate'),ref('payload','other_separate')])]
    nodes['followup']['completion_effects']=[{'kind':'write_readiness','source_key':k,
        'report_ref':ref('payload',field),'report_only':True} for k,field in [(key,'current_separate'),(mate,'other_separate')]]
    return common_program(o,nodes,{},'cell_setup',copy.deepcopy(c['scope']),
        {'explicit_restart_entry':'cell_setup','abandon_pending_calls_on_failure':True,
         'paired_readiness_retained':True,'paired_exposure_retained':True})

def common_program(o,nodes,domains,entry,debt,failure):
    c=o['implementation']['manual_execution_contract']
    return {'name':PROGRAMS[o['implementation']['kind']],'mode':'graph','steps':[],
        'graph':{'schema':'fathom.manual-procedure-graph.1','entry':entry,'nodes':nodes,'domains':domains,
            'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,
                'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,
                'active_retry_stop_navigation_require_exit_release':True,**failure},
            'call_semantics':'Exit is after committed exit-node report/effects and owned physical release; failures abandon pending route. No callee followup runs implicitly.',
            'loop_semantics':'Every loop/call route requires a new explicit choice; no clock/default/repetition count.',
            'state_requirements':['instance/pass/revision/source key/contract/own closure/frame/node/action token',
                'saved explicit choices','captured failed source pass','typed readiness/report origin and source exposure',
                'pending release reason/next continuation','finite owned call stack','full before/after/diagnosis/history','separate audit/session debt']},
        'learner_instruction_context':[o['source_payload']['label'],o['implementation']['source_scope']['selected_source_text'],
            *[x['instruction'] for x in o['implementation']['context_tasks']]],
        'source_facts':{'original_kind':o['implementation']['kind'],'original_contract':copy.deepcopy(c),
            'printed_events':copy.deepcopy(o['implementation']['events']),
            'chosen_vs_printed':'D/U laterP and tempo/reference-pace/readiness choices are learner reports; P/m/a, notes/frets/roles and printed order remain source facts.',
            'source_clock':None,'numeric_accent_or_duration_ratio':None},
        'source_obligations':debt,'hidden_self_check':None,'fixed_bpm':None,
        'performance_observed':False,'grants_credit':False,'automatic_mastery':False,
        'required_owner_extensions':['closed graph factory with per-definition own closure',
            'typed finite branches/domain lookups/source-slice calls/readiness effects',
            'release-first terminal failure and explicit restart preserving history/exposure/debt']}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();h=helpers(root);cache={}
    def pinned(r):
        n=r['path'];p=Path(n);h.require(not p.is_absolute() and '..' not in p.parts,'RELATIVE_INPUT');p=root/p
        h.require(p.resolve().is_relative_to(root) and not any(q.is_symlink() for q in [p,*p.parents]),'INPUT_ESCAPE')
        if n not in cache:cache[n]=p.read_bytes()
        h.require(h.sha(cache[n])==r['sha256'] and ('bytes' not in r or len(cache[n])==r['bytes']),'INPUT_PIN:'+n);return cache[n]
    s=h.strict(pinned({'path':SELECTION,'sha256':SELECTION_SHA}));pinned(s['compiler_dependency']);pinned(s['schema_proposal'])
    descriptor=h.strict(pinned(s['current_descriptor']));accepted={x['selection']['package_key'] for x in descriptor['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'}
    ledger={x['package_key']:x for x in map(h.strict,pinned(s['ledger']).splitlines())}
    for r in s['source_models']:pinned(r)
    contexts={r['path']:h.strict(pinned(r)) for r in s['contexts']};family=h.strict(pinned(s['direction_family']))
    originals={};metadata={}
    for r in s['rows']:
        key=r['key'];l=ledger[key];h.require(key not in accepted and l['official_status']=='Pending' and l['dispatch_ownership']=={'broad_lane_excluded':False,'transferred_shard':None} and l['official_acceptance_binding'] is None,'EXACT_PENDING_NONTRANSFERRED')
        raw=pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw)
        h.require(h.sha(raw)==r['original_row_sha256'] and h.sha(h.encoded(o))==r['original_compact_sha256'] and o['package_key']==key and o['source_identity']==r['source_identity'] and o['unresolved_reasons']==[] and o['implementation']['kind'] in PROGRAMS,'SOURCE_ROW_BINDING')
        originals[key]=o;metadata[key]=r
    family_keys=[x['package_key'] for x in family['source_cases']];h.require(len(family_keys)==8 and set(family_keys)<=set(originals),'DIRECTION_FAMILY_CLOSED')
    family_labels=[originals[k]['source_payload']['label'] for k in family_keys]
    shared_pairs=[v for k in family_keys for v in pair_domain(k,originals[k]['implementation']['manual_execution_contract'])]
    rows=[];counts=collections.Counter()
    for key,o in originals.items():
        kind=o['implementation']['kind'];program=enclosure_program(h,o) if kind=='manual_enclosure_contract' else roll_program(h,o,family_keys,family_labels)
        counts[program['name']]+=1;r=metadata[key]
        context_ref=next(x['path'] for x in o['source_refs'] if x['path'].endswith('source-context.json'))
        rows.append({'schema':h.SCHEMA,'source_key':key,'source_identity':o['source_identity'],
            'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],
            'contract_sha256':h.sha(h.encoded(program)),'payload_ref':r['payload_ref'],'source_pins':r['source_pins'],
            'context_ref':context_ref,'original_record':o,'program':program,
            'qualification':'Closed48future-native graph specification; original source kind retained. No current native execution/installed/accepted/performance/credit claim.'})
    h.require(len(rows)==48 and len(counts)==5 and sorted(counts.values())==[8,8,8,8,16],'EXACT_48_FIVE_PROGRAMS')
    closure={'schema':'fathom.compiled-manual-curriculum-closure.1','table_schema':'fathom.additive-manual-procedure-graph.1',
        'selection':{'path':SELECTION,'sha256':SELECTION_SHA},'schema_proposal':s['schema_proposal'],
        'ledger':s['ledger'],'current_descriptor':s['current_descriptor'],'contexts':contexts,
        'cached_inputs':s['packets'],'source_models':s['source_models'],'direction_family_ref':s['direction_family'],
        'shared_domains':{'direction_family_pairs':shared_pairs},'keys':[r['source_key'] for r in rows],
        'contracts':{r['source_key']:r['contract_sha256'] for r in rows},'program_counts':dict(counts),
        'source_files_reread':0,'runtime_admitted':False,'grants_credit':False}
    return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),
        'rows':48,'programs':5,'graph_nodes':sum(len(r['program']['graph']['nodes']) for r in rows)}

def validate_bundle(rows,closure,expected):
    h=helpers(Path(__file__).resolve().parents[2]);h.require((rows,closure)==expected,'EXACT_EXPORT_DRIFT')
    bykey={r['source_key']:r for r in rows};h.require(len(bykey)==48 and list(bykey)==closure['keys'],'CLOSED48')
    family_keys=sorted({x['selection']['source_key'] for x in closure['shared_domains']['direction_family_pairs']})
    family_labels=[bykey[k]['original_record']['source_payload']['label'] for k in family_keys]
    # Recompute in source-family order, which is significant for audit forms.
    family_rows=[r for r in rows if r['original_record']['implementation']['kind']=='manual_recorded_direction_roll'];family_keys=[r['source_key'] for r in family_rows];family_labels=[r['original_record']['source_payload']['label'] for r in family_rows]
    for r in rows:
        o=r['original_record'];p=r['program'];g=p['graph'];kind=o['implementation']['kind']
        derived=enclosure_program(h,o) if kind=='manual_enclosure_contract' else roll_program(h,o,family_keys,family_labels)
        h.require(p==derived and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']] and h.sha(h.encoded(o))==r['original_compact_sha256'],'SOURCE_PROGRAM_RECOMPUTATION')
        h.require(p['steps']==[] and p['mode']=='graph' and g['entry'] in g['nodes'] and p['source_facts']['printed_events']==o['implementation']['events'],'GRAPH_NOT_NARROWED_LINEAR')
        for name,n in g['nodes'].items():
            h.require(n['kind'] in ['report','choice','end'],'NODE_KIND')
            if n['kind']=='end':continue
            h.require(n['schema']['additionalProperties'] is False and 'default' not in json.dumps(n['schema']) and set(n['schema']['properties'])==set(n['schema']['required']),'CLOSED_BLANK_FORM')
            if n['kind']=='report':h.require(n['next'] in g['nodes'],'REPORT_EDGE')
            else:
                field=n['route_field'];h.require(set(n['routes'])==set(n['schema']['properties'][field]['enum']),'EXACT_CHOICE_ROUTES')
                for route in n['routes'].values():
                    if 'native_protocol' in route:h.require(route['native_protocol'] in ['stop','retry_from_entry'],'OWNED_PROTOCOL')
                    else:h.require(route['next'] in g['nodes'],'CHOICE_EDGE')
                    h.require(len(route.get('calls',[]))<=2,'FINITE_SOURCE_CALLS')
                    for call in route.get('calls',[]):
                        h.require(call['source_key'] in bykey and call['entry'] in bykey[call['source_key']]['program']['graph']['nodes'] and call['exit']=='separate_report','EXACT_SOURCE_SLICE')
        h.require(g['failure_policy']['terminal_current_pass'] is True and g['failure_policy']['nonphysical_failure_activates_physical'] is False and p['fixed_bpm'] is None and p['grants_credit'] is False and p['performance_observed'] is False,'SOURCE_FAILURE_NO_AUTHORITY')
        for e in o['implementation']['events']:
            h.require(e['onset_q'] is None and e['duration_q'] is None,'NO_INVENTED_CLOCK')
        if kind=='manual_enclosure_contract':
            c=o['implementation']['manual_execution_contract'];mate=bykey[c['paired_cell']['package_key']]
            h.require(mate['original_record']['implementation']['manual_execution_contract']['paired_cell']['package_key']==r['source_key'],'EXACT_RECIPROCAL_PAIR')
        elif 'hybrid' not in kind:
            h.require(g['domains']['failed_pass_pairs']==pair_domain(r['source_key'],o['implementation']['manual_execution_contract']),'EXACT_FAILED_PASS_PAIRS')
    return True

def generate(root,out=OUT):
    h=helpers(root);rows,closure,metrics=build(root);validate_bundle(rows,closure,(rows,closure))
    target=Path(root)/out;h.require(not Path(out).is_absolute() and '..' not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False)
    files={'definitions.jsonl':b''.join(h.encoded(r)+b'\n' for r in rows),'family-closure.json':h.encoded(closure)+b'\n'}
    q=lambda x:json.dumps(x,ensure_ascii=False)
    header=['#pragma once','#include <array>','namespace fathom::tasks::manual_procedure_branching_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+q(h.sha(h.encoded(closure)))+';','inline const std::array<Row,48> rows = {{']
    header+=['{'+q(r['source_key'])+','+q(h.encoded(r).decode())+'},' for r in rows]
    header+=['}};','struct Context { const char* path; const char* value; };','inline const std::array<Context,2> contexts = {{']
    header+=['{'+q(p)+','+q(h.encoded(c).decode())+'},' for p,c in closure['contexts'].items()]
    header+=['}};','inline constexpr const char* sharedDomainsJson='+q(h.encoded(closure['shared_domains']).decode())+';','}'];files['GeneratedManualProcedureBranching.hpp']=('\n'.join(header)+'\n').encode()
    pins=[]
    for name,raw in files.items():
        p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    receipt={'outcome':'GRAPH_DATA_CONSTRUCTION_PASS_NATIVE_ENGINE_PENDING','metrics':metrics,'files':pins,
        'program_counts':closure['program_counts'],'source_files_read':0,'native_paths_executed':0,'official_acceptance_increment':0}
    (target/'generation-receipt.json').open('x').write(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--out',default=OUT);a=p.parse_args();print(json.dumps(generate(a.root,a.out)))
