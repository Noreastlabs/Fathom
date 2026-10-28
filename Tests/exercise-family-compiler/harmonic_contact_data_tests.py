#!/usr/bin/env python3
"""Original-witness all-row parity, scalar negatives and future report descriptors.

These are DATA checks, not a native owner or performance proof.
"""
import copy, importlib.util, json, pathlib, time
ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('harmonic_compiler', ROOT/'Tools/exercise-family-compiler/compile_harmonic_contact_family.py')
C = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(C)
OUT = ROOT/C.OUT_REL
checks = refusals = unknown_blocks = 0

def check(value, reason):
    global checks
    checks += 1
    if not value: raise AssertionError(reason)

def rejection(fn):
    global refusals
    rejected = False
    try: fn()
    except (AssertionError, ValueError, KeyError, TypeError): rejected = True
    check(rejected, 'malformed source-bound DATA refused'); refusals += 1

def validate(row, original, entry, context, context_ref, raw):
    impl = original['implementation']
    check(row['schema'] == 'fathom.reference-bound-harmonic-contact-definition.1', 'closed schema')
    check(row['source_key'] == original['package_key'] == entry['package_key'] and row['source_identity'] == original['source_identity'] == entry['source_identity'], 'key and identity')
    check(row['level'] == original['level'] == entry['level'] and row['existing_parent_id'] == original['existing_parent_id'] == entry['existing_parent_id'], 'exact level and existing parent')
    check(row['payload_ref'] == entry['current_payload']['ref'] and row['original_row_sha256'] == C.sha(raw), 'exact raw packet witness')
    check(row['source_record_canonical_sha256'] == C.sha(C.compact(original)) == entry['current_payload']['record_canonical_sha256'] and row['source_record_compact_sha256'] == C.sha(C.insertion(original)) == entry['current_payload']['record_compact_order_sha256'], 'both canonical and insertion-order source pins')
    check(row['retained_contract_path'] == ['implementation'] and row['context_ref'] == context_ref and row['source_pins'] == entry['source_pins'], 'contract path/context/source pins')
    check(row['implementation_kind'] == impl['kind'] and row['source_module'] == impl['source_module'] and row['source_category'] == entry['current_payload']['category'], 'source kind/category/module retained')
    check(row['unit']['heading_path'] == original['source_payload']['parent_path'] and row['unit']['printed_label'] == original['source_payload']['printed_label'], 'heading and unit identity')
    check(row['unit']['source_actions'] == impl['task_steps'] and row['unit']['source_action_refs'] == [['implementation','task_steps',n] for n in range(len(impl['task_steps']))] and row['unit']['complete_notation_witness'] == ['source_payload','exact_unit_lines'], 'source duties and complete notation witness')
    check(row['source_atoms'] == impl['ordered_contacts'], 'complete printed atoms preserved')
    for got, expected in zip(row['source_atoms'], impl['ordered_contacts']):
        check(set(got) == set(expected), 'every source field retained; no extra derived field')
        for key in expected: check(type(got[key]) is type(expected[key]) and got[key] == expected[key], 'exact source atom '+key)
        check(type(got['ordinal']) is int and type(got['midi']) is int and (got['finger'] is None or type(got['finger']) is int), 'scalar types, no bool coercion')
        check(got['onset_q'] is got['duration_q'] is got['acoustic_gate_q'] is None, 'all spans stay unknown')
        check(got['pick_attack'] is True and got['attack'] == 'picked', 'harmonic root not silent')
        matrix = context['harmonic_role_matrix'] if row['level'] == 40 else context['chord_roles']
        check(got['harmonic_role'] == matrix[got['harmony']][got['note_spelling']], 'exact cached harmonic role')
    contracts = {k:v for k,v in impl.items() if k not in ('kind','ordered_contacts','task_steps','ordered_rest_locations')}
    check(row['source_contracts'] == contracts, 'all source fields including response/cadence/variants preserved')
    check(row['timing_authority'] == original['timing_authority'] and row['unresolved_reasons'] == original['unresolved_reasons'] and row['ordered_rest_locations'] == [], 'original timing/unresolved/rest authority')
    check(row['source_unknowns'] == {'unprinted_fingers_retained_null':sum(a['finger'] is None for a in impl['ordered_contacts']), 'source_clock':None, 'source_acoustic_gate':None, 'numeric_metric_projection':None, 'unsaved_pick_variants_not_created':True, 'performer_choices_are_not_source_facts':True}, 'precise unknown source fields')
    check(row['boundaries'] == {'native_model_created':False,'runtime_admitted':False,'observed_performance':False,'whole_child_accepted':False,'grants_credit':False}, 'DATA cannot manufacture native/admission/mastery')
    check(row['instruction_policy_tag'] == C.tag(row['level'],row['source_module']), 'literal instruction profile')
    check(row['source_atoms_sha256'] == C.sha(C.compact(row['source_atoms'])) and row['definition_sha256'] == C.sha(C.compact({k:v for k,v in row.items() if k != 'definition_sha256'})), 'whole definition/atom digest')
    for variant in row['source_contracts'].get('variants',[]):
        for n, atom in enumerate(row['source_atoms']):
            check(variant['contact_ordinals'][n] == atom['ordinal'] and variant['strokes_by_contact'][n] == impl['variants'][0 if variant['pick_start'] == 'D' else 1]['strokes_by_contact'][n], 'every saved pick stroke equals original witness')

def descriptor_tests(blueprints):
    global unknown_blocks
    check(blueprints['native_supported'] is False and len(blueprints['instruction_policies']) == 6 and blueprints['policy_count_is_not_behavior_equivalence'] is True, 'six DATA source tags, no recipe/behavior completion')
    for tag, policy in blueprints['instruction_policies'].items():
        schema = policy['report_schema']; fields = policy['required_reports']
        check(schema['additionalProperties'] is False and set(schema['required']) == set(schema['properties']), 'closed typed reports')
        check(set(fields) == {g['field'] for g in policy['guards'] if g['kind'] == 'manual_reported_met'} and {'kind':'nonempty_trimmed_text','field':'evidence'} in policy['guards'], 'all criteria and trimmed evidence required')
        check(not {'done','learner_done'} & set(schema['properties']) and len(fields) >= 4, 'material source criteria instead of done bit')
        def passes(payload):
            return set(payload) == set(schema['required']) and all(payload[k] == 'reported_met' for k in fields) and type(payload['evidence']) is str and bool(payload['evidence'].strip()) and len(payload['evidence']) <= 4096
        positive = {k:'reported_met' for k in fields}|{'evidence':'synthetic manual source evidence'}
        check(passes(positive), 'pure prospective report descriptor success')
        for field in fields:
            check(schema['properties'][field]['enum'] == ['reported_met','reported_not_met','unknown',None], 'typed negative and unknown retained')
            for value in ('reported_not_met','unknown',None,True):
                bad = copy.deepcopy(positive); bad[field] = value; check(not passes(bad), 'negative/unknown/wrong type unresolved'); unknown_blocks += 1
        for evidence in ('',' \t\r\n',None,'x'*4097):
            bad = copy.deepcopy(positive); bad['evidence'] = evidence; check(not passes(bad), 'blank/unknown/overlong evidence unresolved'); unknown_blocks += 1
        bad = copy.deepcopy(positive); bad['other'] = True; check(not passes(bad), 'extra report refused'); unknown_blocks += 1
    later = blueprints['instruction_policies']['completion_cadence']['conditional_later_pass']
    check(later['null_means_not_required'] is True and later['source_selected_approach_remains_null'] is True and later['requires_separate_manual_realization'] is True, 'P1/2 no second-pass inference and P3/5 manual later realization')

def main():
    start = time.perf_counter(); closure = C.strict((OUT/'family-closure.json').read_bytes()); cache = C.I.Cache(ROOT)
    for ref in closure['source_input_refs']: cache.read(ref)
    selection = C.strict((OUT/'selection.json').read_bytes()); ledger = [C.strict(x) for x in cache.read(selection['ledger']).splitlines()]; by = {e['package_key']:e for e in ledger}
    rows = [C.strict(x) for x in (OUT/'definitions.jsonl').read_bytes().splitlines()]
    check(len(rows) == len({x['source_key'] for x in rows}) == len({x['source_identity'] for x in rows}) == 49 and selection['keys'] == [r['source_key'] for r in rows], 'exact49 unique closed scope')
    descriptor_raw = (OUT/'authority-descriptor-preimage.json').read_bytes(); descriptor = C.strict(descriptor_raw)
    check(C.sha(descriptor_raw) == selection['descriptor_snapshot']['sha256'], 'current authority frozen preimage')
    adopted = {op['selection']['package_key'] for op in descriptor['current_status_resolution']['operations']}; owned = set().union(*(set(x) for x in selection['excluded_owned_keys'].values()))
    check(set(selection['keys']).isdisjoint(adopted|owned), 'all accepted/transferred/owned keys excluded')
    check(selection['current_accepted'] == len(adopted) and selection['current_pending'] == 7271-len(adopted), 'actual status counts from preimage')
    shared = C.strict((OUT/'shared-contexts.json').read_bytes()); total = variants = roots = later_count = joins = unknown_fingers = 0
    for level, context_entry in shared['contexts'].items():
        check(context_entry['context'] == cache.json(context_entry['context_ref']) and int(level) == context_entry['context']['level'], 'two exact cached contexts')
    for row in rows:
        entry = by[row['source_key']]; witness = row['payload_ref']; raw = cache.read(witness).splitlines()[witness['jsonl_line']-1]; original = C.strict(raw); context_entry = shared['contexts'][str(row['level'])]; context = context_entry['context']; context_ref = context_entry['context_ref']
        validate(row,original,entry,context,context_ref,raw); check(C.source_guard(original,entry,context) == row['instruction_policy_tag'], 'original source/schema semantics')
        check(closure['definition_hashes'][row['source_key']] == row['definition_sha256'], 'all-row closure pin')
        total += len(row['source_atoms']); variants += len(row['source_contracts'].get('variants',[])); roots += sum(a['harmonic_role'] == 'R' for a in row['source_atoms']); unknown_fingers += sum(a['finger'] is None for a in row['source_atoms'])
        response = row['source_contracts'].get('source_response_relationship')
        if response: joins += len(response['shared_opening_joins'])
        cadence = row['source_contracts'].get('source_completion_cadence')
        if cadence: later_count += cadence['later_source_pass'] is not None
        # A malicious reissued digest must still fail equality to original witnesses.
        mutations = [lambda x:x['source_atoms'][0].update(midi=None),lambda x:x['source_atoms'][0].update(finger=0),lambda x:x['source_atoms'][0].update(harmonic_role='rest'),lambda x:x['source_atoms'][0].update(acoustic_gate_q=[1,1]),lambda x:x['source_atoms'][0].update(onset_q=[0,1]),lambda x:x['source_atoms'].reverse(),lambda x:x['source_contracts'].update(source_rule='invented'),lambda x:x['payload_ref'].update(jsonl_line=x['payload_ref']['jsonl_line']+1),lambda x:x['context_ref'].update(sha256='0'*64),lambda x:x['boundaries'].update(runtime_admitted=True),lambda x:x['source_unknowns'].update(source_clock=120)]
        for mutate in mutations:
            bad = copy.deepcopy(row); mutate(bad); bad['source_atoms_sha256'] = C.sha(C.compact(bad['source_atoms'])); bad['definition_sha256'] = C.sha(C.compact({k:v for k,v in bad.items() if k != 'definition_sha256'})); rejection(lambda:validate(bad,original,entry,context,context_ref,raw))
        source_mutations = [lambda x:x['implementation']['ordered_contacts'][0].update(ordinal=True),lambda x:x['implementation']['ordered_contacts'][0].update(midi=True),lambda x:x['implementation']['ordered_contacts'][0].update(finger=True),lambda x:x['implementation']['ordered_contacts'][0].update(acoustic_gate_q=[1,1]),lambda x:x['timing_authority'].update(fixed_bpm=120),lambda x:x['implementation'].update(ordered_rest_locations=[{'ordinal':1}])]
        if 'variants' in original['implementation']: source_mutations.append(lambda x:x['implementation']['variants'][0]['strokes_by_contact'].__setitem__(1,'D'))
        else: source_mutations.append(lambda x:x['implementation'].update(variants=[{'pick_start':'D'}]))
        if response: source_mutations += [lambda x:x['implementation']['source_response_relationship']['shared_opening_joins'][0].update(finger=4),lambda x:x['implementation']['source_response_relationship'].update(governing_workbook_tonic='A')]
        if cadence: source_mutations += [lambda x:x['implementation']['source_completion_cadence']['explicit_source_beat_one_anchors'][0].update(quarter_onset=[0,1]),lambda x:x['implementation']['source_completion_cadence']['contact_roles'][1].update(source_beat=2)]
        for mutate in source_mutations:
            bad = copy.deepcopy(original); mutate(bad); rejection(lambda:C.source_guard(bad,entry,context))
    check((total,variants,unknown_fingers,joins,later_count) == (734,70,294,20,3) and roots > 0, 'exact source totals/joins/later-scope')
    header = (OUT/'GeneratedHarmonicContactData.hpp').read_text(); body = header.split('inline const std::array<Row,49> rows = {{\n',1)[1].split('\n}};',1)[0].splitlines(); decoded = [json.loads('['+line[1:-2]+']') for line in body]
    check([json.loads(r[1]) for r in decoded] == rows and [r[0] for r in decoded] == selection['keys'], 'actual emitted header equals JSONL and exact keys')
    check(C.sha(C.compact(closure)) in header, 'actual header source closure pin')
    descriptor_tests(C.strict((OUT/'operator-blueprints.json').read_bytes()))
    result = {'result':'PASS_DATA_ONLY','keys':49,'source_contacts':734,'saved_pick_variants':70,'known_printed_fingers':440,'unknown_printed_fingers':294,'source_root_roles_preserved_as_picked':roots,'response_shared_joins':joins,'cadence_rows_with_later_slide_duty':later_count,'assertions':checks,'malformed_input_refusals':refusals,'negative_unknown_descriptor_blocks':unknown_blocks,'source_contexts':2,'instruction_policy_tags':6,'policy_count_is_not_behavior_equivalence':True,'run_seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache.files),'original_pdf_txt_research':0,'native_owner_runs':0,'official_acceptance_increment':0}
    C.save(OUT/'data-validation.json',result); print(json.dumps(result))

if __name__ == '__main__': main()
