#!/usr/bin/env python3
"""Compile the exact saved 96 cached manual rows into distinct source programs.

No source extraction, per-row models, music generation, runtime admission or
assessment. Complete original records and shared contexts are trusted witnesses;
only curated instructions, input schemas and learner reports cross the UI API.
"""
from pathlib import Path
import argparse, collections, hashlib, json, re, time

SELECTION = 'Results/manager-resume-r03/manual-curriculum-paused-selection-r01.json'
SELECTION_SHA = '797403662a2f61ea02616dc3d63abb1255b28e1273fd2f9aa3a27303b21f0c50'
OUT = 'Build/manager-resume-r03/manual-curriculum-generation-r01'
SCHEMA = 'fathom.compiled-manual-curriculum-definition.1'
TUNING = {'E': 40, 'A': 45, 'D': 50, 'G': 55, 'B': 59, 'e': 64}
PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'E#':5,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11,'B#':0,'Cb':11}
FORMS = {'C':('A',[None,0,-1,-3,-2,-3]),'A':('A',[None,0,2,2,2,0]),'G':('E',[0,-1,-3,-3,-3,0]),'E':('E',[0,2,2,1,0,0]),'D':('D',[None,None,0,2,3,2])}
SETS = [('G','B','e'),('D','G','B'),('A','D','G'),('E','A','D')]
TRIADS = {'C':{'major':['C','E','G'],'minor':['C','Eb','G']},'A':{'major':['A','C#','E'],'minor':['A','C','E']}}
TRIAD_FORMULAS = {
 'G-B-e':{'major':[[0,0,-2],[0,-1,-1],[0,1,0]],'minor':[[0,-1,-2],[0,0,0],[0,1,-1]]},
 'D-G-B':{'major':[[0,-1,-2],[0,-2,-1],[0,0,0]],'minor':[[0,-2,-2],[0,-1,0],[0,0,-1]]},
 'A-D-G':{'major':[[0,-1,-3],[0,-2,-2],[0,0,-1]],'minor':[[0,-2,-3],[0,-1,-1],[0,0,-2]]},
 'E-A-D':{'major':[[0,-1,-3],[0,-2,-2],[0,0,-1]],'minor':[[0,-2,-3],[0,-1,-1],[0,0,-2]]}}
MAJOR = {'F':['F','G','A','Bb','C','D','E'],'C':['C','D','E','F','G','A','B'],'G':['G','A','B','C','D','E','F#'],'D':['D','E','F#','G','A','B','C#'],'A':['A','B','C#','D','E','F#','G#'],'E':['E','F#','G#','A','B','C#','D#']}
MINOR = {'D':['D','E','F','G','A','Bb','C'],'A':['A','B','C','D','E','F','G'],'E':['E','F#','G','A','B','C','D'],'B':['B','C#','D','E','F#','G','A'],'F#':['F#','G#','A','B','C#','D','E'],'C#':['C#','D#','E','F#','G#','A','B']}
RAISED = {'D':'C#','A':'G#','E':'D#','B':'A#','F#':'E#','C#':'B#'}

class Refusal(ValueError): pass
def require(ok, why):
    if not ok: raise Refusal(why)
def encoded(v): return json.dumps(v, ensure_ascii=False, separators=(',',':'), allow_nan=False).encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def strict(raw):
    def pairs(items):
        out={}
        for k,v in items:
            require(k not in out,'DUPLICATE_JSON_MEMBER'); out[k]=v
        return out
    def nonfinite(_): raise Refusal('NONFINITE_JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
def obj(fields): return {'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
def text(nullable=True): return {'type':['string','null'] if nullable else 'string','minLength':1,'maxLength':2000,'input_role':'manual_report'}
def boolean(): return {'type':['boolean','null'],'input_role':'manual_report'}
def integer(lo,hi): return {'type':['integer','null'],'minimum':lo,'maximum':hi,'input_role':'manual_report'}
def menu(values): return {'type': 'integer' if type(values[0]) is int else 'string','enum':values,'input_role':'explicit_choice'}
def literal(value): return {'const':value,'input_role':'source_binding','literal_binding_label':'Printed source/protocol constant; not a new performance report.'}
def array(schema,n): return {'type':'array','items':schema,'minItems':n,'maxItems':n}
def step(name,instruction,fields,expected=None,*,release=False,action='submit',constraints=None,save=None):
    return {'name':name,'instruction':instruction,'action':action,'schema':obj(fields),'expected':expected or {},'requires_known':list(fields),'activates_release':release,'constraints':constraints or [],'save_as':save}
def release(): return step('manual_release','Manually release fretting pressure and stop/mute the external source before continuing.',{'learner_released':boolean(),'external_source_stopped':boolean()},{'learner_released':True,'external_source_stopped':True},action='release')
def performance(name,instruction,duties):
    return [step(name,instruction,{x:boolean() for x in duties},{x:True for x in duties},release=True),release()]

def written_answer(o):
    label=o['source_payload']['label']; body=o['implementation']['source_scope']['selected_source_text']
    direct=re.search(re.escape(label)+r' \| answer: ([^\n]+)',body)
    analysis='Move ' not in label; n=int(label.split('.')[0]); level=o['level']
    if direct:
        answer=direct.group(1)
        if analysis:
            m=re.fullmatch(r'key ([^;]+); ([^;]+); (.+)',answer);require(m is not None,'EXACT_CACHED_ANALYSIS_ANSWER')
            return dict(zip(('key','numerals','functions'),m.groups()))
        return {'chords':answer}
    if analysis:
        m=re.search(r'(?<![A-Za-z0-9])A'+str(n)+r' ([^:]+): ([^;]+); ([^\s]+)',body)
        require(m is not None,'EXACT_CACHED_SELFCHECK_ANSWER')
        key,num,func=m.groups();return {'key':key+(' minor' if level==56 else ''),'numerals':num,'functions':func}
    m=re.search(r'(?<![A-Za-z0-9])B'+str(n)+r' ([^\s]+)',body);require(m is not None,'EXACT_CACHED_TRANSPOSE_ANSWER');return {'chords':m.group(1)}

def audit(o):
    level=o['level']; body=o['implementation']['source_scope']['selected_source_text']; stages=[]
    # Exact cached source clauses, not an inferred checklist completion score.
    if level in (54,55,56,59,63):
        start=body.index('Mastery gate before'); end=len(body)
        for marker in ('Completion audit','Practice log','Workload and practice log','Completion audit and practice log'):
            loc=body.find(marker,start)
            if loc>=0: end=min(end,loc)
        section=body[start:end];clauses=[s.strip() for s in section.splitlines()[1:] if s.strip()]
        # PDF line wraps are kept together; punctuation defines an audit clause.
        clauses=[s.strip() for s in re.split(r'(?<=[.;])\s+', ' '.join(clauses)) if s.strip()]
    else:
        start=body.index('Advancement standard');end=body.index('Practice log',start)
        clauses=[s.strip() for s in re.split(r';\s*',body[start:end].split('\n',1)[1].strip()) if s.strip()]
    require(bool(clauses),'SOURCE_AUDIT_CLAUSES')
    for n,clause in enumerate(clauses):
        f={'source_requirement_met':boolean(),'evidence_reference':text(),'limitations_note':text()};ex={'source_requirement_met':True};constraints=[]
        if level==54 and '30 of 35' in clause:
            f['first_attempt_successes']=integer(0,35);constraints.append({'kind':'minimum','field':'first_attempt_successes','value':30})
        if ('two separate days' in clause or 'two clean days' in clause) or level in (55,56,57,59):
            f.update({'date_1':text(),'date_2':text()});constraints.append({'kind':'distinct_dates','fields':['date_1','date_2']})
        if level==55 and 'two separate days' in clause:
            f.update({'day_1_material':menu(['triads','full_or_partial_rhythm_voicings']),'day_2_material':menu(['triads','full_or_partial_rhythm_voicings'])});constraints.append({'kind':'different','fields':['day_1_material','day_2_material']})
        if level==56 and 'two separate days' in clause:
            f.update({'day_1_material':menu(['natural_v','strong_V_or_V7']),'day_2_material':menu(['natural_v','strong_V_or_V7'])});constraints.append({'kind':'different','fields':['day_1_material','day_2_material']})
        if level==63 and '30 clean seconds' in clause:
            f.update({'clean_seconds_each':integer(0,3600),'all_four_circuits':boolean(),'equal_rest':boolean()});ex.update({'all_four_circuits':True,'equal_rest':True});constraints.append({'kind':'minimum','field':'clean_seconds_each','value':30})
        stages.append(step('audit_'+str(n+1),clause,f,ex,constraints=constraints))
    if level==63:
        stages.append(step('actual_recording_references','Record major and minor performances with intentional system choice and successful recovery.',{'major_recording_reference':text(),'minor_recording_reference':text(),'actual_recordings_declared':boolean()},{'actual_recordings_declared':True}))
    stages.append(step('practice_log','Enter the printed practice-log fields; BPM and evidence are learner declarations, not observed timing.',{'date':text(),'focus':text(),'bpm':integer(1,400),'clean':boolean(),'weak_link':text(),'next_target':text()},{'clean':True}))
    stages[-1]['requires_known'].remove('bpm')
    return stages,{'source_clauses':clauses,'automatic_mastery':False}

def caged_stages(root,form):
    primary,offsets=FORMS[form];frets=[r for r in range(25) if (TUNING[primary]+r)%12==PC[root] and all(x is None or 0<=r+x<=24 for x in offsets)]
    require(bool(frets),'CAGED_AVAILABLE_CHOICE')
    contact=obj({'string':menu(list(TUNING)),'fret':integer(0,24),'named_pitch':text()})
    stages=[step('choose_root_region',f'State the root string and fret for printed {root} / {form} form. Choose an octave whose formula stays on the neck.',{'root':literal(root),'form':literal(form),'root_string':literal(primary),'root_fret':menu(frets)},save='root_region'),
      step('calculate_formula','Calculate the printed form formula, including muted strings; name every root inside it.',{'frets':array(integer(0,24),6),'root_contacts':{'type':'array','items':contact,'minItems':1,'maxItems':6}},constraints=[{'kind':'caged_formula','root':root,'form':form,'offsets':offsets,'primary':primary}],save='form'),
      *performance('silent_formation','Form silently and release before sounding the practical partial. Do not force the largest grip.', ['formed_silently','root_region_identified','pressure_relaxed']),
      step('choose_practical_partial','Explicitly choose a practical partial from the calculated form.',{'contacts':{'type':'array','items':contact,'minItems':2,'maxItems':6}},constraints=[{'kind':'caged_subset','minimum':2}],save='partial'),
      *performance('sound_practical_partial','Sound the chosen practical partial; report this as your manual declaration.', ['partial_sounded','unwanted_strings_muted','root_identity_clear']),
      step('choose_embedded_triad','Name a triad inversion and explicitly choose three contacts inside the calculated form.',{'inversion':menu(['root','first','second']),'contacts':array(contact,3),'lowest_degree':text()},constraints=[{'kind':'caged_subset','minimum':3}],save='triad'),
      *performance('arpeggiate_embedded_triad','Name and arpeggiate the chosen embedded triad inversion.', ['triad_named','inversion_named','arpeggiated','quality_clear'])]
    return stages

def build_program(row,o):
    p=row['program'];body=o['implementation']['source_scope']['selected_source_text'];stages=[];facts={};hidden=None
    if 'written_' in p:
        hidden=written_answer(o);stages=[step('written_response',o['source_payload']['label']+' — write before touching the guitar or revealing the self-check.',{k:text() for k in hidden},save='written_response'),step('delayed_self_check','Explicitly reveal the printed self-check after committing your own response.',{'reveal_requested':boolean()},{'reveal_requested':True},action='reveal'),step('compare_written_response','Compare your committed response with the printed source self-check. This symbolic check does not assess performance.',{'self_checked':boolean()},{'self_checked':True},action='compare',constraints=[{'kind':'written_comparison'}])]
    elif p=='l054_root_form_command':
        root,form=re.fullmatch(r'([A-G]) / ([CAGED]) form',o['source_payload']['label']).groups();stages=caged_stages(root,form);facts={'root':root,'form':form,'formula_offsets':FORMS[form][1]}
    elif p=='l054_caged_atlas':
        stages=[step('choose_target_root','Choose one natural target root for the complete C-A-G-E-D cycle.',{'root':menu(list('CDEFGAB'))},save='atlas_root')]
        # The printed atlas commands a complete five-region cycle. Each region
        # has separate formula/root/partial/triad manual declarations.
        for form in 'CAGED':
            stages+=performance('silent_'+form,'Form the nearest '+form+' region silently. Use another octave if a formula needs a negative fret.', ['root_string_named','formula_calculated','all_roots_named','nearest_region_chosen','formed_silently'])
            stages+=performance('verify_'+form,'Verify one practical partial and one triad fragment in this '+form+' region.', ['practical_partial_verified','triad_fragment_verified','inversion_named','local_scale_tones_identified'])
    elif p.endswith('silent_spelling'):
        minor=o['level']==56;scales=MINOR if minor else MAJOR
        romans=['i','ii°','III','iv','v','VI','VII'] if minor else ['I','ii','iii','IV','V','vi','vii°']
        qualities=['m','dim','M','m','m','M','M'] if minor else ['M','m','m','M','M','m','dim']
        functions=['T','P','T','P','wD','T/P','wD'] if minor else ['T','P','T','P','D','T','D']
        for key,notes in scales.items():
            require(' '.join(notes) in body,'CACHED_SCALE_FACTS')
            for i,note in enumerate(notes):
                expected={'scale_note':note,'chord_name':note+('' if qualities[i]=='M' else qualities[i]),'roman':romans[i],'quality':qualities[i],'function':functions[i]}
                stages.append(step(f'{key}_degree_{i+1}',f'Without the guitar, spell {key}'+(' natural minor' if minor else ' major')+f' degree {i+1}: note, chord, numeral, quality and function.',{k:text() for k in expected},expected))
            if minor:
                expected={'raised_seventh':RAISED[key],'natural_v':notes[4]+'m','strong_V':notes[4],'strong_V7':notes[4]+'7','leading_tone_triad':RAISED[key]+'dim'}
                stages.append(step(key+'_controlled_alteration','Name the controlled raised seventh, natural v, V, V7 and leading-tone diminished chord for '+key+' minor.',{k:text() for k in expected},expected))
        facts={'spelling_sequence':'Printed quality/numeral/scale tables','core_prompts':42,'minor_VI_function':'T/P' if minor else None}
    elif p.endswith('functional_hearing'):
        minor=o['level']==56;keys=list(MINOR if minor else MAJOR)
        stages.append(step('choose_practice_key','Choose a printed practice key; leave timing as your own declared tempo.',{'key':menu(keys),'bpm':integer(1,400)},save='ear_key'))
        stages[-1]['requires_known'].remove('bpm')
        progressions=['i-iv-v-i','i-iv-V-i','i-iv-V7-i','random key: natural v or strong V'] if minor else ['I-IV-V-I','I-vi-IV-V','ii-V-I-I','random key: function before chord name']
        for n,prog in enumerate(progressions,1):
            if n==4:
                stages.append(step('random_key_pass','Draw a printed practice key for the random-key identification pass; this is an explicit manual choice, not generated source audio.',{'drawn_key':menu(keys),'random_key_draw_declared':boolean()},{'random_key_draw_declared':True},save='random_ear_key'))
            duties=['relative_four_beat_spans_followed','sung_before_identification','listened','source_progression_kept']
            if not minor:duties.append('eyes_closed_repeat')
            stages+=performance('ear_pass_'+str(n),'Printed pass '+str(n)+': '+prog+'. Play four beats per printed chord in the governing loop; '+('sing the seventh degree before each dominant.' if minor else 'sing each root; repeat with eyes closed.'), duties)
            stages.append(step('ear_identification_'+str(n),'Manually identify '+('natural v / strong V before chord name.' if minor else 'the function family before chord name.'),{'heard_identification':text(),'independent_identification':boolean(),'limitations_note':text()},{'independent_identification':True}))
        stages.append(step('advancement_boundary','Add a key only after the printed spelling/formation/analysis standard; raise tempo after three clean cells. Rebuild from numerals when transposition fails.',{'source_key_spelling_standard_met':boolean(),'three_clean_cells':boolean(),'repair_or_next_key_note':text()},{'source_key_spelling_standard_met':True,'three_clean_cells':True}))
        facts={'relative_beats_per_chord':4,'fixed_bpm':None,'hearing_observed':False}
    elif p=='l059_triad_atlas':
        for root in ('C','A'):
            for strings in SETS:
                name='-'.join(strings)
                for quality in ('major','minor'):
                    for inv in range(3):
                        offsets=TRIAD_FORMULAS[name][quality][inv];bass=TRIADS[root][quality][inv]
                        frets=[r for r in range(25) if (TUNING[strings[0]]+r)%12==PC[bass] and all(0<=r+x<=24 for x in offsets)]
                        require(frets,'SOURCE_TRIAD_AVAILABLE_POSITION')
                        stages.append(step(f'{root}_{name}_{quality}_{inv}',f'Silently form {root} {quality}, '+['root','first','second'][inv]+f' inversion on {name}. Name all three notes and bass role; verify the third, then release.',{'bass_fret':menu(frets),'named_notes':array(text(),3),'bass_role':text(),'formed_silently':boolean(),'quality_third_verified':boolean()},{'bass_role':['root','third','fifth'][inv],'formed_silently':True,'quality_third_verified':True},release=True,constraints=[{'kind':'triad_names','strings':list(strings),'offsets':offsets,'allowed_notes':TRIADS[root][quality]}]))
                        stages.append(release())
        facts={'silent_formations':48,'source_formulas':TRIAD_FORMULAS,'physical_finger_clearance_cm':1,'no_audio_schedule':True}
    elif p=='l063_technique_mechanics':
        stages.append(step('choose_technique_system','Explicitly choose a printed system; preserve its attack order and fret→attack→release sequence.',{'system':menu(['crosspicking','hybrid','three_string_sweep','four_string_sweep']),'starting_work_seconds':literal(15)},save='technique'))
        stages+=performance('technique_work','Work begins at15 seconds. Fret→attack→release→next string; one active pitch unless an intentional printed pedal. Stop immediately for pain, burning tension, uncontrolled noise or collapsing grip.', ['work_interval_15_seconds_declared','attack_map_followed','fretted_before_attack','released_before_next_string','one_pitch_or_printed_pedal','both_hands_muted','volume_balanced','no_stop_condition'])
        stages.append(step('equal_rest','Rest for the same15-second duration, manually reported; no runtime timer.',{'rest_seconds':integer(0,3600),'rest_taken':boolean()},{'rest_seconds':15,'rest_taken':True}))
        stages.append(step('endurance_boundary','Increase time only after tone and muting remain unchanged through the final repetition.',{'tone_unchanged':boolean(),'muting_unchanged':boolean(),'next_work_seconds':integer(15,3600),'equal_rest_seconds':integer(15,3600)},{'tone_unchanged':True,'muting_unchanged':True},constraints=[{'kind':'equal','fields':['next_work_seconds','equal_rest_seconds']}]))
        facts={'attack_maps':{'crosspicking':'D-U-D-U','hybrid':'P+m+a','three_string_sweep':'D-D-D / U-U-U','four_string_sweep':'D-D-D-D / U-U-U-U'},'initial_work_seconds':15,'equal_rest':True,'stop_conditions':['pain','burning tension','uncontrolled string noise','collapsing pick grip']}
    elif p.endswith('progression_mastery_audit'):stages,facts=audit(o)
    else:raise Refusal('UNRECONCILED_SOURCE_PROGRAM')
    require(stages and all(s['schema']['additionalProperties'] is False for s in stages),'SOURCE_PROGRAM_FIELDS')
    # This explicit source-program whitelist keeps complete operational
    # guidance available for non-secret tasks, while excluding every written
    # task's whole-page excerpt and neighboring self-checks.
    safe_context=[o['source_payload']['label']] if hidden is not None else [body]
    return {'name':p,'steps':stages,'learner_instruction_context':safe_context,'source_facts':facts,'hidden_self_check':hidden,'fixed_bpm':None,'performance_observed':False,'grants_credit':False,'automatic_mastery':False,'adapter_fret_range':[0,24],'range_authority':'Private finite standard-tuning adapter, not a printed universal fret limit.'}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();cache={}
    def pinned(ref):
        p=ref['path'];require(not Path(p).is_absolute() and '..' not in Path(p).parts,'RELATIVE_INPUT')
        f=root/p;require(f.resolve().is_relative_to(root) and not any(q.is_symlink() for q in [f,*f.parents]),'INPUT_SYMLINK_OR_ESCAPE')
        if p not in cache:cache[p]=f.read_bytes()
        require(sha(cache[p])==ref['sha256'] and ('bytes' not in ref or len(cache[p])==ref['bytes']),'CACHED_PIN_DRIFT:'+p)
        return cache[p]
    selection=strict(pinned({'path':SELECTION,'sha256':SELECTION_SHA}));ledger=[strict(x) for x in pinned(selection['selection']['ledger']).splitlines()];bykey={x['package_key']:x for x in ledger};require(len(bykey)==len(ledger),'LEDGER_DUPLICATE')
    refs={x['path']:x for x in selection['cached_input_pins']};contexts={};rows=[];program_counts=collections.Counter()
    for row in selection['exact_rows']:
        key=row['key'];l=bykey[key];require(l['official_status']=='Pending' and l['known_executable_recipe'] is None and l['official_acceptance_binding'] is None and l['dispatch_ownership']=={'broad_lane_excluded':False,'transferred_shard':None},'ELIGIBILITY_DRIFT')
        raw=pinned(refs[row['payload_path']]).splitlines()[row['jsonl_line']-1];o=strict(raw)
        require(sha(raw)==row['original_row_sha256'] and sha(encoded(o))==row['compact_order_sha256'] and o['package_key']==key and o['source_identity']==row['source_identity'] and o['unresolved_reasons']==[],'EXACT_ROW_BINDING')
        require(o['implementation']['kind']=='manual_curriculum_task' and o['implementation']['automated_assessment'] is False,'SOURCE_MANUAL_BOUNDARY')
        context_ref=next(x for x in o['source_refs'] if x['path'].endswith('source-context.json'));ctx=strict(pinned(context_ref));contexts[context_ref['path']]=ctx
        program=build_program(row,o);program_counts[program['name']]+=1
        contract_sha=sha(encoded(program));export={'schema':SCHEMA,'source_key':key,'source_identity':row['source_identity'],'original_row_sha256':sha(raw),'original_compact_sha256':sha(encoded(o)),'contract_sha256':contract_sha,'payload_ref':{**refs[row['payload_path']],'jsonl_line':row['jsonl_line']},'source_pins':l['source_pins'],'context_ref':context_ref['path'],'original_record':o,'program':program,'qualification':'Private source-bound manual procedure; no runtime admission, acceptance, mastery or credit.'}
        rows.append(export)
    require(len(rows)==len({r['source_key'] for r in rows})==96 and len(program_counts)==18,'EXACT_96_18_CLOSURE')
    closure={'schema':'fathom.compiled-manual-curriculum-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'ledger':selection['selection']['ledger'],'cached_inputs':list(refs.values()),'contexts':contexts,'keys':[r['source_key'] for r in rows],'contracts':{r['source_key']:r['contract_sha256'] for r in rows},'program_counts':dict(program_counts),'source_files_reread':0,'new_source_extraction':False,'runtime_admitted':False,'grants_credit':False}
    return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),'rows':96,'programs':18,'source_steps':sum(len(r['program']['steps']) for r in rows)}

def validate_bundle(rows,closure,*,expected=None,root=None):
    # Validation is against the source-pinned compiler output, not attacker-
    # supplied hashes. A caller may cache one trusted build for a bulk check.
    if expected is None:
        authoritative_rows,authoritative_closure,_=build(root or Path(__file__).resolve().parents[2]);expected=(authoritative_rows,authoritative_closure)
    require(rows==expected[0] and closure==expected[1],'EXACT_PINNED_EXPORT_DRIFT')
    require(closure['schema']=='fathom.compiled-manual-curriculum-closure.1' and closure['runtime_admitted'] is False and closure['grants_credit'] is False,'CLOSURE_BOUNDARY')
    require(len(rows)==96 and len({r['source_key'] for r in rows})==96 and [r['source_key'] for r in rows]==closure['keys'],'CLOSED_KEYS')
    for r in rows:
        require(r['schema']==SCHEMA and r['source_key']==r['original_record']['package_key'] and r['source_identity']==r['original_record']['source_identity'],'IDENTITY_BINDING')
        require(sha(encoded(r['program']))==r['contract_sha256']==closure['contracts'][r['source_key']] and sha(encoded(r['original_record']))==r['original_compact_sha256'],'CONTRACT_DRIFT')
        require(r['context_ref'] in closure['contexts'],'MISSING_CONTEXT')
        for s in r['program']['steps']: require('default' not in json.dumps(s['schema']) and s['schema']['additionalProperties'] is False and s['action'] in ('submit','release','reveal','compare'),'MANUAL_SCHEMA')
    return True

def generate(root,out=OUT):
    root=Path(root);rows,closure,metrics=build(root);validate_bundle(rows,closure,expected=(rows,closure));target=root/out;target.mkdir(parents=True,exist_ok=False)
    q=lambda x:json.dumps(x,ensure_ascii=False)
    h=['#pragma once','#include <array>','namespace fathom::tasks::manual_curriculum_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+q(sha(encoded(closure)))+';','inline const std::array<Row,96> rows = {{']
    h += ['{'+q(r['source_key'])+','+q(encoded(r).decode())+'},' for r in rows];h+=['}};','struct Context { const char* path; const char* value; };','inline const std::array<Context,6> contexts = {{']
    h += ['{'+q(p)+','+q(encoded(c).decode())+'},' for p,c in closure['contexts'].items()];h+=['}};','inline constexpr const char* tuningJson='+q(encoded(TUNING).decode())+';','inline constexpr const char* pitchClassesJson='+q(encoded(PC).decode())+';','}']
    files={'definitions.jsonl':b''.join(encoded(r)+b'\n' for r in rows),'family-closure.json':encoded(closure)+b'\n','GeneratedManualCurriculumFamily.hpp':('\n'.join(h)+'\n').encode()}
    pins=[]
    for name,data in files.items():(target/name).open('xb').write(data);pins.append({'path':str((target/name).relative_to(root)),'bytes':len(data),'sha256':sha(data)})
    receipt={'outcome':'PASS','metrics':metrics,'files':pins,'source_program_counts':closure['program_counts'],'original_source_files_read':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--out',default=OUT);a=p.parse_args();print(json.dumps(generate(a.root,a.out)))
