#!/usr/bin/env python3
"""Closed A49 harmonic-contact DATA from cached witnesses; no runtime admission."""
import argparse, collections, copy, hashlib, importlib.util, json, pathlib, re, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT_REL = 'Build/manager-resume-r03/harmonic-contact-data49-r01'
LEDGER = {'path':'Build/manager-resume-r03/family-inventory-r01/family-ledger.jsonl','bytes':20737074,'sha256':'ce8ad63e95cf1670804f058833ec43538d42a611f260d5d1711ee17fc5925d4b'}
KIND = 'harmonic_contract_metric_pending'
SPEC = importlib.util.spec_from_file_location('inventory_core', pathlib.Path(__file__).with_name('build_family_inventory.py'))
I = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(I)

def need(value, reason):
    if not value: raise ValueError(reason)

def compact(value): return json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False).encode()
def insertion(value): return json.dumps(value, separators=(',',':'), ensure_ascii=False, allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, value): path.open('xb').write(compact(value)+b'\n')
def strict(raw): return I.strict_json(raw)
def integer(value, low, high): return type(value) is int and low <= value <= high
def context_refs(context):
    if context['level'] == 40:
        return [context['root_role_rest_correction']['evidence'], context['completion_cadence_source_actions']['source_context'], context['relative_center_response_source_actions']['source_context']]
    return [context['root_role_rest_correction']['evidence'], context['additional_pdf_guidance'], context['manual_ear_matching_supplement']['source_guidance']]

def tag(level, module):
    return {(40,'A'):'triad_target_cell', (40,'D'):'relative_center_call_answer',
            (40,'E'):'completion_cadence', (40,'F'):'eight_bar_center_shift',
            (40,'G'):'controlled_phrase_model', (46,'A'):'dominant_target_cell'}[(level,module)]

def source_guard(original, entry, context):
    impl = original['implementation']; atoms = impl['ordered_contacts']; level = original['level']
    need(original['package_key'] == entry['package_key'] and original['source_identity'] == entry['source_identity'] and level == entry['level'] == context['level'], 'SOURCE_IDENTITY')
    need(impl['kind'] == KIND and impl['runtime_eligible'] is False and impl['canonical_ids_allocated'] is False and impl['mastery_or_credit'] is False, 'SOURCE_KIND_NONADMISSION')
    need(not original['source_payload']['source_discrepancy'] and impl['ordered_rest_locations'] == [] and impl['metric_duration_is_acoustic_gate'] is False, 'NO_SOURCE_CONFLICT_OR_INVENTED_REST')
    timing = original['timing_authority']
    need(timing['fixed_bpm'] is None and timing['selected_projection'] is None and timing['duration_q'] is None and timing['end_q'] is None and timing['ascii_spacing_is_duration'] is False and timing['relative_grid_rows'] == [], 'UNKNOWN_METRIC_CLOCK')
    profile = tag(level, impl['source_module'])
    matrix = context['harmonic_role_matrix'] if level == 40 else context['chord_roles']
    label = original['source_payload']['printed_label']; declared = re.search(r'(\d+)-NOTE TARGET CELL', label.upper())
    if declared: need(len(atoms) == int(declared.group(1)), 'PRINTED_EXTENT')
    need(len(atoms) > 0 and context['root_role_rest_correction']['root_role_is_not_silence'] is True, 'ROOT_ROLE_AUTHORITY')
    for n, atom in enumerate(atoms, 1):
        need(type(atom['ordinal']) is int and atom['ordinal'] == n and atom['kind'] == 'printed_fret_contact', 'ORDINAL_TYPE_ORDER')
        need(integer(atom['string_low_to_high'],1,6) and atom['string_label'] == ['E','A','D','G','B','e'][atom['string_low_to_high']-1] and integer(atom['fret'],0,127), 'PRINTED_CONTACT')
        need(integer(atom['midi'],0,127) and atom['onset_q'] is None and atom['duration_q'] is None and atom['acoustic_gate_q'] is None, 'SOURCE_MIDI_UNKNOWN_SPANS')
        need(atom['pick_attack'] is True and atom['attack'] == 'picked' and atom['same_column_contact_count'] == 1, 'SOURCE_ATTACK_GROUP')
        need(integer(atom['source_line'],1,100000) and integer(atom['source_column_1based'],1,100000), 'SOURCE_LOCATOR')
        need(atom['harmonic_role'] == matrix[atom['harmony']][atom['note_spelling']], 'SOURCE_CHORD_ROLE')
        need(atom['annotations']['Nte'] == atom['note_spelling'], 'SOURCE_NOTE_ANNOTATION')
        role_annotation = 'Job' if level == 40 else 'Rol'
        need(atom['annotations'][role_annotation] == atom['harmonic_role'], 'SOURCE_ROLE_ANNOTATION')
        if level == 40:
            need(integer(atom['finger'],1,4) and atom['finger_authority'] == 'printed Fng row' and atom['annotations']['Fng'] == str(atom['finger']), 'PRINTED_FINGER')
            need(atom['degree'] == atom['annotations']['F#m'] and atom['completion_tone'] == (atom['degree'] == '*'), 'SOURCE_DEGREE_COMPLETION')
        else:
            need(atom['finger'] is None and atom['finger_authority'] == 'optional unprinted digit' and atom['harmonic_role'] in ('R','3','5','b7'), 'UNKNOWN_FINGER_DOMINANT_TARGET')
    if level == 40: need(impl['harmony_sequence'] == [a['harmony'] for a in atoms], 'EXACT_HARMONY_SEQUENCE')
    if profile in ('triad_target_cell','dominant_target_cell'):
        variants = impl['variants']; need(len(variants) == 2 and [v['pick_start'] for v in variants] == ['D','U'], 'SAVED_BOTH_STARTS')
        for v in variants:
            need(v['contact_ordinals'] == list(range(1,len(atoms)+1)), 'VARIANT_SOURCE_ORDINALS')
            need(v['strokes_by_contact'] == [v['pick_start'] if n%2 == 0 else ('U' if v['pick_start'] == 'D' else 'D') for n in range(len(atoms))], 'SAVED_CONTINUOUS_PICK_ORDER')
    else: need('variants' not in impl, 'NO_UNPRINTED_PICK_START_VARIANTS')
    if profile == 'relative_center_call_answer':
        response = impl['source_response_relationship']
        need(len(atoms) == 12 and response['governing_workbook_tonic'] == 'F#' and response['selected_pass'] == 'existing_plain_fretted_picked_pass', 'RESPONSE_SCOPE')
        need(response['selected_numeric_onsets'] is None and response['selected_numeric_acoustic_gates'] is None and response['quarter_unit_mapping'] is None and response['native_projection_complete'] is False and response['performance_or_credit_claimed'] is False, 'RESPONSE_UNKNOWN_CLOCK_NONCOMPLETION')
        need(len(response['phrases']) == 2 and len(response['shared_opening_joins']) == 4 and len(response['contact_roles']) == 12, 'RESPONSE_SOURCE_EXTENT')
        for n, phrase in enumerate(response['phrases']):
            need(phrase['contact_ordinals'] == list(range(n*6+1,n*6+7)) and phrase['active_chord'] == ('A' if n == 0 else 'F#m'), 'CALL_ANSWER_ORDER')
            need(phrase['ending_notes'] == [atoms[o-1]['note_spelling'] for o in phrase['ending_contact_ordinals']], 'RESPONSE_ENDING_NOTES')
            final = atoms[phrase['final_root_contact']-1]
            need(final['note_spelling'] == phrase['final_root_note'] == ('A' if n == 0 else 'F#') and final['harmonic_role'] == 'R', 'RESPONSE_HARMONIC_ROOT_NOT_REST')
        for join in response['shared_opening_joins']:
            call, answer = (atoms[join[k]-1] for k in ('call_ordinal','answer_ordinal'))
            for field, key in [('note_spelling','note'),('midi','midi'),('string_label','string_label'),('fret','fret'),('finger','finger')]:
                need(call[field] == answer[field] == join[key], 'SHARED_OPENING_PHYSICAL_PITCH_JOIN')
            need(call['harmonic_role'] == join['call_chord_role'] and answer['harmonic_role'] == join['answer_chord_role'], 'SHARED_OPENING_CHANGED_CHORD_ROLE')
        for role, atom in zip(response['contact_roles'],atoms):
            need(role['contact_ordinal'] == atom['ordinal'] and role['note'] == atom['note_spelling'] and role['active_chord'] == atom['harmony'] and role['chord_role'] == atom['harmonic_role'] and role['F_sharp_minor_degree'] == atom['degree'] and role['R_means_harmonic_root_not_rest'] == (atom['harmonic_role'] == 'R'), 'RESPONSE_ALL_SOURCE_ROLES')
    if profile == 'completion_cadence':
        cadence = impl['source_completion_cadence']
        need(len(atoms) == 12 and cadence['governing_tonic'] == 'F#' and cadence['direct_pass_contacts'] == list(range(1,13)) and cadence['selected_pass'] == 'direct_fretted_source_first_pass', 'CADENCE_SCOPE')
        need(cadence['selected_numeric_onsets'] is None and cadence['selected_numeric_acoustic_gates'] is None and cadence['quarter_unit_mapping'] is None and cadence['native_projection_complete'] is False and cadence['performance_or_credit_claimed'] is False, 'CADENCE_UNSELECTED_CLOCK')
        for n, (role, atom) in enumerate(zip(cadence['contact_roles'],atoms)):
            need(role['contact_ordinal'] == n+1 and role['bar'] == n//4+1 and role['within_bar_source_order'] == n%4+1 and role['source_beat'] == (1 if n%4 == 0 else None), 'SOURCE_BEAT_ONE_ONLY')
            need(role['note'] == atom['note_spelling'] and role['active_chord'] == atom['harmony'] and role['chord_role'] == atom['harmonic_role'] and role['outside_completion_tone'] == atom['completion_tone'] and role['R_means_harmonic_root_not_rest'] == (atom['harmonic_role'] == 'R'), 'CADENCE_SOURCE_ROLES')
        need([a['contact_ordinal'] for a in cadence['explicit_source_beat_one_anchors']] == [1,5,9] and all(a['quarter_onset'] is None for a in cadence['explicit_source_beat_one_anchors']), 'NO_BEAT_TO_QUARTER_INVENTION')
        for target in cadence['completion_targets']:
            atom = atoms[target['contact_ordinal']-1]; returned = atoms[target['return_to_pool_contact_ordinal']-1]
            need(target['note'] == atom['note_spelling'] and target['string_label'] == atom['string_label'] and target['fret'] == atom['fret'] and target['finger'] == atom['finger'] and target['return_note'] == returned['note_spelling'] and returned['note_spelling'] in cadence['pentatonic_pool'] and returned['ordinal'] == atom['ordinal']+1, 'COMPLETION_IMMEDIATE_POOL_RETURN')
        later = cadence['later_source_pass']
        if cadence['position'] in ('P1','P2'): need(later is None, 'NO_ANALOGICAL_SECOND_PASS')
        else:
            need(later['eligible_completion_contact_ordinals'] == [1,5] and later['completion_tones_to_approach'] == 1 and later['destination_beat_one_required'] is True, 'P3_P5_LATER_SLIDE_DUTY')
            need(all(later[k] is None for k in ('selected_completion_contact','selected_approach_origin','selected_approach_finger_or_attack','selected_curve_or_start_time')) and later['generated_approach_events'] == [] and later['selected'] is False, 'NO_GENERATED_SLIDE_REALIZATION')
    if profile == 'eight_bar_center_shift':
        need(len(atoms) == 32 and impl['harmony_sequence'] == [h for h in ('A','E','D','A','F#m','A','E','F#m') for _ in range(4)], 'EIGHT_BAR_CENTER_SHIFT')
    if profile == 'controlled_phrase_model': need(len(atoms) == 16 and type(impl['source_specific_rule']) is str and bool(impl['source_specific_rule'].strip()), 'EXACT_MODEL_RULE')
    return profile

def row_for(original, entry, raw, context_ref, profile):
    impl = original['implementation']
    row = {'schema':'fathom.reference-bound-harmonic-contact-definition.1', 'source_key':original['package_key'], 'source_identity':original['source_identity'], 'level':original['level'], 'existing_parent_id':original['existing_parent_id'], 'implementation_kind':impl['kind'], 'source_category':entry['current_payload']['category'], 'source_module':impl['source_module'], 'original_row_sha256':sha(raw), 'source_record_canonical_sha256':sha(compact(original)), 'source_record_compact_sha256':sha(insertion(original)), 'payload_ref':entry['current_payload']['ref'], 'retained_contract_path':['implementation'], 'context_ref':context_ref, 'source_pins':entry['source_pins'], 'unit':{'heading_path':original['source_payload']['parent_path'], 'printed_label':original['source_payload']['printed_label'], 'source_actions':copy.deepcopy(impl['task_steps']), 'source_action_refs':[['implementation','task_steps',n] for n in range(len(impl['task_steps']))], 'complete_notation_witness':['source_payload','exact_unit_lines']}, 'source_atoms':copy.deepcopy(impl['ordered_contacts']), 'source_contracts':copy.deepcopy({k:v for k,v in impl.items() if k not in ('kind','ordered_contacts','task_steps','ordered_rest_locations')}), 'timing_authority':copy.deepcopy(original['timing_authority']), 'unresolved_reasons':copy.deepcopy(original['unresolved_reasons']), 'ordered_rest_locations':[], 'instruction_policy_tag':profile, 'source_unknowns':{'unprinted_fingers_retained_null':sum(a['finger'] is None for a in impl['ordered_contacts']), 'source_clock':None, 'source_acoustic_gate':None, 'numeric_metric_projection':None, 'unsaved_pick_variants_not_created':True, 'performer_choices_are_not_source_facts':True}, 'boundaries':{'native_model_created':False,'runtime_admitted':False,'observed_performance':False,'whole_child_accepted':False,'grants_credit':False}}
    row['source_atoms_sha256'] = sha(compact(row['source_atoms'])); row['definition_sha256'] = sha(compact(row)); return row

def operator_blueprints():
    fields = {
        'triad_target_cell':['all_original_contacts','printed_harmonic_roles_named','original_contact_order','both_saved_pick_starts'],
        'dominant_target_cell':['all_original_contacts','root_third_fifth_flat_seventh_named','only_printed_chord_tones','both_saved_pick_starts'],
        'relative_center_call_answer':['all_original_contacts','A_call_then_F_sharp_minor_answer','same_shared_opening','changed_harmonic_roles','printed_A_then_F_sharp_endings','related_but_differently_centered'],
        'completion_cadence':['all_original_contacts','direct_fretted_D_and_G_sharp','source_beat_one_D_G_sharp_F_sharp','immediate_return_to_pentatonic_pool','final_F_sharp_harmonic_root'],
        'eight_bar_center_shift':['all_original_contacts','eight_original_chords','A_center_bars_one_to_four','F_sharp_center_bars_five_to_eight','source_drone_pass','source_no_drone_pass','final_F_sharp_more_final_than_A_at_bar_four'],
        'controlled_phrase_model':['all_original_contacts','original_harmony_schedule','literal_per_model_rule','original_two_bar_endings','secure_beat_one_before_inner_note_replacement']}
    programs = {}
    for name, required in fields.items():
        properties = {k:{'type':['string','null'],'enum':['reported_met','reported_not_met','unknown',None],'learner_label':k.replace('_',' ')} for k in required}
        properties['evidence'] = {'type':['string','null'],'maxLength':4096,'learner_label':'My manual source evidence'}
        programs[name] = {'required_reports':required, 'report_schema':{'type':'object','properties':properties,'required':required+['evidence'],'additionalProperties':False}, 'guards':[{'kind':'manual_reported_met','field':k} for k in required]+[{'kind':'nonempty_trimmed_text','field':'evidence'}], 'source_action_ref':['unit','source_actions'], 'negative_or_unknown':'Retain the raw report, diagnose unresolved and use only the exact source repair; no automatic successful performance.'}
    programs['completion_cadence']['conditional_later_pass'] = {'condition_ref':['source_contracts','source_completion_cadence','later_source_pass'], 'null_means_not_required':True, 'required_when_present':['one_completion_tone_approached_by_slide','same_source_beat_one_arrival'], 'source_selected_approach_remains_null':True, 'requires_separate_manual_realization':True}
    programs['completion_cadence']['conditional_blur_repair_ref'] = ['source_contracts','source_completion_cadence','conditional_blur_repair']
    return {'schema':'fathom.harmonic-contact-operator-blueprints.1', 'native_supported':False, 'instruction_policies':programs, 'policy_count_is_not_behavior_equivalence':True, 'source_atom_api_requirements':['value-owned closed source key/identity/witness binding','exact source ordinal/string/fret/optional printed finger/saved MIDI/spelling/annotation/role','optional numeric metric span and optional saved pick variant; no fallback','R means harmonic root and remains a picked contact'], 'future_shared_owner_requirements':['Reuse a shared source-handle/contact or graph owner; no per-row engine.','Source-role, relative-center and cadence typed manual reports with explicit source-supported repair and nonempty evidence.','Owned release/cancel/retry/navigation fences and persistent manual history/debt require native proof.','An unclocked report must expose source ordinal/groups and written beat anchors without presenting invented quarter onsets.'], 'trusted_contexts_not_learner_form_answers':True, 'external_obligations':{'level40':'Selected440 of580 written tones; ModuleB60 and C80 plus role matrix, drones, recording/two separate days, transfer/improvisation and external session duties remain exact broader manual obligations. Selected source contacts cannot establish book/parent/mastery.', 'level46':'Selected294-tone ModuleA only. Shells, target choruses, guide lines, position phrases, completion bends/slides, written chorus and improvised chorus remain broader source obligations, not manufactured realization or recording proof.'}, 'generated_alternative_contacts':0, 'native_models':0, 'official_acceptance_increment':0}

def build(root):
    start = time.perf_counter(); cache = I.Cache(root)
    ledger = [strict(x) for x in cache.read(LEDGER).splitlines()]; by = {x['package_key']:x for x in ledger}
    need(len(ledger) == len(by) == len({x['source_identity'] for x in ledger}) == 7271, 'LEDGER7271')
    descriptor_path = 'Planning/Fathom-Exercise-WBS-Annex-v1.json'; descriptor = cache.json(descriptor_path); descriptor_ref = cache.reference(descriptor_path)
    need(descriptor['base']['sha256'] == 'dc285a946a929ba08a7e0e1075d56f9c2eb53ce2dfa9c70ea67d34270d2bda6c', 'IMMUTABLE_BASE_REUSE')
    accepted = set()
    for op in descriptor['current_status_resolution']['operations']:
        selection = op['selection']; key = selection['package_key']
        need(key in by and key not in accepted and selection['source_identity'] == by[key]['source_identity'] and selection['existing_parent_id'] == by[key]['existing_parent_id'], 'CURRENT_DESCRIPTOR_JOIN')
        need(op['current_overlay']['status'] == 'Accepted' and op['current_overlay'].get('source_key',key) == key, 'STRICT_CURRENT_STATUS'); accepted.add(key)
    counts = descriptor['current_view']['children']['child_status_counts']
    need(counts == {'Accepted':len(accepted),'Pending':7271-len(accepted)}, 'CURRENT_COUNTS')
    excluded = {}
    paths = {'source67':{'path':'Build/manager-resume-r03/manual-source-assessments67-r01/generated-r03/family-closure.json','bytes':541776,'sha256':'552ebbe02073d087c59a692bb09bb4a37080faa2a92a70896f9f0e1bdb031616'}, 'piecewise17':{'path':'Build/manager-resume-r03/piecewise-contact-family-r01/cohort.json','bytes':374745,'sha256':'68a09de3c6db0ce94774fb7aa91900ee07dd678b0702dfbc76440e17f680f40a'}, 'ordered1401':{'path':'Build/manager-resume-r03/family-inventory-r01/native-projection-cohort.json','bytes':5380406,'sha256':'a6e3c5166d5fa4d2f1a282830cfca994ba93616088939704b0b5c18cb6e11dc0'}, 'physical339':{'path':'Build/manager-resume-r03/unpitched-contact-preparation-r01/cohort.json','bytes':367986,'sha256':'88f2cdffda1516c15e1d9f6aab617519b7d0313be3d92348c265d64bab300998'}}
    for name, ref in paths.items():
        obj = cache.json(ref)
        excluded[name] = set(obj['keys']) if name == 'source67' else {x['source_key'] for x in obj['rows']} if name == 'piecewise17' else {x['package_key'] for x in obj['candidates']} if name == 'ordered1401' else {x['key'] for x in obj['rows']}
    color_seal = cache.json('Build/manager-resume-r03/color-contact-data69-r01/frozen-closeout.json')
    for ref in cache.json(color_seal['artifact_manifest'])['artifacts']:
        if ref['path'].endswith('/selection.json'): color = cache.json(ref); excluded['color69'] = set(color['keys'])
    need({k:len(v) for k,v in excluded.items()} == {'source67':67,'piecewise17':17,'ordered1401':1401,'physical339':339,'color69':69}, 'EXACT_OWNERSHIP_SCOPES')
    pending_A = [x for x in ledger if (x['current_payload'] or {}).get('owner') == 'A' and not x['dispatch_ownership']['broad_lane_excluded'] and x['package_key'] not in accepted]
    owned = set.union(*excluded.values()); remaining = [x for x in pending_A if x['package_key'] not in owned]
    selected = [x for x in remaining if x['current_payload']['implementation_kind'] == KIND]
    need(len(selected) == 49 and collections.Counter(x['level'] for x in selected) == {40:34,46:15}, 'EXACT49_SCOPE')
    refs = {x['current_payload']['ref']['path']:x['current_payload']['ref'] for x in selected}; need(len(refs) == 2, 'EXACT_TWO_PACKETS')
    packets = {}; contexts = {}; context_pins = {}
    for path, ref in refs.items():
        packets[path] = cache.read(ref).splitlines(); context_path = str(pathlib.Path(path).parent/'level-source-context.json')
        context = cache.json(context_path); contexts[context['level']] = context; context_pins[context['level']] = cache.reference(context_path)
        for additional in context_refs(context): cache.read(additional)
    rows = []
    for entry in selected:
        cp = entry['current_payload']; raw = packets[cp['ref']['path']][cp['ref']['jsonl_line']-1]; original = strict(raw)
        need(sha(compact(original)) == cp['record_canonical_sha256'] and sha(insertion(original)) == cp['record_compact_order_sha256'], 'EXACT_ORIGINAL_ROW_PIN')
        context = contexts[entry['level']]
        for kind in ('pdf','txt'): need(context['originals'][kind]['sha256'] == entry['source_pins'][kind+'_sha256'], 'CONTEXT_SOURCE_AUTHORITY_JOIN')
        profile = source_guard(original, entry, context); rows.append(row_for(original, entry, raw, context_pins[entry['level']], profile))
    need(sum(len(r['source_atoms']) for r in rows) == 734 and sum(a['finger'] is None for r in rows for a in r['source_atoms']) == 294 and sum(len(r['source_contracts'].get('variants',[])) for r in rows) == 70, 'EXACT_CONTACT_FINGER_VARIANT_COUNTS')
    selection = {'schema':'fathom.harmonic-contact-selection.1','ledger':LEDGER,'descriptor_snapshot':descriptor_ref,'descriptor_preimage':OUT_REL+'/authority-descriptor-preimage.json','official_base_reused_by_saved_ledger_pin':descriptor['base'],'official_children':7271,'current_accepted':len(accepted),'current_pending':7271-len(accepted),'nontransferred_pending_A':len(pending_A),'unowned_source_indexed_A':len(remaining),'selected_keys':49,'excluded_owned_counts':{k:len(v) for k,v in excluded.items()},'excluded_owned_keys':{k:sorted(v) for k,v in excluded.items()},'keys':[r['source_key'] for r in rows],'source_identity':[r['source_identity'] for r in rows],'remaining_kind_counts':dict(collections.Counter(x['current_payload']['implementation_kind'] for x in remaining)),'instruction_policy_counts':dict(collections.Counter(r['instruction_policy_tag'] for r in rows)),'policy_count_is_not_behavior_equivalence':True,'scope':'DATA_ONLY_SHARED_NATIVE_OWNER_BRIDGE_PENDING'}
    return cache, rows, contexts, context_pins, selection, time.perf_counter()-start

def generate(root):
    cache, rows, contexts, context_pins, selection, seconds = build(root)
    out = pathlib.Path(root)/OUT_REL; need(not out.exists(), 'NEW_OUTPUT_ROOT'); out.mkdir(parents=True)
    save(out/'selection.json',selection); (out/'authority-descriptor-preimage.json').open('xb').write(cache.files['Planning/Fathom-Exercise-WBS-Annex-v1.json']['raw'])
    (out/'definitions.jsonl').open('xb').write(b''.join(compact(r)+b'\n' for r in rows))
    shared = {'schema':'fathom.harmonic-contact-shared-contexts.1','contexts':{str(level):{'context_ref':context_pins[level],'context':ctx} for level,ctx in contexts.items()},'full_context_is_trusted_source_metadata':True}
    save(out/'shared-contexts.json',shared); save(out/'operator-blueprints.json',operator_blueprints())
    closure = {'schema':'fathom.harmonic-contact-data-closure.1','keys':49,'source_contacts':734,'known_printed_fingers':440,'unknown_printed_fingers':294,'selected_metric_rows':0,'unselected_metric_rows':49,'rows_with_saved_pick_variants':35,'saved_pick_variants':70,'rows_without_saved_pick_variants':14,'clock':None,'source_sounding_gates':None,'native_models':0,'source_contexts':2,'source_input_refs':[cache.reference(p) for p in sorted(cache.files)],'definition_hashes':{r['source_key']:r['definition_sha256'] for r in rows},'level_counts':dict(collections.Counter(r['level'] for r in rows)),'instruction_policy_counts':selection['instruction_policy_counts'],'policy_count_is_not_behavior_equivalence':True,'native_owner_pending':True,'runtime_admitted':False,'official_acceptance_increment':0}; save(out/'family-closure.json',closure)
    header = ['#pragma once','#include <array>','namespace fathom::tasks::harmonic_contacts::data {','struct Row { const char* key; const char* json; };','inline const std::array<Row,49> rows = {{']+['{'+json.dumps(r['source_key'])+','+json.dumps(compact(r).decode(),ensure_ascii=False)+'},' for r in rows]+['}};','inline const char* sharedContextsJson='+json.dumps(compact(shared).decode(),ensure_ascii=False)+';','inline const char* sourceClosureSha='+json.dumps(sha(compact(closure)))+';','}']
    (out/'GeneratedHarmonicContactData.hpp').open('x').write('\n'.join(header)+'\n')
    receipt = {'schema':'fathom.harmonic-contact-generation-receipt.1','result':'CLOSED49_SOURCE_DATA_GENERATED_CHECKS_PENDING','generation_seconds':seconds,'cached_files_hashed_once':len(cache.files),'original_source_pdf_txt_reads':0,'old_native_review_replays':0,'new_native_owner_models':0,'official_acceptance_increment':0}; save(out/'generation-receipt.json',receipt); print(json.dumps(receipt))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--root',default=str(ROOT)); args = parser.parse_args(); generate(args.root)
