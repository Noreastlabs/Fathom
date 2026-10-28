#!/usr/bin/env python3
"""One46-row source/form/guard proof with family boundary counterexamples.

No native, UI, acoustic, source-clock, hidden-runtime or installed verdict.
"""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Build/manager-resume-r03/manual-source-phases47-r01'
def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(v):
        counts['assertions']+=1
        if not v:raise AssertionError('SOURCE_PHASE_BOUNDARY')
    def refuse(fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,TypeError,IndexError):counts['malformed_refusals']+=1
        else:raise AssertionError('EXPECTED_REFUSAL')
    def pinned(r):
        if r['path']not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        b=cache[r['path']];check(len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']);return b
    sp=importlib.util.spec_from_file_location('source_phases',ROOT/'Tools/exercise-family-compiler/extend_manual_source_phases.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);h=m.helper(ROOT);s=h.strict((ROOT/m.SELECTION).read_bytes());check(h.sha((ROOT/m.SELECTION).read_bytes())==m.SELECTION_SHA)
    for r in [s['ledger'],s['current_descriptor'],s['held449'],s['visual_source_witness'],s['visual_source_review'],*s['transferred_reservations'],*s['cached_inputs']]:pinned(r)
    visual={x['key']:x for x in h.strict(pinned(s['visual_source_witness']))['clauses']};gen=h.strict((BASE/'generated-r03/generation-receipt.json').read_bytes())
    for r in gen['files']:pinned(r)
    rows=[h.strict(b)for b in (BASE/'generated-r03/definitions.jsonl').read_bytes().splitlines()];cl=h.strict((BASE/'generated-r03/family-closure.json').read_bytes());originals={};rhythm=cl['rhythm_source_choice_domain']
    for row in rows:
        r=row['payload_ref'];raw=pinned(r).splitlines()[r['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==row['original_row_sha256']and h.sha(json.dumps(o,ensure_ascii=False,separators=(',',':')).encode())==row['original_compact_sha256']and o['package_key']==row['source_key']and o['source_identity']==row['source_identity']);originals[row['source_key']]=o;counts['exact_source_roundtrips']+=1
        p=row['program'];spans=p['source_literal_ref']['source_span_witnesses'];check(h.sha(' '.join(x['text']for x in spans).encode())==p['source_literal_sha256'])
        for x in spans:
            w=x['witness']
            if w['kind']=='accepted_original_pdf_visual_clause':check(x['text']==visual[row['source_key']]['observed_printed_clause']and w['review_sha256']==s['visual_source_review']['sha256']);counts['exact_reviewed_visual_clauses']+=1
            else:
                b=o
                for k in w['original_record_path']:b=b[k]
                if w['kind']=='original_record_span':b=b[w['start']:w['end']]
                check(b==x['text'])
            check(h.sha(x['text'].encode())==w['text_sha256']);counts['exact_source_fragments']+=1
        check(p['source_clock']is None and p['fixed_bpm']is None and not p['runtime_admitted']and not p['grants_credit']);f=p['graph']['failure_policy'];check(f['terminal_current_pass']and f['physical_failure_requires_release']and f['active_retry_stop_navigation_require_exit_release']and not f['nonphysical_failure_activates_physical']);counts['release_and_unknown_specifications']+=1
    check(m.validate(h,rows,cl,originals,visual,rhythm));held={h.strict(b)['source_key']for b in pinned(s['held449']).splitlines()};transferred=set()
    for r in s['transferred_reservations']:x=h.strict(pinned(r));check(len(x['keys'])==x['key_count']);transferred.update(x['keys'])
    check(len(held)==449 and len(transferred)==190 and set(cl['keys']).isdisjoint(held|transferred));check(len(rows)==46 and m.ISOLATED not in cl['keys']and len(cl['isolated_candidate_source_conflicts'])==1);check(sum(cl['denominator91'].values())==91)
    # All8 source rhythm options are references to already owned original
    # cards, never8 additional implementation identities.
    rhythm_payload=next(x['payload_ref']for x in rows if 'clap_air_chord'in x['program']['name']);lines=pinned(rhythm_payload).splitlines()
    for key,d in rhythm.items():
        raw=lines[d['payload_jsonl_line']-1];o=h.strict(raw);check(o['package_key']==key and o['source_identity']==d['source_identity']and h.sha(raw)==d['original_row_sha256']);ev=o['implementation']['events'];check(d['P_indices']==[e['subdivision_index']for e in ev if e['source_token']=='P']and len(ev)==16);counts['rhythm_source_choice_roundtrips']+=1
    def sample(sc):
        if 'enum'in sc:return next(x for x in sc['enum']if x is not None)
        t=sc['type'];t=t[0]if type(t)is list else t
        if t=='string':return 'x'
        if t=='boolean':return True
        if t=='integer':return sc.get('minimum',0)
        if t=='array':return [sample(sc['items'])for _ in range(sc['minItems'])]
        if t=='object':return {k:sample(v)for k,v in sc['properties'].items()}
        raise ValueError('UNKNOWN_TYPE')
    for row in rows:
        p=row['program'];nodes=p['graph']['nodes'];domains=p['graph']['domains']
        for id,n in nodes.items():
            if n['kind']=='end':continue
            payload=sample(n['schema']);payload.update(copy.deepcopy(n.get('expected',{})));saved={};failed={'pass_tag':payload.get('failed_criterion','choose_source')}
            for g in n.get('constraints',[]):
                if g['kind']=='same_as_saved':saved.setdefault(g['right']['path'][0],{})[g['right']['path'][1]]=payload[g['left']['path'][0]]
                if g['kind']=='source_order_permutation':payload[g['field']]=m.INVERSIONS[:]
                if g['kind']=='source_adjacent_sets':payload[g['current_field']]=m.SETS[0];payload[g['target_field']]=m.SETS[1]
                if g['kind']=='source_assignment_coverage':payload[g['field']]=[{'position':a,'pattern':b}for a in g['positions']for b in g['patterns']]
                if g['kind']=='selected_source_literal':
                    domain=domains[g['domain']];choice=next(iter(domain));a,b=g['choice_ref']['path'];saved.setdefault(a,{})[b]=choice
                    for report,literal in g['reports'].items():payload[report]=copy.deepcopy(domain[choice][literal])
            h.validate_payload(n['schema'],payload);counts['closed_forms']+=1;check('default'not in json.dumps(n['schema']));refuse(lambda:h.validate_payload(n['schema'],{**payload,'extra':True}))
            for g in n.get('constraints',[]):
                check(m.data_guard(h,g,payload,saved,failed,domains));counts['guard_positive_paths']+=1;refuse(lambda:m.data_guard(h,{**g,'foreign':True},payload,saved,failed,domains))
                if g['kind']=='nonempty_trimmed_text':
                    for v in [None,' ']:check(m.data_guard(h,g,{**payload,g['field']:v},saved,failed,domains)is False);counts['valid_unknown_or_blank_negatives']+=1
                if g['kind']=='source_nonempty_lists':
                    for field in g['fields']:
                        for v in [None,'  ']:q=copy.deepcopy(payload);q[field][0]=v;check(m.data_guard(h,g,q,saved,failed,domains)is False);counts['valid_unknown_or_blank_negatives']+=1
                        q=copy.deepcopy(payload);q[field][0]=True;refuse(lambda:m.data_guard(h,g,q,saved,failed,domains))
                if g['kind']=='source_resolved_fields':
                    for field in g['fields']:
                        if type(payload[field])is list:q=copy.deepcopy(payload);q[field][0]=None
                        else:q={**payload,field:None}
                        check(m.data_guard(h,g,q,saved,failed,domains)is False);counts['valid_unknown_or_blank_negatives']+=1
                if g['kind']=='source_order_permutation':check(m.data_guard(h,g,{**payload,g['field']:['root']*3})is False);counts['source_order_negatives']+=1
                if g['kind']=='source_adjacent_sets':
                    for pair,expected in [(('G_B_e','D_G_B'),True),(('D_G_B','G_B_e'),True),(('G_B_e','E_A_D'),False),(('A_D_G','A_D_G'),False)]:q={**payload,g['current_field']:pair[0],g['target_field']:pair[1]};check(m.data_guard(h,g,q)is expected);counts['adjacent_choice_boundaries']+=1
                if g['kind']=='selected_source_literal':
                    q=copy.deepcopy(payload);field=next(iter(g['reports']));q[field]=None;check(m.data_guard(h,g,q,saved,failed,domains)is False);counts['valid_unknown_or_blank_negatives']+=1
                    foreign=copy.deepcopy(saved);a,b=g['choice_ref']['path'];foreign[a][b]='foreign';refuse(lambda:m.data_guard(h,g,payload,foreign,failed,domains));refuse(lambda:m.data_guard(h,{**g,'choice_ref':{**g['choice_ref'],'extra':True}},payload,saved,failed,domains))
                if g['kind']=='source_assignment_coverage':
                    q=copy.deepcopy(payload);q[g['field']][0]=q[g['field']][1];check(m.data_guard(h,g,q)is False);q[g['field']][0]={'position':'P1','pattern':None};check(m.data_guard(h,g,q)is False);counts['assignment_coverage_negatives']+=2
            for field,value in n.get('expected',{}).items():
                if type(value)is bool:
                    q={**payload,field:not value};h.validate_payload(n['schema'],q);check(q[field]!=value);counts['manual_negative_report_specifications']+=1;refuse(lambda:h.validate_payload(n['schema'],{**payload,field:'true'}))
            if n['kind']=='source_reference_view':check(n['physical']is False and n['schema']['properties']=={}and not any(z.get('physical',False)for z in nodes.values()));counts['reference_only_nongates']+=1
            if n['kind']=='owned_source_answer_reveal':
                check(nodes['written_response']['next']==id and nodes['written_response']['expected']=={}and n['requires_committed_node']=='written_response'and n['learner_visible_after_reveal_only']);check('printed_answer'not in json.dumps(nodes['written_response']['schema'])and 'printed_answer'not in json.dumps(nodes['manual_self_check']['schema']));counts['source_answer_hiding_specifications']+=1
            for route in n.get('routes',{}).values():
                if 'guard'not in route:continue
                g=route['guard'];check(route['guard_phase']=='after_owned_release_before_new_repair_activation')
                if g['kind']=='failed_report_predicate':
                    f={'payload':{g['field']:False}};check(m.data_guard(h,g,{},failed=f));check(m.data_guard(h,g,{},failed={'payload':{g['field']:True}})is False);check(m.data_guard(h,g,{},failed={'payload':{g['field']:None}})is False);refuse(lambda:m.data_guard(h,g,{},failed={'payload':{g['field']:'false'}}));counts['conditional_repair_boundaries']+=3
                else:
                    f={'pass_tag':'continuous_source_unit','payload':{'boundary_reports':['no_issue','scrape','unknown','no_issue']}};check(m.data_guard(h,g,{'chosen_boundary':2},failed=f));check(m.data_guard(h,g,{'chosen_boundary':1},failed=f)is False);check(m.data_guard(h,g,{'chosen_boundary':3},failed=f)is False);refuse(lambda:m.data_guard(h,g,{'chosen_boundary':2},failed={**f,'pass_tag':'foreign'}));refuse(lambda:m.data_guard(h,g,{'chosen_boundary':True},failed=f));counts['conditional_boundary_repair_paths']+=3
                refuse(lambda:m.data_guard(h,{**g,'foreign':True},{'chosen_boundary':2},failed=f));target=nodes[route['next']];check(target['physical']is True and target['next']=='repair_choice');counts['repair_not_completion_checks']+=1
        if 'continuous_'in p['name']:check(nodes['continuous_source_unit']['expected']['reported_tone_count']==90 and len(nodes['continuous_source_unit']['expected']['boundary_reports'])==4 and p['source_state_protocols'][0]['internal_UI_reports']is False);counts['continuous90_unit_specifications']+=1
        if 'silent_formation_transfer'in p['name']:check(nodes['spell']['physical']is False and nodes['name_strings']['physical']is False);counts['nonphysical_preparation_checks']+=1
        if 'three_pass_dominant_capstone'in p['name']:check(domains['source_bar_total']is None and domains['source_recovery_context_duty_retained']and domains['new_recovery_card_implementation_identities']==0 and nodes['source_recovery_context']['expected']['reported_source_recovery_pairs']==12 and len([x for x in nodes.values()if x.get('physical')])==4);counts['supplement_scope_checks']+=1
        if 'atlas_71'in p['name']:check(domains['automatic_enharmonic_conversion']is False and 'G#m7b5_parent'in nodes['choose_source']['schema']['properties']['chosen_source_function']['enum']and 'G#7alt_applied'in nodes['choose_source']['schema']['properties']['chosen_source_function']['enum']);counts['source_function_spelling_domain_checks']+=1
        index=rows.index(row)
        for field,value in [('source_kind','source_defined_task'),('grants_credit',True)]:
            changed=copy.deepcopy(rows);closure=copy.deepcopy(cl);changed[index]['program'][field]=value;changed[index]['contract_sha256']=h.sha(h.encoded(changed[index]['program']));closure['contracts'][row['source_key']]=changed[index]['contract_sha256'];refuse(lambda:m.validate(h,changed,closure,originals,visual,rhythm))
    result={'outcome':'46_SOURCE_FORM_TYPED_GRAPH_BOUNDARY_PROOF_PASS_NATIVE_PENDING','candidate_rows':47,'clear_DATA_rows':46,'four_reference_only_rows':4,'six_written_response_rows':6,'physical_manual_rows':36,'isolated_L68_pass_columns':1,'prior_L59_conflicts':2,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'PDF_or_TXT_reads':0,'native_executed':0,'official_acceptance_increment':0,'limits':'Compiler/source/schema/guard specification proof only; native owner/release/branch/debt/history/learner projections and hidden-answer runtime remain unexecuted.'}
    (BASE/'bulk-validation-r02.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':run()
