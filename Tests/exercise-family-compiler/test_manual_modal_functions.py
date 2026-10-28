#!/usr/bin/env python3
"""One exhaustive51 DATA roundtrip/source-unit/form/choice boundary proof."""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2];sp=importlib.util.spec_from_file_location('modal_function_data',ROOT/'Tools/exercise-family-compiler/extend_manual_modal_functions.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def prove(root=ROOT,out=None):
    start=time.perf_counter();root=Path(root).resolve();h=m.helper(root);rows,cl,originals,proofs,cache,metrics=m.build(root);count=collections.Counter()
    def check(v,code):count['assertions']+=1;assert v,code
    def refuses(fn):
        count['malformed_refusals']+=1
        try:fn()
        except(h.BindingError,AssertionError,KeyError,ValueError,TypeError):return
        raise AssertionError('EXPECTED_UNCHANGED_REFUSAL')
    def eq(a,b):
        if type(a)is not type(b):return False
        if type(a)is dict:return set(a)==set(b)and all(eq(a[k],b[k])for k in a)
        if type(a)is list:return len(a)==len(b)and all(eq(x,y)for x,y in zip(a,b))
        return a==b
    def payload(s):
        t=s['type'];t=t if type(t)is list else[t]
        if 'enum'in s:return copy.deepcopy(next(x for x in s['enum']if x is not None))
        if 'object'in t:return {k:payload(v)for k,v in s['properties'].items()}
        if 'array'in t:return [payload(s['items'])for _ in range(s['minItems'])]
        if 'boolean'in t:return True
        if 'integer'in t:return max(1,s.get('minimum',0))
        if 'string'in t:return 'Manually reported source observation'
        raise AssertionError('TYPE')
    def leaves(s,v,path=()):
        t=s['type'];t=t if type(t)is list else[t]
        if 'object'in t:
            for k,c in s['properties'].items():yield from leaves(c,v[k],(*path,k))
        elif 'array'in t:
            for i,x in enumerate(v):yield from leaves(s['items'],x,(*path,i))
        else:yield path,s,v
    def changed(q,path,v):
        q=copy.deepcopy(q);target=q
        for k in path[:-1]:target=target[k]
        target[path[-1]]=v;return q
    check((root/m.OUT/'definitions.jsonl').read_bytes()==b''.join(h.encoded(r)+b'\n'for r in rows),'ALL51_ROUNDTRIP');check((root/m.OUT/'family-closure.json').read_bytes()==h.encoded(cl)+b'\n','CLOSURE_ROUNDTRIP')
    for row in rows:
        o=originals[row['source_key']];c=o['implementation']['manual_execution_contract'];before=h.encoded(o);profile=row['program']['source_task_kind'];model=cache.pinned(proofs[profile]['pure_function_model']);a=m.fixtures(model,c);p=row['program'];nodes=p['graph']['nodes'];check(m.validate(h,p,o,a),'ALL_SOURCE_REPORTS_RETAINED')
        for choice in m.choice_paths(c,profile):
            plan=m.selection(model,c,profile,choice);check(plan==m.selection(model,c,profile,choice),'PINNED_SELECTOR_DETERMINISM');check(h.encoded(o)==before,'IMMUTABLE_ORIGINAL');count['exact_source_choice_paths']+=1
            chosen_contacts=[]
            for k,v in plan.items():
                if type(v)is list:chosen_contacts.extend(v)
            check(len(chosen_contacts)==(12 if profile=='intervals'else 8 if profile in ['triads','sevenths']else 16 if profile in ['modes','progressions']else 10 if profile=='dominant_release'else 8+len(c['derived_core_contacts'])),'WHOLE_SOURCE_CONTACT_EXTENT')
            if profile=='dominant_release':check(plan['stop_after_order']==10 and len(plan['release'])==2 and plan['generated_backing']is False,'SOURCE_RELEASE_THEN_STOP')
            if profile=='modes':check(plan['accompaniment']==c['steps'][0]['choices'][choice['support_choice_index']]and not plan['accompaniment_automatically_generated'],'EXTERNAL_SUPPORT_EXPLICIT')
            if profile=='function_core':check(plan['core_before_final']+plan['core_final']==m.selection(model,c,profile,choice)['core_before_final']+m.selection(model,c,profile,choice)['core_final'],'SOURCE_CORE_REPLAY_ORDER')
        valid=m.choice_paths(c,profile)[0]
        for bad in [{**valid,'start_stroke':'P'},{**valid,'bpm':90},{**valid,'package_key':'foreign'}]:refuses(lambda bad=bad:m.selection(model,c,profile,bad))
        if 'support_choice_index'in valid:
            for bad in [-1,100000,False,0.0,None]:refuses(lambda bad=bad:m.selection(model,c,profile,{**valid,'support_choice_index':bad}))
        if 'release_choice'in valid:
            for bad in [-1,len(c['release_choices']),False,0.0,None]:refuses(lambda bad=bad:m.selection(model,c,profile,{**valid,'release_choice':bad}))
        count['all_row_legal_data_paths']+=1
        for id in ['choose_realization','prepare','complete_musical_unit','quality']:
            n=nodes[id];q=payload(n['schema']);q.update(copy.deepcopy(n['expected']));h.validate_payload(n['schema'],q);check(all(eq(q[k],v)for k,v in n['expected'].items()),'SOURCE_TYPED_EXPECTED');count['typed_forms']+=1;pre=h.encoded(n)
            refuses(lambda:h.validate_payload(n['schema'],{**q,'untrusted':True}));missing=copy.deepcopy(q);missing.pop(next(iter(missing)));refuses(lambda:h.validate_payload(n['schema'],missing))
            for path,s,value in leaves(n['schema'],q):
                types=s['type'];types=types if type(types)is list else[types]
                if 'null'in types:
                    unknown=changed(q,path,None);h.validate_payload(n['schema'],unknown);check(h.encoded(n)==pre,'UNKNOWN_REPORT_NO_MUTATION');count['valid_unknown_reports']+=1
                    if path[0]in n['expected']:check(not eq(unknown[path[0]],n['expected'][path[0]]),'UNKNOWN_CANNOT_MATCH_SOURCE_REPORT')
                refuses(lambda path=path:h.validate_payload(n['schema'],changed(q,path,{})))
                if type(value)is bool:
                    negative=changed(q,path,not value);h.validate_payload(n['schema'],negative);check(path[0]in n['expected']and not eq(negative[path[0]],n['expected'][path[0]]),'NEGATIVE_SOURCE_REPORT_DIAGNOSIS');count['valid_negative_reports']+=1
                if type(value)is str and path[0]in n['expected']:
                    wrong=changed(q,path,'Foreign pitch/function/source target');h.validate_payload(n['schema'],wrong);check(not eq(wrong[path[0]],n['expected'][path[0]]),'WRONG_SOURCE_LITERAL_DIAGNOSED')
            check(h.encoded(n)==pre,'MALFORMED_STABLE_NODE')
        ref_indices=[r['original_contract_path'][1]for r in nodes['complete_musical_unit']['source_action_refs']];check(ref_indices==list(range(1,len(c['steps'])-1)),'FULL_CONTIGUOUS_MUSICAL_UNIT');check(nodes['complete_musical_unit']['next']=='quality'and nodes['complete_musical_unit']['physical']is True,'NO_INTERNAL_UI_RELEASE_REPORT_SEAM');check(nodes['prepare']['physical']is False and nodes['quality']['physical']is False,'NO_FABRICATED_PHYSICAL_REPORT_ACTIVATION')
        if profile in ['triads','sevenths','progressions','modes']:
            names=[]
            for v in a:
                if 'ordered_naming'in v:names.append(v['ordered_naming'])
            check(all(type(x)is list and len(x)==2 for x in names),'CHORD_THEN_MODE_PAIR');check(all(x[0]!=x[1]for x in names),'CHORD_MODE_DOMAIN_SEPARATE')
        sung=[v for v in c['steps']if v['action'].startswith('sing_')];check(sung,'SOURCE_SUNG_BEFORE_FINAL_REQUIRED');check(any('sung'in k and type(v)is bool and v for report_values in a for k,v in report_values.items()),'SOURCE_BEFORE_FINAL_ACK_REQUIRED')
        if profile=='dominant_release':
            route=nodes['repair_choice']['routes']['printed_G_sharp_repair'];check(route['failed_node']=='quality'and route['guard']=={'kind':'failed_report_predicate','field':'Gsharp_major_third_clear_reported','equals':False},'EXACT_DOMINANT_QUALITY_REPAIR');check(nodes['printed_G_sharp_repair']['next']=='repair_choice'and p['source_state_protocols'][0]['repair_alone_grants_completion']is False,'NO_REPAIR_ONLY_COMPLETION');check(p['source_state_protocols'][0]['unknown_does_not_clear'],'UNKNOWN_RETAINS_SOURCE_COLOR_DEBT');count['source_repair_boundaries']+=1
        check(h.sha(h.encoded(p))==row['contract_sha256']==cl['contracts'][row['source_key']],'ALL_ROW_PROGRAM_SHA');check(h.encoded(o)==before,'ALL_ORIGINAL_BYTES_PRESERVED')
    refuses(lambda:h.strict('{"x":1,"x":2}'));refuses(lambda:h.strict('{"x":NaN}'));refuses(lambda:h.strict('{"x":Infinity}'))
    r={'outcome':'PASS51_SOURCE_MODEL_FORM_GRAPH_DATA_NATIVE_PENDING','rows':51,'profiles':m.COUNTS,'counts':dict(count),'generation_metrics':metrics,'seconds':time.perf_counter()-start,'source_pdf_txt_reads':0,'native_execution':False,'official_acceptance_increment':0,'limits':['Pure cached source/model/schema/program proof. Native chosen-contact projection/owned release/history/recovery/token/UI/current Home/independent acceptance remains pending.','Grouped reports preserve source stage duties but do not measure whether singing/physical/support execution occurred in the required order. No inferred clock or automatic backing.']}
    if out:p=Path(out);p.parent.mkdir(exist_ok=True,parents=True);p.open('x').write(json.dumps(r,indent=2)+'\n')
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',default=str(ROOT));p.add_argument('--out');a=p.parse_args();print(json.dumps(prove(a.root,a.out)))
