#!/usr/bin/env python3
"""Source-bound Level60 D–J44 data. References witnesses; no current224 edits."""
from pathlib import Path
import argparse, collections, copy, hashlib, importlib.util, itertools, json, time

SELECTION='Build/manager-resume-r03/manual-procedure-level060-harmonic-r01/selection.json'
SELECTION_SHA='8bd2099a7122953e239c96578528aa6589ba939bc4f438cc07346d2e6e7038e7'
OUT='Build/manager-resume-r03/manual-procedure-level060-harmonic-r01/generated-r02'
PROGRAMS={'manual_picking_system_comparison':'l060_picking_comparison',
 'manual_guide_tone_accent_workflow':'l060_guide_accent',
 'manual_same_root_quality_ladder':'l060_quality_ladder',
 'manual_major_progression_two_pass_workflow':'l060_major_two_pass_cadence',
 'manual_minor_progression_guide_followup':'l060_minor_guide_cadence',
 'manual_harmonic_framing_workflow':'l060_harmonic_framing'}

def dependencies(root, selection):
    result=[]
    for name in ['helper','graph_helper']:
        r=selection[name];p=Path(root)/r['path'];raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('PREIMPORT_HELPER_PIN')
        spec=importlib.util.spec_from_file_location('harmonic_'+name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result.append(m)
    return result

def binding(index):return {'original_contract_path':['steps',index]}

def program(h,g,o):
    impl=o['implementation'];c=impl['manual_execution_contract'];kind=impl['kind'];key=o['package_key'];prep=c['steps'][0]
    nodes={};domains={};pname=PROGRAMS[kind]
    if kind=='manual_harmonic_framing_workflow':pname+='_'+c['kind']
    def add(name,instruction,fields,expected,next_node,physical=False,source=None):
        node=g.report(h,instruction,fields,expected,next_node,physical=physical)
        if source is not None:node['source_action_ref']=binding(source)
        nodes[name]=node;return node
    bools=lambda *names:g.bools(h,*names)
    true=lambda *names:g.truths(*names)
    add('silent_work','Before sounding, explicitly report forming and spelling all56 source root/quality/family commands silently. A single cell does not perform this prerequisite.',
        bools('all56_formed_silently','all56_spelled','no_stop_condition'),true('all56_formed_silently','all56_spelled','no_stop_condition'),'name_source')
    groups=prep.get('groups')
    if groups:
        fields={'key':h.text(),'functions':h.array(h.text(),3),'chords':h.array(h.text(),3),'spellings':h.array(h.array(h.text(),4),3)}
        expected={'key':prep['key'],'functions':[x['function'] for x in groups],'chords':[x['chord'] for x in groups],'spellings':[x['spelling'] for x in groups]}
        gm=prep.get('guide_tone_members') or {x['role']:x for x in prep['initial_guide_members']}
    elif kind=='manual_same_root_quality_ladder':
        fields={'root':h.text(),'qualities':h.array(h.text(),7),'initial_spelling':h.array(h.text(),4)}
        expected={'root':prep['root'],'qualities':prep['qualities'],'initial_spelling':prep['spelling']};gm=prep['guide_tone_members']
    elif kind=='manual_harmonic_framing_workflow':
        fields={'source_heading':h.text(),'initial_spelling':h.array(h.text(),4)}
        expected={'source_heading':prep['source_heading'],'initial_spelling':prep['initial_chord_spelling']};gm=prep['guide_members']
    else:
        fields={'chord':h.text(),'spelling':h.array(h.text(),4),'active_strings':h.array(h.integer(1,6),4)}
        expected={n:prep[n] for n in fields};gm=prep['guide_tone_members']
    add('name_source','Name the exact source key/chord/functions/spellings and zone before attacks. Enter your own reports; source bindings are never filled answers.',fields,expected,'choose_guides',source=0)
    roles=list(gm);h.require(len(roles)==2,'EXACT_TWO_GUIDES')
    minor=kind=='manual_minor_progression_guide_followup'
    choices=['third_then_seventh','seventh_then_third']
    third=next(r for r in roles if r in ['3','b3']);seventh=next(r for r in roles if r in ['7','b7'])
    guide_selection={n:g.ref('payload',n) for n in ['first_guide','second_guide']}
    saved_guide_selection={n:g.ref('saved','guide_choice',n) for n in ['first_guide','second_guide']}
    domains['initial_guides']=[{'selection':{'first_guide':a,'second_guide':b},'contacts':[copy.deepcopy(gm[a]),copy.deepcopy(gm[b])]} for a,b in [roles,roles[::-1]]]
    guide_fields={'first_guide':h.menu(roles),'second_guide':h.menu(roles)}
    if minor:
        domains['initial_guides']=[{'selection':{'guide_order':order},'contacts':[copy.deepcopy(gm[a]),copy.deepcopy(gm[b])]} for order,(a,b) in zip(choices,[(third,seventh),(seventh,third)])]
        guide_fields={'guide_order':h.menu(choices)};guide_selection={'guide_order':g.ref('payload','guide_order')};saved_guide_selection={'guide_order':g.ref('saved','guide_choice','guide_order')}
    node=add('choose_guides','Choose which source third/seventh guide contact to rehearse first; use each once. The source does not fix this order or numeric accent strength.',
        guide_fields, {},'guide_preparation')
    node['save_as']='guide_choice';node['constraints']=[g.guard('domain_lookup',domain='initial_guides',selection=guide_selection)]
    guide_fields={n:h.array(schema,2) for n,schema in [('named_pitches',h.text()),('roles',h.text()),('strings',h.integer(1,6)),('frets',h.integer(0,24))]}
    guide_fields.update(bools('chosen_order_followed','guide_tones_accented','clean_tone','no_stop_condition'))
    node=add('guide_preparation','Rehearse and name both guide contacts in your explicitly selected order, accenting them before roots/fifths/scales/speed. These two preparation attacks are outside printed inventory.',guide_fields,true('chosen_order_followed','guide_tones_accented','clean_tone','no_stop_condition'),'source_2',True,0)
    node['computed_expected']={'kind':'selected_domain_reports','domain':'initial_guides','selection':saved_guide_selection,'fields':{'named_pitches':'printed_note','roles':'role','strings':'string','frets':'fret'}}
    node['source_contacts_ref']=['steps',0,'guide_tone_members' if 'guide_tone_members' in prep else 'initial_guide_members' if 'initial_guide_members' in prep else 'guide_members']
    events=impl['events']
    def performance(i,s,next_node,contacts,picks=None,extra=None):
        # Some comparison cards print only geometry/strokes. Bind note/role to
        # the already-retained exact source shape, never derive a new pitch.
        named=[]
        for e in contacts:
            if 'printed_note' in e and 'role' in e:named.append(e);continue
            candidates=[x for x in c['steps'][1].get('preparatory_blocked_members',[])
                if x['string']==e['string'] and x['fret']==e['fret']]
            h.require(len(candidates)==1,'EXACT_LINKED_SOURCE_MEMBER')
            named.append({**candidates[0],**e})
        contacts=named
        field={'named_pitches':h.array(h.text(),len(contacts)),'roles':h.array(h.text(),len(contacts)),
            **bools('complete_source_order','clean_tone','separate_notes','controlled_crossing','no_stop_condition')}
        expect={'named_pitches':[e['printed_note'] for e in contacts],'roles':[e['role'] for e in contacts],
            **true('complete_source_order','clean_tone','separate_notes','controlled_crossing','no_stop_condition')}
        if picks is not None:field['pick_sequence']=h.array(h.menu(['D','U']),len(picks));expect['pick_sequence']=picks
        if 'accent_event_orders' in s:
            field['accent_event_orders']=h.array(h.integer(1,len(events)),len(s['accent_event_orders']));expect['accent_event_orders']=s['accent_event_orders']
        for duty in extra or []:field[duty]=h.boolean();expect[duty]=True
        node=add('source_'+str(i+1),s['action'].replace('_',' ')+'. Preserve its complete retained source guidance; report only after the coherent physical phrase. Source clock remains unknown.',field,expect,next_node,True,i)
        node['source_contacts_ref']=['events']
        return node
    for i,s in enumerate(c['steps'][1:],1):
        action=s['action'];name='source_'+str(i+1);next_node='source_'+str(i+2) if i+1<len(c['steps']) else 'end_cell'
        if action=='explicit_learner_release_of_final_tonic_sustain':
            # The native pending release immediately after source3 is exactly this
            # source action. No second acknowledgement or fabricated timed sustain.
            nodes['source_3']['next']=next_node
            nodes['source_3']['release_source_action_ref']=binding(i)
            nodes['source_3']['held_until_owned_release']=True
            continue
        if action.startswith('user_report_alternate_note_separation_reliable'):
            add(name,'Before economy, explicitly report reliable alternate-picking note separation. Unknown/negative terminates this pass; fresh retry starts at silent work, after owned release.',bools('alternate_separation_reliable','no_stop_condition'),true('alternate_separation_reliable','no_stop_condition'),next_node,source=i)
        elif action=='name_quality_using_third_seventh_and_changed_fifth':
            add(name,'Name quality from its third/seventh and changed fifth only when present. Do not add a locally unprinted b5 accent or an extra attack.',
                {'guide_roles':h.array(h.text(),2),'b5_confirms_quality':h.boolean(),'b5_locally_accented':h.boolean(),'no_extra_attack_or_accent':h.boolean()},
                {'guide_roles':s['guide_roles'],'b5_confirms_quality':s['b5_confirms_quality'],'b5_locally_accented':s['b5_is_locally_accented'],'no_extra_attack_or_accent':True},next_node,source=i)
        elif action.startswith('user_report') or action.startswith('name_ii_V_I'):
            duties={'source_duties_reported':h.boolean(),'no_stop_condition':h.boolean(),'limitations_note':h.text()}
            if s.get('comparison_conditions'):
                duties.update({n+'_unchanged':h.boolean() for n in s['comparison_conditions']})
            exp={n:True for n in duties if n!='limitations_note'}
            add(name,action.replace('_',' ')+'. This finishes only this selected cell; full source gate/session duties remain separate.',duties,exp,next_node,source=i)
        elif action=='perform_selected_guide_only_cadence_after_full_arpeggios':
            gs=s['guide_groups'];domain=[]
            for selected_order in choices:
                contacts=[]
                for group in gs:
                    guides=[e for e in group['members'] if e['role'] in ['3','b3','7','b7']]
                    third=next(e for e in guides if e['role'] in ['3','b3']);seventh=next(e for e in guides if e['role'] in ['7','b7'])
                    contacts.extend([third,seventh] if selected_order==choices[0] else [seventh,third])
                domain.append({'selection':{'guide_order':selected_order},'contacts':copy.deepcopy(contacts)})
            domains['minor_guide_followup']=domain
            node=add(name,'Re-enter your chosen global third/seventh order before the guide-only hearing test. The retained selection applies that same order to iiø, V and i. Six attacks are the retained chosen realization, not a printed count; strokes remain unknown.',
                {'guide_order':h.menu(choices)},{},name+'_perform',source=i)
            node['save_as']='followup_choice'
            node['constraints']=[g.guard('same_as_saved',left=g.ref('payload','guide_order'),right=g.ref('saved','guide_choice','guide_order')),g.guard('domain_lookup',domain='minor_guide_followup',selection={'guide_order':g.ref('payload','guide_order')})]
            node=add(name+'_perform','Perform only the chosen third and seventh of each chord after the full arpeggios. Report cadence audibility and no added scale tone; picking/timing are not fixed.',
                {'named_pitches':h.array(h.text(),6),'roles':h.array(h.text(),6),**bools('cadence_audible_from_guides','no_added_scale_tone','separate_notes','no_stop_condition')},
                true('cadence_audible_from_guides','no_added_scale_tone','separate_notes','no_stop_condition'),next_node,True,i)
            node['computed_expected']={'kind':'selected_domain_reports','domain':'minor_guide_followup','selection':{'guide_order':g.ref('saved','followup_choice','guide_order')},'fields':{'named_pitches':'printed_note','roles':'role'}}
        else:
            if 'event_orders' in s:contacts=[events[j-1] for j in s['event_orders']]
            elif 'question_event_orders' in s:contacts=[events[j-1] for j in s['question_event_orders']+s['answer_event_orders']]
            elif 'mirror' in s:contacts=s['mirror']
            elif 'events' in s:contacts=s['events'][1:]
            else:raise ValueError('UNSUPPORTED_SOURCE_ACTION:'+action)
            picks=s.get('picks',s.get('picking'))
            if 'mirror' in s:picks=[e['pick'] for e in s['mirror']]
            if 'events' in s:picks=[e['pick'] for e in contacts]
            extra=[]
            if any(n in s for n in ['preparatory_blocked_members','blocked_members','events']):extra+=['one_preparatory_blocked_chord','complete_spelling_before_block']
            if s.get('held_conditions'):extra += [n+'_unchanged' for n in s['held_conditions']]
            if action=='perform_two_continuous_seven_note_no_top_repeat_loops':extra+=['no_pause_between_two_loops','second_loop_opposite_stroke','no_top_repeat']
            if action=='perform_seven_ascending_four_tone_groups_naming_changed_quality_factor':extra+=['named_spelling_each_group','third_seventh_emphasis','changed_fifth_identified','root_fret_fixed','no_extra_local_accent_marks']
            if action=='perform_preparatory_initial_block_then_full_minor_cadence':extra+=['half_diminished_b5_clear','dominant_major_third_emphasized','tonic_b3_b7_settled','named_each_chord','no_unprinted_scale_tone']
            if action=='perform_four_tone_question_and_four_tone_answer_then_hold_final_tonic':extra+=['question_answer_rhythm_matched','held_final_tonic_until_release']
            node=performance(i,s,next_node,contacts,picks,extra)
            if 'one_factor_transitions' in s:
                factors=[x['factor'] for x in s['one_factor_transitions']]
                node['schema']['properties']['changed_factors']=h.array(h.text(),len(factors));node['schema']['required'].append('changed_factors');node['expected']['changed_factors']=factors
    nodes['end_cell']=g.end('user_reported_selected_cell_finished_only')
    return {'name':pname,'mode':'graph','steps':[],
        'graph':{'schema':'fathom.manual-procedure-graph.1','entry':'silent_work','nodes':nodes,'domains':domains,
            'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':'silent_work'},
            'call_semantics':'No inter-row calls in these44; continuous two seven-note loops stay one coherent physical report with no release/response between loops.',
            'loop_semantics':'Only the two source-written seven-note loops are one finite physical action; no automatic additional repetition.'},
        'learner_instruction_context_ref':{'original_record_paths':[['source_payload','label'],['implementation','source_scope','selected_source_text'],['implementation','context_tasks']],
            'original_contract_paths':[['physical_boundary','exact_text'],['source_required_practice_duty','exact_text']]},
        'source_facts':{'original_kind':kind,'source_clock':None,'fixed_bpm':None,'numeric_accent_strength':None,
            'printed_attacks':c['printed_attacks'],'printed_memberships':c['printed_memberships'],'main_cell_pick_policy':'Source null preserved; selected starter ALT is separate from main untimed framing/guide-only/ladder.'},
        'source_obligations_ref':{'original_contract_paths':[['required_silent_work'],['source_required_practice_duty']],
            'full_source_gate_or_session_completed':False,'cell_discharge_of_whole_gate':False},
        'hidden_self_check':None,'fixed_bpm':None,'performance_observed':False,'grants_credit':False,'automatic_mastery':False}

def build(root):
    start=time.perf_counter();root=Path(root).resolve();sr=(root/SELECTION).read_bytes()
    if hashlib.sha256(sr).hexdigest()!=SELECTION_SHA:raise ValueError('SELECTION_PIN')
    s=json.loads(sr);h,g=dependencies(root,s);cache={}
    def pinned(r):
        p=Path(r['path']);h.require(not p.is_absolute() and '..' not in p.parts,'RELATIVE_INPUT')
        full=root/p;h.require(full.resolve().is_relative_to(root) and not any(x.is_symlink() for x in [full,*full.parents]),'INPUT_ESCAPE')
        if r['path'] not in cache:cache[r['path']]=full.read_bytes()
        raw=cache[r['path']];h.require(h.sha(raw)==r['sha256'] and len(raw)==r['bytes'],'INPUT_PIN');return raw
    for r in [s['ledger'],s['current_descriptor'],s['c96_selection'],*s['cached_inputs'],*s['source_models'],*s['prior128']]:pinned(r)
    descriptor=h.strict(cache[s['current_descriptor']['path']]);accepted={x['selection']['package_key'] for x in descriptor['current_status_resolution']['operations'] if x['current_overlay']['status']=='Accepted'}
    rows=[];originals={};profiles=collections.Counter()
    for r in s['rows']:
        raw=pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw)
        h.require(r['key'] not in accepted and h.sha(raw)==r['original_row_sha256'] and o['package_key']==r['key'] and o['source_identity']==r['source_identity'] and o['unresolved_reasons']==[],'EXACT_PENDING_SOURCE_ROW')
        p=program(h,g,o);profiles[p['name']]+=1;originals[r['key']]=o
        rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],
            'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],
            'payload_ref':r['payload_ref'],'retained_contract_path':['implementation','manual_execution_contract'],
            'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,
            'qualification':'New44 candidate data, original witnesses by exact reference. No current224/native/installed/accepted or learner credit claim.'})
    h.require(len(rows)==44 and len(profiles)==7,'CLOSED44_SEVEN_PROGRAMS')
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},
        'keys':[r['source_key'] for r in rows],'contracts':{r['source_key']:r['contract_sha256'] for r in rows},
        'cached_witnesses':s['cached_inputs'],'source_models':s['source_models'],'profile_counts':dict(profiles),
        'contexts':{r['path']:h.strict(cache[r['path']]) for r in s['cached_inputs'] if r['path'].endswith('source-context.json')},
        'witness_storage':'Original record/contracts remain in immutable cached packets; do not duplicate into row program/header.',
        'operator_extension':{'kind':'selected_domain_reports','required_fields':['kind','domain','selection','fields'],'meaning':'Resolve closed finite selection, project exact retained contact list in order into typed report fields. Two initial guide contacts or six chosen minor follow-up contacts; no caller-authored contacts or invented strokes/clocks.'},
        'release_binding_extension':'Physical node optional release_source_action_ref accounts for original explicit sustain-release action through the required native owned release, not a second acknowledgement or timed release.',
        'native_execution':False,'runtime_admitted':False,'grants_credit':False}
    validate(rows,closure,originals,h,g)
    return rows,closure,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':len(cache),'rows':44,'source_programs':7,'graph_nodes':sum(len(r['program']['graph']['nodes']) for r in rows)},originals

def validate(rows,closure,originals,h,g):
    h.require(len(rows)==44 and [r['source_key'] for r in rows]==closure['keys'],'EXACT_KEYS')
    for r in rows:
        o=originals[r['source_key']];p=r['program'];graph=p['graph']
        h.require(p==program(h,g,o) and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'SOURCE_PROGRAM_BINDING')
        h.require('original_record' not in r and 'original_contract' not in p['source_facts'],'REFERENCE_WITNESSES_NOT_DUPLICATED')
        bound=set()
        for n in graph['nodes'].values():
            if n['kind']=='end':continue
            h.require(n['schema']['additionalProperties'] is False and set(n['schema']['required'])==set(n['schema']['properties']) and 'default' not in json.dumps(n['schema']),'BLANK_CLOSED_FORM')
            h.require(n['next'] in graph['nodes'],'FINITE_EDGE')
            if 'source_action_ref' in n:bound.add(n['source_action_ref']['original_contract_path'][1])
            if 'release_source_action_ref' in n:bound.add(n['release_source_action_ref']['original_contract_path'][1])
        h.require(bound==set(range(len(o['implementation']['manual_execution_contract']['steps']))),'COMPLETE_SOURCE_PHASES')
        h.require(p['grants_credit'] is False and p['performance_observed'] is False and p['fixed_bpm'] is None,'NO_AUTHORITY_OR_CLOCK')
    return True

def generate(root,out=OUT):
    rows,closure,metrics,_=build(root);s=json.loads((Path(root)/SELECTION).read_bytes());h,_=dependencies(root,s)
    target=Path(root)/out;h.require(not Path(out).is_absolute() and '..' not in Path(out).parts and target.resolve().is_relative_to(Path(root).resolve()),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False)
    files={'definitions.jsonl':b''.join(h.encoded(r)+b'\n' for r in rows),'family-closure.json':h.encoded(closure)+b'\n'}
    q=lambda v:json.dumps(v,ensure_ascii=False)
    header=['#pragma once','#include <array>','namespace fathom::tasks::manual_procedure_harmonic_generated {','struct Row { const char* key; const char* value; };','inline constexpr const char* closureSha256='+q(h.sha(h.encoded(closure)))+';','inline const std::array<Row,44> rows = {{']
    header+=['{'+q(r['source_key'])+','+q(h.encoded(r).decode())+'},' for r in rows];header+=['}};','}'];files['GeneratedManualProcedureHarmonic.hpp']=('\n'.join(header)+'\n').encode();pins=[]
    for name,raw in files.items():
        p=target/name;p.open('xb').write(raw);pins.append({'path':str(p.relative_to(Path(root))),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'CLOSED44_SOURCE_PHASE_DATA_PASS_FUTURE_NATIVE_PENDING','metrics':metrics,'files':pins,'source_program_profiles':closure['profile_counts'],'original_txt_pdf_reads':0,'native_paths_executed':0,'official_acceptance_increment':0}
    (target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);x=a.parse_args();print(json.dumps(generate(x.root,x.out)))
