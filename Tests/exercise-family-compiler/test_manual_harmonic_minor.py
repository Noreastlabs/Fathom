#!/usr/bin/env python3
"""Consolidated source/model/graph DATA proof; no native or learner autofill."""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2]
sp=importlib.util.spec_from_file_location('harmonic_minor_data',ROOT/'Tools/exercise-family-compiler/extend_manual_harmonic_minor.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def prove(root=ROOT,output=None):
    start=time.perf_counter();root=Path(root).resolve();h=m.helper(root);rows,cl,originals,proofs,cache,metrics=m.build(root);counts=collections.Counter()
    def check(v,code):counts['assertions']+=1;assert v,code
    def refuses(fn):
        counts['malformed_refusals']+=1
        try:fn()
        except (h.BindingError,AssertionError,KeyError,ValueError,TypeError):return
        raise AssertionError('EXPECTED_UNCHANGED_REFUSAL')
    def equal(a,b):
        if type(a)is not type(b):return False
        if type(a)is dict:return set(a)==set(b)and all(equal(a[k],b[k])for k in a)
        if type(a)is list:return len(a)==len(b)and all(equal(x,y)for x,y in zip(a,b))
        return a==b
    def payload(s,expected=None):
        if expected is not None:return copy.deepcopy(expected)
        t=s['type'];t=t if type(t)is list else[t]
        if 'enum'in s:return next(copy.deepcopy(x)for x in s['enum']if x is not None)
        if 'object'in t:return {k:payload(v)for k,v in s['properties'].items()}
        if 'array'in t:return [payload(s['items'])for _ in range(s.get('minItems',1))]
        if 'boolean'in t:return True
        if 'integer'in t:return max(1,s.get('minimum',0))
        if 'string'in t:return 'Actual learner-reported source evidence'
        raise AssertionError('SCHEMA_TYPE')
    def walks(s,v,path=()):
        t=s['type'];t=t if type(t)is list else[t]
        if 'object'in t:
            for k,c in s['properties'].items():yield from walks(c,v[k],(*path,k))
        elif 'array'in t:
            for i,a in enumerate(v):yield from walks(s['items'],a,(*path,i))
        else:yield path,s,v
    def put(v,path,value):
        out=copy.deepcopy(v);target=out
        for part in path[:-1]:target=target[part]
        target[path[-1]]=value;return out
    defs=root/m.BASE/'generated-r02/definitions.jsonl';closure=root/m.BASE/'generated-r02/family-closure.json'
    check(defs.read_bytes()==b''.join(h.encoded(r)+b'\n'for r in rows),'GENERATED_ALL47_ROUNDTRIP');check(closure.read_bytes()==h.encoded(cl)+b'\n','CLOSURE_ROUNDTRIP')
    for row in rows:
        original=originals[row['source_key']];c=original['implementation']['manual_execution_contract'];p=row['program'];profile=p['source_task_kind'];before=h.encoded(original);nodes=p['graph']['nodes'];model=cache.pinned(proofs[profile]['model']);check(m.validate_program(h,p,original),'SOURCE_GRAPH')
        for choice in m.choices(c,profile):
            one=m.old_selection(model,c,choice);two=m.old_selection(model,c,choice);check(one==two,'EXISTING_SELECTOR_DETERMINISM');check(h.encoded(original)==before,'ORIGINAL_IMMUTABLE');counts['exact_source_choice_paths']+=1
            if profile=='leading':
                check(len(one['picked'])==len(one['ornament'])==6,'SOURCE6_SOUNDING_POSITIONS');check(sum(x['picked_attack']for x in one['ornament'])==5,'SOURCE5_PICKED_ATTACKS');target=one['ornament'][choice['pair_start']];check(target['articulation']==choice['technique']and target['selected_pick']is None,'EXPLICIT_SINGLE_PAIR');check(target['sounding_note']=='A'and target['source_target_fret_equivalent']==target['original_source_contact']['fret'],'CHOSEN_VS_PRINTED_TARGET')
                if choice['technique']=='half_step_bend':check(target['performed_fret']==target['source_target_fret_equivalent']-1 and target['bend_semitones']==1 and target['acoustic_tolerance']is None,'BEND_PRINTED_VS_PERFORMED')
            if profile=='capstone':check(len(one)==16 and sum(len(b['ordered_contacts'])for b in one)==64,'UNINTERRUPTED_SOURCE64');check([b['chord']for b in one]==c['steps'][1]['chords_by_bar'],'SOURCE16_HARMONY')
        if profile!='octaves':
            valid=m.choices(c,profile)[0];refuses(lambda:m.old_selection(model,c,{**valid,'start_stroke':'P'}));refuses(lambda:m.old_selection(model,c,{**valid,'bpm':80}));refuses(lambda:m.old_selection(model,c,{**valid,'package_key':'foreign'}))
        saved={};counts['exact_legal_graph_paths']+=1
        ordered=['source_step_'+str(i)for i in range(1,len(c['steps'])+1)]
        if 'choose_realization'in nodes:ordered.insert(0,'choose_realization')
        for id in ordered:
            n=nodes[id];q=payload(n['schema']);q.update(copy.deepcopy(n['expected']))
            if id=='choose_realization':q.update(m.choices(c,profile)[0])
            for g in n['constraints']:
                if g['kind']=='same_as_saved':a=g['left']['path'][0];b,z=g['right']['path'];q[a]=copy.deepcopy(saved[b][z])
                if g['kind']=='source_choice_implication':q['shift_needed_reported']=False
            h.validate_payload(n['schema'],q);check(all(equal(q[k],v)for k,v in n['expected'].items()),'TYPED_SOURCE_EXPECTED_REPORT');check(all(m.data_guard(h,g,q,saved)for g in n['constraints']),'SOURCE_FORM_GUARDS');saved[id]=q;counts['typed_source_forms']+=1
            unchanged=h.encoded(n);refuses(lambda:h.validate_payload(n['schema'],{**q,'untrusted_extra':True}));check(h.encoded(n)==unchanged,'MALFORMED_UNCHANGED')
            for path,s,value in walks(n['schema'],q):
                if 'null'in (s['type']if type(s['type'])is list else[s['type']]):
                    unknown=put(q,path,None);h.validate_payload(n['schema'],unknown);check(h.encoded(n)==unchanged,'UNKNOWN_RETAINED_NO_SCHEMA_MUTATION');counts['valid_unknown_reports']+=1
                bad={}if type(value)is not dict else []
                refuses(lambda path=path,bad=bad:h.validate_payload(n['schema'],put(q,path,bad)))
                if type(value)is bool:
                    negative=put(q,path,not value);h.validate_payload(n['schema'],negative);counts['valid_negative_boolean_reports']+=1
                    check(not equal(negative,q),'NEGATIVE_MUST_NOT_BE_SUCCESS_LITERAL')
            if profile=='capstone'and id=='source_step_3':
                for field,value in [('announcements',q['announcements'][:-1]),('announcements',q['announcements']+[q['announcements'][-1]])]:refuses(lambda field=field,value=value:h.validate_payload(n['schema'],{**q,field:value}))
                bad=copy.deepcopy(q);bad['announcements'][0]['next_chord']='foreign chord';h.validate_payload(n['schema'],bad);check(not equal(bad['announcements'],n['expected']['announcements']),'WRONG_NEXT_CHORD_DIAGNOSED');bad=copy.deepcopy(q);bad['announcements'][14]['bar']=16;h.validate_payload(n['schema'],bad);check(not equal(bad['announcements'],n['expected']['announcements']),'NO_EXTRA_FINAL_ANNOUNCEMENT');check(n['physical']is True and n['next']=='source_step_4','NO_INTERNAL_CAPSTONE_REPORT_SEAMS')
        check(h.encoded(original)==before,'ALL_ROW_ORIGINAL_PRESERVED')
        if profile=='augmented-second':
            g=next(g for g in nodes['source_step_3']['constraints']if g['kind']=='source_choice_implication')
            for needed,strategy,result in [(True,'shift',True),(True,'comfortable_reach',False),(False,'shift',True),(False,'comfortable_reach',True),(None,'shift',False),(None,'comfortable_reach',False)]:check(m.data_guard(h,g,{'shift_needed_reported':needed},{'choose_realization':{'hand_strategy':strategy}})is result,'EXACT_SHIFT_CAUSAL_RULE')
            refuses(lambda:m.data_guard(h,g,{'shift_needed_reported':'yes'},{'choose_realization':{'hand_strategy':'shift'}}));check(p['source_state_protocols'][0]['outcome']=='stopped','SOURCE_PAIN_STOPS_NOT_SUCCESS')
        if profile in ['comparison','leading']:
            route=nodes['repair_choice']['routes']['directional_pair_repair'if profile=='comparison'else'sing_resolution_repair'];check(route['failed_node']=='source_step_4'and route['guard']['equals']is False and route['guard_phase']=='after_owned_release_before_new_repair_activation','FAILED_NODE_AND_NEGATIVE_BOUND');check(nodes[route['next']]['next']=='repair_choice','NO_REPAIR_SUCCESS_SHORTCUT');counts['conditional_source_repair_paths']+=1
            field=route['guard']['field']
            for tag,v,expected in [('source_step_4',False,True),('source_step_4',True,False),('source_step_4',None,False),('source_step_2',False,False)]:check(m.repair_eligible(h,route,{'pass_tag':tag,'payload':{field:v}})is expected,'EXACT_REPAIR_CAUSAL_PREDICATE')
            refuses(lambda:m.repair_eligible(h,route,{'pass_tag':'source_step_4','payload':{field:'false'}}));refuses(lambda:m.repair_eligible(h,route,{'pass_tag':'source_step_4','payload':{field:False},'foreign':True}))
        if profile=='comparison':check(p['source_state_protocols'][0]['unknown_does_not_clear']and set(p['source_state_protocols'][0]['retain_across'])=={'retry','stop','navigation','restart'},'REPAIR_DEBT_PERSISTENCE_REQUIRED')
        if profile=='melodic':check(nodes['source_step_4']['physical']and nodes['source_step_5']['expected']['longer_than_previous_reported']is True and c['steps'][3]['duration_relation']['numeric_values']is None,'QUALITATIVE_SOURCE_HOLD')
        if profile=='dominants':check(len(c['steps'][4]['selected_chord_route_realization'])==6 and nodes['source_step_5']['expected']['all_three_pairs_in_order_reported'],'FULL_THREE_SOURCE_HEARING_PAIRS')
        if profile=='triads':check(set(c['steps'][1]['required_core_secure_reports'])<=set(nodes['source_step_2']['expected']),'EXACT_SOURCE_CORE_READINESS')
    refuses(lambda:h.strict('{"x":1,"x":2}'));refuses(lambda:h.strict('{"x":NaN}'));refuses(lambda:h.strict('{"x":Infinity}'))
    for r in rows:check(h.sha(h.encoded(r['program']))==r['contract_sha256']==cl['contracts'][r['source_key']],'ALL_ROW_PROGRAM_HASH')
    result={'outcome':'PASS_47_CACHED_SOURCE_MODEL_GRAPH_DATA_NATIVE_PENDING','counts':dict(counts),'rows':47,'source_profiles':m.COUNTS,'seconds':time.perf_counter()-start,'construction_metrics':metrics,'source_pdf_txt_reads':0,'native_execution':False,'official_acceptance_increment':0,'limits':['Pure source/model/form/schema proof only; per-instance native tokens/history/release/projection/debt/stop operators require independent future native/current Home QA.','Pinned existing pure selector function is source oracle, not a native learner factory. No acoustic/comfort/clock/mastery is measured.']}
    if output:p=Path(output);p.parent.mkdir(parents=True,exist_ok=True);p.open('x').write(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',default=str(ROOT));a.add_argument('--out');x=a.parse_args();print(json.dumps(prove(x.root,x.out)))
