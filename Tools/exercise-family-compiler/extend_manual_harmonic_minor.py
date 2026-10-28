#!/usr/bin/env python3
"""47 cached harmonic-minor manual contracts, nine shared graph constructors.

Original contracts/contexts/models are immutable reference inputs. This DATA
compiler does not read original PDF/TXT, run native tasks or confer acceptance.
"""
from pathlib import Path
import argparse,ast,collections,copy,functools,hashlib,importlib.util,itertools,json,time
BASE='Build/manager-resume-r03/manual-harmonic-minor47-r01'
MANIFEST=BASE+'/source-family-manifest.json'
MANIFEST_SHA='553557c02948a81e81a38c812113f5c693fc8be0d62e3d5f26a889077130b0fe'
OUT=BASE+'/generated-r02'
HELPER={'path':'Tools/exercise-family-compiler/compile_source_defined_assessments.py','bytes':48641,'sha256':'49a5b6ea51a92ada7cf98383fb400b6660f2f1eeb0a664748c5b15e70346f953'}
COUNTS={'comparison':6,'octaves':3,'leading':6,'augmented-second':6,'melodic':5,'triads':7,'dominants':3,'diminished':10,'capstone':1}
def helper(root):
    raw=(Path(root)/HELPER['path']).read_bytes();assert len(raw)==HELPER['bytes']and hashlib.sha256(raw).hexdigest()==HELPER['sha256'];sp=importlib.util.spec_from_file_location('harmonic_minor_primitives',Path(root)/HELPER['path']);h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h);return h
def exact_at(o,path):
    for part in path:
        if type(part)is int:assert type(o)is list and 0<=part<len(o),'SOURCE_ARRAY_PATH'
        else:assert type(part)is str and type(o)is dict and part in o,'SOURCE_FIELD_PATH'
        o=o[part]
    return o
@functools.lru_cache(maxsize=9)
def frozen_selector(model_bytes):
    """Compile only the pinned existing pure selector once per source profile."""
    t=ast.parse(model_bytes);f=[n for n in t.body if isinstance(n,ast.FunctionDef)and n.name=='selection'];assert len(f)==1
    env={'copy':copy,'rh':lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}
    exec(compile(ast.Module(body=f,type_ignores=[]),'<pinned existing pure source selector>','exec'),env)
    return env['selection']
def old_selection(model_bytes,contract,choice):
    """Reuse existing pure code; no imports, source extraction or main campaign."""
    request={'package_key':contract['package_key'],'contract_sha256':hashlib.sha256(json.dumps(contract,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),**choice}
    return frozen_selector(model_bytes)(contract,request)
def repair_eligible(h,route,failed):
    """Pure future guard oracle, never native owner execution."""
    g=route['guard'];h.require(set(g)=={'kind','field','equals'}and g['kind']=='failed_report_predicate'and g['equals']is False and route['failed_node']=='source_step_4'and g['field']in ['harmonic_pair_more_directional_reported','G_sharp_incomplete_A_settled_reported'],'CLOSED_REPAIR_DESCRIPTOR')
    h.require(type(failed)is dict and set(failed)=={'pass_tag','payload'}and type(failed['pass_tag'])is str and type(failed['payload'])is dict,'FAILED_SOURCE_BINDING')
    if failed['pass_tag']!=route['failed_node']:return False
    h.require(g['field']in failed['payload'],'FAILED_SOURCE_FIELD');value=failed['payload'][g['field']];h.require(type(value)in[bool,type(None)],'FAILED_REPORT_TYPE')
    return value is False
def choice_domains(c,profile):
    if profile=='octaves':return {}
    d={'start_stroke':['D','U']}
    if profile=='leading':d.update(pair_start=[1,5],technique=list(c['techniques']))
    if profile=='augmented-second':d['hand_strategy']=['shift','comfortable_reach']
    if profile=='triads':d['accent_role']=list(c['eligible_accent_roles'])
    return d
def choices(c,profile):
    d=choice_domains(c,profile);names=list(d)
    return [dict(zip(names,values))for values in itertools.product(*(d[n]for n in names))]
def make_program(h,o,profile,model):
    c=o['implementation']['manual_execution_contract'];nodes={};ordered=[];source_steps=c['steps'];pending_repair=[]
    def bools(fs):return {f:h.boolean()for f in fs}
    def array(s,n):return {'type':'array','items':s,'minItems':n,'maxItems':n}
    def nonempty(f):return {'kind':'nonempty_trimmed_text','field':f,'minimum':1,'maximum':2048}
    def rep(n,instruction,fields=None,expected=None,physical=False,refs=None,guards=None,id=None):
        id=id or 'source_step_'+str(n);field={'manual_source_evidence':h.text(True,2048),**(fields or{})};g=[nonempty('manual_source_evidence'),*(guards or[])];ref=refs if refs is not None else [{'original_contract_path':['steps',n-1]}];nodes[id]=h.report(instruction,field,expected or{},'end_unit',ref,constraints=g,physical=physical,tag=id,save=id);ordered.append(id);return id
    def acks(n,instruction,fs,physical=False,extra=None,expected=None,guards=None):
        return rep(n,instruction,{**bools(fs),**(extra or{})},{**dict.fromkeys(fs,True),**(expected or{})},physical,guards=guards)
    domains=choice_domains(c,profile)
    if domains:
        fields={n:({'type':'integer','enum':v,'input_role':'explicit_chosen_source_realization'}if type(v[0])is int else h.menu(v))for n,v in domains.items()}
        for f in fields.values():f['input_role']='explicit_chosen_source_realization'
        rep(0,'Explicitly choose the private realization. Printed pitches/contacts are fixed source facts; D/U strict alternation, accent and comfortable hand/ornament choices are learner choices. Nothing is selected initially.',fields,refs=[],id='choose_realization')
    def preparation(n):
        acks(n,'Compare natural and harmonic minor before this register. Sing G#-A and F-G#-A; retain G# spelling and name its actual job before playing. Singing register/durations and guitar contacts for this symbolic preparation remain unknown.', ['collections_compared_reported','G_sharp_A_sung_reported','F_G_sharp_A_sung_reported','G_sharp_spelling_reported','actual_G_sharp_job_named_before_playing_reported'],extra={'reported_G_sharp_job':h.text(True,2048)},guards=[nonempty('reported_G_sharp_job')])
    if profile=='comparison':
        preparation(1)
        acks(2,'Play all seven printed contacts, G-A, G#-A, then G-G#-A, with identical rhythm and volume. No numeric rhythm or dynamics are supplied.', ['all_seven_contacts_reported','identical_rhythm_and_volume_reported'],True)
        acks(3,'Manually record the G-A and G#-A pairs without announcing them. Use the same chosen two-note picking pattern for both pairs; recording is external.', ['both_pairs_recorded_reported','pairs_not_announced_reported','matched_pair_rhythm_and_volume_reported'],True,{'recording_reference':h.text(True,2048)},guards=[nonempty('recording_reference')])
        acks(4,'Listen to your retained recording. Report whether the harmonic-minor pair sounded more directional; a negative report retains the printed lengthen-A/reduce-approach-accent repair.', ['harmonic_pair_more_directional_reported'],extra={'listened_recording_reference':h.text(True,2048)},guards=[{'kind':'same_as_saved','left':h.ref('payload','listened_recording_reference'),'right':h.ref('saved','source_step_3','recording_reference')}])
        acks(5,'Report the natural b7 modal color and raised7 leading-tone distinction from your actual listening.', ['natural_b7_modal_and_raised7_function_reported'])
        pending_repair.append({'id':'directional_pair_repair','failed_node':'source_step_4','field':'harmonic_pair_more_directional_reported','instruction':c['repair_on_nondirectional_report']['exact_text'],'refs':[{'original_contract_path':['repair_on_nondirectional_report']}],'reports':['tonic_As_lengthened_relative_to_prior_attempt_reported','approach_note_accents_reduced_reported','both_pairs_rerecorded_without_announcing_reported','recording_listened_again_reported'],'source_restart_required':True})
    elif profile=='octaves':
        acks(1,'Name the fixed A harmonic-minor key, scale/degrees and G# leading-tone function. Source literals are instructions, not supplied learner answers.',[],extra={'G_sharp_function':h.text(True,2048)},expected={'G_sharp_function':c['steps'][0]['G_sharp_function']})
        preparation(2)
        for n,start in [(3,'D'),(4,'U')]:acks(n,'Perform the complete sixteen-tone printed mirror with '+start+' start, repeated highest A at the turnaround and continuous chosen strict alternation. Both source starts are required; no numeric clock.', ['complete_sixteen_contact_mirror_reported','highest_A_repeated_reported','continuous_pick_cycle_reported'],True,{'reported_source_start':h.menu(['D','U'],True)},expected={'reported_source_start':start})
        fs=c['steps'][4]['required_reports'];acks(5,'Report the retained source spelling, intentional F-G# interval, directional G#-A, repeated top A and uninterrupted pick cycle.',fs)
    elif profile=='leading':
        preparation(1);acks(2,'First pick all six printed 7-1-2-1-7-1 notes; the later ornament does not replace this first picked pass.', ['all_six_notes_picked_reported'],True)
        acks(3,'Sustain then release the final A. This is a hold/release duty with no new attack or fixed duration.', ['final_A_sustained_and_released_reported'],True)
        acks(4,'Play G# alone, A alone, then the pair and report incomplete G# versus settled A. If unrelated, sing7-1 before playing again.', ['G_sharp_incomplete_A_settled_reported'],True)
        acks(5,'Before the later selected single-pair ornament, report comfortable string tension. Pain or persistent tension always permits stop; no comfort is detected.', ['string_tension_comfortable_reported'])
        acks(6,'Perform the later six sounding positions with exactly the chosen one G#-A pair replaced by the chosen slide, hammer-on or half-step bend. Five picked attacks retain strict alternation; bend sounding target is distinct from its performed fret.', ['chosen_single_pair_ornament_reported','six_sounding_positions_reported','five_picked_attacks_reported'],True,{'reported_pair_start':{'type':['integer','null'],'enum':[1,5,None]},'reported_technique':h.menu(c['techniques'],True)},guards=[{'kind':'same_as_saved','left':h.ref('payload','reported_pair_start'),'right':h.ref('saved','choose_realization','pair_start')},{'kind':'same_as_saved','left':h.ref('payload','reported_technique'),'right':h.ref('saved','choose_realization','technique')}])
        acks(7,'Sustain then release the final A after the ornament without a new attack or numeric duration.', ['final_A_sustained_and_released_reported'],True)
        acks(8,'Report leading-tone/tonic identity and G# spelling preserved.', ['leading_tone_tonic_and_spelling_reported'])
        pending_repair.append({'id':'sing_resolution_repair','failed_node':'source_step_4','field':'G_sharp_incomplete_A_settled_reported','instruction':'Sing7-1 before playing the pair again; then retry the complete source unit.','refs':[{'original_contract_path':['steps',3]}],'reports':['G_sharp_A_sung_before_replay_reported'],'source_restart_required':True})
    elif profile=='augmented-second':
        preparation(1)
        nodes['source_step_1']['schema']['properties']['pain_or_persistent_tension_reported']=h.boolean();nodes['source_step_1']['schema']['required'].append('pain_or_persistent_tension_reported');nodes['source_step_1']['expected']['pain_or_persistent_tension_reported']=False
        acks(2,'Play E then F. Preserve the source F contact while preparing the next destination; this is not an exit release.', ['E_then_F_in_source_order_reported'],True)
        acks(3,'Prepare the printed G# fret before releasing F. Choose a hand shift whenever needed, rather than a rigid stretch. No extra attack or preparation duration is inferred.', ['prepared_before_F_release_reported'],True,{'shift_needed_reported':h.boolean()},guards=[{'kind':'source_choice_implication','condition_field':'shift_needed_reported','when':True,'choice_ref':h.ref('saved','choose_realization','hand_strategy'),'required_choice':'shift'}])
        acks(4,'Perform the remaining six source contacts G#-A-G#-F-E-A. Do not add a repeated top A from prose shorthand.', ['remaining_six_source_contacts_reported'],True)
        acks(5,'Report intentional augmented-second control, comfortable physical strategy and tonic destination.', ['interval_control_and_tonic_reported'])
    elif profile=='melodic':
        acks(1,'Name the final tonic function and printed melodic job before playing. No underlying E7/G#dim harmony is invented for this melodic cell.',[],extra={'final_function':h.text(True,2048)},expected={'final_function':'tonic'})
        preparation(2);acks(3,'Perform the first seven printed contacts in order.', ['first_seven_source_contacts_reported'],True)
        acks(4,'Play the final printed A and hold it longer than the preceding note. The relation is qualitative; no seconds, ratio or extra attack is supplied.', ['final_A_sustained_reported'],True)
        acks(5,'Report actual release and that final A was longer than the previous note. The release is not a new attack.', ['released_reported','longer_than_previous_reported'],True)
        acks(6,'Report tonic function and spelling preserved.', ['tonic_and_spelling_preserved_reported'])
    elif profile=='triads':
        preparation(1);atlas=c['source_atlas'];fs=c['steps'][1]['required_core_secure_reports'];acks(2,'Name the printed triad, spelling, quality and function. Only the retained source criteria gate extension beyond the secure i-iv-V-vii° functional core.',fs,extra={f:h.text(True,2048)for f in ['chord','spelling','quality','function']},expected={f:atlas[f]for f in ['chord','spelling','quality','function']})
        acks(3,'Perform all eight mirror contacts, repeat the highest root and accent both written occurrences of your explicitly selected third/altered-fifth role. Diminished/augmented quality must remain distinct.', ['all_eight_mirror_contacts_reported','highest_root_repeated_reported','both_selected_quality_tone_accents_reported'],True,{'reported_accent_role':h.menu(c['eligible_accent_roles'],True)},guards=[{'kind':'same_as_saved','left':h.ref('payload','reported_accent_role'),'right':h.ref('saved','choose_realization','accent_role')}])
        acks(4,'Play the retained Em then E source arpeggios back to back, holding then releasing each final E. Report E major stronger pull toward Am. Support source children are not thereby completed or credited.', ['back_to_back_and_both_E_holds_reported','E_major_stronger_pull_toward_Am_reported'],True)
        acks(5,'Report distinct printed triad quality and mirror integrity.',c['steps'][4]['required_reports'])
    elif profile=='dominants':
        preparation(1);acks(2,'Name the printed dominant and its function; explain the retained voice-leading map without adding/reordering played contacts.', ['voice_leading_understood_reported'],extra={'chord':h.text(True,2048),'function':h.text(True,2048)},expected={'chord':c['source_chord'],'function':c['source_function']})
        acks(3,'Perform all eight printed mirror contacts with the repeated turnaround E.', ['all_eight_source_contacts_reported','turnaround_preserved_reported'],True)
        acks(4,'Hold then release final E, with no new attack or numeric hold.', ['final_E_hold_and_release_reported'],True)
        acks(5,'Perform the whole retained hearing sequence Em→Am, E→Am, E7→Am in source order, without louder dominants. Hold/release all three final Es; these chosen source-route realizations do not complete support children.', ['all_three_pairs_in_order_reported','dominants_not_louder_reported','all_three_dominant_final_E_holds_reported'],True)
        acks(6,'Report modal minor-v versus stronger V/V7 resolution, distinguishing G/G# and D functions.',c['steps'][5]['required_reports'])
    elif profile=='diminished':
        preparation(1);acks(2,'Before playing, name root/chord/destination, sing G#-A and understand the retained resolution explanation. The voice map does not add/reorder played contacts.', ['G_sharp_A_sung_before_playing_reported','source_resolution_explanation_understood_reported'],extra={'root':h.text(True,2048),'chord':h.text(True,2048),'destination':h.text(True,2048)},expected={'root':'G#','chord':c['source_chord'],'destination':'Am'})
        acks(3,'Perform all eight written contacts from the diminished chord into the tonic area. R denotes chord root, never a rest; preserve every repeated attack actually printed.', ['all_eight_written_contacts_reported','printed_harmonic_regions_and_attack_order_reported'],True)
        acks(4,'Report dominant-function resolution, source integrity and tonic destination.',c['steps'][3]['required_reports'])
    elif profile=='capstone':
        preparation(1);acks(2,'Name the printed sixteen-bar progression and the distinct G# jobs in E7 and G#dim7 before the uninterrupted capstone.', ['G_sharp_functions_reported'],extra={'chords_by_bar':array(h.text(True,2048),16)},expected={'chords_by_bar':list(c['steps'][1]['chords_by_bar'])})
        item=h.schema({'bar':h.integer(True,16),'beat':h.integer(True,4),'next_chord':h.text(True,2048),'announced_on_beat4_reported':h.boolean()});expected=[{**a,'announced_on_beat4_reported':True}for a in c['steps'][2]['announcement_schedule']]
        acks(3,'Perform the complete continuous64-contact capstone before reporting. Announce the next chord on source beat4 of bars1–15, retain all eight printed final-two-bar Am attacks, and add no post-bar16 announcement/cycle. Beat4 is a symbolic manual duty, not an inferred note/quarter mapping or scheduler.', ['all64_contacts_in_order_reported'],True,{'announcements':array(item,15)},expected={'announcements':expected})
        acks(4,'Report source root accents, core functions and the closed tonic ending.',c['steps'][3]['required_reports'])
    else:raise ValueError('UNKNOWN_SOURCE_PROFILE')
    for a,b in zip(ordered,ordered[1:]):nodes[a]['next']=b
    nodes['end_unit']=h.end('source_unit_manual_reports_only_no_credit')
    original_order=ordered[:];tags=['source_step_'+str(n)for n in range(1,len(source_steps)+1)]
    rep(0,'Bind the actual failed source report and diagnosis. A repair never discharges the original failed pass; release must occur before new physical work.',{'failed_criterion':h.menu(tags),'diagnosis':h.text(True,2048)},refs=[],guards=[{'kind':'same_as_failed_pass','payload_ref':h.ref('payload','failed_criterion')},nonempty('diagnosis')],id='repair_bind');nodes['repair_bind']['next']='repair_choice'
    routes={'retry_complete_source_unit':{'next':original_order[0],'native_protocol':'retry_from_entry'},'stop':{'next':'end_unit','native_protocol':'stop'}}
    for r in pending_repair:
        rep(0,r['instruction'],bools(r['reports']),dict.fromkeys(r['reports'],True),True,r['refs'],id=r['id']);nodes[r['id']]['next']='repair_choice';routes[r['id']]={'next':r['id'],'guard':{'kind':'failed_report_predicate','field':r['field'],'equals':False},'failed_node':r['failed_node'],'guard_phase':'after_owned_release_before_new_repair_activation'}
    nodes['repair_choice']=h.choice('Explicitly retry the complete source unit, stop after owned release, or choose an applicable printed repair. Unknown diagnoses cannot activate a repair.', 'repair_action',list(routes),routes)
    protocols=[]
    if profile=='augmented-second':protocols.append({'kind':'source_reported_stop_condition','node':'source_step_1','field':'pain_or_persistent_tension_reported','when':True,'outcome':'stopped','release_existing_physical_debt':True,'nonphysical_report_does_not_fabricate_activation':True,'unknown_unresolved':True})
    if profile=='leading':protocols.append({'kind':'source_later_comfort_boundary','required_before_node':'source_step_6','comfort_node':'source_step_5','field':'string_tension_comfortable_reported','unknown_or_false_blocks':True,'earlier_picked_and_hold_duties_retained':True})
    if profile=='comparison':protocols.append({'kind':'source_directional_repair_debt','failed_node':'source_step_4','field':'harmonic_pair_more_directional_reported','negative_activates':True,'unknown_does_not_clear':True,'repair_node':'directional_pair_repair','retain_across':['retry','stop','navigation','restart'],'clear_requires':'owned complete source retry with new recording/listening and positive directional report; repair acknowledgement alone insufficient'})
    return {'name':'b_harmonic_minor_'+profile,'mode':'graph','steps':[],'graph':{'schema':'fathom.manual-procedure-graph.1','entry':original_order[0],'nodes':nodes,'domains':{'explicit_realization':domains},'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':original_order[0],'failed_pass_repair_entry':'repair_bind'},'call_semantics':'Source steps retained exactly; no note clock/observed performance. Physical continuity and held-contact duties remain owner responsibilities.','loop_semantics':'Printed repair is conditional on retained failed node/report, requires prior owned release and returns to full retry without completing failed unit.'},'source_kind':o['implementation']['kind'],'source_task_kind':profile,'source_contract_sha256':h.sha(h.encoded(c)),'source_literal_sha256':h.sha(h.encoded(c['steps'])),'source_literal_ref':{'original_record_path':['implementation','manual_execution_contract','steps']},'learner_instruction_context_ref':{'original_record_paths':[['implementation','instructions'],['implementation','source_scope','selected_source_text'],['implementation','manual_execution_contract','source_session_remainder'],['implementation','manual_execution_contract','source_full_book_mastery']],'context_instructions_only':True,'never_include_printed_answer_pre_reveal':True},'source_realization':{'frozen_model':model,'function':'selection','choice_domains':domains,'choice_node':'choose_realization'if domains else None,'selection_is_private_choice_not_printed_pick_map':True,'source_contacts_from_retained_steps_only':True,'hand_or_bend_comfort_and_physical_execution_not_observed':True,'symbolic_clock':None},'source_state_protocols':protocols,'learner_hidden_source_answers':[],'future_guard_extensions':sorted({g['kind']for n in nodes.values()for g in n.get('constraints',[])}|({'failed_report_predicate'}if pending_repair else set())),'source_limits':['Complete full-book/page20 and session duties remain reference-bound external evidence debt; this source unit does not assert their completion.','Support-route performances do not complete or credit support identities.','Printed notes/degrees/contacts/source beat labels are source facts; every reported name/action/listening/quality/comfort result starts blank.','D/U strict alternation and selected accents/hand strategy/ornament are explicit private realization choices. Only octave source imposes both starts.','No numeric note clock, fixed BPM, recording/acoustic detection, automatic mastery, native/installed or acceptance claim.','Source binding, chosen-contact projection, release/history/debt persistence and independent/current Home QA remain required.'],'source_clock':None,'fixed_bpm':None,'sounding_span':None,'performance_observed':False,'recording_observed':False,'automatic_mastery':False,'runtime_admitted':False,'original_kind_preserved':True,'grants_credit':False}
def build(root):
    start=time.perf_counter();root=Path(root).resolve();h=helper(root);cache=h.Inputs(root);raw=(root/MANIFEST).read_bytes();h.require(h.sha(raw)==MANIFEST_SHA,'MANIFEST_PIN');s=h.strict(raw)
    for p in [s['ledger'],s['current_descriptor'],s['prospective_C64'],s['closed449'],*s['B88_frozen_definitions'],*s['transferred190']]:cache.pinned(p)
    accepted={x['selection']['package_key']for x in h.strict(cache.pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};held={h.strict(l)['source_key']for l in cache.pinned(s['closed449']).splitlines()};future=set(h.strict(cache.pinned(s['prospective_C64']))['keys'])|{h.strict(l)['source_key']for p in s['B88_frozen_definitions']for l in cache.pinned(p).splitlines()};transferred=set()
    for p in s['transferred190']:x=h.strict(cache.pinned(p));h.require(len(x['keys'])==x['key_count'],'TRANSFER_COUNT');transferred.update(x['keys'])
    h.require(len(accepted)==2567 and len(held)==449 and len(future)==152 and len(transferred)==190,'EXACT_OWNERSHIP')
    proofs={p['profile']:p for p in s['cached_source_and_model_proofs']}
    for p in proofs.values():cache.pinned(p['model']);h.require(h.strict(cache.pinned(p['source_workflow_proof']))['result']=='PASS','CACHED_SOURCE_PROOF')
    rows=[];originals={};profiles=collections.Counter();step_refs=0
    for r in s['rows']:
        raw=cache.pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);c=exact_at(o,r['retained_contract_path']);h.require(h.sha(raw)==r['original_row_sha256']and h.sha(h.encoded(o))==r['original_compact_sha256']and h.sha(h.encoded(c))==r['retained_contract_sha256'],'SOURCE_ROW_PIN');h.require(o['package_key']==r['source_key']and o['source_identity']==r['source_identity']and o['implementation']['kind']==r['original_kind']and r['source_key']not in accepted|held|future|transferred,'EXACT_KEY_CUSTODY');cache.pinned(r['context_ref']);h.require(c['fixed_bpm']is None and not c['grants_credit']and not c['runtime_admitted'],'SOURCE_BOUNDARY')
        profile=r['model_profile'];p=make_program(h,o,profile,proofs[profile]['model']);validate_program(h,p,o);profiles[profile]+=1;originals[r['source_key']]=o;step_refs+=len(c['steps']);rows.append({'schema':'fathom.manual-procedure-reference-definition.1',**{k:r[k]for k in ['source_key','source_identity','original_row_sha256','original_compact_sha256','payload_ref','retained_contract_path','source_pins','context_ref']},'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'Cached source/model-bound private DATA; native projection/release/history/independent/installed/current Home acceptance pending.'})
    h.require(dict(profiles)==COUNTS and len(rows)==len({r['source_key']for r in rows})==47,'EXACT47_NINE_PROFILES')
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':MANIFEST,'sha256':MANIFEST_SHA},'keys':[r['source_key']for r in rows],'contracts':{r['source_key']:r['contract_sha256']for r in rows},'context_bindings':{r['context_ref']['path']:r['context_ref']for r in rows},'cached_source_and_model_proofs':s['cached_source_and_model_proofs'],'original_source_read_policy':s['original_source_read_policy'],'source_program_profile_counts':dict(profiles),'factoring':'Nine source-behavior compiler constructors, one shared form/graph schema; source constants derived by exact retained-contract paths. No per-row models. Original record/context reused once by immutable reference.','bridge_requirements':['Allow only exact47 keys and their nine original kinds with retained manual_execution_contract path; no kind conversion or canonical identity allocation.','Bind each steps[index]/repair source_action_ref to retained contract; render whitelisted readable source contacts/fields/rules and complete session/mastery context without raw provenance.','Reuse pinned pure selection functions as source oracle for one deterministic shared chosen-contact projection (D/U, accent, hand strategy, later single-pair articulation); chosen and printed contacts must remain distinct.','Implement source_choice_implication and source_reported_stop_condition; unknown shift/comfort/pain stays unresolved and cannot clear readiness or physical debt.','Bind conditional repairs to exact retained failed node as well as typed false report; preserve directional repair debt through restart/navigation and require full retry, not repair-only completion.','Retain uninterrupted64-contact capstone with15 symbolic source beat4 announcements, final8Am attacks/no new cycle; do not insert internal report/release steps or note clock.','Preserve source-internal F-held preparation, final-note hold/release and external recording/listening; reports do not imply measured comfort/performance/mastery.'],'native_execution':False,'runtime_admitted':False,'grants_credit':False,'official_acceptance_increment':0}
    metrics={'rows':47,'source_profiles':dict(profiles),'retained_source_step_refs':step_refs,'graph_nodes':sum(len(r['program']['graph']['nodes'])for r in rows),'context_copies':0,'original_source_reads':0,'cached_files_hashed_once':cache.hashes,'seconds':time.perf_counter()-start}
    return rows,closure,originals,proofs,cache,metrics
def validate_program(h,p,o):
    c=o['implementation']['manual_execution_contract'];nodes=p['graph']['nodes'];assert p['source_contract_sha256']==h.sha(h.encoded(c))and p['source_kind']==o['implementation']['kind']
    assert p['fixed_bpm']is None and p['source_clock']is None and not any(p[f]for f in ['performance_observed','recording_observed','automatic_mastery','runtime_admitted','grants_credit'])
    refs=set()
    for id,n in nodes.items():
        if n['kind']=='end':assert n['grants_credit']is False;continue
        schema=n['schema'];assert schema['additionalProperties']is False and set(schema['properties'])==set(schema['required'])and 'default'not in json.dumps(schema)
        for r in n.get('source_action_refs',[]):
            path=r['original_contract_path'];target=exact_at(c,path);assert type(target)is dict
            if path[0]=='steps':assert len(path)==2 and type(path[1])is int;refs.add(path[1])
            else:assert path==['repair_on_nondirectional_report']
        if n['kind']=='choice':assert set(n['routes'])==set(schema['properties'][n['route_field']]['enum'])and all(r['next']in nodes for r in n['routes'].values())
        else:assert n['next']in nodes
    assert refs==set(range(len(c['steps'])))and p['graph']['failure_policy']['nonphysical_failure_activates_physical']is False
    return True
def data_guard(h,g,payload,saved=None,failed=None):
    if g['kind']=='source_choice_implication':
        h.require(set(g)=={'kind','condition_field','when','choice_ref','required_choice'}and g['condition_field']=='shift_needed_reported'and g['when']is True and g['choice_ref']==h.ref('saved','choose_realization','hand_strategy')and g['required_choice']=='shift','CLOSED_SHIFT_GUARD');v=payload[g['condition_field']];h.require(type(v)in[bool,type(None)],'SHIFT_REPORT_TYPE');choice=saved['choose_realization']['hand_strategy'];h.require(choice in ['shift','comfortable_reach'],'SHIFT_CHOICE');return v is not None and (not v or choice=='shift')
    return h.data_guard(g,payload,saved,failed)
def generate(root,out=OUT):
    root=Path(root).resolve();rows,cl,_,_,_,metrics=build(root);h=helper(root);dest=root/out;h.require(not Path(out).is_absolute()and '..'not in Path(out).parts and dest.resolve().is_relative_to(root),'OUTPUT_PATH');dest.mkdir(parents=True,exist_ok=False);files=[]
    for name,b in {'definitions.jsonl':b''.join(h.encoded(r)+b'\n'for r in rows),'family-closure.json':h.encoded(cl)+b'\n'}.items():(dest/name).open('xb').write(b);files.append({'path':str((dest/name).relative_to(root)),'bytes':len(b),'sha256':h.sha(b)})
    result={'outcome':'47_SOURCE_MODEL_DATA_PASS_NATIVE_PENDING','metrics':metrics,'files':files,'official_acceptance_increment':0};(dest/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
