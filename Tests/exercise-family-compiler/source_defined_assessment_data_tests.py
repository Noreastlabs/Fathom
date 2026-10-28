#!/usr/bin/env python3
"""Closed67 reference/schema/proposed-guard DATA checks. No native owner claim."""
import argparse,copy,hashlib,importlib.util,json,tempfile,time
from pathlib import Path

def run(root):
    started=time.perf_counter();root=Path(root).resolve();path=root/'Tools/exercise-family-compiler/compile_source_defined_assessments.py';spec=importlib.util.spec_from_file_location('assessment67',path);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    rows,closure,metrics,originals=h.build(root);checks=0;refusals=0;negatives=0
    def check(value,why):
        nonlocal checks
        checks+=1
        if not value:raise AssertionError(why)
    def refuse(fn,why):
        nonlocal refusals
        try:fn()
        except h.BindingError:refusals+=1;return
        raise AssertionError('DID_NOT_REFUSE_'+why)
    def negative(g,p,why,**kw):
        nonlocal negatives
        check(h.data_guard(g,p,**kw) is False,why);negatives+=1
    check(len(rows)==67 and len({r['source_key'] for r in rows})==67 and len({r['source_identity'] for r in rows})==67,'EXACT_KEYS_IDENTITIES')
    # Bind the actual generated candidate rather than claiming the oracle build
    # itself proves bytes emitted in a prior process.
    generated=root/h.OUT;receipt=h.strict((generated/'generation-receipt.json').read_bytes())
    for pin in receipt['files']:
        raw=(root/pin['path']).read_bytes();check(len(raw)==pin['bytes'] and h.sha(raw)==pin['sha256'],'ACTUAL_EMITTED_FILE_PIN')
    emitted=[h.strict(line) for line in (generated/'definitions.jsonl').read_bytes().splitlines()]
    check(emitted==rows,'ALL_ACTUAL_EMITTED_SOURCE_PROGRAMS');check(h.strict((generated/'family-closure.json').read_bytes())==closure,'ACTUAL_SHARED_CLOSURE')
    check(h.strict((generated/'operator-proposal.json').read_bytes())==h.operators(),'ACTUAL_CLOSED_OPERATORS')
    for r in emitted:check(h.sha(h.encoded(r['program']))==r['contract_sha256'],'ACTUAL_ALL67_CONTRACTS')
    nodes=0;criteria=0;quantities=0;refcounts=0;date_gates=0;both_starts=0
    for r in rows:
        p=r['program'];o=originals[r['source_key']];joined=' '.join(x['text'] for x in o['implementation']['task_contract']['ordered_source_instructions'])
        check(r['contract_sha256']==h.sha(h.encoded(p))==closure['contracts'][r['source_key']],'PROGRAM_PIN')
        check(p['source_literal_sha256']==h.sha(joined.encode()),'SOURCE_LITERAL_BINDING')
        for c in p['source_criteria']:
            criteria+=1;a=c['source_excerpt']['start'];b=c['source_excerpt']['end'];check(joined[a:b]==c['literal'],'ALL_LITERAL_CRITERIA')
            check(c['id'] in p['graph']['nodes'] and p['graph']['nodes'][c['id']]['pass_tag']==c['id'],'EXACT_FAILED_CRITERION_TAG')
            if c.get('two_distinct_manual_dates'):date_gates+=1
            if c.get('both_start_debt'):both_starts+=1
            for q in c['quantities']:
                quantities+=1;check(c['literal'][q['start']:q['end']]==q['literal'],'QUANTITY_ADJACENT_LITERAL')
                if q['role']=='manual_count_criterion':
                    check(q.get('report_fields'),'QUANTITY_REPORTED')
                    for f in q['report_fields']:
                        n=p['graph']['nodes'][c['id']];check(f in n['schema']['required'],'QUANTITY_FORM_BINDING')
                        check(n['expected'].get(f)==q['value'] if q['comparison']=='exact' else {'kind':q['comparison'],'field':f,'value':q['value']} in n['constraints'],'EXACT_SOURCE_COUNT_BOUND')
        for name,n in p['graph']['nodes'].items():
            nodes+=1
            if n['kind']=='end':continue
            check('default' not in json.dumps(n['schema']),'BLANK_FORM_SCHEMA')
            for ref in n.get('source_action_refs',[]):
                refcounts+=1;idx=ref['original_contract_path'][1];check(0<=idx<len(o['implementation']['task_contract']['ordered_source_instructions']),'EVERY_SOURCE_STEP')
            malformed={};refuse(lambda n=n:h.validate_payload(n['schema'],malformed),'MISSING_FIELDS')
        for k in ('fixed_bpm','source_clock','sounding_span'):check(p[k] is None,'UNKNOWN_CLOCK_OR_SOUND')
        for k in ('runtime_admitted','performance_observed','recording_observed','automatic_mastery','grants_credit'):check(p[k] is False,'NO_CREDIT_OR_OBSERVATION')
        corrupted=copy.deepcopy(p);corrupted['source_criteria'][0]['literal']+=' invented';refuse(lambda:h.validate_program(corrupted,o),'SOURCE_MUTATION')
    # Exact recognizer counterexamples prevent numbers being borrowed across words
    # or from chord suffixes/ordinals. No source reread is used.
    check(h.quantities('After bar 4, mute the strings and sing the tonic.')==[],'BAR_LOCATION_NOT_STRING_COUNT')
    check(h.quantities('Make A7, D7, and E7 audible through hybrid target cells.')==[],'CHORD_SUFFIX_NOT_TARGET_COUNT')
    q=h.quantities('Tempo rule: add 2 BPM after three clean trips;');check(len(q)==1 and q[0]['value']==3 and q[0]['comparison']=='minimum','BPM_NOT_TRIP_COUNT')
    q=h.quantities('transform one motif in seven ways;');check([x['value'] for x in q]==[1,7],'MOTIF_AND_WAYS_SEPARATE')
    q=h.quantities('execute all 24 timed seam slides and all 24 one-pick chains without extra attacks;');check([x['value'] for x in q]==[24,24],'SEAM_AND_CHAIN_COUNTS')
    check(all(c['literal'].strip() not in ('1.','2.','3.','4.','5.') for r in rows for c in r['program']['source_criteria']),'LIST_NUMBERS_ARE_METADATA')
    # Closed type/date/count/text comparators: well-formed negatives are outcomes,
    # malformed objects/types refuse; no state/history/native execution is modeled.
    minimum={'kind':'minimum','field':'n','value':13};maximum={'kind':'maximum','field':'n','value':4}
    check(h.data_guard(minimum,{'n':13}),'MINIMUM_INCLUSIVE');negative(minimum,{'n':12},'SCORE_BELOW');negative(minimum,{'n':None},'SCORE_UNKNOWN')
    check(h.data_guard(maximum,{'n':4}),'MAXIMUM_INCLUSIVE');negative(maximum,{'n':5},'MAXIMUM_EXCEEDED');refuse(lambda:h.data_guard(minimum,{'n':True}),'BOOL_IS_NOT_INTEGER')
    for kind in ('equal','different'):
        guard={'kind':kind,'fields':['a','b']};check(h.data_guard(guard,{'a':'source1','b':'source1' if kind=='equal' else 'source2'}),'COMPARATOR_POSITIVE');negative(guard,{'a':None,'b':'source1'},'COMPARATOR_UNKNOWN')
    negative({'kind':'different','fields':['a','b']},{'a':'same material','b':'same material'},'SAME_MATERIAL')
    date={'kind':'distinct_dates','fields':['a','b']};check(h.data_guard(date,{'a':'2024-02-29','b':'2024-03-01'}),'LEAP_DATE_POSITIVE')
    for a,b in [('2026-10-01','2026-10-01'),('2026-02-29','2026-03-01'),('2026-13-01','2026-10-02'),('2026-10-01',None)]:negative(date,{'a':a,'b':b},'INVALID_OR_REPEATED_DATE')
    blank={'kind':'nonempty_trimmed_text','field':'e','minimum':1,'maximum':2048};negative(blank,{'e':' \t\n '},'WHITESPACE_EVIDENCE');negative(blank,{'e':None},'UNKNOWN_EVIDENCE');check(h.data_guard(blank,{'e':' actual evidence '}),'TRIM_TEST_ONLY_NO_REWRITE')
    refuse(lambda:h.data_guard({**minimum,'default':13},{'n':13}),'EXTRA_GUARD_FIELD');refuse(lambda:h.data_guard({'kind':'invented'},{'n':13}),'UNKNOWN_GUARD');refuse(lambda:h.data_guard(minimum,{}),'MISSING_GUARD_FIELD')
    # Both source rubrics: all typed dimensions retained, totals bound to reported
    # prior values, every day threshold enforced, no-zero dimensions are separate.
    rubric_rows=[r for r in rows if any('rubric' in c for c in r['program']['source_criteria'])];check(len(rubric_rows)==2,'TWO_PRINTED_RUBRICS')
    rubric_dimensions=0
    for r in rubric_rows:
        p=r['program'];dims=[c for c in p['source_criteria'] if 'rubric' in c];gate=next(c for c in p['source_criteria'] if c.get('score_gate'));n=p['graph']['nodes'][gate['id']];count=len(dims);rubric_dimensions+=count
        check((count,gate['score_gate']['minimum'],gate['score_gate']['maximum']) in ((6,10,12),(8,13,16)),'EXACT_PRINTED_RUBRIC')
        check(gate['two_distinct_manual_dates'] and gate['score_gate']['attempts']==2,'RUBRIC_TWO_DAYS')
        saved={d['id']:{'rating_'+str(day)+'_'+h.slug(d['rubric']['dimension']):2 for day in (1,2)} for d in dims}
        payload={k:v for d in saved.values() for k,v in d.items()};payload.update({'reported_score_1':2*count,'reported_score_2':2*count,'date_1':'2026-10-01','date_2':'2026-10-02'})
        for g in n['constraints']:
            if g['kind'] in ('reported_score_sum','same_as_saved','minimum','distinct_dates'):check(h.data_guard(g,payload,saved=saved),'RUBRIC_VALID_REPORTED_NUMBERS')
        for day in (1,2):
            total='reported_score_'+str(day);bad={**payload,total:2*count-1};sum_guard=next(g for g in n['constraints'] if g['kind']=='reported_score_sum' and g['total_field']==total);negative(sum_guard,bad,'TOTAL_MISMATCH')
            threshold=next(g for g in n['constraints'] if g['kind']=='minimum' and g['field']==total);negative(threshold,{**payload,total:gate['score_gate']['minimum']-1},'DAILY_THRESHOLD')
            if count==8:
                zeros=[g for g in n['constraints'] if g['kind']=='minimum' and g['field'].startswith('rating_'+str(day))];check(len(zeros)==3,'THREE_REQUIRED_NONZERO_DIMENSIONS_PER_DAY')
                for g in zeros:negative(g,{**payload,g['field']:0},'NO_ZERO_DIMENSION')
        mismatch=next(g for g in n['constraints'] if g['kind']=='same_as_saved');negative(mismatch,{**payload,mismatch['left']['path'][0]:1},'PRIOR_RATING_SUBSTITUTION',saved=saved)
    # The source A-instead-of-F# branch has the real low-drone/density repair.
    minor=next(r for r in rows if originals[r['source_key']]['source_payload']['printed_label']=='Minor-center check');ns=minor['program']['graph']['nodes'];check(ns['tonic_choice']['routes']['A']['next']=='tonic_repair' and ns['tonic_repair']['physical'] is True,'SOURCE_TONIC_REPAIR');check(ns['tonic_choice']['routes']['unknown']['next']=='unresolved_tonic','UNKNOWN_TONIC_NOT_ACCEPTED')
    # Printed tempo choice guard and persistent-debt blueprint are source-bound.
    tempo_rows=[r for r in rows if r['program']['graph']['source_state_protocols']];check(len(tempo_rows)==3,'THREE_SOURCE_TEMPO_RULES')
    for r in tempo_rows:
        ns=r['program']['graph']['nodes'];proto=r['program']['graph']['source_state_protocols'][0];check(set(proto['retain_across'])=={'retry','cancel','navigation','restart','unknown report'} and proto['hold_or_increase_cannot_clear_debt'],'PERSISTENT_DEBT_BLUEPRINT')
        ch=next(n for n in ns.values() if n.get('save_as')=='tempo_choice');g=next(g for g in ch['constraints'] if g['kind']=='source_policy_reported')
        base={'tempo_decision':'hold','reported_error_count':1,'reported_tension':False};check(h.data_guard(g,base),'HOLD_WITH_NO_TRIGGER')
        negative(g,{**base,'reported_error_count':2},'TWO_ERRORS_BLOCK_HOLD');negative(g,{**base,'reported_tension':True},'TENSION_BLOCK_HOLD');negative(g,{**base,'reported_tension':None},'UNKNOWN_TENSION_BLOCKS');check(h.data_guard(g,{**base,'tempo_decision':'reduce_after_errors_or_tension','reported_error_count':2}),'REQUIRED_REDUCTION_CHOICE')
        dn=ns[proto['reduction_node']];dg=next(g for g in dn['constraints'] if g.get('policy')=='reported_bpm_delta')
        for bpm in (94,95,96):check(h.data_guard(dg,{'prior_manual_bpm':100,'new_manual_bpm':bpm}),'REDUCE4_6')
        for bpm in (93,97,100,102):negative(dg,{'prior_manual_bpm':100,'new_manual_bpm':bpm},'BAD_REDUCTION_DELTA')
        up=ns[proto['increase_node']];ug=next(g for g in up['constraints'] if g.get('policy')=='reported_bpm_delta');check(h.data_guard(ug,{'prior_manual_bpm':100,'new_manual_bpm':102}),'ADD2');negative(ug,{'prior_manual_bpm':100,'new_manual_bpm':103},'BAD_INCREASE');cg=next(g for g in up['constraints'] if g.get('field')=='reported_clean_complete_trips');negative(cg,{'reported_clean_complete_trips':2},'ONLY_TWO_CLEAN_TRIPS')
    # Exact failed-criterion binding has no arbitrary success route.
    for r in rows:
        ns=r['program']['graph']['nodes'];g=ns['repair_bind']['constraints'][0];check(h.data_guard(g,{'failed_criterion':'source_extent'},failed={'pass_tag':'source_extent'}),'FAILED_CRITERION_BIND');negative(g,{'failed_criterion':r['program']['source_criteria'][0]['id']},'FOREIGN_FAILED_CRITERION',failed={'pass_tag':'source_extent'});check(ns['repair_choice']['routes']['restart_complete_source_extent']['next']=='source_extent' and ns['repair_choice']['routes']['stop']['native_protocol']=='stop','COMPLETE_RETRY_OR_STOP')
    # Current cached preimages are strict path/pin authority; tested in an isolated
    # temporary root, without editing producer/original/installed files.
    with tempfile.TemporaryDirectory(prefix='assessment67-') as td:
        p=Path(td);(p/'row').write_bytes(b'{}');c=h.Inputs(p);pin={'path':'row','bytes':2,'sha256':hashlib.sha256(b'{}').hexdigest()};check(c.pinned(pin)==b'{}' and c.pinned(pin)==b'{}' and c.hashes==1,'HASH_FILE_ONCE');refuse(lambda:c.pinned({**pin,'sha256':'0'*64}),'PREIMAGE_CONFLICT');refuse(lambda:c.pinned({**pin,'path':'../row'}),'PATH_ESCAPE');(p/'link').symlink_to(p/'row');refuse(lambda:c.pinned({**pin,'path':'link'}),'SYMLINK')
    return {'outcome':'CLOSED67_CACHED_SOURCE_AND_PROPOSED_DATA_GUARD_PASS_NATIVE_PENDING','rows':67,'contexts':33,'criteria':criteria,'graph_nodes':nodes,'quantity_descriptors':quantities,'source_action_comparisons':refcounts,'two_day_criteria':date_gates,'both_start_criteria':both_starts,'rubric_dimensions':rubric_dimensions,'assertions':checks,'malformed_refusals':refusals,'well_formed_negative_controls':negatives,'seconds':time.perf_counter()-started,'input_hashes_cached_once':metrics['cached_files_hashed_once'],'native_paths_executed':0,'original_txt_pdf_reads':0,'official_acceptance_increment':0}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',required=True);x=a.parse_args();result=run(x.root);target=Path(x.root)/x.out;target.open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
