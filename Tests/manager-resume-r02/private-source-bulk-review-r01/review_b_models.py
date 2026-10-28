"""Independent bounded behavior checks, called only after coordinator freeze."""
from copy import deepcopy
from source_oracles import I_NOTES,I_DEGREES,I_ROLES,I_CONTACTS,K_PAIRS,TUNING_INT,PC

def check_workflow(m,c,r,done,q,label):
    n=len(done)
    q.check(m.workflow_state(c,None,[])['state']=='AWAITING_SELECTION',label+' awaits explicit choice')
    for end in range(n+1):
        out=m.workflow_state(c,r,deepcopy(done[:end]))
        expected='USER_REPORTED_STEPS_FINISHED' if end==n else 'IN_PROGRESS'
        q.check(out['state']==expected,label+f' prefix{end}')
        q.check(out['grants_credit'] is False and out['performance_observed'] is False,label+' manual boundary')
        if end<n:q.check(out['next_step']['order']==end+1,label+' next-step order')
    for i in range(n):
        for response,state in [('stopped','STOPPED'),('needs_retry','NEEDS_RETRY')]:
            seq=deepcopy(done[:i])+[{'step':i+1,'response':response}]
            out=m.workflow_state(c,r,seq)
            q.check(out['state']==state and out['next_step'] is None,label+f' {response} at{i+1}')
            if i+1<n:
                q.refuse(lambda:m.workflow_state(c,r,seq+[done[i+1]]),m.Refusal,label+' continuation after terminal')
        for field,value in done[i].items():
            if type(value) is bool:
                seq=deepcopy(done[:i+1]);seq[-1][field]=False
                q.check(m.workflow_state(c,r,seq)['state']=='NEEDS_RETRY',label+' negative '+field)
                for malformed in [None]:
                    bad=deepcopy(done[:i+1]);bad[-1][field]=malformed
                    q.refuse(lambda:m.workflow_state(c,r,bad),m.Refusal,label+' typed/unknown '+field)
        bad=deepcopy(done[:i+1]);bad[-1]['credit_awarded']=True
        q.refuse(lambda:m.workflow_state(c,r,bad),m.Refusal,label+' hidden response credit')
    for i in range(n-1):
        bad=deepcopy(done);bad[i],bad[i+1]=bad[i+1],bad[i]
        q.refuse(lambda:m.workflow_state(c,r,bad),m.Refusal,label+' adjacent step reorder')
    for patch in [dict(package_key='foreign'),dict(contract_sha256='0'*64),dict(start_stroke=True),dict(start_stroke='X'),dict(bpm=120),dict(performance_observed=True)]:
        q.refuse(lambda:m.workflow_state(c,dict(r,**patch),[]),m.Refusal,label+' malformed or foreign selection')
    q.refuse(lambda:m.workflow_state(c,None,done[:1]),m.Refusal,label+' report without choice')

def run_i(m,rows,q):
    q.check(len(rows)==5,'I five records')
    for i,row in enumerate(rows):
        c=row['implementation']['manual_execution_contract'];label=f'I P{i+1}'
        events=c['ordered_contacts']
        q.check([e['printed_note'] for e in events]==I_NOTES,label+' original notes')
        q.check([e['degree'] for e in events]==I_DEGREES,label+' original degrees')
        q.check([e['role'] for e in events]==I_ROLES,label+' original PDF roles')
        q.check([(e['string'],e['fret']) for e in events]==I_CONTACTS[i],label+' exact original TAB contacts')
        q.check([e['order'] for e in events]==list(range(1,17)),label+' exact contact order')
        for e in events:
            q.check((TUNING_INT[e['string']]+e['fret'])%12==PC[e['printed_note']],label+' contact pitch arithmetic')
            q.check(e['onset_q'] is None and e['duration_q'] is None,label+' unknown clocks')
        for stroke in ['D','U']:
            r={'package_key':c['package_key'],'contract_sha256':m.digest(c),'start_stroke':stroke}
            plan=m.selection(c,r)
            q.check(len(plan['paired'])==16 and len(plan['variation_call'])==len(plan['variation_answer'])==8,label+' exact two eight-tone phrases')
            q.check([e['selected_pick'] for e in plan['paired']]==list(('DU' if stroke=='D' else 'UD')*8),label+' chosen picking')
            q.check(plan['variation_answer'][-1]['order']==16 and plan['variation_answer'][-1]['printed_note']=='A',label+' existing finalA')
            q.check(plan['silent_gap']['source_beats']==2 and plan['silent_gap']['duration_q'] is None and plan['silent_gap']['seconds'] is None,label+' gap stays unscheduled')
        r['start_stroke']='D'
        done=[{'step':1,'response':'acknowledged','ordered_names':['A-minor call','E-dominant answer -> A'],'prepared_safely_reported':True},
          {'step':2,'response':'acknowledged','complete_printed_pair_played_reported':True},
          {'step':3,'response':'acknowledged','eight_contact_call_played_reported':True},
          {'step':4,'response':'acknowledged','silent_source_beats':2,'internal_bar_count_continued_reported':True},
          {'step':5,'response':'acknowledged','eight_contact_answer_ended_on_existing_A_reported':True},
          {'step':6,'response':'acknowledged',**dict.fromkeys(['minor_call_dominant_answer_distinguished_reported','rhythmic_identity_preserved_reported','two_silent_beats_counted_with_internal_bar_count_reported','final_A_completed_answer_without_extra_attack_reported','final_A_released_reported','source_safety_followed_reported'],True)}]
        check_workflow(m,c,r,done,q,label)
        mutations=[lambda x:x['ordered_contacts'].pop(),lambda x:x['ordered_contacts'][0].update(duration_q=1),
          lambda x:x['ordered_contacts'][0].update(string=True),lambda x:x['ordered_contacts'][0].update(fret=True),
          lambda x:x['ordered_contacts'][0].update(printed_note='B'),lambda x:x.update(grants_credit=True),
          lambda x:x.update(performance_observed=True),lambda x:x['steps'][3]['gap'].update(seconds=1),
          lambda x:x['steps'][4].update(additional_final_A_attack=True)]
        for mut in mutations:
            bad=deepcopy(c);mut(bad);q.refuse(lambda:m.validate_contract(bad),m.Refusal,label+' source/schema corruption')

def run_k(m,rows,q):
    q.check(len(rows)==12,'K twelve records')
    for i,row in enumerate(rows):
        c=row['implementation']['manual_execution_contract'];pair=K_PAIRS[i];label=f'K card{i+1}'
        q.check(c['printed_label']==f'{pair[0]}: {pair[1]} -> {pair[2]}',label+' exact source pitches')
        q.check(c['printed_roles']==f'{pair[3]} -> {pair[4]}',label+' exact function spelling')
        q.check([e['printed_note'] for e in c['source_pitch_events']]==list(pair[1:3]),label+' ordered source pair')
        q.check(all(e[f] is None for e in c['source_pitch_events'] for f in ['onset_q','duration_q','string','fret']),label+' original contact/clock unknowns')
        origins=[{'string':s,'fret':f} for s,base in sorted(TUNING_INT.items()) for f in range(25) if (base+f)%12==PC[pair[1]]]
        destinations=[{'string':s,'fret':f} for s,base in sorted(TUNING_INT.items()) for f in range(25) if (base+f)%12==PC[pair[2]]]
        q.check(c['source_contact_menu']==origins,label+' complete authored finite menu')
        for origin in origins:
            midi=TUNING_INT[origin['string']]+origin['fret']
            distance=min(abs(TUNING_INT[t['string']]+t['fret']-midi) for t in destinations)
            targets=[t for t in destinations if abs(TUNING_INT[t['string']]+t['fret']-midi)==distance]
            q.check(m.nearest_targets(origin,pair[2])==targets,label+' independently derived nearest menu including ties')
        origin=origins[len(origins)//2]
        target=m.nearest_targets(origin,pair[2])[0]
        for stroke in ['D','U']:
            r={'package_key':c['package_key'],'contract_sha256':m.digest(c),'source_contact':origin,'target_contact':target,'start_stroke':stroke,'rest_of_bar_plan':'Manually keep the existing pulse and simplify the remaining phrase.'}
            plan=m.selection(c,r)
            q.check(len(plan['chosen_pair'])==2 and [e['selected_pick'] for e in plan['chosen_pair']]==list('DU' if stroke=='D' else 'UD'),label+' chosen pair')
            q.check(plan['remainder_notes_or_attacks_generated'] is False and plan['grants_credit'] is False,label+' no invented remainder or credit')
        done=[{'step':1,'response':'acknowledged','printed_label':c['printed_label'],'printed_roles':c['printed_roles'],'target_named_before_origin_reported':True,'existing_bar_and_pulse_prepared_reported':True,'chosen_contacts_safe_and_secure_reported':True},
          {'step':2,'response':'acknowledged','chosen_origin_played_reported':True},
          {'step':3,'response':'acknowledged','chosen_named_target_reached_preserving_pulse_reported':True},
          {'step':4,'response':'acknowledged','rest_of_bar_plan':r['rest_of_bar_plan'],'rest_of_existing_bar_simplified_reported':True},
          {'step':5,'response':'acknowledged',**dict.fromkeys(['chosen_target_secure_reported','pulse_preserved_reported','named_destination_heard_reported','two_selected_pair_contacts_played_reported','rest_of_existing_bar_simplified_reported','final_target_released_reported','source_safety_followed_reported'],True)}]
        check_workflow(m,c,r,done,q,label)
        bad=dict(r,source_contact={'string':True,'fret':0});q.refuse(lambda:m.selection(c,bad),m.Refusal,label+' bool string')
        bad=dict(r,rest_of_bar_plan=' ');q.refuse(lambda:m.selection(c,bad),m.Refusal,label+' no remainder plan')
        far=next((t for t in destinations if t not in m.nearest_targets(origin,pair[2])),None)
        if far is not None:q.refuse(lambda:m.selection(c,dict(r,target_contact=far)),m.Refusal,label+' farther chosen target')
        for field in ['grants_credit','performance_observed','numeric_clock']:
            bad=deepcopy(c);bad[field]=120 if field=='numeric_clock' else True
            q.refuse(lambda:m.validate_contract(bad),m.Refusal,label+' hidden metadata '+field)
