#!/usr/bin/env python3
"""Exhaustive18 source/row/form integrity; bounded finger-vector causal proof."""
from pathlib import Path
import argparse,collections,copy,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2];sp=importlib.util.spec_from_file_location('frame_system_data',ROOT/'Tools/exercise-family-compiler/extend_manual_frame_system.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def prove(root=ROOT,out=None):
    start=time.perf_counter();root=Path(root).resolve();lib=m.library(root);h=lib.helper(root);rows,cl,originals,proofs,cache,metrics=m.build(root);counts=collections.Counter()
    def check(v,code):counts['assertions']+=1;assert v,code
    def refuses(fn):
        counts['malformed_refusals']+=1
        try:fn()
        except(h.BindingError,AssertionError,KeyError,TypeError,ValueError):return
        raise AssertionError('EXPECTED_REFUSAL')
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
        if 'string'in t:return 'Actual manual source report'
        raise AssertionError('TYPE')
    def leaves(s,v,path=()):
        t=s['type'];t=t if type(t)is list else[t]
        if 'object'in t:
            for k,c in s['properties'].items():yield from leaves(c,v[k],(*path,k))
        elif 'array'in t:
            for i,x in enumerate(v):yield from leaves(s['items'],x,(*path,i))
        else:yield path,s,v
    def changed(q,path,v):
        out=copy.deepcopy(q);target=out
        for k in path[:-1]:target=target[k]
        target[path[-1]]=v;return out
    def contacts(v):
        if type(v)is list:return sum(contacts(x)for x in v)
        if type(v)is dict:
            if 'ordered_contacts'in v:return len(v['ordered_contacts'])
            if 'printed_note'in v and ('fret'in v or 'string'in v):return 1
            return sum(contacts(x)for x in v.values())
        return 0
    check((root/m.OUT/'definitions.jsonl').read_bytes()==b''.join(h.encoded(r)+b'\n'for r in rows),'ALL18_ROUNDTRIP');check((root/m.OUT/'family-closure.json').read_bytes()==h.encoded(cl)+b'\n','CLOSURE_ROUNDTRIP')
    for row in rows:
        o=originals[row['source_key']];c=o['implementation']['manual_execution_contract'];p=row['program'];profile=p['source_task_kind'];model=cache.pinned(proofs[profile]['model']);before=h.encoded(o);check(m.validate(h,p,o,m.fixtures(model,c)),'SOURCE_VALIDATION');nodes=p['graph']['nodes'];valid=m.representative_choices(c,profile)[0]
        for choice in m.representative_choices(c,profile):
            plan=m.selection(h,model,c,profile,choice);check(plan==m.selection(h,model,c,profile,choice),'SOURCE_SELECTOR_DETERMINISTIC');check(h.encoded(o)==before,'NO_ORIGINAL_MUTATION');counts['source_choice_paths']+=1
            extent=84 if profile=='seams'else 128 if profile=='capstone'else 90 if profile=='zigzags'else 2*c['printed_contacts'] if profile=='lanes'else c['printed_contacts']+c['additional_translated_contacts'];check(contacts(plan)==extent,'COMPLETE_ACTUAL_SOURCE_EXTENT')
            if profile in ['seams','capstone']:
                groups=plan['pass1']+plan['pass2'];cs=[e for g in groups for e in g['ordered_contacts']];check([e['practice_attack_order']for e in cs]==list(range(1,len(cs)+1)),'CONTINUOUS_TWO_PASS_ORDER');check([e['selected_pick']for e in cs]==['D'if (i%2==0)==(choice['start_stroke']=='D')else'U'for i in range(len(cs))],'NO_PICK_RESET_BETWEEN_PASSES')
            if profile=='lanes':check(all(e['fret_finger']==1 for e in plan['finger1'])and [e['fret_finger']for e in plan['local']]==choice['second_pass_fingers'],'PRINTED_FIRST1_VS_CHOSEN_LOCAL_FINGERS')
            if profile=='sequences':check(len(plan['translations'])==4 and [x['frame']for x in plan['translations']]==[x['frame']for x in c['steps'][3]['derived_routes']],'ALL_FOUR_SOURCE_FRAME_TRANSLATIONS')
        for bad in [{**valid,'start_stroke':'P'},{**valid,'bpm':80},{**valid,'source_key':'foreign'}]:refuses(lambda bad=bad:m.selection(h,model,c,profile,bad))
        if profile=='lanes':
            for bad in [[None]*c['printed_contacts'],[False]*c['printed_contacts'],[0]*c['printed_contacts'],[5]*c['printed_contacts'],[1.0]*c['printed_contacts'],[1]*(c['printed_contacts']-1),[1]*(c['printed_contacts']+1)]:refuses(lambda bad=bad:m.selection(h,model,c,profile,{**valid,'second_pass_fingers':bad}))
            counts['finger_vector_full_product_enumerated']=0
        saved={};id='choose_realization';visited=[]
        while nodes[id]['kind']!='end':
            n=nodes[id];q=payload(n['schema']);q.update(copy.deepcopy(n['expected']))
            if id=='choose_realization':q.update(valid)
            for g in n['constraints']:
                if g['kind']=='same_as_saved':b,z=g['right']['path'];q[g['left']['path'][0]]=copy.deepcopy(saved[b][z])
            h.validate_payload(n['schema'],q);check(all(eq(q[k],v)for k,v in n['expected'].items()),'EXACT_SOURCE_REPORTS');check(all(h.data_guard(g,q,saved)for g in n['constraints']),'SOURCE_CHOICE_REPORT_BINDING');counts['typed_forms']+=1;pre=h.encoded(n)
            refuses(lambda:h.validate_payload(n['schema'],{**q,'extra':True}))
            for path,s,value in leaves(n['schema'],q):
                types=s['type'];types=types if type(types)is list else[types]
                if 'null'in types:
                    unknown=changed(q,path,None);h.validate_payload(n['schema'],unknown);counts['valid_unknown_reports']+=1;check(h.encoded(n)==pre,'UNKNOWN_NO_SCHEMA_MUTATION')
                    if path[0]in n['expected']:check(not eq(unknown[path[0]],n['expected'][path[0]]),'UNKNOWN_NOT_SOURCE_SUCCESS')
                refuses(lambda path=path:h.validate_payload(n['schema'],changed(q,path,{})))
                if type(value)is bool:
                    negative=changed(q,path,not value);h.validate_payload(n['schema'],negative);check(path[0]in n['expected']and not eq(negative[path[0]],n['expected'][path[0]]),'NEGATIVE_REPORT_DIAGNOSES');counts['valid_negative_reports']+=1
            if id=='normal_local_fingering_ready':
                g=n['constraints'][0];unknown=copy.deepcopy(q);unknown['reported_second_pass_fingers'][0]=None;h.validate_payload(n['schema'],unknown);check(h.data_guard(g,unknown,saved)is False,'UNKNOWN_FINGER_REENTRY_BLOCKS_SECOND_PASS');wrong=copy.deepcopy(q);wrong['reported_second_pass_fingers'][0]=2;h.validate_payload(n['schema'],wrong);check(h.data_guard(g,wrong,saved)is False,'WRONG_CHOSEN_FINGER_REPORT_BLOCKS_SECOND_PASS')
            saved[id]=q;visited.append(id);id=n['next']
        counts['all_row_legal_data_paths']+=1
        if profile=='sequences':check(visited.index('descending_readiness')<visited.index('all_other_frame_translations')and nodes['descending_readiness']['expected']['secure_reports'],'DESCENDING_PREREQUISITE_GATE_BEFORE_TRANSLATION');counts['source_readiness_boundaries']+=1
        if profile in ['seams','zigzags','capstone']:check(sum(nodes[n]['physical']for n in visited)==1,'NO_INTERNAL_CONTINUITY_UI_SEAM')
        if profile=='seams':check(c['source_clock']is None and 'fixed_bpm'not in c and p['original_clock_fields']['fixed_bpm_present']is False,'ORIGINAL_CLOCK_PROPERTY_ABSENCE_RETAINED')
        check(h.encoded(o)==before and h.sha(h.encoded(p))==row['contract_sha256']==cl['contracts'][row['source_key']],'ORIGINAL_AND_PROGRAM_HASH')
    refuses(lambda:h.strict('{"x":1,"x":2}'));refuses(lambda:h.strict('{"x":NaN}'))
    r={'outcome':'PASS18_SOURCE_MODEL_GROUPED_PROGRAM_DATA_NATIVE_PENDING','rows':18,'profiles':m.COUNTS,'counts':dict(counts),'generation_metrics':metrics,'seconds':time.perf_counter()-start,'source_pdf_txt_reads':0,'native_execution':False,'official_acceptance_increment':0,'limits':['Pure cached source/model/form/group-order proof; native prerequisite/release/continuity/history/token/choice projection/current Home/independent acceptance deferred.','Representative bounded finger vectors, all-entry malformed/unknown guards; 4^16 combinations deliberately not enumerated and no ergonomic/performance success inferred.']}
    if out:p=Path(out);p.parent.mkdir(parents=True,exist_ok=True);p.open('x').write(json.dumps(r,indent=2)+'\n')
    return r
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',default=str(ROOT));a.add_argument('--out');x=a.parse_args();print(json.dumps(prove(x.root,x.out)))
