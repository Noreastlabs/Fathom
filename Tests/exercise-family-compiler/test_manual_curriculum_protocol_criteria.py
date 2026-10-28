#!/usr/bin/env python3
"""One closed23 span/schema/criterion/policy proof; no native execution."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-curriculum-protocols23-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(value):
        counts['assertions']+=1
        if not value:raise AssertionError('B_SOURCE_CRITERION')
    def refuse(fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,TypeError,IndexError):counts['malformed_refusals']+=1
        else:raise AssertionError('REFUSAL_MISSING')
    def pinned(r):
        if r['path']not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        raw=cache[r['path']];check(len(raw)==r['bytes']and hashlib.sha256(raw).hexdigest()==r['sha256']);return raw
    p=ROOT/'Tools/exercise-family-compiler/extend_manual_curriculum_protocol_criteria.py';spec=importlib.util.spec_from_file_location('b_criteria',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=(ROOT/m.SELECTION).read_bytes();check(hashlib.sha256(raw).hexdigest()==m.SELECTION_SHA);s=json.loads(raw);binding=json.load(open(ROOT/m.BINDING));pinned(binding);h=m.load_helper(ROOT,binding)
    for r in [s['ledger'],s['current_descriptor'],s['excluded_c96'],s['exception_witness'],s['exception_independent_review'],*s['cached_inputs']]:pinned(r)
    receipt=json.load(open(BASE/'generated-r03/generation-receipt.json'))
    for r,sha in zip(receipt['files'],['63a0a830674d660e7477e685b436c8e1f3ef9b43e84df1bb0958ba8d258276b1','1b44e26617b3c023ab6d15907ce85e4fdb6aa466987f66a96d7e98ea67ccf0ae']):check(r['sha256']==sha);pinned(r)
    rows=[h.strict(x)for x in (BASE/'generated-r03/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r03/family-closure.json').read_bytes());visual=h.strict(pinned(s['exception_witness']));originals={};materials=s['source_material_catalog'];reps={}
    for r in rows:
        ref=r['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==r['original_row_sha256']and o['package_key']==r['source_key']and o['source_identity']==r['source_identity']);originals[r['source_key']]=o;counts['exact_source_roundtrips']+=1
        p=r['program'];
        if 'level060/modulej/p020-u001/' in r['source_key']:
            header=next(x for x in p['source_metadata'] if 'THE PICK MAY MOVE THROUGH FOUR STRINGS;' in x['literal']);check(header['manual_gate'] is False and header['role']=='source_capability_header');check(header['id'] not in p['graph']['nodes']);counts['capability_header_negatives']+=1
        for x in p['source_criteria']:
            if x['literal'].startswith(('TENSION shorten','CHORD IDENTITY LOST return')):
                for q in x['quantities']:
                    check(q['role']=='conditional_source_repair_fact' and q['unconditional_completion_gate'] is False);check(q['id']+'_reported_'+h.slug(q['unit']) not in p['graph']['nodes'][x['id']]['schema']['properties']);counts['conditional_repair_count_negatives']+=1
        reps.setdefault(p['name'],r);check(r['retained_contract_path']==['implementation']and p['source_kind']=='manual_curriculum_task');check(p['runtime_admitted']is False and p['performance_observed']is False and p['fixed_bpm']is None and p['grants_credit']is False);check(p['graph']['nodes']['source_extent']['physical']is True)
        spans=p['source_literal_ref']['source_span_witnesses'];body=o['implementation']['source_scope']['selected_source_text']
        for span in spans:
            w=span['witness']
            if w['kind']=='original_record_span':check(body[w['start']:w['end']]==span['text']and h.sha(span['text'].encode())==w['text_sha256']);check(w['original_record_path']==['implementation','source_scope','selected_source_text']);counts['source_spans']+=1
            else:check(w['kind']=='independently_reviewed_visual_clause'and w['path']=='visually_read_fifth_row');check(span['text']=='Fifth '+' '.join(visual['visually_read_fifth_row'][q]for q in ['maj7','7','m7','m7b5']));counts['reviewed_visual_clauses']+=4
        joined=' '.join(x['text']for x in spans);check(h.sha(joined.encode())==p['source_literal_sha256']);mask=[False]*len(joined)
        for x in p['source_metadata']+p['source_criteria']:
            a,b=x['source_excerpt']['start'],x['source_excerpt']['end'];check(joined[a:b]==x['literal']);mask[a:b]=[True]*(b-a)
        check(all(x or char.isspace()for x,char in zip(mask,joined)));counts['source_criteria']+=len(p['source_criteria'])
        if p['name']=='b_source_recording_quality':
            gate=next(x for x in p['source_criteria']if 'clean on two days'in x['literal']);check(p['graph']['nodes']['tempo_choice']['routes']['hold_tempo']['next']=='end_tempo_held');check(p['graph']['nodes'][gate['id']]['constraints'][-1]=={'kind':'distinct_dates','fields':['date_1','date_2']})
    check(m.validate(rows,closure,originals,h,visual,materials))
    def sample(schema):
        t=schema['type'];t=t[0]if type(t)is list else t
        if 'enum'in schema:return next(x for x in schema['enum']if x is not None)
        if t=='string':return 'Declared manual source-test evidence'
        if t=='boolean':return True
        if t=='integer':return schema.get('minimum',0)
        if t=='array':return [sample(schema['items'])for _ in range(schema['minItems'])]
        if t=='object':return {k:sample(v)for k,v in schema['properties'].items()}
        raise ValueError('UNSUPPORTED_SCHEMA')
    for row in rows:
        p=row['program'];nodes=p['graph']['nodes']
        for name,n in nodes.items():
            if n['kind']=='end':continue
            payload=sample(n['schema']);payload.update(copy.deepcopy(n['expected']));failed={'pass_tag':payload.get('failed_criterion','source_extent')};saved={}
            for guard in n['constraints']:
                if guard['kind']=='minimum':payload[guard['field']]=guard['value']
                elif guard['kind']=='maximum':payload[guard['field']]=guard['value']
                elif guard['kind']=='distinct_dates':payload[guard['fields'][0]]='2026-09-01';payload[guard['fields'][1]]='2026-09-02'
                elif guard['kind']=='source_protocol_reported':
                    if guard['policy']=='timed_ladder':payload[guard['work_field']]=[x+2 for x in guard['source_work_targets']];payload[guard['rest_field']]=list(payload[guard['work_field']]);payload[guard['clean_sets_field']]=guard['minimum_clean_sets']
                    else:payload[guard['systems_field']]=['crosspick']*16
            h.validate_payload(n['schema'],payload);counts['typed_forms']+=1
            for guard in n['constraints']:
                if not m.data_guard(h,guard,payload,materials,saved,failed):raise AssertionError((row['source_key'],name,guard,payload))
                check(True);counts['guard_positive_paths']+=1;refuse(lambda:m.data_guard(h,{**guard,'foreign':True},payload,materials,saved,failed))
                key=guard.get('field')
                if key and key in payload:
                    changed=copy.deepcopy(payload);changed[key]=None
                    if None in (n['schema']['properties'][key]['type']if type(n['schema']['properties'][key]['type'])is list else []):pass
                    if 'null'in (n['schema']['properties'][key]['type']if type(n['schema']['properties'][key]['type'])is list else []):h.validate_payload(n['schema'],changed);check(m.data_guard(h,guard,changed,materials,saved,failed)is False);counts['valid_unknown_negatives']+=1
                if guard['kind']=='distinct_dates':
                    changed=copy.deepcopy(payload);changed[guard['fields'][1]]=changed[guard['fields'][0]];check(m.data_guard(h,guard,changed,materials,saved,failed)is False);changed[guard['fields'][1]]='2026-02-30';check(m.data_guard(h,guard,changed,materials,saved,failed)is False);counts['date_negative_paths']+=2
                if guard['kind']=='source_material_reuse':check(m.data_guard(h,guard,{**payload,guard['field']:'foreign-source-key'},materials)is False);counts['foreign_material_negatives']+=1
                if guard['kind']=='source_protocol_reported':
                    changed=copy.deepcopy(payload)
                    if guard['policy']=='timed_ladder':changed[guard['rest_field']][0]=15;check(m.data_guard(h,guard,changed,materials)is False);changed=copy.deepcopy(payload);changed[guard['clean_sets_field']][1]=2;check(m.data_guard(h,guard,changed,materials)is False);counts['ladder_negative_paths']+=2
                    else:changed[guard['systems_field']][:4]=['crosspick','hybrid','down_sweep','up_sweep'];check(m.data_guard(h,guard,changed,materials)is False);counts['system_ceiling_negative_paths']+=1
            refuse(lambda:h.validate_payload(n['schema'],{**payload,'extra_report':True}))
            if n['kind']=='report':check(n['next']in nodes)
            else:
                check(set(n['routes'])==set(n['schema']['properties'][n['route_field']]['enum']));check(all(r['next']in nodes for r in n['routes'].values()))
    for material in materials:
        ref=material['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==material['original_row_sha256']and o['package_key']==material['key']and len(o['implementation']['events'])==material['printed_contact_count']);check(all(e['onset_q']is None and e['duration_q']is None for e in o['implementation']['events']));counts['closed_reuse_material_roundtrips']+=1
    for name,r in reps.items():
        i=rows.index(r)
        for mutate in [lambda p:p.update(source_kind='source_defined_task'),lambda p:p.update(grants_credit=True),lambda p:p['graph']['nodes']['source_extent'].update(physical=False),lambda p:p['graph']['failure_policy'].update(terminal_current_pass=False)]:
            altered=copy.deepcopy(rows);cl=copy.deepcopy(closure);mutate(altered[i]['program']);altered[i]['contract_sha256']=h.sha(h.encoded(altered[i]['program']));cl['contracts'][r['source_key']]=altered[i]['contract_sha256'];refuse(lambda:m.validate(altered,cl,originals,h,visual,materials))
    accepted={x['selection']['package_key']for x in h.strict(pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};check(set(closure['keys']).isdisjoint(accepted));check(len(rows) == 23 and counts['source_criteria'] == 173 and counts['reviewed_visual_clauses']==4)
    result={'outcome':'23_SOURCE_SPAN_SCHEMA_CRITERION_AND_POLICY_PROOF_PASS_NATIVE_PENDING','rows':23,'source_program_profiles':10,'source_criteria':173,'graph_nodes':267,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'original_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'current_accepted_overlap':0,'limits':'Source physical extents and intermediate duties are manual reports, not generated music/performance. Original kind retained, only four visual Fifth clauses independently accepted. New source-span/material-reuse/protocol guard native bridges and distinct behavior/UI/package review pending; tempo-hold gate unselected, take-mode multiplicity unforced.'};(BASE/'bulk-validation-r02.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
