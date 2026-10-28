#!/usr/bin/env python3
"""Single35 cached source oracle/branch-data gate, no native/performance claim."""
from pathlib import Path
import ast,collections,copy,hashlib,importlib.util,json,time,types
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-procedure-source-targets-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(v):
        counts['assertions']+=1
        if not v:raise AssertionError('SOURCE_TARGET_DATA')
    def refuse(fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError):counts['expected_refusals']+=1
        else:raise AssertionError('REFUSAL_MISSING')
    def pinned(r):
        if r['path'] not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        raw=cache[r['path']];check(hashlib.sha256(raw).hexdigest()==r['sha256'] and len(raw)==r['bytes']);return raw
    p=ROOT/'Tools/exercise-family-compiler/extend_manual_curriculum_source_targets.py';spec=importlib.util.spec_from_file_location('source_targets',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=(BASE/'selection.json').read_bytes();check(hashlib.sha256(raw).hexdigest()==m.SELECTION_SHA);selection=json.loads(raw);h,g=m.dependencies(ROOT,selection)
    for r in [selection['ledger'],selection['reference_helper'],*selection['cached_inputs'],*selection['source_models']]:pinned(r)
    receipt=h.strict((BASE/'generated-r02/generation-receipt.json').read_bytes())
    expected=['2d763f64e47ccaa93b787267311f4661352674bf576d33865b918df21f869969','5bb08e2322bfbc9a94527b930c7ba1b1e162df86b872f6634b6f7c8efeb57f95','eee90ce229c9eec7f1b7a5ee983ca3c3bff2060540d0c745e6c3a6110faafd57']
    for r,sha in zip(receipt['files'],expected):check(r['sha256']==sha);pinned(r)
    rows=[h.strict(x) for x in (BASE/'generated-r02/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r02/family-closure.json').read_bytes());originals={}
    for r in rows:
        ref=r['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];check(h.sha(raw)==r['original_row_sha256']);o=h.strict(raw);check(o['package_key']==r['source_key'] and o['source_identity']==r['source_identity']);originals[r['source_key']]=o;counts['exact_source_roundtrips']+=1
    check(m.validate(rows,closure,originals,h,g))
    def pure(name,names,extra=None):
        ref=next(x for x in selection['source_models'] if Path(x['path']).name==name);tree=ast.parse(pinned(ref));funcs=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names];check({x.name for x in funcs}==set(names));ns={'copy':copy,'rh':lambda v:h.sha(h.encoded(v))};ns.update(extra or {});exec(compile(ast.Module(body=funcs,type_ignores=[]),ref['path'],'exec'),ns);return types.SimpleNamespace(**{n:ns[n] for n in names})
    state=pure('finite_level051_manual_scans_r01.py',['response_state']);bridge=pure('finite_level062_bridge_manual_r01.py',['selection'])
    models={'manual_bridge_workflow':bridge,'manual_capstone_workflow':pure('finite_level062_capstone_manual_r01.py',['selection'],{'b':bridge}),
        'manual_recovery_workflow':pure('finite_level062_recovery_manual_r01.py',['selection']),
        'manual_source_motif_target_workflow':pure('finite_level061_motif_manual_r01.py',['selection']),
        'manual_minor_progression_workflow':pure('finite_level061_minor_manual_r01.py',['selection']),
        'manual_source_zone_phrase':pure('finite_level061_zones_manual_r01.py',['selection'])}
    reps={}
    for row in rows:
        o=originals[row['source_key']];c=o['implementation']['manual_execution_contract'];p=row['program'];nodes=p['graph']['nodes'];kind=o['implementation']['kind'];source=models[kind];base={'package_key':row['source_key'],'contract_sha256':h.sha(h.encoded(c))};choices=[];reps.setdefault(p['name'],row)
        check(p['fixed_bpm'] is None and p['grants_credit'] is False and p['performance_observed'] is False)
        check(all(e['onset_q'] is None and e['duration_q'] is None for e in o['implementation']['events']))
        check(p['source_obligations_ref']['full_gate_or_session_completed'] is False)
        if o['level']==62:
            for domain in p['graph']['domains']['chosen_alternate']:
                if kind=='manual_recovery_workflow':
                    for trigger in ['missed_shift','non_chord_tone']:choices.append({**base,**domain['selection'],'trigger':trigger,'simplified_remainder_description':'My declared simplified route'})
                else:choices.append({**base,**domain['selection']})
            for choice in choices:
                result=source.selection(c,choice);domain=next(x for x in p['graph']['domains']['chosen_alternate'] if x['selection']['start_stroke']==choice['start_stroke']);check(result['event_picks']==[e['chosen_pick'] for e in domain['contacts']]);check(all('pick' not in e or e['pick'] is None for e in o['implementation']['events']));counts['source_choice_paths']+=1
            check('chosen_pick_sequence' in nodes['phrase']['schema']['properties'])
            if kind=='manual_recovery_workflow':
                check([x['original_contract_path'] for x in nodes['phrase']['source_action_refs']]==[['steps',3],['steps',4]])
                check(nodes['phrase']['next']=='self_report' and 'continued_with_chosen_simplified_remainder' in nodes['phrase']['expected'])
                check(nodes['choices']['constraints'][0]['kind']=='nonempty_trimmed_text')
                check(nodes['phrase']['constraints'][0]['kind']=='same_as_saved')
                for plan in ['', '   ', 'x'*513, True]:
                    refuse(lambda:source.selection(c,{**choices[0],'simplified_remainder_description':plan}))
                for plan in ['x','x'*512]:check(source.selection(c,{**choices[0],'simplified_remainder_description':plan})['remainder_fixed_events'] is None)
            elif kind=='manual_capstone_workflow':
                check(len(o['implementation']['events'])==64 and len(c['steps'][0]['key_blocks'])==4)
                check(nodes['context']['expected']['key_order']==[x['key'] for x in c['steps'][0]['key_blocks']])
            else:check(len(o['implementation']['events'])==8)
        elif kind=='manual_source_motif_target_workflow':
            for domain in p['graph']['domains']['targets']:
                choice={**base,**domain['selection']};check(source.selection(c,choice)['target_orders']==domain['selection']['target_orders']);choices.append(choice);counts['source_choice_paths']+=1
                check(domain['contacts']==[o['implementation']['events'][i-1] for i in choice['target_orders']])
            check(nodes['space']['expected']['at_least_one_complete_source_beat_of_space'] is True)
            if c['required_target_orders'] is None:
                check(len(choices)==16);check(nodes['identity']['expected']['preserved_identity']==c['steps'][1]['identity_contract']['preserved'])
                # H4 includes two unchanged register contacts; never flatten to octave transpose.
                if c['motif_code']=='H4':check(c['steps'][1]['identity_contract']['uniform_octave_shift_claimed'] is False)
            else:
                check(len(choices)==1 and choices[0]['target_orders']==c['required_target_orders'])
                check(nodes['identity']['physical'] is True and nodes['identity']['expected']['half_my_reference_pace'] is True)
                check(c['steps'][1]['relative_speed_ratio_to_learner_reference']==[1,2])
        else:
            source.selection(c,base);choices=[base];counts['source_choice_paths']+=1
            if kind=='manual_minor_progression_workflow':
                check(nodes['target_preparation']['expected']['named_pitches']==[x['printed_note'] for x in c['steps'][1]['targets']])
                check(c['steps'][2]['conditional_global_space_duty']['numeric_onset_inserted'] is False)
            else:
                check(nodes['context']['expected']['named_pitches']==c['steps'][0]['target_notes'])
                check(c['family_response_not_completed_by_single_child'] is True)
        for mutate in [lambda x:x.update(contract_sha256='0'*64),lambda x:x.update(package_key='foreign'),lambda x:x.update(extra_clock=90)]:
            bad=copy.deepcopy(choices[0]);mutate(bad);refuse(lambda:source.selection(c,bad))
        if o['level']==62:refuse(lambda:source.selection(c,{**choices[0],'start_stroke':'P'}))
        elif kind=='manual_source_motif_target_workflow':refuse(lambda:source.selection(c,{**choices[0],'target_orders':[True,5]}))
        done=[{'step':i+1,'response':'acknowledged'} for i in range(len(c['steps']))];check(state.response_state(c,done)=='USER_REPORTED_STEPS_FINISHED')
        for i in [0,len(done)-1]:
            for response,status in [('needs_retry','NEEDS_RETRY'),('stopped','STOPPED')]:
                terminal=done[:i]+[dict(done[i],response=response)];check(state.response_state(c,terminal)==status);refuse(lambda:state.response_state(c,terminal+[{'step':i+2,'response':'acknowledged'}]));counts['terminal_source_checks']+=1
    for name,row in reps.items():
        i=rows.index(row);specific=[lambda p:p['graph']['nodes']['phrase'].update(physical=False)]
        if name=='l062_pulse_recovery':specific += [lambda p:p['graph']['nodes']['phrase'].update(source_action_refs=[{'original_contract_path':['steps',3]}]),lambda p:p['graph']['nodes']['choices'].update(constraints=[])]
        if name.startswith('l061_motif'):specific += [lambda p:p['graph']['nodes']['space']['expected'].update(at_least_one_complete_source_beat_of_space=False)]
        for mutate in [lambda p:p.update(fixed_bpm=90),lambda p:p.update(grants_credit=True),lambda p:p['graph']['failure_policy'].update(terminal_current_pass=False),*specific]:
            changed=copy.deepcopy(rows);cl=copy.deepcopy(closure);mutate(changed[i]['program']);changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));cl['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(changed,cl,originals,h,g))
    raw=(ROOT/selection['current_descriptor']['path']).read_bytes();d=h.strict(raw);accepted={x['selection']['package_key'] for x in d['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'};check(set(closure['keys']).isdisjoint(accepted))
    for r in receipt['files']:pinned(r)
    result={'outcome':'35_CACHED_SOURCE_TARGET_FORM_AND_COUNTEREXAMPLES_PASS_NATIVE_PENDING','rows':35,'source_programs':8,'graph_nodes':192,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'current_accepted_overlap':0,'current_descriptor_sha256':h.sha(raw),'limits':'Data/source pure-function proof only; future native projection/merged physical source-phase/release/factory/view/package and distinct review pending. Recovery raw512 input bound is authored UI scope; source stripped-plan validity retained. Musical/listening/recording/source whole-gate obligations unobserved.'};(BASE/'bulk-validation-r01.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
