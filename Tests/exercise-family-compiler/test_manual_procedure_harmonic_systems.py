#!/usr/bin/env python3
"""Closed44 cached source/program proof; no native/GUI or acoustic observation."""
from pathlib import Path
import ast, collections, copy, hashlib, importlib.util, json, time, types
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-procedure-level060-harmonic-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(ok):
        counts['assertions']+=1
        if not ok:raise AssertionError('HARMONIC_SOURCE_GRAPH')
    def refuse(fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError):counts['expected_refusals']+=1
        else:raise AssertionError('MISSING_REFUSAL')
    def pin(r):
        if r['path'] not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        raw=cache[r['path']];check(hashlib.sha256(raw).hexdigest()==r['sha256']);check(len(raw)==r['bytes']);return raw
    compiler=ROOT/'Tools/exercise-family-compiler/extend_manual_curriculum_harmonic_systems.py'
    check(hashlib.sha256(compiler.read_bytes()).hexdigest()=='828281888f08cb51ef01e9ea374b1895947cb2c876781522056ce6cf44618e7a')
    s=importlib.util.spec_from_file_location('harmonic',compiler);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    raw=(BASE/'selection.json').read_bytes();check(hashlib.sha256(raw).hexdigest()==m.SELECTION_SHA);selection=json.loads(raw);h,g=m.dependencies(ROOT,selection)
    for r in [selection['ledger'],*selection['cached_inputs'],*selection['source_models'],*selection['prior128'],selection['c96_selection']]:pin(r)
    receipt=h.strict((BASE/'generated-r02/generation-receipt.json').read_bytes())
    for r in receipt['files']:pin(r)
    rows=[h.strict(s) for s in (BASE/'generated-r02/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r02/family-closure.json').read_bytes());originals={}
    for row in rows:
        r=row['payload_ref'];raw=pin(r).splitlines()[r['jsonl_line']-1];check(h.sha(raw)==row['original_row_sha256']);o=h.strict(raw);originals[row['source_key']]=o
        check(o['package_key']==row['source_key'] and o['source_identity']==row['source_identity']);counts['exact_packet_roundtrips']+=1
    check(m.validate(rows,closure,originals,h,g))
    def pure(name,names,extra=None):
        ref=next(r for r in selection['source_models'] if Path(r['path']).name==name);tree=ast.parse(pin(ref));functions=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names];check({x.name for x in functions}==set(names));ns={'copy':copy,'rh':lambda v:h.sha(h.encoded(v)),'VALIDATOR':'cached_pure_model'};ns.update(extra or {});exec(compile(ast.Module(body=functions,type_ignores=[]),ref['path'],'exec'),ns);return types.SimpleNamespace(**{n:ns[n] for n in names})
    state=pure('finite_level051_manual_scans_r01.py',['response_state']);module=lambda *_:state
    common=pure('finite_level060_remaining_families_manual_r01.py',['choose_common','state_for','workflow_state'],{'module':module})
    minor=pure('finite_level060_minor_progressions_manual_r01.py',['selection','workflow_state'],{'module':module})
    representatives={}
    for row in rows:
        o=originals[row['source_key']];c=o['implementation']['manual_execution_contract'];p=row['program'];graph=p['graph'];kind=o['implementation']['kind'];representatives.setdefault(p['name'],row);done=[{'step':i+1,'response':'acknowledged'} for i in range(len(c['steps']))]
        check(c['required_silent_work']['formations']==56 and c['source_required_practice_duty']['completed'] is None)
        check(graph['entry']=='silent_work' and graph['failure_policy']['explicit_restart_entry']=='silent_work')
        check(all(e['onset_q'] is None and e['duration_q'] is None for e in o['implementation']['events']))
        check(p['source_obligations_ref']['full_source_gate_or_session_completed'] is False)
        check(state.response_state(c,done)=='USER_REPORTED_STEPS_FINISHED')
        for i in [0,len(done)-1]:
            for response,expected in [('needs_retry','NEEDS_RETRY'),('stopped','STOPPED')]:
                reports=done[:i]+[dict(done[i],response=response)];check(state.response_state(c,reports)==expected);refuse(lambda:state.response_state(c,reports+[{'step':i+2,'response':'acknowledged'}]));counts['retained_terminal_checks']+=1
        for domain in graph['domains']['initial_guides']:
            base={'package_key':c['package_key'],'contract_sha256':h.sha(h.encoded(c)),'silent56_report':'user_reports_complete'}
            if kind=='manual_minor_progression_guide_followup':
                request={**base,**domain['selection']};chosen=minor.selection(c,request)
                check([{k:e[k] for k in ['printed_note','role','string','fret']} for e in chosen['selected_guides'][:2]]==[{k:e[k] for k in ['printed_note','role','string','fret']} for e in domain['contacts']])
            else:
                request={**base,'guide_role_order':[domain['selection']['first_guide'],domain['selection']['second_guide']]};chosen=common.choose_common(c,request,True);check(chosen['guide_role_order']==request['guide_role_order'])
            check(chosen['runtime_admitted'] is False and chosen['grants_credit'] is False);counts['source_guide_choices']+=1
            for mutate in [lambda r:r.update(contract_sha256='0'*64),lambda r:r.update(silent56_report=True),lambda r:r.update(package_key='foreign')]:
                bad=copy.deepcopy(request);mutate(bad);refuse(lambda:minor.selection(c,bad) if kind=='manual_minor_progression_guide_followup' else common.choose_common(c,bad,True))
        # Verify referenced linked shapes by packet and exact source-record hash;
        # geometry-only cards do not gain locally printed pitch facts.
        for s in c['steps']:
            if 'source_shape' in s:
                ref=s['source_shape'];raw=pin(ref).splitlines()[ref['line']-1];check(h.sha(h.encoded(h.strict(raw)))==ref['record_sha256']);counts['linked_source_shape_bindings']+=1
        if kind=='manual_picking_system_comparison':
            check(c['source_passes']==[8,8,14] and c['printed_attacks']==30)
            node=graph['nodes']['source_5'];check(len(node['expected']['pick_sequence'])==14 and node['expected']['pick_sequence']==list('DUDUDUDUDUDUDU'))
            check(node['expected']['no_pause_between_two_loops'] is True and node['expected']['no_top_repeat'] is True)
            check(c['steps'][4]['no_pause_or_response_between_loops'] is True)
        elif kind=='manual_guide_tone_accent_workflow':
            s=c['steps'][1];check(graph['nodes']['source_2']['expected']['accent_event_orders']==s['accent_event_orders'])
            check(graph['nodes']['source_3']['expected']['b5_locally_accented']==c['steps'][2]['b5_is_locally_accented'])
        elif kind=='manual_same_root_quality_ladder':
            t=c['steps'][2]['one_factor_transitions'];check([x['factor'] for x in t]==['seventh','third','fifth','fifth','third','seventh'])
            check(c['printed_attacks']==28 and c['steps'][2]['picking'] is None)
            check('pick_sequence' not in graph['nodes']['source_3']['expected'])
        elif kind=='manual_major_progression_two_pass_workflow':
            check(graph['nodes']['source_3']['next']=='source_4')
            check(graph['nodes']['source_4']['expected']['accent_event_orders']==[])
            check(graph['nodes']['source_4']['expected']['pick_sequence']==list('DDDDUUUU')*3)
        elif kind=='manual_minor_progression_guide_followup':
            check(len(graph['domains']['minor_guide_followup'])==2)
            check(graph['nodes']['source_3']['constraints'][0]['kind']=='same_as_saved')
            for domain in graph['domains']['minor_guide_followup']:
                request={'package_key':c['package_key'],'contract_sha256':h.sha(h.encoded(c)),'silent56_report':'user_reports_complete',**domain['selection']};result=minor.selection(c,request)
                fields=['printed_note','role','string','fret'];check([[e[n] for n in fields] for e in result['selected_guides']]==[[e[n] for n in fields] for e in domain['contacts']]);check(all(e['pick'] is None for e in result['selected_guides']));counts['source_minor_followup_choices']+=1
        elif kind=='manual_harmonic_framing_workflow':
            check('pick_sequence' not in graph['nodes']['source_3']['expected'])
            if c['kind']=='scale_connection':
                chord={e['printed_note'] for e in o['implementation']['events'][:4]};expected=[e['order'] for e in o['implementation']['events'][4:12] if e['printed_note'] in chord]
                check(graph['nodes']['source_3']['expected']['accent_event_orders']==expected)
                check(graph['nodes']['source_4']['expected']['accent_event_orders']==[])
            else:
                n=graph['nodes']['source_3'];check(n['held_until_owned_release'] is True and n['release_source_action_ref']['original_contract_path']==['steps',3]);check(n['next']=='source_5' and 'source_4' not in graph['nodes']);check(c['steps'][2]['numeric_rhythm'] is None and c['steps'][2]['final_sustain_duration'] is None)
    # Small source-family counterexample set, not a permutation/state campaign.
    for name,row in representatives.items():
        i=rows.index(row);specific=[]
        if name=='l060_picking_comparison':specific=[lambda p:p['graph']['nodes']['source_5']['expected'].update(no_pause_between_two_loops=False)]
        if name=='l060_guide_accent':specific=[lambda p:p['graph']['nodes']['source_2']['expected'].update(accent_event_orders=[])]
        if name=='l060_quality_ladder':specific=[lambda p:p['graph']['nodes']['source_3']['expected'].update(changed_factors=['fifth']*6)]
        if name=='l060_major_two_pass_cadence':specific=[lambda p:p['graph']['nodes']['source_3'].update(next='source_5')]
        if name=='l060_minor_guide_cadence':specific=[lambda p:p['graph']['nodes']['source_3'].update(constraints=[])]
        if name.endswith('question_answer'):specific=[lambda p:p['graph']['nodes']['source_3'].pop('release_source_action_ref')]
        if name.endswith('scale_connection'):specific=[lambda p:p['graph']['nodes']['source_3']['expected'].update(accent_event_orders=[5])]
        for mutation in [lambda p:p.update(fixed_bpm=90),lambda p:p.update(grants_credit=True),lambda p:p['graph']['failure_policy'].update(terminal_current_pass=False),*specific]:
            changed=copy.deepcopy(rows);cl=copy.deepcopy(closure);mutation(changed[i]['program']);changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));cl['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(changed,cl,originals,h,g))
    current=(ROOT/selection['current_descriptor']['path']).read_bytes();descriptor=h.strict(current);accepted={x['selection']['package_key'] for x in descriptor['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'};check(set(closure['keys']).isdisjoint(accepted))
    for r in receipt['files']:pin(r)
    result={'outcome':'44_CACHED_SOURCE_PROGRAM_AND_BOUNDARIES_PASS_NATIVE_PENDING','rows':44,'source_programs':7,'graph_nodes':386,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'current_accepted_overlap':0,'current_descriptor_sha256':h.sha(current),'limits':'Exact data/source-model comparisons; no native owner/GUI/package or independent review claim. Physical, audible, source gate/session duties unobserved. Initial eight-profile minor choice data remains historical and superseded by exact two-profile corrected r02.'}
    (BASE/'bulk-validation-r01.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
