#!/usr/bin/env python3
"""Source-safe B23 protocol/atlas/assessment DATA using the shared criterion code.

Original B kind and source span witnesses remain distinct from the A helper's
temporary input shape. No generic original done bit is admitted as implementation.
Musical extents precede manual criterion forms; no source choices/music/clock are
invented. Every bridge and independently reviewed visual correction is explicit.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,re,time,collections
BASE='Build/manager-resume-r03/manual-curriculum-protocols23-r01'
SELECTION=BASE+'/selection-r02.json'
SELECTION_SHA='55ba6a1012daae292e478dd1578feb708c4d96ca269b2b911aac5456b389b6ae'
BINDING=BASE+'/shared-criterion-helper-binding.json'
OUT=BASE+'/generated-r03'

def load_helper(root,binding):
    p=Path(root)/binding['path'];raw=p.read_bytes()
    if len(raw)!=binding['bytes']or hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('SHARED_HELPER_PIN')
    spec=importlib.util.spec_from_file_location('frozen_source_criterion_helper',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);return h

def data_guard(h,g,payload,materials,saved=None,failed=None):
    """Closed future B policy oracle. Native ownership proof is separate."""
    if g['kind']=='source_material_reuse':
        h.require(set(g)=={'kind','field','catalog','no_new_printed_notes'}and g['catalog']=='level063_modules_a_i'and g['no_new_printed_notes']is True,'CLOSED_MATERIAL_GUARD');h.require(g['field']in payload,'MISSING_MATERIAL');value=payload[g['field']];h.require(type(value)in [str,type(None)],'MATERIAL_TYPE');return value is not None and value in {r['key']for r in materials}
    if g['kind']=='source_protocol_reported':
        policy=g.get('policy')
        if policy=='timed_ladder':
            h.require(set(g)=={'kind','policy','work_field','rest_field','clean_sets_field','source_work_targets','minimum_clean_sets','final_set_count_is_private_minimum'}and g['source_work_targets']==[15,15,15,15,30,30,45,45,60]and g['minimum_clean_sets']==[1,3,2,2,1]and g['final_set_count_is_private_minimum']is True,'CLOSED_LADDER_GUARD')
            a,b,c=[payload[k]for k in [g['work_field'],g['rest_field'],g['clean_sets_field']]];h.require(type(a)is list and type(b)is list and type(c)is list and len(a)==len(b)==9 and len(c)==5 and all(type(x)in [int,type(None)]for x in a+b+c),'LADDER_REPORT_TYPE')
            return all(x is not None for x in a+b+c)and all(x>=n and y>=x for x,y,n in zip(a,b,g['source_work_targets']))and all(x>=n for x,n in zip(c,g['minimum_clean_sets']))
        if policy=='four_bar_system_ceiling':
            h.require(set(g)=={'kind','policy','systems_field','block_width','maximum_distinct'}and g['block_width']==4 and g['maximum_distinct']==2,'CLOSED_SYSTEM_CEILING');v=payload[g['systems_field']];h.require(type(v)is list and len(v)==16 and all(type(x)in [str,type(None)]for x in v),'SYSTEM_REPORT_TYPE');return all(x in ['crosspick','hybrid','down_sweep','up_sweep']for x in v)and all(len(set(v[i:i+4]))<=2 for i in range(0,16,4))
        raise ValueError('UNKNOWN_SOURCE_PROTOCOL')
    return h.data_guard(g,payload,saved,failed)

def source_lines(o,visual):
    """Exact selected source spans; one visual clause is an additive witness."""
    body=o['implementation']['source_scope']['selected_source_text'];label=o['source_payload']['label'];spans=[]
    def line(text,start=None,*,visual_ref=None):
        if not text.strip():return
        if visual_ref:
            spans.append({'text':text,'witness':{'kind':'independently_reviewed_visual_clause','path':visual_ref}});return
        if start is None:
            matches=[m.start()for m in re.finditer(re.escape(text),body)];assert matches,'SOURCE_LITERAL_NOT_FOUND';start=matches[0]
        assert body[start:start+len(text)]==text
        spans.append({'text':text,'witness':{'kind':'original_record_span','original_record_path':['implementation','source_scope','selected_source_text'],'start':start,'end':start+len(text),'text_sha256':hashlib.sha256(text.encode()).hexdigest()}})
    line(label)
    if '-supplement'in o['package_key']:
        line(label);return spans
    if label=='Timed block ladder':
        line('Stage Work Rest Standard')
        for stage,seconds,standard in [(1,15,'1 clean set'),(2,15,'3 clean sets'),(3,30,'2 clean sets'),(4,45,'2 clean sets'),(5,60,'same tone start to finish')]:line(f'{stage} {seconds} sec {seconds} sec {standard}')
        return spans
    cursor=0
    for text in body.splitlines():
        start=body.find(text,cursor);cursor=start+len(text)
        if text==label:continue
        if o['level']==60 and label.startswith('Formula atlas')and text.startswith('RFUifLthE '):
            row=visual['visually_read_fifth_row'];line('Fifth '+ ' '.join(row[q]for q in ['maj7','7','m7','m7b5']),visual_ref='visually_read_fifth_row')
        else:line(text,start)
    assert len(spans)>1;return spans

def profile(o):
    label=o['source_payload']['label'];page=o['implementation']['source_scope']['locator']['physical_page']
    if page==2:return 'source_foundation_atlas'
    if page==20:return 'source_mastery_criteria_log'
    if '-supplement'in o['package_key']:return 'source_system_transition'if page==16 else'source_recovery_directive'
    return {'Timed block ladder':'source_timed_ladder','Phrase-endurance ladder':'source_phrase_endurance','Recording audit':'source_recording_quality','Four-pass orchestration':'source_four_pass_orchestration','Dynamic and density arc':'source_dynamic_form','Final recorded assignment':'source_final_recorded_assignment'}[label]

def make_program(h,o,visual,materials):
    spans=source_lines(o,visual);label=o['source_payload']['label'];kind=profile(o)
    virtual={'source_payload':{'printed_label':label},'implementation':{'task_contract':{'ordered_source_instructions':[{'order':i+1,'text':x['text']}for i,x in enumerate(spans)],'task_kind':o['implementation']['interaction_contract']['source_task_kind']}}}
    joined,metadata,criteria=h.partition(virtual['implementation']['task_contract'])
    # This B source header expresses a capability, not an exercised count.
    # Preserve the exact original span as visible metadata, outside gates.
    for x in list(criteria):
        if o['level']==60 and kind=='source_mastery_criteria_log' and 'THE PICK MAY MOVE THROUGH FOUR STRINGS;' in x['literal']:
            criteria.remove(x);x['role']='source_capability_header';x['manual_gate']=False;metadata.append(x)
    nodes={};tags=['source_extent',*[x['id'] for x in criteria]]
    nodes['source_extent']=h.report('Perform the complete selected source unit before entering criterion reports. Retain uninterrupted musical form and every source-internal stop/release/relocation duty; no music or clock is generated. '+joined,{'source_extent_evidence':h.text(True,4096),'unreported_stop_condition':h.menu(['none_reported','stop_or_tension_reported','unknown'],True)},{'unreported_stop_condition':'none_reported'},criteria[0]['id'],[h.source_ref(i) for i in range(len(spans))],constraints=[{'kind':'nonempty_trimmed_text','field':'source_extent_evidence','minimum':1,'maximum':4096}],physical=True,tag='source_extent')
    for i,x in enumerate(criteria):
        fields={'reported_outcome':h.menu(['reported_met','reported_not_met','unknown'],True),'manual_evidence':h.text(True,2048)};expected={'reported_outcome':'reported_met'};guards=[{'kind':'nonempty_trimmed_text','field':'manual_evidence','minimum':1,'maximum':2048}]
        x['quantities']=h.quantities(x['literal']);x['evidence_kind']='source_criterion_manual_report';x['observed']=False
        # Error-repair instructions are conditional on their named diagnosis;
        # the printed extent is not a universal completion requirement.
        if x['literal'].startswith(('TENSION shorten','CHORD IDENTITY LOST return')):
            for q in x['quantities']:
                q['role']='conditional_source_repair_fact';q['unconditional_completion_gate']=False
        for q in x['quantities']:
            if q['role']!='manual_count_criterion':continue
            field=q['id']+'_reported_'+h.slug(q['unit']);fields[field]=h.integer();q['report_fields']=[field]
            if q['comparison']=='exact':expected[field]=q['value']
            else:guards.append({'kind':q['comparison'],'field':field,'value':q['value']})
        if re.search(r'two separate (?:clean )?days',x['literal'],re.I):
            for day in [1,2]:
                fields['date_'+str(day)]=h.text(True,10);fields['day_'+str(day)+'_evidence']=h.text(True,2048);fields['day_'+str(day)+'_outcome']=h.menu(['reported_met','reported_not_met','unknown'],True);expected['day_'+str(day)+'_outcome']='reported_met';guards.append({'kind':'nonempty_trimmed_text','field':'day_'+str(day)+'_evidence','minimum':1,'maximum':2048})
            guards.append({'kind':'distinct_dates','fields':['date_1','date_2']});x['two_distinct_manual_dates']=True
        nodes[x['id']]=h.report(x['literal']+' Enter the actual source criterion outcome and evidence; unknown/unmet remains unresolved.',fields,expected,criteria[i+1]['id'] if i+1<len(criteria) else 'end_unit',x['source_action_refs'],constraints=guards,tag=x['id'],save=x['id'])
    nodes['end_unit']=h.end('user_reported_selected_source_criteria_only_no_mastery_or_credit')
    nodes['repair_bind']=h.report('Bind the failed criterion and diagnosis. This report does not replace its failed evidence.',{'failed_criterion':h.menu(tags),'diagnosis':h.text(True,2048)},{},'repair_choice',[],constraints=[{'kind':'same_as_failed_pass','payload_ref':h.ref('payload','failed_criterion')},{'kind':'nonempty_trimmed_text','field':'diagnosis','minimum':1,'maximum':2048}],save='repair')
    nodes['repair_choice']=h.choice('Explicitly restart the complete source unit or stop. Preserve all failed reports, source debt and owned release.','repair_action',['restart_complete_source_extent','stop'],{'restart_complete_source_extent':{'next':'source_extent','native_protocol':'retry_from_entry'},'stop':{'next':'end_unit','native_protocol':'stop'}})
    p={'name':'b_'+kind,'mode':'graph','steps':[],'graph':{'schema':'fathom.manual-procedure-graph.1','entry':'source_extent','nodes':nodes,'domains':{},'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':'source_extent','failed_pass_repair_entry':'repair_bind'},'call_semantics':'No generated notes, clocks or source-material choice. Reports follow the complete source extent.','loop_semantics':'Only explicit complete restart with retained debt/history; no automatic repetition.'},'source_criteria':criteria,'source_metadata':metadata,'source_literal_sha256':h.sha(joined.encode()),'source_kind':'manual_curriculum_task','source_task_kind':virtual['implementation']['task_contract']['task_kind'],'source_literal_ref':{'source_span_witnesses':spans,'normalization':'Single space between exact curated source lines; only four Fifth formulas are bound to additive accepted visual evidence. Original Rule/layout text remains unchanged in original/context refs.'},'learner_instruction_context_ref':{'original_record_paths':[['source_payload','label'],['implementation','context_tasks']],'source_span_witnesses_required':True},'source_limits':[],'future_guard_extensions':['minimum','maximum','distinct_dates','nonempty_trimmed_text'],'source_obligations_ref':{'broader_context_discharged':False},'source_clock':None,'sounding_span':None,'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'recording_observed':False,'grants_credit':False,'automatic_mastery':False,'runtime_admitted':False}
    def bind(r):
        path=r['original_contract_path'];assert len(path) == 2 and path[0]=='ordered_source_instructions';return copy.deepcopy(spans[path[1]]['witness'])
    for n in p['graph']['nodes'].values():
        if 'source_action_refs'in n:n['source_span_refs']=[bind(r)for r in n.pop('source_action_refs')]
    for x in p['source_criteria']+p['source_metadata']:x['source_span_refs']=[bind(r)for r in x.pop('source_action_refs')]
    # Additional typed fields distinguish source mechanics from a generic done
    # bit. These are manual declarations; they cannot verify acoustic facts.
    nodes=p['graph']['nodes'];first=p['source_criteria'][0]['id'];extent=nodes['source_extent']
    def add(node,name,schema,expected=None):
        node['schema']['properties'][name]=schema;node['schema']['required'].append(name)
        if expected is not None:node['expected'][name]=expected
    def bool_field(node,name):add(node,name,h.boolean(),True)
    def count_field(node,name,n):add(node,name,h.integer(),n)
    if kind.startswith('source_')and o['level']==63:
        if kind in ['source_system_transition','source_recovery_directive','source_timed_ladder','source_phrase_endurance']:
            add(extent,'reused_source_material_key',h.menu([r['key']for r in materials]));extent['constraints'].append({'kind':'source_material_reuse','field':'reused_source_material_key','catalog':'level063_modules_a_i','no_new_printed_notes':True});bool_field(extent,'printed_note_geometry_order_retained')
        for duty in ['source_muting_preserved','source_chord_identity_preserved','source_stop_and_release_duties_followed']:bool_field(extent,duty)
    if kind=='source_system_transition':
        text=label.lower();before='crosspick' if text.startswith('crosspick') else 'hybrid' if text.startswith('hybrid') else 'sweep';after='hybrid' if '-> hybrid' in text else 'sweep' if '-> sweep' in text else 'crosspick'
        add(nodes[first],'reported_system_before',h.menu(['crosspick','hybrid','sweep']),before);add(nodes[first],'reported_system_after',h.menu(['crosspick','hybrid','sweep']),after)
        if 'repeat 2'in text:count_field(nodes[first],'reported_switch_repeat',2)
        if 'full release'in text:bool_field(extent,'full_hand_release_before_crosspick')
        if 'low register'in text:bool_field(extent,'crosspick_low_then_hybrid_high_register')
        if 'question'in text:bool_field(extent,'hybrid_question_then_sweep_answer')
        if 'recovery'in text:bool_field(extent,'source_sweep_burst_then_crosspicked_recovery')
    if kind=='source_recovery_directive':
        for duty in {'crosspick':['only_three_note_roll_recovery'],'hybrid':['pick_only_target_after_finger_miss'],'sweep':['burst_stopped_on_highest_clean_note'],'pick':['next_target_is_new_downstroke'],'fatigue':['complete_full_beat_rest','density_reduced']}[label.split()[0].lower()]:bool_field(extent,duty)
        add(extent,'actual_trigger_and_source_repair_evidence',h.text(True,2048));extent['constraints'].append({'kind':'nonempty_trimmed_text','field':'actual_trigger_and_source_repair_evidence','minimum':1,'maximum':2048})
    if kind=='source_timed_ladder':
        durations=[15,15,15,15,30,30,45,45,60];add(nodes[first],'reported_work_seconds',{'type':'array','items':h.integer(),'minItems':9,'maxItems':9});add(nodes[first],'reported_rest_seconds',{'type':'array','items':h.integer(),'minItems':9,'maxItems':9});add(nodes[first],'reported_clean_sets_by_stage',{'type':'array','items':h.integer(),'minItems':5,'maxItems':5});nodes[first]['constraints'].append({'kind':'source_protocol_reported','policy':'timed_ladder','work_field':'reported_work_seconds','rest_field':'reported_rest_seconds','clean_sets_field':'reported_clean_sets_by_stage','source_work_targets':durations,'minimum_clean_sets':[1,3,2,2,1],'final_set_count_is_private_minimum':True});p['source_limits'].append({'kind':'source_count_limit','requirement':'The source60-second final stage has no fixed set count; one is the preserved private minimum, not a printed count. Reported integer-second surface is authored bounded resolution; underlying work time is not observed.'})
    if kind=='source_phrase_endurance':
        count_field(nodes[first],'reported_completed_stages',5);add(nodes[first],'first_stage_work_seconds',h.integer());nodes[first]['constraints'].append({'kind':'minimum','field':'first_stage_work_seconds','value':15});add(extent,'chosen_four_bar_boundary',h.menu(['full_beat_rest','full_hand_release']));bool_field(extent,'chosen_boundary_preserved_per_four_bars');p['source_limits'].append({'kind':'source_timing_limit','requirement':'Only first one-chord stage specifies15seconds. Later stage duration and number of loops are unknown, no numerical schedule supplied.'})
    if kind=='source_recording_quality':
        for name in ['first_ten_second_recording_reference','final_ten_second_recording_reference']:add(nodes[first],name,h.text(True,2048));nodes[first]['constraints'].append({'kind':'nonempty_trimmed_text','field':name,'minimum':1,'maximum':2048})
        for d in ['note_length','pick_noise','finger_volume','skipped_string_muting','tempo','chord_identity']:add(nodes[first],'reported_'+d,h.menu(['same','worse','unknown'],True),'same')
        gate=next(x for x in p['source_criteria'] if 'clean on two days' in x['literal']);before=next(n for n in nodes.values() if n.get('next')==gate['id']);before['next']='tempo_choice';nodes['tempo_choice']=h.choice('Holding tempo leaves the two-day advancement gate unselected. Requesting that gate requires distinct dated evidence; no BPM or source clock is generated.','tempo_decision',['hold_tempo','report_two_clean_days'],{'hold_tempo':{'next':'end_tempo_held'},'report_two_clean_days':{'next':gate['id']}});nodes['end_tempo_held']=h.end('recording_audit_reported_tempo_gate_unselected')
        for day in [1,2]:
            add(nodes[gate['id']],'date_'+str(day),h.text(True,10));add(nodes[gate['id']],'day_'+str(day)+'_longest_block_evidence',h.text(True,2048));bool_field(nodes[gate['id']],'day_'+str(day)+'_longest_block_clean');nodes[gate['id']]['constraints'].append({'kind':'nonempty_trimmed_text','field':'day_'+str(day)+'_longest_block_evidence','minimum':1,'maximum':2048})
        nodes[gate['id']]['constraints'].append({'kind':'distinct_dates','fields':['date_1','date_2']});gate['two_distinct_manual_dates']=True;gate['conditional_on_explicit_tempo_gate_report']=True
        p['source_limits'].append({'kind':'source_tempo_gate','requirement':'Longest current block must be clean on two days before adding tempo. This recording unit retains the full source clause; a same-quality report alone never authorizes tempo advancement or verifies audio.'})
    if kind=='source_four_pass_orchestration':
        count_field(extent,'reported_complete_capstone_passes',4);bool_field(extent,'same_selected_capstone_note_inventory');bool_field(extent,'one_system_for_first_complete_capstone');bool_field(extent,'printed_rotation_second_pass');bool_field(extent,'register_choices_third_pass');bool_field(extent,'phrase_job_choices_fourth_pass')
    if kind=='source_dynamic_form':
        add(extent,'reported_dynamic_blocks',{'type':'array','items':h.text(),'minItems':5,'maxItems':5},['p','mp','mf','f','mp']);bool_field(extent,'bar16_complete_release');bool_field(extent,'recognized_arpeggio_contour');bool_field(extent,'chord_tone_each_harmonic_change');bool_field(extent,'full_beat_rest_each_four_bars');add(extent,'reported_systems_per_bar',{'type':'array','items':h.menu(['crosspick','hybrid','down_sweep','up_sweep']),'minItems':16,'maxItems':16});extent['constraints'].append({'kind':'source_protocol_reported','policy':'four_bar_system_ceiling','systems_field':'reported_systems_per_bar','block_width':4,'maximum_distinct':2})
    if kind=='source_final_recorded_assignment':
        for name in ['major_performance_recording_reference','minor_performance_recording_reference','first_printed_system_take_reference','second_function_chosen_take_reference']:add(extent,name,h.text(True,2048));extent['constraints'].append({'kind':'nonempty_trimmed_text','field':name,'minimum':1,'maximum':2048})
        for name in ['major16bar_performance','minor16bar_performance','first_take_printed_systems','second_take_by_musical_function','second_reportedly_more_musical']:bool_field(extent,name)
        p['source_limits'].append({'kind':'source_take_pairing_limit','requirement':'Source requires major/minor performances and first/second take roles; it does not explicitly fix whether each mode supplies its own two takes. This contract retains all four declared references without requiring four distinct recordings or inventing take-mode pairing. Independent source interpretation remains required.'})
    if kind=='source_foundation_atlas':
        if o['level']==60:count_field(extent,'reported_silent_formations',56);bool_field(extent,'root_quality_chord_tones_and_attack_zone_named');bool_field(extent,'formed_without_sounding');p['source_limits'].append({'kind':'additive_visual_source_clause','requirement':'Only four exact independent-reviewed Fifth formulas correct the rendered table row. Original Rule/layout text remains in original/context refs; source overlap and cached bytes unchanged.'})
        elif o['level']==61:
            for name in ['four_quality_target_hierarchy_named','approach_and_enclosure_formulas_reentered','final_repeated_target_pitch_center','delayed_resolution_grid_preserved']:bool_field(extent,name)
        else:
            for name in ['five_source_zones_named','six_shift_actions_in_source_order','skip_independent_attacks_and_muting','odd_loop_start_reversal','long_shift_cycle_preserved','muted_preview_before_sounding','four_chord_role_maps_named']:bool_field(extent,name)
    if kind=='source_mastery_criteria_log':
        # Source numerical duties outside A67's bounded noun vocabulary are
        # entered explicitly by their unambiguous printed gate clauses.
        gates={60:[('silent_commands',56),('blocked_arpeggiated_shapes',56),('seven_note_loop_cells',8),('same_root_quality_ladders',2),('major_progressions',6),('minor_progressions',6),('arpeggio_scale_links',6),('call_answer_pairs',8),('capstones',2)],61:[('target_rotations',16),('approach_cells',24),('zone_phrases',5),('adjacent_zone_response',1),('enclosure_cells',16),('delayed_resolutions',12),('motif_transformations',6),('recovery_cards',12),('major_phrases',6),('minor_phrases',6),('model_solos',2),('capstones',2)],62:[('triad_fragments',8),('seventh_routes',6),('motif_transformations',8),('inversion_chains',8),('recovery_cards',12),('bridge_templates',3),('major_routes',6),('minor_routes',6)]}[o['level']]
        for field,n in gates:
            add(extent,'reported_'+field,h.integer());extent['constraints'].append({'kind':'minimum','field':'reported_'+field,'value':n})
        if o['level']in [60,61]:
            for day in [1,2]:add(extent,'date_'+str(day),h.text(True,10));add(extent,'day_'+str(day)+'_capstone_evidence',h.text(True,2048));extent['constraints'].append({'kind':'nonempty_trimmed_text','field':'day_'+str(day)+'_capstone_evidence','minimum':1,'maximum':2048})
            extent['constraints'].append({'kind':'distinct_dates','fields':['date_1','date_2']})
        if o['level']==61:
            for day in [1,2]:add(extent,'day_'+str(day)+'_model_solo_evidence',h.text(True,2048));extent['constraints'].append({'kind':'nonempty_trimmed_text','field':'day_'+str(day)+'_model_solo_evidence','minimum':1,'maximum':2048})
        if o['level']==62:
            for field in ['triad_fragment_D_start','triad_fragment_U_start','seventh_route_D_start','seventh_route_U_start','all_recovery_without_stopping_form','capstone_key_sequence_and_cycle_preserved']:bool_field(extent,field)
        for name in ['reported_log_date','reported_log_focus','reported_log_next_target','reported_log_weak_link']:add(extent,name,h.text(True,2048))
        add(extent,'reported_log_bpm',h.integer());p['source_limits'].append({'kind':'manual_gate_scope','requirement':'Counts/date/evidence are learner declarations, not installed/accepted metadata or observed performance. Every source progression/diagnosis/log clause is retained. Unknown BPM stays unknown and does not grant tempo authority.'})
    p['original_kind_preserved']=True;p['runtime_admitted']=False;p['source_material_catalog_ref']='level063_modules_a_i';p['source_obligations_ref'].update({'original_context_and_full_page_ref':True,'full_parent_or_book_gate':False});p['future_guard_extensions']=sorted(set(p['future_guard_extensions'])|{'source_span_binding','source_material_reuse','source_protocol_reported'})
    return p,spans

def build(root):
    start=time.perf_counter();root=Path(root).resolve();raw=(root/SELECTION).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SELECTION_SHA:raise ValueError('SELECTION_PIN')
    s=json.loads(raw);binding=json.loads((root/BINDING).read_bytes());h=load_helper(root,binding);cache=h.Inputs(root)
    for r in [s['ledger'],s['current_descriptor'],s['excluded_c96'],s['exception_witness'],s['exception_independent_review'],*s['cached_inputs']]:cache.pinned(r)
    visual=h.strict(cache.pinned(s['exception_witness']));review=h.strict(cache.pinned(s['exception_independent_review']));h.require(review['decision']=='ACCEPT_EXACT_FOUR_VISIBLE_LEVEL060_FIFTH_SOURCE_CLAUSES' and review['reviewed_witness']==s['exception_witness'] and review['independent_observation']['visible_fifth_row']==visual['visually_read_fifth_row'],'VISUAL_INDEPENDENT_ACCEPT');accepted={x['selection']['package_key']for x in h.strict(cache.pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};rows=[];originals={};counts=collections.Counter()
    for r in s['rows']:
        raw=cache.pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);h.require(h.sha(raw)==r['original_row_sha256']and o['package_key']==r['key']and o['source_identity']==r['source_identity']and r['key']not in accepted and o['implementation']['kind']=='manual_curriculum_task','EXACT_PENDING_ROW');originals[r['key']]=o;p,spans=make_program(h,o,visual,s['source_material_catalog']);counts[p['name']]+=1;rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':['implementation'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'Source-span-bound manual source criteria DATA; source material/plan/clock/acoustic realization not generated. Native guard/factory/release source bridges and distinct review pending.'})
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'shared_criterion_helper':binding,'keys':[r['source_key']for r in rows],'contracts':{r['source_key']:r['contract_sha256']for r in rows},'cached_witnesses':s['cached_inputs'],'contexts':{r['path']:h.strict(cache.pinned(r))for r in s['cached_inputs']if r['path'].endswith('source-context.json')},'source_material_catalog':{'level063_modules_a_i':s['source_material_catalog']},'source_visual_witness':s['exception_witness'],'source_visual_independent_review':s['exception_independent_review'],'profile_counts':dict(counts),'profile_counts_are_not_behavior_equivalence':True,'native_integration_debt':['Manual_curriculum_task/implementation raw reference factory support without source-kind substitution','Source span refs with exact byte/text hash and accepted additive visual clause','Closed source_material_reuse/source_protocol_reported bridges, no synthetic picking/music','Unknown/negative criterion diagnosis/source debt/native release/history','Independent source/behavior/UI/installed package review; original done-bit insufficient'],'native_execution':False,'runtime_admitted':False,'grants_credit':False};validate(rows,closure,originals,h,visual,s['source_material_catalog']);return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':cache.hashes,'rows':23,'source_program_profiles':dict(counts),'source_criteria':sum(len(r['program']['source_criteria'])for r in rows),'graph_nodes':sum(len(r['program']['graph']['nodes'])for r in rows)},originals

def validate(rows,closure,originals,h,visual,materials):
    h.require(len(rows) == 23 and len({r['source_key']for r in rows}) == 23 and [r['source_key']for r in rows]==closure['keys'],'EXACT23')
    for r in rows:
        p=r['program'];expected,_=make_program(h,originals[r['source_key']],visual,materials);h.require(p==expected and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'EXACT_PROGRAM')
        h.require(p['source_kind']=='manual_curriculum_task'and r['retained_contract_path']==['implementation']and p['performance_observed']is False and p['runtime_admitted']is False and p['grants_credit']is False,'NO_SOURCE_KIND_SUBSTITUTION_OR_AUTHORITY')
        for n in p['graph']['nodes'].values():
            if n['kind']=='end':continue
            h.require(n['schema']['additionalProperties']is False and set(n['schema']['properties'])==set(n['schema']['required'])and 'default'not in json.dumps(n['schema']),'CLOSED_SCHEMA')
    return True

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);h=load_helper(root,json.loads((Path(root)/BINDING).read_bytes()));target=Path(root)/out;h.require(not Path(out).is_absolute()and '..'not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False);pins=[]
    for name,raw in {'definitions.jsonl':b''.join(h.encoded(r)+b'\n'for r in rows),'family-closure.json':h.encoded(closure)+b'\n'}.items():p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'CLOSED23_SOURCE_PROTOCOL_CRITERIA_DATA_PASS_NATIVE_PENDING','metrics':metrics,'files':pins,'original_pdf_reads_here':0,'native_paths_executed':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
