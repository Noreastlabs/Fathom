#!/usr/bin/env python3
"""Closed12 exact source-table and every finite chosen-contact pair proof."""
from pathlib import Path
import collections,copy,hashlib,importlib.util,json,time
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Build/manager-resume-r03/manual-procedure-recovery-table-r01'

def run():
    start=time.perf_counter();counts=collections.Counter();cache={}
    def check(v):
        counts['assertions']+=1
        if not v:raise AssertionError('TABLE_SOURCE_PROGRAM')
    def refuse(fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError):counts['expected_refusals']+=1
        else:raise AssertionError('REFUSAL_MISSING')
    def pinned(r):
        if r['path']not in cache:cache[r['path']]=(ROOT/r['path']).read_bytes()
        raw=cache[r['path']];check(hashlib.sha256(raw).hexdigest()==r['sha256']and len(raw)==r['bytes']);return raw
    p=ROOT/'Tools/exercise-family-compiler/extend_manual_curriculum_recovery_table.py';spec=importlib.util.spec_from_file_location('table_program',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    raw=(ROOT/m.SELECTION).read_bytes();check(hashlib.sha256(raw).hexdigest()==m.SELECTION_SHA);s=json.loads(raw);h,g=m.dependencies(ROOT,s)
    for r in [s['ledger'],s['current_descriptor'],*s['cached_inputs']]:pinned(r)
    receipt=json.load(open(BASE/'generated-r01/generation-receipt.json'))
    for r,sha in zip(receipt['files'],['722c94054cad6003d67f6a8fcdade1286cb5fa9e7dfab0577e98ca970cda1fa0','1e4bb61df3b9769521b6508522d55b70935e68553a161ef33a740ab6c19afb16']):check(r['sha256']==sha);pinned(r)
    rows=[h.strict(x)for x in (BASE/'generated-r01/definitions.jsonl').read_bytes().splitlines()];closure=h.strict((BASE/'generated-r01/family-closure.json').read_bytes());originals={};whole_tones=0
    for row in rows:
        ref=row['payload_ref'];raw=pinned(ref).splitlines()[ref['jsonl_line']-1];o=h.strict(raw);check(h.sha(raw)==row['original_row_sha256']and o['package_key']==row['source_key']and o['source_identity']==row['source_identity']);originals[row['source_key']]=o;counts['exact_source_roundtrips']+=1
        p=row['program'];source=o['implementation']['table_task']['printed_fields'];chord,weak,target,function=source;ctx=closure['contexts'][row['context_ref']];page=next(x['text']for x in ctx['pdf_pages']if x['physical_page']==16);intro=next(x['text']for x in ctx['pdf_pages']if x['physical_page']==1)
        check(' '.join(source)in page);check('Twelve two-note recovery cards'in page and 'after\nan unstable note.'in page);check('Play the target alone first. Sing the target. Add the approach at half speed.'in intro);check(p['source_facts']['printed_geometry']is None and p['source_facts']['printed_strokes']is None);check(o['implementation']['events']==[]and o['implementation']['interaction_contract']['response_schema']['learner_marked_done']['default']is None)
        seen=set();pc=m.PC
        for domain in p['graph']['domains']['chosen_pair']:
            choice=domain['selection'];a,b=domain['contacts'];check(len(domain['contacts'])==2 and [a['printed_note'],b['printed_note']]==[weak,target]and [a['role'],b['role']]==function.split(' -> '));check([a['pick'],b['pick']]==[None,None]);am=m.OPEN_MIDI[a['string']]+a['fret'];bm=m.OPEN_MIDI[b['string']]+b['fret'];check(am%12==pc[weak]and bm%12==pc[target]and bm-am==domain['absolute_delta_semitones']);check(choice=={'weak_string':a['string'],'weak_fret':a['fret'],'target_string':b['string'],'target_fret':b['fret']});signature=tuple(choice.values());check(signature not in seen);seen.add(signature);counts['chosen_contact_pairs']+=1
        if weak=='D'and target=='E':check(p['choice_domain_authority']['absolute_interval_semitones']==2);whole_tones+=1
        for name in ['target_preview','recover']:check(p['graph']['nodes'][name]['physical']is True)
        check(p['graph']['nodes']['choose']['constraints'][0]['kind']=='domain_lookup');check(p['graph']['nodes']['recover']['computed_expected']['kind']=='selected_domain_reports');check(p['source_obligations_ref']['two_bar_space_not_manufactured_inside_pair']is True and p['source_obligations_ref']['remaining_progression_phrase_unobserved']is True);check(p['grants_credit']is False and p['performance_observed']is False and p['fixed_bpm']is None)
        for mutate in [lambda p:p['source_facts'].update(printed_geometry='chosen'),lambda p:p['graph']['nodes']['recover'].update(physical=False),lambda p:p['graph']['nodes']['choose'].update(constraints=[]),lambda p:p.update(grants_credit=True)]:
            changed=copy.deepcopy(rows);cl=copy.deepcopy(closure);i=rows.index(row);mutate(changed[i]['program']);changed[i]['contract_sha256']=h.sha(h.encoded(changed[i]['program']));cl['contracts'][row['source_key']]=changed[i]['contract_sha256'];refuse(lambda:m.validate(changed,cl,originals,h,g))
    check(whole_tones == 1 and counts['chosen_contact_pairs'] == 576 and m.validate(rows,closure,originals,h,g))
    # Every allowed pair is generated in one register. Foreign/too-wide choices
    # cannot pass exact finite-domain lookup; geometry does not become source.
    for row in rows:
        choices=[x['selection']for x in row['program']['graph']['domains']['chosen_pair']]
        for bad in [{'weak_string':7,'weak_fret':0,'target_string':1,'target_fret':0},{'weak_string':6,'weak_fret':0,'target_string':1,'target_fret':24}]:check(bad not in choices);counts['foreign_geometry_rejections']+=1
    accepted={x['selection']['package_key']for x in h.strict(pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};check(set(closure['keys']).isdisjoint(accepted))
    result={'outcome':'12_TABLE_SOURCE_PROGRAM_AND_FINITE_CONTACT_PROOF_PASS_NATIVE_PENDING','rows':12,'source_programs':1,'graph_nodes':72,**dict(counts),'cached_inputs_hashed_once':len(cache),'seconds':time.perf_counter()-start,'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0,'current_accepted_overlap':0,'source_correction':'Cmaj7 D->E is a source nearest target at two semitones, not a universal chromatic neighbor. Pre-generation assertion refused before any output; corrected selection-r02 preserves source.','limits':'Finite authored contact-domain DATA/source proof; original table has no geometry/strokes/timing. Original generic done-bit contract not sufficient; new native source-kind/reference-path/display and independent review pending. Full session/progression phrase/listening unobserved.'};(BASE/'bulk-validation-r01.json').open('x').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':run()
