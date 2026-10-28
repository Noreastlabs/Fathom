#!/usr/bin/env python3
"""One44 all-row source roundtrip and representative source-program boundaries."""
from pathlib import Path
import ast, collections, copy, hashlib, importlib.util, json, math, time, types
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-procedure-level063-protocols-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(v):
        counts['assertions']+=1
        if not v:raise AssertionError('LEVEL063_SOURCE_PROGRAM')
    def refuse(fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError,TypeError):counts['expected_refusals']+=1
        else:raise AssertionError('REFUSAL_MISSING')
    def pinned(r):
        if r['path'] not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        raw=cache[r['path']];check(hashlib.sha256(raw).hexdigest()==r['sha256'] and len(raw)==r['bytes']);return raw
    path=ROOT/'Tools/exercise-family-compiler/extend_manual_curriculum_level063_protocols.py';spec=importlib.util.spec_from_file_location('protocols',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=(BASE/'selection.json').read_bytes();check(hashlib.sha256(raw).hexdigest()==m.SELECTION_SHA);selection=json.loads(raw);h,g=m.dependencies(ROOT,selection)
    for r in [selection['ledger'],selection['current_descriptor'],*selection['cached_inputs'],*selection['source_models']]:pinned(r)
    receipt=h.strict((BASE/'generated-r01/generation-receipt.json').read_bytes());expected_pins=['29f8a751587482c0097105754572314101895899fad99f6bbcd57c66d02af219','ca7849378ae2f55ca73027ec30f267b92a34f21db7a00f5802dc7b1513c34431','f139b3c3791f2aa8745dcdda37f84c3ad474717a3ed7986d14de1c6cce88aaeb']
    for r,sha in zip(receipt['files'],expected_pins):check(r['sha256']==sha);pinned(r)
    rows=[h.strict(x) for x in (BASE/'generated-r01/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r01/family-closure.json').read_bytes());originals={}
    for r in rows:
        ref=r['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];check(h.sha(raw)==r['original_row_sha256']);o=h.strict(raw);check(o['package_key']==r['source_key'] and o['source_identity']==r['source_identity']);originals[r['source_key']]=o;counts['exact_source_roundtrips']+=1
    check(m.validate(rows,closure,originals,h,g))
    def pure(name,names,extra=None):
        r=next(x for x in selection['source_models'] if Path(x['path']).name==name);tree=ast.parse(pinned(r));f=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in names];check({x.name for x in f}==set(names));ns={'copy':copy,'math':math,'rh':lambda v:h.sha(h.encoded(v))};ns.update(extra or {});exec(compile(ast.Module(body=f,type_ignores=[]),r['path'],'exec'),ns);return types.SimpleNamespace(**{n:ns[n] for n in names})
    stateless=pure('finite_level051_manual_scans_r01.py',['response_state']);shared={'module':lambda *_:stateless,'VALIDATOR':None}
    triad=pure('finite_level063_triad_sweeps_manual_r01.py',['selection','workflow_state','recovery_plan','recovery_state'],{**shared,'FAILURE':'retained source failure rule','CAPTION':'retained source caption'})
    seventh=pure('finite_level063_seventh_sweeps_manual_r01.py',['selection','workflow_state'])
    compare=pure('finite_level063_system_compare_manual_r01.py',['selection','workflow_state'],shared)
    cadence=pure('finite_level063_cadences_manual_r01.py',['selection','workflow_state'],shared)
    dimensions=['note_length','pick_noise','finger_volume','skipped_string_muting','tempo','chord_identity']
    endurance=pure('finite_level063_endurance_manual_r02.py',['selection','seconds','workflow_state'],{'DIMENSIONS':dimensions})
    models={'manual_sweep_burst_rest_and_repair':triad,'manual_seventh_sweep_release_breath_repeat':seventh,'manual_four_system_comparison':compare,'manual_assigned_system_cadence':cadence,'manual_endurance_circuit_ladder':endurance};reps={}
    for r in rows:
        o=originals[r['source_key']];c=o['implementation']['manual_execution_contract'];kind=o['implementation']['kind'];p=r['program'];nodes=p['graph']['nodes'];source=models[kind];base={'package_key':r['source_key'],'contract_sha256':h.sha(h.encoded(c))};choices=[];reps.setdefault(p['name'],r)
        check(p['grants_credit'] is False and p['fixed_bpm'] is None and p['performance_observed'] is False);check(p['source_obligations_ref']['full_gate_or_session_completed'] is False)
        if kind=='manual_sweep_burst_rest_and_repair':
            source.selection(c,base);done=[{'step':i+1,'response':'acknowledged'} for i in range(4)];check(source.workflow_state(c,base,done)['state']=='USER_REPORTED_STEPS_FINISHED');bad=done[:3]+[{'step':4,'response':'needs_retry'}]
            for d in ['D','U']:
                plan=source.recovery_plan(c,base,bad,d);domain=next(x for x in p['graph']['domains']['one_way'] if x['selection']['direction']==d);check(plan['steps'][0]['ordered_contacts']==domain['contacts']);check(plan['steps'][2]['ordered_contacts']==c['steps'][1]['ordered_contacts']);check(plan['steps'][0]['numeric_tempo_ratio'] is None);check(source.recovery_state(c,base,bad,{'source_contract_sha256':h.sha(h.encoded(c)),'direction':d},[{'step':i+1,'response':'acknowledged'} for i in range(5)])['state']=='USER_REPORTED_STEPS_FINISHED');counts['source_repair_paths']+=1
            for i in range(3):refuse(lambda:source.recovery_plan(c,base,done[:i]+[{'step':i+1,'response':'needs_retry'}],'D'))
            refuse(lambda:source.recovery_plan(c,base,done,'D'));check(p['graph']['failure_policy']['failed_node_repair_entry']=={'self_report':'repair_choice'});choices=[base]
        elif kind=='manual_seventh_sweep_release_breath_repeat':
            cycle=[('mirror','acknowledged'),('full_hand_release','acknowledged'),('one_breath','acknowledged')]
            seq=lambda a:[{'sequence':i+1,'action':x,'response':v} for i,(x,v) in enumerate(a)]
            for n in [2,3]:
                a=[('setup','acknowledged')]
                for i in range(n):a+=cycle+[('compare','clean_match_finish' if i==n-1 else 'clean_match_repeat')]
                done=source.workflow_state(c,base,seq(a));check(done['state']=='USER_REPORTED_SELECTED_REPETITIONS_FINISHED' and done['learner_reported_repetitions']==n);counts['source_repeat_paths']+=1
            for bad in [[('setup','acknowledged')]+cycle+[('compare','clean_match_finish')],[('setup','acknowledged'),('mirror','acknowledged'),('one_breath','acknowledged')],[('setup','acknowledged')]+cycle+[('compare','not_clean')]+cycle]:refuse(lambda:source.workflow_state(c,base,seq(bad)))
            check(source.workflow_state(c,base,seq([('setup','acknowledged')]+cycle+[('compare','not_clean')]))['state']=='NEEDS_RETRY');check('clean_match_finish' not in nodes['compare1']['routes']);check(nodes['compare2']['routes']['clean_match_repeat']['next']=='mirror2');check(nodes['mirror1']['release_source_action_ref']['original_contract_path']==['actions','full_hand_release']);check(nodes['mirror1']['next']=='breath1' and nodes['breath1']['next']=='compare1');check(c['source_fixed_repetition_count'] is None);choices=[base]
        elif kind=='manual_four_system_comparison':
            for d,u in [('D','D'),('U','U'),('D','U'),('U','D')]:
                choice={**base,'tempo_label':'My current tempo','tone_label':'My current tone','D_hybrid_later_P':d,'U_hybrid_later_P':u};result=source.selection(c,choice);choices.append(choice)
                for n in nodes.values():
                    project=n.get('computed_expected')
                    if project:
                        system=c['steps'][n['source_action_ref']['original_contract_path'][1]]['system'];values=choice[project['directions_ref']['path'][-1]];check(m.resolve_projection(project,values)==[x['pick_direction'] for x in result['plans'][system] if x['pick']=='P']);check(project['first_P_order']==9);counts['source_P_projection_paths']+=1
            done=[{'step':i+1,'response':'acknowledged',**({'comparison_note':'My own comparison'} if i==len(c['steps'])-1 else {})} for i in range(len(c['steps']))];check(source.workflow_state(c,choices[0],done)['state']=='USER_REPORTED_STEPS_FINISHED');refuse(lambda:source.workflow_state(c,choices[0],[{k:v for k,v in x.items() if k!='comparison_note'} for x in done]));refuse(lambda:source.selection(c,{**choices[0],'tempo_label':' trailing '}))
        elif kind=='manual_assigned_system_cadence':
            for pattern in [['D']*5,['U']*5,['D','U','D','U','D']]:
                choice={**base,**({'D_later_P':pattern,'U_later_P':pattern} if c['assigned_system']=='hybrid' else {})};result=source.selection(c,choice);choices.append(choice)
                for n in nodes.values():
                    project=n.get('computed_expected')
                    if project:
                        key='printed' if project['protocol_start']=='D' else 'opposite';check(m.resolve_projection(project,choice[project['directions_ref']['path'][-1]])==[x['pick_direction'] for x in result[key] if x['pick']=='P']);counts['source_P_projection_paths']+=1
                check((result['opposite'] is None)==(c['assigned_system']=='sweep'))
            done=[{'step':i+1,'response':'acknowledged'} for i in range(len(c['steps']))];check(source.workflow_state(c,choices[0],done)['state']=='USER_REPORTED_STEPS_FINISHED')
        else:
            hasp=any(e['pick']=='P' for e in c['source_contacts']);pnum=sum(e['pick']=='P' for e in c['source_contacts'])
            for pattern in ['D','U','alternating']:
                choice=dict(base)
                if hasp:
                    for label,first in [('printed_P','D'),('opposite_P','U')]:choice[label]=[first]+[(pattern if pattern!='alternating' else ('D' if i%2==0 else 'U')) for i in range(pnum-1)]
                result=source.selection(c,choice);choices.append(choice)
                for n in nodes.values():
                    project=n.get('computed_expected')
                    if project:
                        key='printed' if project['protocol_start']=='D' else 'opposite';check(m.resolve_projection(project,choice[project['directions_ref']['path'][-1]])==[x['pick_direction'] for x in result[key] if x['pick']=='P']);counts['source_P_projection_paths']+=1
            done=[];last_work=None;work_indices=[];rest_indices=[];audit_indices=[]
            for i,s in enumerate(c['steps']):
                n=i+1;sk=s['kind']
                if sk in ['setup','finish']:a={'step':n,'response':'acknowledged'}
                elif sk=='written':a={'step':n,'response':'clean'}
                elif sk=='work':
                    last_work=s['target_seconds']+2.5;a={'step':n,'response':'work_reported','reported_seconds':last_work,'first_recording':'My actual first segment','final_recording':'My actual final segment','boundary_release_reported':True};work_indices.append(i)
                    node=nodes['source_'+str(i)];check(node['constraints'][0]['lower_bound_ref']==g.ref('contract','steps',i,'target_seconds'));check(m.numeric_guard(last_work,s['target_seconds']))
                elif sk=='rest':a={'step':n,'response':'rest_reported','reported_seconds':last_work};rest_indices.append(i)
                else:a={'step':n,'response':'manual_audit','comparisons':{d:'same' for d in dimensions},'clean_set_reported':True};audit_indices.append(i)
                done.append(a)
            result=source.workflow_state(c,choices[0],done);check(result['state']=='USER_REPORTED_SELECTED_LADDER_FINISHED' and result['reported_clean_timed_sets']==9);check(len(result['recording_windows'])==9);check(result['recording_windows'][0]['overlap_seconds']==2.5);counts['source_endurance_complete_paths']+=1
            wi,ri,ai=work_indices[0],rest_indices[0],audit_indices[0]
            for field,value in [('reported_seconds',14.9),('reported_seconds',True),('boundary_release_reported',False),('first_recording','   ')]:
                bad=copy.deepcopy(done[:wi+1]);bad[wi][field]=value;refuse(lambda:source.workflow_state(c,choices[0],bad))
            bad=copy.deepcopy(done[:ri+1]);bad[ri]['reported_seconds']=15;refuse(lambda:source.workflow_state(c,choices[0],bad))
            for field,value in [('clean_set_reported',False),('comparisons',{d:('worse' if d=='tempo' else 'same') for d in dimensions})]:
                bad=copy.deepcopy(done[:ai+1]);bad[ai][field]=value;check(source.workflow_state(c,choices[0],bad)['state']=='NEEDS_RETRY');refuse(lambda:source.workflow_state(c,choices[0],bad+[done[ai+1]]));counts['source_negative_audit_paths']+=1
            check(c['tempo_advance_gate']['tempo_advance_authorized'] is False and c['timed_contact_count'] is None);check(p['graph']['failure_policy']['fatigue_repair_execution_not_claimed'] is True)
        for mutate in [lambda x:x.update(package_key='foreign'),lambda x:x.update(contract_sha256='0'*64),lambda x:x.update(source_clock=90)]:
            bad=copy.deepcopy(choices[0]);mutate(bad);refuse(lambda:source.selection(c,bad))
        for n in nodes.values():
            d=n.get('computed_expected')
            if d and d['kind']=='source_order_P_directions':
                rawchoices=choices[0][d['directions_ref']['path'][-1]];check(m.resolve_projection(d,rawchoices)[0]==d['protocol_start']);refuse(lambda:m.resolve_projection(d,True));refuse(lambda:m.resolve_projection({**d,'first_P_order':999},rawchoices));refuse(lambda:m.resolve_projection({**d,'extra':True},rawchoices));counts['projection_descriptors_checked']+=1
    for value in [None,True,'15',float('inf'),float('nan'),-1]:check(m.numeric_guard(value,15) is False)
    check(m.numeric_guard(17.5,17.5));check(not m.numeric_guard(15,17.5))
    for name,row in reps.items():
        i=rows.index(row)
        for mutate in [lambda p:p.update(grants_credit=True),lambda p:p.update(fixed_bpm=90),lambda p:p['graph']['failure_policy'].update(terminal_current_pass=False),lambda p:p['graph']['nodes']['setup']['schema'].update(additionalProperties=True)]:
            changed=copy.deepcopy(rows);cl=copy.deepcopy(closure);mutate(changed[i]['program']);changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));cl['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(changed,cl,originals,h,g))
    descriptor=pinned(selection['current_descriptor']);accepted={x['selection']['package_key'] for x in h.strict(descriptor)['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'};check(set(closure['keys']).isdisjoint(accepted))
    result={'outcome':'44_LEVEL063_CACHED_SOURCE_PROGRAM_AND_COUNTEREXAMPLES_PASS_NATIVE_PENDING','rows':44,'source_programs':10,'graph_nodes':519,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'current_accepted_overlap':0,'current_descriptor_sha256':h.sha(descriptor),'limits':'Producer DATA and retained stateless source-oracle proof only. New operators/number forms/actions-source release/repair admission/terminal-failure loops and independent native/view/package review pending. Fatigue repairs are retained guidance, not executed repairs. Manual audio/timing/listening/two-day/full-gate obligations unobserved.'};(BASE/'bulk-validation-r01.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
