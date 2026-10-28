#!/usr/bin/env python3
"""One closed B20 source/span/schema/guard bulk check. Native QA stays separate."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-readiness20-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(value):
        counts['assertions']+=1
        if not value:raise AssertionError('READINESS_SOURCE_OR_GUARD')
    def refuse(fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,TypeError,IndexError):counts['malformed_refusals']+=1
        else:raise AssertionError('EXPECTED_MALFORMED_REFUSAL')
    def pinned(r):
        if r['path']not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        b=cache[r['path']];check(len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']);return b
    spec=importlib.util.spec_from_file_location('readiness',ROOT/'Tools/exercise-family-compiler/extend_manual_readiness.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);h=m.helper(ROOT);s=h.strict((ROOT/m.SELECTION).read_bytes());check(h.sha((ROOT/m.SELECTION).read_bytes())==m.SELECTION_SHA)
    for ref in [s['ledger'],s['current_descriptor'],*s['cached_inputs']]:pinned(ref)
    receipt=json.load(open(BASE/'generated-r02/generation-receipt.json'))
    for r in receipt['files']:pinned(r)
    rows=[h.strict(x)for x in (BASE/'generated-r02/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r02/family-closure.json').read_bytes());originals={}
    for row in rows:
        ref=row['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==row['original_row_sha256']and h.sha(json.dumps(o,ensure_ascii=False,separators=(',',':')).encode())==row['original_compact_sha256']and o['package_key']==row['source_key']and o['source_identity']==row['source_identity']);originals[row['source_key']]=o;counts['exact_source_roundtrips']+=1
        p=row['program'];joined=' '.join(x['text']for x in p['source_literal_ref']['source_span_witnesses']);check(h.sha(joined.encode())==p['source_literal_sha256']);mask=[False]*len(joined)
        for span in p['source_literal_ref']['source_span_witnesses']:
            w=span['witness'];body=o
            for key in w['original_record_path']:body=body[key]
            check(body[w['start']:w['end']]==span['text']and h.sha(span['text'].encode())==w['text_sha256']);counts['exact_original_spans']+=1
        for x in p['source_criteria']+p['source_metadata']+p['source_conditional_repairs']:
            a,b=x['source_excerpt']['start'],x['source_excerpt']['end'];check(joined[a:b]==x['literal']);mask[a:b]=[True]*(b-a)
        check(all(mark or c.isspace()for mark,c in zip(mask,joined)));check(all(x['manual_gate']is False for x in p['source_metadata']));check(all(x['unconditional_gate']is False for x in p['source_conditional_repairs']));counts['source_criteria']+=len(p['source_criteria']);counts['source_conditional_repairs']+=len(p['source_conditional_repairs'])
        for n in p['graph']['nodes'].values():
            if str(n.get('pass_tag','')).startswith('source_repair_'):check(n['pass_tag']in p['graph']['nodes']['repair_bind']['schema']['properties']['failed_criterion']['enum']);counts['repair_failure_rebind_paths']+=1
        if 'top_string_silent' in p['name']:check('1-3-5 major root position'not in joined and joined.startswith('Silent-formation audit'));counts['foreign_recognition_answer_exclusions']+=1
        check(p['source_clock']is None and p['fixed_bpm']is None and p['runtime_admitted']is False and p['grants_credit']is False);check(p['graph']['nodes']['source_extent']['physical']is True and p['graph']['nodes']['prior_extent']['physical']is False)
    check(m.validate(h,rows,closure,originals));
    from decimal import Decimal
    decimal_schema={'type':['number','null'],'minimum':0,'maximum':10000}
    for value in [Decimal('15.000000000000000000000000000001'),0,None]:m.validate_payload(h,decimal_schema,value);check(True);counts['finite_nullable_decimal_paths']+=1
    for value in [True,'15',Decimal('NaN'),Decimal('Infinity'),Decimal('-0.00000000000000000000001'),10001]:refuse(lambda:m.validate_payload(h,decimal_schema,value))
    check(len(rows)==20 and len({r['source_key']for r in rows})==20)
    accepted={x['selection']['package_key']for x in h.strict(pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};transferred=set()
    for ref in s['transferred_reservations']:
        x=h.strict(pinned(ref));check(len(x['keys'])==x['key_count']);transferred.update(x['keys'])
    check(len(transferred)==190 and set(closure['keys']).isdisjoint(accepted|transferred));check(len(s['rows'])+len(s['remaining_key_refs'])==91 and len(s['remaining_key_refs'])-len(s['isolated_source_conflicts_within91'])==69)
    def sample(schema):
        if 'enum'in schema:return next(x for x in schema['enum']if x is not None)
        t=schema['type'];t=t[0]if type(t)is list else t
        if t=='string':return '2026-09-01'if schema.get('maxLength',1000)==10 else 'Declared source-test evidence'
        if t=='boolean':return True
        if t in ['integer','number']:return schema.get('minimum',0)
        if t=='array':return [sample(schema['items'])for _ in range(schema['minItems'])]
        if t=='object':return {k:sample(v)for k,v in schema['properties'].items()}
        raise ValueError('UNKNOWN_TYPE')
    for row in rows:
        nodes=row['program']['graph']['nodes']
        for name,n in nodes.items():
            if n['kind']=='end':continue
            payload=sample(n['schema']);payload.update(copy.deepcopy(n['expected']));saved={};failed={'pass_tag':payload.get('failed_criterion','source_extent')}
            for g in n['constraints']:
                if g['kind']=='minimum':payload[g['field']]=g['value']
                if g['kind']=='maximum'and payload[g['field']]>g['value']:payload[g['field']]=g['value']
                if g['kind']=='distinct_dates':payload[g['fields'][0]]='2026-09-01';payload[g['fields'][1]]='2026-09-02'
                if g['kind']=='same_as_saved':saved[g['right']['path'][0]]={g['right']['path'][1]:payload[g['left']['path'][0]]}
                if g['kind']=='source_policy_reported'and g['policy']=='reported_bpm_delta':payload[g['before_field']]=70;payload[g['after_field']]=72;saved={'workload_choice':{'prior_manual_bpm':70}}
                if g['kind']=='readiness_next_day_reports':payload[g['before_field']]='2026-09-01';payload[g['after_field']]='2026-09-02'
            m.validate_payload(h,n['schema'],payload);counts['closed_typed_forms']+=1
            for g in n['constraints']:
                check(m.data_guard(h,g,payload,saved,failed));counts['guard_positive_paths']+=1;refuse(lambda:m.data_guard(h,{**g,'foreign':True},payload,saved,failed))
                if 'field'in g and 'null'in n['schema']['properties'][g['field']]['type']:
                    changed=copy.deepcopy(payload);changed[g['field']]=None;m.validate_payload(h,n['schema'],changed);check(m.data_guard(h,g,changed,saved,failed)is False);counts['valid_unknown_negatives']+=1
                if g['kind']=='distinct_dates':
                    changed=copy.deepcopy(payload);changed[g['fields'][1]]=changed[g['fields'][0]];check(m.data_guard(h,g,changed,saved,failed)is False);changed[g['fields'][1]]='2026-02-30';check(m.data_guard(h,g,changed,saved,failed)is False);counts['date_negatives']+=2
                if g['kind']=='readiness_named_reports':
                    for field in g['fields']:
                        changed=copy.deepcopy(payload);changed[field]=[None];check(m.data_guard(h,g,changed,saved,failed)is False);changed[field]=['  '];check(m.data_guard(h,g,changed,saved,failed)is False);counts['named_report_negatives']+=2
                if g['kind']=='readiness_next_day_reports':
                    for date in ['2026-09-01','2026-09-03','2026-02-30',None]:changed=copy.deepcopy(payload);changed[g['after_field']]=date;check(m.data_guard(h,g,changed,saved,failed)is False);counts['next_day_negatives']+=1
                    for field in g['array_fields']:changed=copy.deepcopy(payload);changed[field][0]=None;check(m.data_guard(h,g,changed,saved,failed)is False);counts['listening_unknown_negatives']+=1
                if g['kind']=='source_policy_reported'and g['policy']=='workload_route_tempo_choice':
                    for errors,clean,choice,expected in [(2,3,'hold_current_tempo',False),(2,3,'increase_after_three_clean_repetitions',False),(2,0,'reduce_route_to_one_tetrachord',True),(1,2,'increase_after_three_clean_repetitions',False),(1,3,'increase_after_three_clean_repetitions',True),(None,3,'hold_current_tempo',False),(0,None,'hold_current_tempo',False)]:
                        changed={**payload,g['error_count_field']:errors,g['clean_count_field']:clean,g['choice_field']:choice};check(m.data_guard(h,g,changed,saved,failed)is expected);counts['workload_boundary_paths']+=1
                    changed={**payload,g['error_count_field']:True};refuse(lambda:m.data_guard(h,g,changed,saved,failed))
            refuse(lambda:m.validate_payload(h,n['schema'],{**payload,'extra_report':True}));check('default'not in json.dumps(n['schema']));counts['form_no_default_checks']+=1
    # Source-altering mutants keep their hash consistent and must still refuse
    # against the original source-bound constructor; no mirror-only check.
    for row in rows:
        i=rows.index(row)
        for mutate in [lambda p:p.update(source_kind='source_defined_task'),lambda p:p.update(grants_credit=True),lambda p:p['graph']['nodes']['prior_extent'].update(physical=True)]:
            changed=copy.deepcopy(rows);cl=copy.deepcopy(closure);mutate(changed[i]['program']);changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));cl['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(h,changed,cl,originals))
    result={'outcome':'20_SOURCE_SPAN_TYPED_GRAPH_BOUNDARY_PROOF_PASS_NATIVE_PENDING','indexed_denominator':91,'selected_rows':20,'remaining_source_clear_or_response_specific':69,'isolated_L59_conflicts_within91':2,'profiles':16,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'PDF_or_TXT_reads':0,'native_executed':0,'official_acceptance_increment':0,'limits':'No musical/clock/acoustic/listening/installed execution. New named-array/next-day/workload route-reduction guard bridges and persistent reduction state require separate native and independent review.'};(BASE/'bulk-validation-r03.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
