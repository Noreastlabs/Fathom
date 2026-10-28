#!/usr/bin/env python3
"""Closed B20 readiness/audit/log DATA; source and native authority stay separate.

Reuses frozen A typed primitives, not its source-specific program constructor.
All fragments point into original B strings; headings/facts and conditional
error repairs are not unconditional performance criteria. No musical answers,
clock, source-kind conversion, per-key model or acceptance is generated.
"""
from pathlib import Path
import argparse,collections,copy,hashlib,importlib.util,json,re,time
BASE='Build/manager-resume-r03/manual-readiness20-r01'
SELECTION=BASE+'/selection-r01.json'
SELECTION_SHA='15c9daca9b24a3e64851783597e0b80386a6b6797a0510615ce0b7498f4b6bb8'
HELPER={'path':'Tools/exercise-family-compiler/compile_source_defined_assessments.py','bytes':48641,'sha256':'49a5b6ea51a92ada7cf98383fb400b6660f2f1eeb0a664748c5b15e70346f953'}
OUT=BASE+'/generated-r02'
ERROR_LABELS=[
 'G# OPTIONAL','F-G# RUSHES','Em / E BLUR','DIM ROOT LOST','G# OVERUSED','PICK RESET',
 'LOST FRAME','EARLY SHIFT','AUG2 COLLAPSE','WEAK LEADING TONE','RINGING STRING','FORM LOSS',
 'MODE NAME WITHOUT FUNCTION','INTERVAL RUN BECOMES SCALE','AUG2 RUSH','V7 SOUNDS MINOR','DIMINISHED CELL SOUNDS RANDOM','III+ SOUNDS UNSTABLE',
 'F LEAKS INTO ASCENT','G LEAKS INTO SYMMETRIC DESCENT','CLASSICAL DESCENT SOUNDS FORCED','D7 SOUNDS LIKE Dm7','Bm7 SOUNDS DIMINISHED','TONIC SOUNDS MAJOR',
 'WRONG F / F#','WRONG G / G#','NOISY SEAM','LATE DESTINATION','LOST TONIC','RIGID STRETCH',
 'MODE WITHOUT CHORD','LOST #4','LOST b6','ALTERED SOUP','WRONG MODE 7 NAME','INTERVAL FRET SEARCH',
 'LOST D7','LOST G#7','WRONG C SPELLING','SUB DOES NOT RESOLVE','DIRECT/SUB CONFUSION']

def helper(root):
    raw=(root/HELPER['path']).read_bytes();assert len(raw)==HELPER['bytes'] and hashlib.sha256(raw).hexdigest()==HELPER['sha256'],'HELPER_PIN'
    spec=importlib.util.spec_from_file_location('frozen_criterion_primitives',root/HELPER['path']);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);return h

def fragments(o):
    i=o['implementation'];path=['implementation','source_scope','selected_source_text'] if 'source_scope'in i else ['implementation','task','instructions'];body=i['source_scope']['selected_source_text']if 'source_scope'in i else i['task']['instructions'];begin=0
    # The legacy silent-audit task retained its entire page including separate
    # recognition answers. Only its exact audit subsection is this unit.
    if o['level']==52 and i['task']['label']=='Silent-formation audit':begin=body.index('Silent-formation audit\n')
    source=[];cursor=begin
    for line in body[begin:].splitlines():
        start=body.find(line,cursor);cursor=start+len(line)
        if not line.strip():continue
        points={0,len(line)}
        if line.startswith('MASTERY GATE: '):points.add(len('MASTERY GATE: '))
        for m in re.finditer(r'(?<!\d)\d+\.\s',line):points.add(m.start())
        error_points=[]
        for label in ERROR_LABELS:
            at=line.find(label+' ')
            if at>=0:points.add(at);error_points.append((at,label))
        points=sorted(points)
        for a,b in zip(points,points[1:]):
            while a<b and line[a].isspace():a+=1
            while b>a and line[b-1].isspace():b-=1
            if a==b:continue
            text=line[a:b];error=next((label for at,label in error_points if at==a),None)
            meta=bool(re.match(r'^(?:Guitar Exercises|Scale Exercises|NEXT\b|Standard tuning\b|Page \d|Mastery gate\b|MASTERY GATE BEFORE|Section (?:VI|VII|VIII|IX) mastery|Practice log\b|Completion audit\b|Section VI completion standard|Ten-phase|Eleven-phase|Written workload audit|Listening assignment|Ear-training passes|Silent-formation audit$|Form audit$|Date\b|TOTAL WRITTEN TONES)',text,re.I)) or text.isupper()
            meta=meta or text==i['task']['label']
            # Inventory/table numbers and printed tone totals are facts. They
            # remain readable source context, never a performed count gate.
            inventory=bool(re.match(r'^(?:[A-J] - |\d+ (?:compare|octave|leading|aug2|triad|dominant|diminished|zone|position|seam|lanes|sequence|zigzags|characteristic|tension|mode|E7b9|cadence|call/response|form comparisons|directional|raised-|progressions)|Formations?\b)',text))
            source.append({'text':text,'role':'conditional_error_repair'if error else 'source_metadata'if meta or inventory else 'source_criterion','error_label':error,'witness':{'kind':'original_record_span','original_record_path':path,'start':start+a,'end':start+b,'text_sha256':hashlib.sha256(text.encode()).hexdigest()}})
    assert source
    return body,source

def profile(o):
    label=o['implementation']['task']['label'];level=o['level']
    if level==54:return 'practical_voicing_form_audit'
    if label.startswith('Silent audit:'):return 'four_set_silent_formation_audit'
    if label=='Silent-formation audit':return 'top_string_silent_formation_first_attempt_audit'
    if level==52:return 'natural_triad_two_day_mastery'
    if level==53:return 'four_set_first_attempt_triad_mastery'
    if level==69 and 'workload'in label:return 'melodic_minor_workload_tempo_and_next_day_listening'
    return 'level'+str(level)+'_readiness_criteria_log'

def make_program(h,o):
    body,spans=fragments(o);kind=profile(o);criteria=[];metadata=[];repairs=[];joined=' '.join(x['text']for x in spans);cursor=0
    for span in spans:
        x={'literal':span['text'],'source_excerpt':{'start':cursor,'end':cursor+len(span['text']),'normalization':'single space between exact original fragments'},'source_span_refs':[span['witness']]};cursor+=len(span['text'])+1
        if span['role']=='conditional_error_repair':x['error_label']=span['error_label'];x['unconditional_gate']=False;repairs.append(x)
        elif span['role']=='source_metadata':x['role']='heading_inventory_or_context_fact';x['manual_gate']=False;metadata.append(x)
        else:x['id']='criterion_'+str(len(criteria)+1).zfill(3);criteria.append(x)
    # A single finite formation inventory is a source audit, not a header gate.
    if kind=='four_set_silent_formation_audit'and not criteria:
        x=metadata.pop(0);x.pop('role');x.pop('manual_gate');x['id']='criterion_001';criteria.append(x)
    assert criteria,'NO_SOURCE_DUTIES'
    nodes={};refs=[x['witness']for x in spans];first=criteria[0]['id'];all_tags=['source_extent',*[x['id']for x in criteria]]
    def report(instruction,fields,expected,next_node,source,**kwargs):
        n=h.report(instruction,fields,expected,next_node,[],**kwargs);n.pop('source_action_refs');n['source_span_refs']=copy.deepcopy(source);return n
    evidence={'source_extent_evidence':h.text(True,4096),'source_stop_or_tension':h.menu(['none_reported','reported_stop_or_tension','unknown'],True)}
    guard=[{'kind':'nonempty_trimmed_text','field':'source_extent_evidence','minimum':1,'maximum':4096}]
    nodes['work_mode']=h.choice('Choose whether to perform this source unit now or enter evidence from earlier manual sessions. Neither selection verifies performance, readiness or credit.','evidence_mode',['perform_source_now','report_prior_manual_sessions'],{'perform_source_now':{'next':'source_extent'},'report_prior_manual_sessions':{'next':'prior_extent'}})
    nodes['source_extent']=report('Perform the complete selected source extent before submitting. Retain every uninterrupted musical form, source-internal release/relocation, listening and stop condition. No notes, clock or answers are supplied. '+joined,copy.deepcopy(evidence),{'source_stop_or_tension':'none_reported'},first,refs,constraints=guard,physical=True,tag='source_extent')
    nodes['prior_extent']=report('Report evidence of the complete source extent across earlier manual sessions. This does not activate a new physical performance or establish mastery. '+joined,copy.deepcopy(evidence),{'source_stop_or_tension':'none_reported'},first,refs,constraints=guard,tag='source_extent')
    for index,x in enumerate(criteria):
        fields={'reported_outcome':h.menu(['reported_met','reported_not_met','unknown'],True),'manual_evidence':h.text(True,2048)};expected={'reported_outcome':'reported_met'};guards=[{'kind':'nonempty_trimmed_text','field':'manual_evidence','minimum':1,'maximum':2048}]
        x['quantities']=h.quantities(x['literal']);x['observed']=False
        for q in x['quantities']:
            # Source geometry, form size and a method's capability are not a
            # completion quantity. Only exact instructed acts are eligible.
            if q['role']!='manual_count_criterion' or not re.search(r'\b(?:play|perform|complete|pass|spell|identify|switch|map|use|record|sing|draw|form|arpeggiate|transform)\b',x['literal'],re.I):q['role']='source_fact';continue
            field=q['id']+'_reported_source_'+h.slug(q['unit']);fields[field]=h.integer();q['report_fields']=[field];q['report_scope']='Distinct units from this exact printed source duty, not repetitions or installed rows.'
            if q['comparison']=='exact':expected[field]=q['value']
            else:guards.append({'kind':q['comparison'],'field':field,'value':q['value']})
        if re.search(r'(?:two (?:separate |clean )?days|on two days)',x['literal'],re.I):
            for n in [1,2]:fields['date_'+str(n)]=h.text(True,10);fields['day_'+str(n)+'_evidence']=h.text(True,2048);guards.append({'kind':'nonempty_trimmed_text','field':'day_'+str(n)+'_evidence','minimum':1,'maximum':2048})
            guards.append({'kind':'distinct_dates','fields':['date_1','date_2']});x['two_separately_entered_dates']=True
        if 'record'in x['literal'].lower():fields['reported_recording_reference']=h.text(True,2048);guards.append({'kind':'nonempty_trimmed_text','field':'reported_recording_reference','minimum':1,'maximum':2048})
        nodes[x['id']]=report(x['literal']+' Enter your actual source-specific outcome and evidence. Unknown/unmet remains a failed criterion with retained diagnosis.',fields,expected,criteria[index+1]['id']if index+1<len(criteria)else'end_unit',x['source_span_refs'],constraints=guards,tag=x['id'],save=x['id'])
    extra=nodes[first]
    def field(name,s,expected=None):
        extra['schema']['properties'][name]=s;extra['schema']['required'].append(name)
        if expected is not None:extra['expected'][name]=expected
    def acknowledge(name):field(name,h.boolean(),True)
    def count(name,value,minimum=False):
        field(name,h.integer());extra['constraints'].append({'kind':'minimum'if minimum else 'maximum','field':name,'value':value})
        if not minimum:extra['expected'][name]=value
    if kind=='top_string_silent_formation_first_attempt_audit':
        count('reported_distinct_source_combinations',42)
        for quality in ['major','minor']:count('reported_'+quality+'_source_attempts',21);count('reported_'+quality+'_correct_first_attempts',18,True);extra['constraints'].append({'kind':'maximum','field':'reported_'+quality+'_correct_first_attempts','value':21})
        for name in ['spelling_and_G_B_e_degree_order_stated_before_shape','destination_looked_at_before_formation','formed_silently_then_released_then_blocked_verification','all_42_source_combinations_across_multiple_sessions']:acknowledge(name)
        field('reported_sessions',h.integer());extra['constraints'].append({'kind':'minimum','field':'reported_sessions','value':2})
    if kind=='four_set_silent_formation_audit':
        count('reported_source_formations',168)
        for name in ['all_four_source_string_sets','all_seven_natural_roots','both_source_qualities','all_three_source_inversions','formed_silently']:acknowledge(name)
    if kind=='four_set_first_attempt_triad_mastery':
        for family in ['G_B_e','D_G_B','A_D_G','E_A_D']:
            count('reported_'+family+'_distinct_attempts',42);count('reported_'+family+'_first_attempt_correct',30,True);extra['constraints'].append({'kind':'maximum','field':'reported_'+family+'_first_attempt_correct','value':42})
        count('reported_source_progressions',8);count('reported_source_capstones',2)
    if kind=='practical_voicing_form_audit':
        for name in ['named_source_roots','reported_triad_inversions','reported_omitted_strings']:
            field(name,{'type':'array','items':h.text(True,128),'minItems':1,'maxItems':128})
        acknowledge('all_selected_source_roots_and_fragments_covered');acknowledge('reduction_kept_harmonic_identity')
        # Length/coverage of the source voicing catalogue is not fabricated.
        extra['constraints'].append({'kind':'readiness_named_reports','fields':['named_source_roots','reported_triad_inversions','reported_omitted_strings']})
    two_days=bool(re.search(r'(?:two (?:separate |clean |recorded )?days|on two days)',joined,re.I))
    last=nodes[criteria[-1]['id']]
    if two_days:
        day_scope=[x['text']for x in spans if re.search(r'(?:two (?:separate |clean |recorded )?days|on two days)',x['text'],re.I)]
        last['source_two_day_scope_literals']=day_scope;last['instruction']+=' Two-day evidence applies only to these exact source clauses: '+' | '.join(day_scope)
        for n in [1,2]:last['schema']['properties']['source_gate_date_'+str(n)]=h.text(True,10);last['schema']['properties']['source_gate_day_'+str(n)+'_evidence']=h.text(True,2048);last['expected']['source_gate_day_'+str(n)+'_reported_clean']=True;last['schema']['properties']['source_gate_day_'+str(n)+'_reported_clean']=h.boolean();last['constraints'].append({'kind':'nonempty_trimmed_text','field':'source_gate_day_'+str(n)+'_evidence','minimum':1,'maximum':2048})
        last['schema']['required']=list(last['schema']['properties']);last['constraints'].append({'kind':'distinct_dates','fields':['source_gate_date_1','source_gate_date_2']})
    # Each retained log records learner values rather than filling source facts
    # into reported state. No source clock or numeric tempo authority is added.
    if 'Practice log'in joined or 'practice log'in joined or 'Date 'in joined:
        nodes['log']=report('Enter your manual practice log for this source unit. Date, focus, pick start, BPM, weak link and next target remain your own reports; unknown stays unresolved.',{'reported_log_date':h.text(True,10),'reported_log_focus':h.text(True,2048),'reported_log_pick_start':h.menu(['D','U','not_applicable'],True),'reported_log_bpm':{'type':['number','null'],'minimum':0,'maximum':10000,'input_role':'manual_report'},'reported_log_clean':h.boolean(),'reported_log_weak_link':h.text(True,2048),'reported_log_next_target':h.text(True,2048)},{},'end_unit',refs,tag='log',save='log')
        last['next']='log';all_tags.append('log')
    state_protocols=[];extensions={'source_span_binding','readiness_named_reports'}if kind=='practical_voicing_form_audit'else{'source_span_binding'}
    if kind=='melodic_minor_workload_tempo_and_next_day_listening':
        # The written tone inventory is not a performance quota. Listening on
        # the next day and three clean repetitions are actual source duties.
        nxt=last['next'];last['next']='workload_tempo';values=['hold_current_tempo','increase_after_three_clean_repetitions','reduce_route_to_one_tetrachord']
        ch=h.choice('Choose the printed workload rule explicitly. Add2 BPM only after3 clean repetitions at the current route length. If the wrong sixth or seventh appears twice, reduce to one tetrachord before changing tempo. Holding is allowed when no reduction is owed.','tempo_decision',values,{values[0]:{'next':'next_day_listening'},values[1]:{'next':'tempo_increase'},values[2]:{'next':'route_repair'}},reported_wrong_sixth_or_seventh_count=h.integer(),reported_clean_repetitions=h.integer(),prior_manual_bpm=h.integer(maximum=10000))
        ch['save_as']='workload_choice';ch['constraints']=[{'kind':'source_policy_reported','policy':'workload_route_tempo_choice','choice_field':'tempo_decision','error_count_field':'reported_wrong_sixth_or_seventh_count','clean_count_field':'reported_clean_repetitions','error_threshold':2,'increase_requires_clean_repetitions':3}];nodes['workload_tempo']=ch;extensions.add('workload_route_tempo_choice')
        nodes['tempo_increase']=report('Manually report prior/new BPM. The source change is exactly+2; there is no generated pulse.',{'prior_manual_bpm':h.integer(maximum=10000),'new_manual_bpm':h.integer(maximum=10000)},{},'next_day_listening',refs,constraints=[{'kind':'same_as_saved','left':h.ref('payload','prior_manual_bpm'),'right':h.ref('saved','workload_choice','prior_manual_bpm')},{'kind':'source_policy_reported','policy':'reported_bpm_delta','before_field':'prior_manual_bpm','after_field':'new_manual_bpm','minimum_delta':2,'maximum_delta':2}],tag='tempo_increase')
        nodes['route_repair']=report('Perform the printed one-tetrachord reduction before changing tempo. No tetrachord pitches or fixed new BPM are invented.',{'reduced_to_one_source_tetrachord':h.boolean(),'repair_evidence':h.text(True,2048)},{'reduced_to_one_source_tetrachord':True},'next_day_listening',refs,constraints=[{'kind':'nonempty_trimmed_text','field':'repair_evidence','minimum':1,'maximum':2048}],physical=True,tag='route_repair')
        nodes['next_day_listening']=report('Report the printed next-day unannounced recording identification, including the natural/harmonic/melodic upper tetrachords and symmetric/classical descents. Source answers and acoustic correctness are not supplied.',{'recorded_date':h.text(True,10),'listened_date':h.text(True,10),'unannounced_recording_references':{'type':'array','items':h.text(True,2048),'minItems':5,'maxItems':5},'reported_identifications':{'type':'array','items':h.text(True,256),'minItems':5,'maxItems':5},'all_five_reportedly_identified_by_ear':h.boolean()},{'all_five_reportedly_identified_by_ear':True},nxt,refs,constraints=[{'kind':'readiness_next_day_reports','before_field':'recorded_date','after_field':'listened_date','array_fields':['unannounced_recording_references','reported_identifications']}],tag='next_day_listening');extensions.add('readiness_next_day_reports');all_tags+=['tempo_increase','route_repair','next_day_listening']
        state_protocols.append({'kind':'source_workload_route_reduction_debt','activate_node':'workload_tempo','error_count_field':'reported_wrong_sixth_or_seventh_count','error_threshold':2,'unknown_retains_debt':True,'required_route_repair_node':'route_repair','source_extent':'one tetrachord; no generated notes','retain_across':['retry','cancel','navigation','restart'],'tempo_change_blocked_while_debt':True,'hold_cannot_clear_debt':True,'new_clock_or_bpm_reduction':None})
    nodes['end_unit']=h.end('source_criteria_reported_only_no_parent_mastery_or_credit')
    all_tags+=['source_repair_'+str(index+1)for index in range(len(repairs))];all_tags+=['workload_tempo']if kind=='melodic_minor_workload_tempo_and_next_day_listening'else[]
    nodes['repair_bind']=report('Bind the actual failed source criterion and your diagnosis. Successful source answers cannot replace that failed report.',{'failed_criterion':h.menu(all_tags),'diagnosis':h.text(True,2048)},{},'repair_choice',[],constraints=[{'kind':'same_as_failed_pass','payload_ref':h.ref('payload','failed_criterion')},{'kind':'nonempty_trimmed_text','field':'diagnosis','minimum':1,'maximum':2048}],save='repair')
    routes={'restart_complete_source_extent':{'next':'work_mode','native_protocol':'retry_from_entry'},'stop':{'next':'end_unit','native_protocol':'stop'}}
    for index,x in enumerate(repairs):
        id='source_repair_'+str(index+1);routes[x['error_label']]={'next':id};nodes[id]=report(x['literal']+' Perform only this explicitly selected source repair; it cannot discharge the original failed criterion or source gate.',{'repair_reported':h.boolean(),'manual_repair_evidence':h.text(True,2048)},{'repair_reported':True},'repair_choice',x['source_span_refs'],constraints=[{'kind':'nonempty_trimmed_text','field':'manual_repair_evidence','minimum':1,'maximum':2048}],physical=True,tag=id)
    nodes['repair_choice']=h.choice('Stop, explicitly restart the complete source extent, or select a printed source repair. No repair authorizes source completion; the failed criterion and physical release remain due.','repair_action',list(routes),routes)
    for n in nodes.values():n.pop('source_action_refs',None)
    return {'name':'b_'+kind,'mode':'graph','steps':[],'graph':{'schema':'fathom.manual-procedure-graph.1','entry':'work_mode','nodes':nodes,'domains':{},'failure_policy':{'terminal_current_pass':True,'diagnosis_required':True,'physical_failure_requires_release':True,'nonphysical_failure_activates_physical':False,'active_retry_stop_navigation_require_exit_release':True,'explicit_restart_entry':'work_mode','failed_pass_repair_entry':'repair_bind'},'call_semantics':'All exact source duties are manual evidence. Current performance and earlier sessions are explicitly separate. No generated source notes, clock or copied answers.','loop_semantics':'Selected printed repair may loop; it never discharges original failed criterion. Only explicit full restart with retained source debt/history.'},'source_kind':'manual_curriculum_task','source_task_kind':o['implementation'].get('interaction_contract',{}).get('source_task_kind','manual_readiness'), 'source_criteria':criteria,'source_metadata':metadata,'source_conditional_repairs':repairs,'source_literal_sha256':h.sha(joined.encode()),'source_literal_ref':{'source_span_witnesses':spans,'normalization':'single space between exact original fragments; headings and source facts nongating'},'source_state_protocols':state_protocols,'future_guard_extensions':sorted(extensions),'source_limits':['Counts/dates/listening/recordings/quality/names are learner declarations, not source performance observation or installed metadata.','All broader original parent/book/context duties remain source debt; this manual graph grants no readiness/mastery/credit.','Finite input bounds are private collection limits, not printed clock/tempo/count maxima unless an exact source criterion says so.','Conditional source repairs do not establish recovery or discharge original failed criteria; owned physical release and history must be preserved.'],'source_clock':None,'fixed_bpm':None,'sounding_span':None,'hidden_self_check':None,'performance_observed':False,'recording_observed':False,'automatic_mastery':False,'runtime_admitted':False,'original_kind_preserved':True,'grants_credit':False}

def data_guard(h,g,payload,saved=None,failed=None):
    kind=g['kind']
    if kind=='readiness_named_reports':
        h.require(set(g)=={'kind','fields'}and g['fields']==['named_source_roots','reported_triad_inversions','reported_omitted_strings'],'NAMED_REPORT_DESCRIPTOR')
        for key in g['fields']:
            values=payload[key];h.require(type(values)is list and 1<=len(values)<=128 and all(type(x)in[str,type(None)]for x in values),'NAMED_REPORT_TYPE')
            if any(x is None or not x.strip()for x in values):return False
        return True
    if kind=='readiness_next_day_reports':
        h.require(set(g)=={'kind','before_field','after_field','array_fields'}and g['before_field']=='recorded_date'and g['after_field']=='listened_date'and g['array_fields']==['unannounced_recording_references','reported_identifications'],'NEXT_DAY_DESCRIPTOR')
        import datetime
        values=[payload[g['before_field']],payload[g['after_field']]];h.require(all(type(x)in[str,type(None)]for x in values),'DATE_TYPES')
        if any(x is None or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x)for x in values):return False
        try:a,b=map(datetime.date.fromisoformat,values)
        except ValueError:return False
        if b-a!=datetime.timedelta(days=1):return False
        arrays=[payload[key]for key in g['array_fields']];h.require(all(type(x)is list and len(x)==5 and all(type(v)in[str,type(None)]for v in x)for x in arrays),'LISTENING_TYPES')
        return all(v is not None and bool(v.strip())for x in arrays for v in x)
    if kind=='source_policy_reported'and g.get('policy')=='workload_route_tempo_choice':
        h.require(set(g)=={'kind','policy','choice_field','error_count_field','clean_count_field','error_threshold','increase_requires_clean_repetitions'}and g['error_threshold']==2 and g['increase_requires_clean_repetitions']==3,'WORKLOAD_CHOICE_DESCRIPTOR')
        choice=payload[g['choice_field']];errors=payload[g['error_count_field']];clean=payload[g['clean_count_field']];h.require(choice in ['hold_current_tempo','increase_after_three_clean_repetitions','reduce_route_to_one_tetrachord']and type(errors)in[int,type(None)]and type(clean)in[int,type(None)],'WORKLOAD_CHOICE_TYPE')
        if errors is None or clean is None:return False
        if errors>=2:return choice=='reduce_route_to_one_tetrachord'
        return choice=='hold_current_tempo' or choice=='increase_after_three_clean_repetitions'and clean>=3 or choice=='reduce_route_to_one_tetrachord'
    return h.data_guard(g,payload,saved,failed)

def validate_payload(h,s,value):
    """Add exact finite-number DATA validation without changing frozen helper."""
    from decimal import Decimal
    types=s['type']if type(s['type'])is list else[s['type']]
    if value is None:h.require('null'in types,'REPORT_NULL');return
    if 'number'in types:
        h.require(type(value)is int or type(value)is Decimal,'FINITE_DECIMAL_TYPE');number=Decimal(value);h.require(number.is_finite(),'FINITE_DECIMAL');h.require(Decimal(s.get('minimum','-1e308'))<=number<=Decimal(s.get('maximum','1e308')),'FINITE_DECIMAL_RANGE');return
    if types==['object']:
        h.require(type(value)is dict and s['additionalProperties']is False and set(value)==set(s['required'])==set(s['properties']),'EXACT_REPORT_OBJECT')
        for k,v in value.items():validate_payload(h,s['properties'][k],v)
    elif types==['array']:
        h.require(type(value)is list and s['minItems']<=len(value)<=s['maxItems'],'REPORT_ARRAY')
        for v in value:validate_payload(h,s['items'],v)
    else:h.validate_payload(s,value)

def build(root):
    start=time.perf_counter();root=Path(root).resolve();h=helper(root);cache=h.Inputs(root);raw=(root/SELECTION).read_bytes();h.require(h.sha(raw)==SELECTION_SHA,'SELECTION_PIN');s=h.strict(raw)
    for r in [s['ledger'],s['current_descriptor'],*s['cached_inputs']]:cache.pinned(r)
    accepted={x['selection']['package_key']for x in h.strict(cache.pinned(s['current_descriptor']))['current_status_resolution']['operations']if x['current_overlay']['status']=='Accepted'};transferred=set()
    for ref in s['transferred_reservations']:
        x=h.strict(cache.pinned(ref));h.require(len(x['keys'])==x['key_count'],'TRANSFER_COUNT');transferred.update(x['keys'])
    h.require(len(transferred)==190,'EXACT190_TRANSFER');rows=[];originals={};profiles=collections.Counter()
    for r in s['rows']:
        raw=cache.pinned(r['payload_ref']).splitlines()[r['payload_ref']['jsonl_line']-1];o=h.strict(raw);h.require(h.sha(raw)==r['original_row_sha256']and h.sha(json.dumps(o,ensure_ascii=False,separators=(',',':')).encode())==r['original_compact_sha256']and o['package_key']==r['key']and o['source_identity']==r['source_identity']and o['implementation']['kind']=='manual_curriculum_task'and r['key']not in accepted|transferred,'EXACT_PENDING_SOURCE_ROW');originals[r['key']]=o;p=make_program(h,o);profiles[p['name']]+=1;rows.append({'schema':'fathom.manual-procedure-reference-definition.1','source_key':r['key'],'source_identity':r['source_identity'],'original_row_sha256':r['original_row_sha256'],'original_compact_sha256':r['original_compact_sha256'],'payload_ref':r['payload_ref'],'retained_contract_path':['implementation'],'source_pins':r['source_pins'],'context_ref':r['context_ref'],'contract_sha256':h.sha(h.encoded(p)),'program':p,'qualification':'Source-bound typed readiness/audit/log DATA only. Native named-report/next-day/workload policy, state/release/history, independent behavior/UI/package source review pending.'})
    closure={'schema':'fathom.manual-procedure-reference-closure.1','selection':{'path':SELECTION,'sha256':SELECTION_SHA},'shared_criterion_helper':HELPER,'keys':[x['source_key']for x in rows],'contracts':{x['source_key']:x['contract_sha256']for x in rows},'cached_witnesses':s['cached_inputs'],'contexts':{r['path']:h.strict(cache.pinned(r))for r in s['cached_inputs']if r['path'].endswith('source-context.json')},'source_kind':'manual_curriculum_task','source_program_profile_counts':dict(profiles),'profile_counts_are_not_behavior_equivalence':True,'denominator':{'indexed_pending_B_manual_rows':91,'selected_source_clear':20,'remaining_response_or_reference_rows':69,'isolated_L59_source_conflicts':2},'native_integration_debt':['Exact B manual_curriculum_task implementation reference closure; no source-kind substitution.','Source_span_refs may target selected_source_text or legacy task.instructions; only selected exact source unit is learner-visible.','Typed readiness_named_reports, readiness_next_day_reports and workload_route_tempo_choice closed guards.','Persistent route-reduction debt with source+owner token binding and retain/release semantics; current449 untouched.','Distinct source/native/behavior/UI/installed review; source facts versus performed reports; no mastery or credit.'],'native_execution':False,'runtime_admitted':False,'grants_credit':False};validate(h,rows,closure,originals)
    return rows,closure,originals,{'seconds':time.perf_counter()-start,'cached_files_hashed_once':cache.hashes,'rows':20,'profiles':dict(profiles),'source_criteria':sum(len(x['program']['source_criteria'])for x in rows),'graph_nodes':sum(len(x['program']['graph']['nodes'])for x in rows)}

def validate(h,rows,closure,originals):
    h.require(len(rows)==len({x['source_key']for x in rows})==20 and closure['keys']==[x['source_key']for x in rows],'EXACT20')
    for r in rows:
        p=r['program'];h.require(p==make_program(h,originals[r['source_key']])and h.sha(h.encoded(p))==r['contract_sha256']==closure['contracts'][r['source_key']],'EXACT_SOURCE_PROGRAM');h.require(r['retained_contract_path']==['implementation']and p['source_kind']=='manual_curriculum_task'and not p['grants_credit']and not p['runtime_admitted']and p['source_clock']is None,'NO_AUTHORITY_BROADENING')
        nodes=p['graph']['nodes'];h.require(nodes['source_extent']['physical']is True and nodes['prior_extent']['physical']is False,'EXPLICIT_EVIDENCE_SCOPE');h.require(all(x['manual_gate']is False for x in p['source_metadata'])and all(not x['unconditional_gate']for x in p['source_conditional_repairs']),'FACTS_NOT_GATES')
        for n in nodes.values():
            if n['kind']=='end':continue
            h.require(n['schema']['additionalProperties']is False and set(n['schema']['properties'])==set(n['schema']['required'])and 'default'not in json.dumps(n['schema']),'CLOSED_BLANK_TYPED_FIELDS')
            if n['kind']=='report':h.require(n['next']in nodes,'CLOSED_NEXT')
            else:h.require(set(n['routes'])==set(n['schema']['properties'][n['route_field']]['enum'])and all(x['next']in nodes for x in n['routes'].values()),'CLOSED_ROUTES')
    return True

def generate(root,out=OUT):
    root=Path(root).resolve();rows,closure,_,metrics=build(root);h=helper(root);target=root/out;h.require(not Path(out).is_absolute()and '..'not in Path(out).parts and target.resolve().is_relative_to(root),'OUTPUT_PATH');target.mkdir(parents=True,exist_ok=False);files=[]
    for name,raw in {'definitions.jsonl':b''.join(h.encoded(x)+b'\n'for x in rows),'family-closure.json':h.encoded(closure)+b'\n'}.items():(target/name).open('xb').write(raw);files.append({'path':str((target/name).relative_to(root)),'bytes':len(raw),'sha256':h.sha(raw)})
    result={'outcome':'20_CLOSED_READINESS_SOURCE_DATA_NATIVE_PENDING','metrics':metrics,'files':files,'source_PDF_or_TXT_reads':0,'native_executed':0,'official_acceptance_increment':0};(target/'generation-receipt.json').open('x').write(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--root',required=True);a.add_argument('--out',default=OUT);args=a.parse_args();print(json.dumps(generate(args.root,args.out)))
