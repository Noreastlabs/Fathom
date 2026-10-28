#!/usr/bin/env python3
"""Exhaustive22 DATA bindings/forms, focused source/choice/reveal boundaries.

These are compiler/schema proofs. No native hiding, sound or physical execution.
"""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-seventh-lab22-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(v):
        counts['assertions']+=1
        if not v:raise AssertionError('SEVENTH_SOURCE_OR_GUARD')
    def refuse(fn):
        try:fn()
        except(AssertionError,ValueError,KeyError,TypeError,IndexError):counts['malformed_refusals']+=1
        else:raise AssertionError('EXPECTED_REFUSAL')
    def pinned(r):
        if r['path']not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        b=cache[r['path']];check(len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']);return b
    sp=importlib.util.spec_from_file_location('seventh_lab',ROOT/'Tools/exercise-family-compiler/extend_manual_seventh_lab.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);h=m.helper(ROOT)
    s=h.strict((ROOT/m.SELECTION).read_bytes());check(h.sha((ROOT/m.SELECTION).read_bytes())==m.SELECTION_SHA)
    for r in [s['ledger'],s['current_descriptor'],*s['cached_inputs'],*s['transferred_reservations']]:pinned(r)
    receipt=json.load(open(BASE/'generated-r01/generation-receipt.json'))
    for r in receipt['files']:pinned(r)
    rows=[h.strict(b)for b in (BASE/'generated-r01/definitions.jsonl').read_bytes().splitlines()];cl=h.strict((BASE/'generated-r01/family-closure.json').read_bytes());originals={}
    for row in rows:
        r=row['payload_ref'];raw=pinned(r).splitlines()[r['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==row['original_row_sha256']and h.sha(json.dumps(o,ensure_ascii=False,separators=(',',':')).encode())==row['original_compact_sha256']and o['package_key']==row['source_key']and o['source_identity']==row['source_identity']);originals[row['source_key']]=o;counts['exact_source_roundtrips']+=1
        p=row['program'];spans=p['source_literal_ref']['source_span_witnesses'];check(h.sha(' '.join(x['text']for x in spans).encode())==p['source_literal_sha256'])
        for x in spans:
            w=x['witness'];b=o
            for k in w['original_record_path']:b=b[k]
            if w['kind']=='original_record_span':b=b[w['start']:w['end']]
            else:check(w['kind']=='original_record_literal')
            check(b==x['text']and h.sha(b.encode())==w['text_sha256']);counts['original_source_fragments']+=1
        check(p['source_clock']is None and not p['runtime_admitted']and not p['grants_credit']);fp=p['graph']['failure_policy'];check(fp['terminal_current_pass']and fp['physical_failure_requires_release']and fp['active_retry_stop_navigation_require_exit_release']and not fp['nonphysical_failure_activates_physical']);counts['release_debt_specifications']+=1
    check(m.validate(h,rows,cl,originals));check(len(rows)==22 and len(cl['isolated_F2'])==2)
    transferred=set()
    for r in s['transferred_reservations']:x=h.strict(pinned(r));check(x['key_count']==len(x['keys']));transferred.update(x['keys'])
    accepted={x['selection']['package_key']for x in h.strict(pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};check(len(transferred)==190 and set(cl['keys']).isdisjoint(transferred|accepted))
    def sample(sc):
        if 'enum'in sc:return next(x for x in sc['enum']if x is not None)
        t=sc['type'];t=t[0]if type(t)is list else t
        if t=='string':return 'x'
        if t=='boolean':return True
        if t=='integer':return sc.get('minimum',0)
        if t=='array':return [sample(sc['items'])for _ in range(sc['minItems'])]
        if t=='object':return {k:sample(v)for k,v in sc['properties'].items()}
        raise ValueError('SCHEMA_TYPE')
    for row in rows:
        p=row['program'];nodes=p['graph']['nodes']
        for name,n in nodes.items():
            if n['kind']=='end':continue
            payload=sample(n['schema']);payload.update(copy.deepcopy(n.get('expected',{})));saved={};failed={'pass_tag':payload.get('failed_criterion','perform')}
            for g in n.get('constraints',[]):
                if g['kind']=='seventh_quality_permutation':payload[g['field']]=m.QUALITIES[:]
                if g['kind']=='nonempty_trimmed_text':payload[g['field']]='x'
                if g['kind']=='same_as_saved':saved.setdefault(g['right']['path'][0],{})[g['right']['path'][1]]=payload[g['left']['path'][0]]
            h.validate_payload(n['schema'],payload);counts['closed_forms']+=1;refuse(lambda:h.validate_payload(n['schema'],{**payload,'foreign':True}));check('default'not in json.dumps(n['schema']))
            for g in n.get('constraints',[]):
                check(m.data_guard(h,g,payload,saved,failed));counts['guard_positive_paths']+=1;refuse(lambda:m.data_guard(h,{**g,'foreign':True},payload,saved,failed))
                if g['kind']=='nonempty_trimmed_text':
                    for value in [None,' ']:v={**payload,g['field']:value};check(m.data_guard(h,g,v,saved,failed)is False);counts['valid_unknown_or_blank_negatives']+=1
                if g['kind']=='seventh_nonempty_reports':
                    for key in g['fields']:
                        for value in [None,'  ']:v=copy.deepcopy(payload);v[key][0]=value;check(m.data_guard(h,g,v,saved,failed)is False);counts['valid_unknown_or_blank_negatives']+=1
                        v=copy.deepcopy(payload);v[key][0]=True;refuse(lambda:m.data_guard(h,g,v,saved,failed))
                if g['kind']=='seventh_quality_permutation':
                    for value in [['maj7']*4,['maj7','7','m7',None]]:check(m.data_guard(h,g,{**payload,g['field']:value})is False);counts['recording_order_negatives']+=1
                    refuse(lambda:m.data_guard(h,g,{**payload,g['field']:[True,'7','m7','m7b5']}))
            for field,expected in n.get('expected',{}).items():
                if type(expected)is bool:
                    altered={**payload,field:not expected};h.validate_payload(n['schema'],altered);check(altered[field]!=expected);counts['false_report_specifications']+=1
                    refuse(lambda:h.validate_payload(n['schema'],{**payload,field:'true'}))
            if name=='choose_root'and 'chosen_root_fret'in payload:
                domain=n['schema']['properties']['chosen_root_fret']['enum'];check(domain==p['performer_choice_metadata']['authored_root_fret_choices']);refuse(lambda:h.validate_payload(n['schema'],{**payload,'chosen_root_fret':next(x for x in range(25)if x not in domain)}));counts['exact_authored_contact_domains']+=1
            if n['kind']=='owned_saved_choice_reveal':
                check(n['requires_committed_node']=='audition'and n['learner_visible_after_reveal_only']and n['schema']['properties']=={}and p['learner_hidden_saved_choices']==[n['saved_choice_ref']]);check(nodes['audition']['next']==name and nodes['recording']['next']=='audition');counts['hidden_reveal_specifications']+=1
        if 'silent_quality_command'in p['name']:check(nodes['perform']['expected']['formations_reportedly_silent']is True and not any('attack_count'in f for n in nodes.values()for f in n.get('schema',{}).get('properties',{})));counts['silent_ladder_exclusions']+=1
        if 'three_register'in p['name']:check(nodes['choose_plan']['schema']['properties']['ensemble_bass_root_needed']['type']=='boolean');refuse(lambda:h.validate_payload(nodes['choose_plan']['schema'],{'chosen_chords_by_bar':['A7']*12,'ensemble_bass_root_needed':None}));counts['explicit_plan_specifications']+=1
        i=rows.index(row);changed=copy.deepcopy(rows);closure=copy.deepcopy(cl);changed[i]['program']['source_kind']='source_defined_task';changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));closure['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(h,changed,closure,originals))
    result={'outcome':'22_SOURCE_FORMS_GUARDS_SPECIFICATION_PASS_NATIVE_PENDING',**dict(counts),'rows':22,'source_program_profiles':7,'indexed_denominator':91,'completed_DATA_with_prior20':42,'isolated_source_rows':4,'remaining_other_rows':45,'cached_files_hashed_once':len(cache),'seconds':time.perf_counter()-start,'PDF_TXT_reads':0,'native_execution':False,'official_acceptance_increment':0,'deferred_QA':['Distinct source/musical realization review.','Native saved-choice visibility/reveal, owner/pass/revision/action/history/release and hidden history guards.','Explicit chosen contact/spelling and whole-session/listening duties; no acoustic observation.','Original ModuleF two-column visual exception outside these22.']}
    (BASE/'bulk-validation-r01.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':run()
