#!/usr/bin/env python3
"""One cached-source/graph data proof. Does not execute a native owner or PDF job."""
from pathlib import Path
import ast, collections, copy, hashlib, importlib.util, itertools, json, time, types

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Build/manager-resume-r03/manual-procedure-branching-r01'
PINS = {
    'selection.json': '81d6bf864806b50ad61ffe22977a1bc85221525ef1e915273c784dfc9da0fe35',
    'operator-schema-r02.json': '19706b499d4e49d04a0b1d69bbf65284eb78468d653fb8ec3c4157b5b1883673',
    'generated-r02/definitions.jsonl': '171e3a1c3724fce07d6cf898b6a460511fe499f5ec9e83fd98172032e4067d1b',
    'generated-r02/family-closure.json': 'aeabd631f1dc0267b5085036b7c21393481d801e63c5699da54b949c2d565286',
    'generated-r02/GeneratedManualProcedureBranching.hpp': '6daa1dcc31afb28d864e44d78787c488586d15b2d77571f4022505c01da8b712',
}

def run():
    start = time.perf_counter()
    counts = collections.Counter()
    def check(condition, label='SOURCE_GRAPH'):
        counts['assertions'] += 1
        if not condition:
            raise AssertionError(label)
    def refuse(call):
        try:
            call()
        except (AssertionError, ValueError, KeyError, IndexError):
            counts['expected_refusals'] += 1
        else:
            raise AssertionError('REFUSAL_MISSING')
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()
    cache = {}
    def pinned(ref):
        path = ref['path']
        if path not in cache:
            cache[path] = (ROOT / path).read_bytes()
        raw = cache[path]
        check(sha(raw) == ref['sha256'], 'INPUT_PIN:' + path)
        check('bytes' not in ref or len(raw) == ref['bytes'])
        return raw
    for name, digest in PINS.items():
        check(sha((BASE / name).read_bytes()) == digest, 'SAVED_EXPORT_PIN')
    compiler = ROOT / 'Tools/exercise-family-compiler/extend_manual_curriculum_branching.py'
    check(sha(compiler.read_bytes()) == '2d00c6cd26f6b3c1b6f9c0fbe6eea5d4aa0ae332c2f9b2c13fe0d577af15971c')
    spec = importlib.util.spec_from_file_location('branching_data', compiler)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    h = m.helpers(ROOT)
    selection = h.strict((BASE / 'selection.json').read_bytes())
    operators = h.strict((BASE / 'operator-schema-r02.json').read_bytes())
    rows = [h.strict(x) for x in (BASE / 'generated-r02/definitions.jsonl').read_bytes().splitlines()]
    closure = h.strict((BASE / 'generated-r02/family-closure.json').read_bytes())
    check(m.validate_bundle(rows, closure, (rows, closure)))
    # The old descriptor witness is historical. Recheck current exact keys separately;
    # do not regenerate data against the root's later canonical adoption.
    descriptor_path = ROOT / selection['current_descriptor']['path']
    descriptor_raw = descriptor_path.read_bytes()
    descriptor = h.strict(descriptor_raw)
    accepted = {x['selection']['package_key'] for x in descriptor['current_status_resolution']['operations']
                if x['current_overlay']['status'] == 'Accepted'}
    check(set(closure['keys']).isdisjoint(accepted), 'CURRENT_ACCEPTED_EXCLUSION')
    ledger = {x['package_key']: x for x in map(h.strict, pinned(selection['ledger']).splitlines())}
    for ref in [selection['compiler_dependency'], selection['schema_proposal'],
                *selection['prior80'], *selection['packets'], *selection['contexts'],
                *selection['source_models'], selection['direction_family']]:
        pinned(ref)
    for ref in selection['contexts']:
        check(h.strict(pinned(ref)) == closure['contexts'][ref['path']])
    bykey = {r['source_key']: r for r in rows}
    bykind = collections.defaultdict(list)
    def walk(value):
        if isinstance(value, dict):
            yield value
            for v in value.values():
                yield from walk(v)
        elif isinstance(value, list):
            for v in value:
                yield from walk(v)
    for row in rows:
        key = row['source_key']; original = row['original_record']; p = row['program']; g = p['graph']
        ref = row['payload_ref']; raw = pinned(ref).splitlines()[ref['jsonl_line'] - 1]
        check(sha(raw) == row['original_row_sha256'] and h.strict(raw) == original)
        check(ledger[key]['official_status'] == 'Pending')
        check(ledger[key]['dispatch_ownership'] == {'broad_lane_excluded': False, 'transferred_shard': None})
        check(ledger[key]['official_acceptance_binding'] is None)
        counts['cached_packet_roundtrips'] += 1
        bykind[original['implementation']['kind']].append(row)
        check(g['failure_policy']['terminal_current_pass'] is True)
        check(g['failure_policy']['nonphysical_failure_activates_physical'] is False)
        check(g['failure_policy']['active_retry_stop_navigation_require_exit_release'] is True)
        check(p['source_facts']['printed_events'] == original['implementation']['events'])
        check(all(e['onset_q'] is None and e['duration_q'] is None for e in p['source_facts']['printed_events']))
        check(p['grants_credit'] is False and p['performance_observed'] is False and p['fixed_bpm'] is None)
        for node in g['nodes'].values():
            fields = operators['node_fields'][node['kind']]
            check(set(fields['required']) <= set(node) <= set(fields['required'] + fields['optional']))
            if node['kind'] == 'end':
                check(node['grants_credit'] is False); continue
            counts['closed_forms'] += 1
            check(node['schema']['additionalProperties'] is False)
            check(all('default' not in x for x in walk(node['schema'])))
            for item in walk(node):
                if 'scope' in item and 'path' in item:
                    check(set(item) == {'scope', 'path'} and item['scope'] in ['payload','saved','failed','frame'])
                    check(bool(item['path']) and all(type(v) is str and bool(v) or type(v) is int and v >= 0 for v in item['path']))
                if 'kind' in item and item['kind'] in operators['guards']:
                    check(set(item) == set(operators['guards'][item['kind']]['required_fields']))
                    counts['guard_descriptors'] += 1
            if 'computed_expected' in node:
                x = node['computed_expected']; check(set(x) == set(operators['computed_expected'][x['kind']]['required_fields']))
            for x in node['completion_effects']:
                check(set(x) == set(operators['completion_effects'][x['kind']]['required_fields']))
                check(x['source_key'] in bykey and x['report_only'] is True)
    # Load only pure retained source functions, never their PDF-reading module main.
    source_pins = {Path(r['path']).name: r for r in selection['source_models']}
    def pure(name, names, extra=None):
        ref = source_pins[name]; tree = ast.parse(pinned(ref))
        functions = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in names]
        check({x.name for x in functions} == set(names))
        ns = {'copy': copy, 'rh': lambda v: h.sha(h.encoded(v)), 'VALIDATOR': 'cached_pure_validator',
              'STOP': 'retained_source_stop_instruction', 'SYMBOLS': {'P':'pick','m':'middle finger','a':'ring finger'}}
        if extra: ns.update(extra)
        exec(compile(ast.Module(body=functions, type_ignores=[]), ref['path'], 'exec'), ns)
        return types.SimpleNamespace(**{name: ns[name] for name in names})
    shared = pure('finite_level051_manual_scans_r01.py', ['response_state'])
    source_module = lambda *_: shared
    cross = pure('finite_level063_crosspick_manual_r01.py', ['selection','workflow_state','retry_crossing_pair'], {'module':source_module})
    direction = pure('finite_level063_direction_manual_r01.py', ['select','workflow_state','crossings','family_audit'], {'module':source_module})
    triad = pure('finite_level063_hybrid_triads_manual_r01.py', ['selection','workflow_state'], {'module':source_module})
    seventh = pure('finite_level063_hybrid_sevenths_manual_r01.py', ['selection','workflow_state'], {'module':source_module})
    enclosure = pure('finite_level061_enclosure_manual_r01.py', ['followup'])
    for kind, group in bykind.items():
        for row in group:
            c = row['original_record']['implementation']['manual_execution_contract']; g = row['program']['graph']
            n = len(c['steps']); done = [{'step':i+1,'response':'acknowledged'} for i in range(n)]
            check(shared.response_state(c, done) == 'USER_REPORTED_STEPS_FINISHED')
            for response, state in [('needs_retry','NEEDS_RETRY'),('stopped','STOPPED')]:
                terminal = [dict(done[0], response=response)]
                check(shared.response_state(c, terminal) == state)
                refuse(lambda: shared.response_state(c, terminal + done[1:2]))
            counts['retained_terminal_model_checks'] += 3
            if kind == 'manual_crosspick_both_start_roll':
                req = {'package_key':c['package_key'],'contract_sha256':h.sha(h.encoded(c))}
                for pair in g['domains']['failed_pass_pairs']:
                    p = pair['selection']['pass']; i = 2 if p == 'D' else 3
                    failed = done[:i-1] + [{'step':i,'response':'needs_retry'}]
                    result = cross.retry_crossing_pair(c, req, failed, pair['selection']['pair_start'])
                    check(result['ordered_contacts'] == pair['contacts'])
                    check(result['loop_count'] is None and result['numeric_clock'] is None)
                    counts['source_pair_checks'] += 1
                for bad in [True, 0, 8, None]:
                    refuse(lambda: cross.retry_crossing_pair(c, req, [done[0],{'step':2,'response':'needs_retry'}], bad))
                check(None in g['nodes']['repair_choice']['schema']['properties']['failed_pass']['enum'])
            elif 'hybrid' in kind:
                source = triad if 'triad' in kind else seventh
                later = sum(x['pick'] == 'P' for x in c['steps'][1]['source_contacts']) - 1
                req = {'package_key':c['package_key'],'contract_sha256':h.sha(h.encoded(c))}
                for choices in itertools.product(['D','U'], repeat=2*later):
                    payload = {p+'_later_P_directions':list(choices[i*later:(i+1)*later]) for i,p in enumerate(['D','U'])}
                    chosen = {**req, **payload} if source is seventh else {**req,'D_pass_second_P':choices[0],'U_pass_second_P':choices[1]}
                    result = source.selection(c, chosen)
                    for p in ['D','U']:
                        cs = result[p+'_start_plan']
                        check([x['pick_direction'] for x in cs if x['pick']=='P'] == [p,*payload[p+'_later_P_directions']])
                        check(all(x['pick_direction'] is None for x in cs if x['pick'] in ['m','a']))
                        check([x['pick'] for x in cs] == [x['pick'] for x in c['steps'][1]['source_contacts']])
                    counts['source_explicit_choice_plans'] += 1
                if source is triad:
                    setup = g['nodes']['setup']; check(setup['physical'] is True)
                    check(setup['expected']['calibration_agents'] == ['P','m','a'])
                    check(setup['source_action_binding']['minimum_setup_attacks_outside_printed_eight'] == 3)
                else:
                    setup = g['nodes']['setup']['source_action_binding']
                    check(setup['source_specific_sustain_permission'] is None and setup['numeric_duration_ratio'] is None)
                    check(g['nodes']['choose']['expected']['conservative_release_policy_chosen'] is True)
                    for p in ['D','U']:
                        check(g['nodes'][p+'_pass']['expected']['bass_shorter_than_upper'] is True)
                        check(g['nodes'][p+'_pass']['expected']['bass_released_before_upper'] is True)
                refuse(lambda: source.workflow_state(c, chosen, done[1:2]))
            elif kind == 'manual_enclosure_contract':
                own = row['source_key']; mate = c['paired_cell']['package_key']; follow = g['nodes']['followup']
                check(bykey[mate]['original_record']['implementation']['manual_execution_contract']['paired_cell']['package_key'] == own)
                for a,b in itertools.product([False,True],repeat=2):
                    ready = {own:a,mate:b}
                    for choice in ['repeat_current','practice_other_order','alternate_one_pair','stop']:
                        if choice == 'alternate_one_pair' and not (a and b):
                            refuse(lambda: enclosure.followup(c,choice,ready)); continue
                        route = enclosure.followup(c,choice,ready)
                        emitted = [x['source_key'] for x in follow['routes'][choice].get('calls',[])]
                        check(route['ordered_source_keys'] == emitted and route['performed'] is False)
                        check(len(emitted) <= 2)
                        counts['paired_source_routes'] += 1
                refuse(lambda: enclosure.followup(c,'alternate_one_pair',{own:True,mate:None}))
                refuse(lambda: enclosure.followup(c,'repeat_current',{own:True,mate:1}))
                check(follow['constraints'][0]['kind'] == 'known_boolean_reports')
                check(sum(node.get('physical',False) for node in g['nodes'].values()) == 6)
                check(g['nodes']['separate_report']['completion_effects'][0]['source_key'] == own)
                for route in follow['routes'].values():
                    for call in route.get('calls',[]):
                        check(call['entry'] == 'cell_setup' and call['exit'] == 'separate_report')
                check(g['failure_policy']['abandon_pending_calls_on_failure'] is True)
    # One coherent eight-case audit oracle: every actual adjacent source pair, plus
    # missing/duplicate/tempo/recording/unknown counterexamples. No file/audio claim.
    f = h.strict(pinned(selection['direction_family'])); fr = selection['direction_family']
    ds = bykind['manual_recorded_direction_roll']; contracts = {}; submissions = []
    for row in ds:
        c = row['original_record']['implementation']['manual_execution_contract']; k = row['source_key']; contracts[k] = c
        req = {'package_key':k,'contract_sha256':h.sha(h.encoded(c)),'family_sha256':fr['sha256'],'tempo_label':'explicit learner setting'}
        answers = [{'step':i+1,'response':'acknowledged',**({'recording_locator':'declared take '+k+str(i)} if i in [1,2] else {})} for i in range(4)]
        submissions.append({'selection':req,'responses':answers,'judgments':{p:{'result':'consistent','pair_start':None} for p in ['D','U']}})
    family_req = {'family_sha256':fr['sha256'],'tempo_label':'explicit learner setting'}
    check(direction.family_audit(f,fr,contracts,family_req,submissions)['state'] == 'USER_REPORTED_FAMILY_AUDIT_FINISHED')
    domain = closure['shared_domains']['direction_family_pairs']
    for i,row in enumerate(ds):
        for pair in [x for x in domain if x['selection']['source_key'] == row['source_key']]:
            sub = copy.deepcopy(submissions); p = pair['selection']['pass']; n = pair['selection']['pair_start']
            sub[i]['judgments'][p] = {'result':'louder' if n%2 else 'later','pair_start':n}
            result = direction.family_audit(f,fr,contracts,family_req,sub)
            check(result['selected_pair_repairs'][0]['ordered_contacts'] == pair['contacts'])
            check(result['selected_pair_repairs'][0]['mute_skipped_strings'] == pair['mute_skipped_strings'])
            check(result['recording_or_audio_verified'] is False)
            counts['source_pair_checks'] += 1
    for change in [lambda s:s.pop(),lambda s:s.__setitem__(1,copy.deepcopy(s[0])),
                   lambda s:s[0]['selection'].update(tempo_label='different'),lambda s:s[0]['responses'][1].pop('recording_locator'),
                   lambda s:s[0]['responses'].pop(),lambda s:s[0]['judgments']['D'].update(result='consistent',pair_start=1),
                   lambda s:s[0]['judgments']['D'].update(result='later',pair_start=True),
                   lambda s:s[0]['judgments']['D'].update(result='later',pair_start=8),
                   lambda s:s[0]['judgments']['D'].update(result='detected_clean'),lambda s:s[0]['judgments'].pop('U')]:
        bad = copy.deepcopy(submissions); change(bad)
        refuse(lambda: direction.family_audit(f,fr,contracts,family_req,bad))
    # Representative source-graph mutants recompute identity to exercise semantic
    # source binding rather than merely tripping the exported outer hash.
    mutants = [lambda p:p.update(grants_credit=True),lambda p:p.update(fixed_bpm=90),
               lambda p:p['graph']['failure_policy'].update(terminal_current_pass=False),
               lambda p:p['graph']['failure_policy'].update(nonphysical_failure_activates_physical=True)]
    for group in bykind.values():
        exemplar = group[0]; index = rows.index(exemplar)
        specific = []
        kind = exemplar['original_record']['implementation']['kind']
        if 'hybrid_triad' in kind:
            specific = [lambda p:p['graph']['nodes']['setup']['expected'].update(calibration_agents=['P']),
                        lambda p:p['graph']['nodes']['choose']['schema']['properties']['D_later_P_directions'].update(default=['D'])]
        elif 'hybrid_seventh' in kind:
            specific = [lambda p:p['graph']['nodes']['D_pass']['expected'].pop('bass_shorter_than_upper'),
                        lambda p:p['graph']['nodes']['setup']['source_action_binding'].update(source_specific_sustain_permission=True)]
        elif kind == 'manual_enclosure_contract':
            specific = [lambda p:p['graph']['nodes']['followup']['routes']['alternate_one_pair'].pop('guards'),
                        lambda p:p['graph']['nodes']['followup']['routes']['alternate_one_pair']['calls'].reverse(),
                        lambda p:p['graph']['nodes']['separate_report'].update(completion_effects=[])]
        else:
            specific = [lambda p:p['graph']['domains']['failed_pass_pairs'][0]['selection'].update(pair_start=8),
                        lambda p:p['graph']['nodes']['repair_pair'].update(physical=False)]
        for mutate in mutants + specific:
            changed = copy.deepcopy(rows); c = copy.deepcopy(closure); mutate(changed[index]['program'])
            changed[index]['contract_sha256'] = h.sha(h.encoded(changed[index]['program']))
            c['contracts'][changed[index]['source_key']] = changed[index]['contract_sha256']
            refuse(lambda: m.validate_bundle(changed,c,(changed,c)))
    for bad in ['{"a":1,"a":2}','{"n":NaN}','{"n":Infinity}']:
        refuse(lambda: h.strict(bad))
    for name, digest in PINS.items():
        check(sha((BASE / name).read_bytes()) == digest, 'FINAL_SAVED_EXPORT_DRIFT')
    result = {'outcome':'CACHED_SOURCE_GRAPH_DATA_PASS_NATIVE_EXECUTION_PENDING','rows':48,'source_programs':5,
              'graph_nodes':456,**dict(counts),'cached_inputs_hashed_once':len(cache),'original_txt_pdf_reads':0,
              'native_paths_executed':0,'native_reports_created':0,'official_acceptance_increment':0,
              'seconds':time.perf_counter()-start,
              'current_descriptor':{'path':selection['current_descriptor']['path'],'bytes':len(descriptor_raw),'sha256':sha(descriptor_raw)},
              'current_accepted_keys':len(accepted),'selected48_current_accepted_overlap':0,
              'limits':'Data/source helper oracles only. Native tokens/release/history/graph operators, GUI, registry/package and independent review remain C/root-owned and NOT RUN here. Recordings, physical/listening/full-session duties remain unobserved.'}
    target = BASE / 'bulk-validation-r01.json'
    target.open('x').write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    run()
