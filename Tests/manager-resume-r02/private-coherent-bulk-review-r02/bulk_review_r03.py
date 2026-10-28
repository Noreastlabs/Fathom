"""Distinct source/behavior QA; only execute after coordinator combined freeze.

Independent original-derived oracles and chord/contact fixtures; no producer test
imports. All playing/singing/physical-release statements below are synthetic.
"""
from copy import deepcopy
import datetime, hashlib, importlib.util, itertools, json
from pathlib import Path
import sys, time, traceback

ROOT=Path(__file__).resolve().parents[3]
LANE=Path('manager-resume-r02/private-coherent-bulk-review-r02')
checks=refusals=0
labels={}
def check(ok,label):
    global checks
    checks+=1
    if not ok: raise AssertionError(label)
def hash_bytes(b): return hashlib.sha256(b).hexdigest()
def canon(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def read(p): return json.loads((ROOT/p).read_text())
def pin(r):
    b=(ROOT/r['path']).read_bytes()
    check(len(b)==r['bytes'] and hash_bytes(b)==r['sha256'], 'frozen pin '+r['path'])
def module(p,name):
    s=importlib.util.spec_from_file_location(name,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def refuse(call,kind,exc,snapshot=None):
    global refusals
    before=deepcopy(snapshot()) if snapshot else None
    try: call()
    except exc as e:
        check(type(e) is exc,kind+' exact refusal identity')
        if snapshot:check(snapshot()==before,kind+' no mutation')
        refusals+=1;labels[kind]=labels.get(kind,0)+1
        return str(e)
    raise AssertionError('Expected refusal: '+kind)

TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
PC={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
QUALITY={'maj7':([0,4,7,11],['root','3','5','7']), 'm7':([0,3,7,10],['root','b3','5','b7']), '7':([0,4,7,10],['root','3','5','b7']), 'm7b5':([0,3,6,10],['root','b3','b5','b7'])}
def harmony(symbol):
    n=2 if len(symbol)>1 and symbol[1] in '#b' else 1
    note,q=symbol[:n],symbol[n:];root=(PC[note[0]]+(1 if note.endswith('#') else -1 if note.endswith('b') else 0))%12
    offsets,roles=QUALITY[q];return [(root+x)%12 for x in offsets],roles
def top_choice(f,midi=None):
    midi=72+PC[f.card['literal_top']] if midi is None else midi
    s,base=next((s,b) for s,b in reversed(list(TUNING.items())) if 0<=midi-b<=24)
    return {'key':f.key,'literal_top':f.card['literal_top'],'contact':{'string':s,'fret':midi-base,'midi':midi},'original_workbook':True,'own_instrument':True}
def expected_role(f):
    pcs,roles=harmony(f.current()['harmony']);return roles[pcs.index(PC[f.card['literal_top']])]
def plan(f):
    current=f.current();pcs,_=harmony(current['harmony']);stage=current['stage'];top=deepcopy(f.top)
    want=[PC[f.card['literal_top']]] if stage=='melody' else [pcs[0],PC[f.card['literal_top']]] if stage in ('root_melody','bass_melody_reduction') else [pcs[1],pcs[3],PC[f.card['literal_top']]] if stage=='shell_melody' else pcs.copy()
    want.remove(top['midi']%12)
    options=[[{'string':s,'fret':fre,'midi':b+fre} for s,b in TUNING.items() for fre in range(25) if s!=top['string'] and b+fre<top['midi'] and (b+fre)%12==pitch] for pitch in want]
    for combination in itertools.product(*options):
        contacts=list(combination)+[top]
        if len({c['string'] for c in contacts})!=len(contacts):continue
        if stage in ('root_melody','bass_melody_reduction') and min(contacts,key=lambda x:x['midi'])['midi']%12!=pcs[0]:continue
        return dict({k:current[k] for k in ('key','harmony','stage')},contacts=contacts,rationale='Explicit synthetic authored realization; not a source contact or performed sound.')
    raise AssertionError('No independent finite fixture: '+str(current))
def report(f):
    return dict({k:f.current()[k] for k in ('key','harmony','stage')},contacts=deepcopy(f.plan['contacts']),attack_counts=[1]*len(f.plan['contacts']),duties={k:'yes' for k in f.duties()},diagnosis='',notes='Synthetic manual declaration, no acoustic or physical observation.')
SING={'sung_before_voicing':'yes','notes':'Synthetic sung-before-voicing declaration.'}
def texture(f,collect=None,modify_report=None,role='correct'):
    def call(fn,*args):
        if collect is not None:collect.append(deepcopy(f))
        fn(f.token(),*args)
    call(f.sing_top,deepcopy(SING));call(f.choose_voicing,plan(f));call(f.name_role,{'role':expected_role(f) if role=='correct' else role,'notes':'Independent symbolic/manual role fixture.'})
    call(f.play,True);call(f.release,{'learner_released':True})
    r=report(f)
    if modify_report:modify_report(r)
    call(f.report,r)
    if f.state=='stage_reported':call(f.advance)
def audit_payload(f,unknown=False):
    keys=f.contract['audit_questions'];ans={k:'Manual source-specific judgment retained; no machine hearing.' for k in keys}
    if unknown:ans[keys[0]]=None
    return {'answers':ans,'notes':'Synthetic musical-choice audit.','diagnosis':'Unknown judgment requires a further explicit audit.' if unknown else ''}
def remaining(f,collect=None):
    count=0
    while f.state!='audit':
        if f.state=='need_additional':
            if collect is not None:collect.append(deepcopy(f))
            extra=next(h for h in f.contract['source_sibling_candidates'] if h not in f.card['source_harmonies'])
            f.choose_additional(f.token(),{'key':f.key,'harmony':extra,'rationale':'Explicit authored extra substitute, no new source identity.'})
        texture(f,collect);count+=1
        check(count<=20,'finite complete family walkthrough')
    if collect is not None:collect.append(deepcopy(f))
    f.audit(f.token(),audit_payload(f))
    if collect is not None:collect.append(deepcopy(f))
    f.finish(f.token())
    if collect is not None:collect.append(deepcopy(f))
    return count

def b_source(m,packet):
    family=m.Family(ROOT);oracle={r['package_key']:r for r in read('Build/'+str(LANE)+'/level053-original-oracle.json')}
    scope=read('Prompts/fullscope-private-b-r01/coherent-level053-moduleb-r04/exact-key-reservation.json')
    old_raw=(ROOT/m.PACKET).read_bytes().splitlines()
    old=[json.loads(x) for x in old_raw]
    rows=[json.loads(x) for x in (ROOT/packet['path']).read_text().splitlines()]
    check([r['package_key'] for r in rows]==scope['keys']==family.keys,'B all167 frozen ordered keys')
    check(m.REPRESENTATIVE not in family.keys,'installed representative excluded')
    for row,bound in zip(rows,scope['rows']):
        key=row['package_key'];o=oracle[key];c=family.contract(key);original=old[bound['one_based_payload_line']-1]
        check(hash_bytes(old_raw[bound['one_based_payload_line']-1])==bound['current_record_sha256'],'B current-row rawhash withoutnewline')
        check(hash_bytes(canon(family.bindings[key]))==bound['binding_canonical_sha256'],'B complete binding hash')
        check(row['source_identity']==c['source_identity']==o['source_identity']==bound['source_identity'],'B allkey original identity')
        for k in ('source_refs','source_payload','timing_authority','level','existing_parent_id'):check(row[k]==original[k],'B source/provenance unchanged '+k)
        for k in ('events','instructions','table_task','source_scope','context_tasks'):check(row['implementation'][k]==original['implementation'][k],'B original implementation/context '+k)
        check([v['fret'] for v in c['voices_low_to_high']]==o['frets'] and [v['string'] for v in c['voices_low_to_high']]==o['strings'],'B original contacts')
        check([v['printed_note'] for v in c['voices_low_to_high']]==o['literal_notes_low_to_high'],'B exact spellings')
        check([v['printed_degree'] for v in c['voices_low_to_high']]==o['degrees_low_to_high'],'B inversion degrees')
        check([v['derived_standard_tuning_midi'] for v in c['voices_low_to_high']]==o['derived_standard_tuning_midi'],'B independent pitch arithmetic')
        check([a['kind'] for a in c['actions']]==['blocked_triad','string_contact','string_contact','string_contact'] and [a['voices'] for a in c['actions'][1:]]==[[v] for v in c['voices_low_to_high']],'B samecontacts lowmiddlehigh')
        check(row['implementation']['manual_execution_contract']==c,'B actual frozen contract fullmatch')
        check(c['numeric_clock'] is c['bpm'] is c['acoustic_gates'] is None,'B absent clocks preserved')
        check(not any(c[k] for k in ['physical_reports_verified','performance_observed','automatic_assessment','persistence_or_attempt','grants_credit','runtime_admitted','official_child_accepted']),'B no unsupported acceptance')
        check(c['optional_authored_pulse_policy_reference']['execution_implemented_by_this_model'] is False,'B policy chosen reference only')
    family.load_packet(ROOT/packet['path'],packet['sha256']);check(True,'B model frozen packet wholeload')
    refuse(lambda:family.contract(m.REPRESENTATIVE),'B installed sibling guard',m.Refusal)
    for key in ['foreign','exercise-completeness-r01/level053/modulec/p007','']:
        refuse(lambda key=key:family.contract(key),'B foreign key',m.Refusal)
    return family
def b_do(t,kind,payload=None):return t.apply(t.capture(kind),t.expected_payload(kind) if payload is None else payload)
def b_complete(t,states=None):
    for kind in ['select','ready','respond','respond','respond','respond','release']:
        if states is not None:states.append(t)
        b_do(t,kind)
    check(t.snapshot()['phase']=='CLOSED' and t.snapshot()['outcome']=='USER_REPORTED_STEPS_FINISHED','B complete fouraction manual path')
    check(not t.snapshot()['performance_observed'] and not t.snapshot()['grants_credit'],'B finish manual only')
def b_behavior(m,family):
    for key in family.keys:b_complete(m.Task(family,family.contract(key)))
    # Each of24 set/quality/inversion classes; one root per class sufficient for ownership/order/retry matrix.
    representatives={}
    for key in family.keys:
        c=family.contract(key);representatives.setdefault((c['voices_low_to_high'][0]['string'],c['quality'],c['inversion']),c)
    check(len(representatives)==24,'B24 semantic equivalence classes')
    for c in representatives.values():
        t=m.Task(family,c)
        foreign=m.Task(family,c).capture('select')
        refuse(lambda:t.apply(foreign,{'mode':'source_order_only'}),'B foreign instance',m.Refusal,t.snapshot)
        refuse(lambda:b_do(t,'ready'),'B wrongstage ready',m.Refusal,t.snapshot)
        refuse(lambda:b_do(t,'release'),'B premature release',m.Refusal,t.snapshot)
        refuse(lambda:b_do(t,'select',{'mode':'even_pulse','bpm':120}),'B invented clock choice',m.Refusal,t.snapshot)
        stale=t.capture('select');b_do(t,'select')
        refuse(lambda:t.apply(stale,{'mode':'source_order_only'}),'B stale token',m.Refusal,t.snapshot)
        payload=t.expected_payload('ready');payload['outside_strings_muted_reported']=None
        refuse(lambda:b_do(t,'ready',payload),'B malformed manualchoice',m.Refusal,t.snapshot)
        payload=t.expected_payload('ready');payload['named_notes_low_to_high'][0]='C#' if payload['named_notes_low_to_high'][0]!='C#' else 'Db'
        b_do(t,'ready',payload)
        check(t.phase=='RELEASE' and t.pending=='RETRY_REQUESTED' and t.diagnosis is not None,'B failed setup diagnosed')
        refuse(lambda:b_do(t,'again',{}),'B retry cannot bypass physicalrelease',m.Refusal,t.snapshot)
        refuse(lambda:b_do(t,'release',{'released_completely_reported':1}),'B bool physicalrelease typed',m.Refusal,t.snapshot)
        b_do(t,'release');oldhistory=deepcopy(t.history);b_do(t,'again',{});check(t.history[:len(oldhistory)]==oldhistory,'B retry retains diagnosis history')
        b_complete(t)
        b_do(t,'reopen',{});b_do(t,'select');b_do(t,'ready')
        payload=t.expected_payload('respond');payload['action_order']=2
        refuse(lambda:b_do(t,'respond',payload),'B wrong action order',m.Refusal,t.snapshot)
        payload=t.expected_payload('respond');payload['action_order']=True
        refuse(lambda:b_do(t,'respond',payload),'B malformed bool action',m.Refusal,t.snapshot)
        payload=t.expected_payload('respond');payload['written_action']['voices'][0]['fret']+=1
        b_do(t,'respond',payload);check(t.pending=='RETRY_REQUESTED','B contact drift requires releaseandretry')
        b_do(t,'release');b_do(t,'again',{});b_complete(t)
        for response in ['unknown','needs_retry','stopped']:
            b_do(t,'again',{});b_do(t,'select');b_do(t,'ready');b_do(t,'respond',{'response':response})
            check(t.phase=='RELEASE' and t.pending==('CANCELLED' if response=='stopped' else 'RETRY_REQUESTED'),'B unknown/failure/stop truthfully retained')
            refuse(lambda:b_do(t,'reopen',{}),'B stopped recovery releasefence',m.Refusal,t.snapshot)
            b_do(t,'release');before=deepcopy(t.history);b_do(t,'again',{});b_complete(t);check(t.history[:len(before)]==before,'B same task completes after failed declaration')
        for kind in ['cancel','navigate']:
            b_do(t,'again',{});b_do(t,'select');b_do(t,'ready');b_do(t,kind,{})
            refuse(lambda:b_do(t,'again',{}),'B cancelled releasefence',m.Refusal,t.snapshot)
            b_do(t,'release');b_do(t,'reopen',{});b_complete(t)
    return {'all_key_legal_paths':167,'equivalence_classes':24}

def c_source(m,packet):
    oracle=read('Build/'+str(LANE)+'/level083-original-oracle.json');scope=read('Results/fullscope-private-c-r01/remaining-backlog-resume-r65/chosen-scope.json')
    original=(ROOT/scope['original_read_only_packet']['path']).read_bytes().splitlines(keepends=True)
    rows=[json.loads(x) for x in (ROOT/packet['path']).read_text().splitlines()];cards=m.cards()
    check([r['package_key'] for r in rows]==[r['package_key'] for r in oracle],'C all41 original orderedkeys')
    for row,o,card,s in zip(rows,oracle,cards,scope['rows']):
        raw=original[s['current_payload']['jsonl_line']-1];old=json.loads(raw)
        check(hash_bytes(raw)==s['current_raw_jsonl_line_sha256'],'C currentrow newlinehash')
        for k in ('package_key','source_identity','module','literal_top','source_harmonies','literal_roles'):check(card[k]==o[k],'C independent originalcard '+k)
        for k in ('source_refs','source_payload','timing_authority','field_limitations'):check(row[k]==old[k],'C immutable source/provenance '+k)
        task=row['implementation']['task'];check(task['table_fields']==old['implementation']['task']['table_fields'],'C printed exact table retained')
        behavior=task['fixed_top_behavior'];check(behavior['literal_top']==o['literal_top'] and behavior['source_harmonies']==o['source_harmonies'] and behavior['source_changing_roles']==o['literal_roles'],'C frozen behavior original literals')
        c=m.contract(row['package_key']);check(c['stages']==('melody','root_melody','shell_melody','full_voicing'),'C exact source stageorder')
        check(c['source_card']==card and c['complete_manual_contract'] is True,'C exact resolved current contract')
        for i,h in enumerate(o['source_harmonies']):
            pcs,roles=harmony(h);check(PC[o['literal_top']] in pcs,'C fixedtop independent pitch arithmetic')
            if o['module']=='C':check(o['literal_roles'][i]==roles[pcs.index(PC[o['literal_top']])],'C exact printedrole independent arithmetic')
        check(not row['contract_capabilities']['Accepted'] and not row['contract_capabilities']['native_valid'],'C no runtime/acceptance')
    for key in ['foreign','exercise-completeness-r01/level083/moduled/p011','']:
        refuse(lambda key=key:m.FixedTopFlow(key),'C foreign key',m.Refusal)
    return [r['package_key'] for r in oracle]

def c_behavior(m,keys):
    states=[];textures=0
    for key in keys:
        f=m.FixedTopFlow(key)
        f.set_top(f.token(),top_choice(f));n=remaining(f,states if key in [keys[0],keys[35]] else None);textures+=n
        check(n==(4 if f.card['module']=='AB' else 16),'C whole key all harmonies/textures')
        check(f.state=='completed' and f.harmonies[:len(f.card['source_harmonies'])]==f.card['source_harmonies'],'C complete original system')
        if f.card['module']=='C':check(len(f.harmonies)==4 and f.harmonies[3] not in f.card['source_harmonies'],'C extra substitute labeled chosen')
        check(f.history[-1]['data']=={'whole_workbook_complete':False,'performance_verified':False,'mastery_awarded':False,'learner_credit':False,'official_acceptance':False,'source_two_day14of16_gate_satisfied':False},'C no14of16 or hearing/masterycredit claim')
        check(f.learner_view()['source_clocks'] is None,'C source clocks unknown')
    # Wrong-stage all meaningful actions across each distinct AB/C legal state.
    unique={}
    for f in states:unique.setdefault((f.card['module'],f.state),f)
    for f in unique.values():
        calls={'set_top':(f.set_top,top_choice(f),('setup',)), 'sing_top':(f.sing_top,deepcopy(SING),('need_sing',)),
          'choose_voicing':(f.choose_voicing,{'key':f.key},('choose_voicing',)), 'name_role':(f.name_role,{'role':None,'notes':'Unknown.'},('need_role',)),
          'play':(f.play,True,('ready_play',)), 'release':(f.release,{'learner_released':True},('await_release','reopen_release')),
          'report':(f.report,{},('report',)), 'choose_additional':(f.choose_additional,{},('need_additional',)),
          'audit':(f.audit,audit_payload(f),('audit',)), 'diagnose':(f.diagnose,'Synthetic diagnosis.',('needs_retry','needs_reduction'))}
        for name,(fn,arg,valid) in calls.items():
            if f.state not in valid:refuse(lambda fn=fn,arg=arg:fn(f.token(),arg),'C wrongstage '+name,m.Refusal,lambda:deepcopy(f.__dict__))
        if f.state!='ready_finish':refuse(lambda:f.finish(f.token()),'C prematurefinish',m.Refusal,lambda:deepcopy(f.__dict__))
        if f.state!='stage_reported':refuse(lambda:f.advance(f.token()),'C stage/order advance',m.Refusal,lambda:deepcopy(f.__dict__))
        # Cancel every reachable legal state; reopen must require explicit release and retain owner/history.
        g=deepcopy(f);before=deepcopy(g.history);stale=g.token();g.cancel(g.token());g.reopen(g.token())
        refuse(lambda:g.release(stale,{'learner_released':True}),'C stale aftercancel',m.Refusal,lambda:deepcopy(g.__dict__))
        refuse(lambda:g.release(g.token(),{'learner_released':False}),'C physical release false',m.Refusal,lambda:deepcopy(g.__dict__))
        refuse(lambda:g.sing_top(g.token(),deepcopy(SING)),'C reopen releasefence',m.Refusal,lambda:deepcopy(g.__dict__))
        g.release(g.token(),{'learner_released':True});check(g.history[:len(before)]==before,'C cancel source/history retained')
    # Typed choices, same-MIDI alternative string, source-role unknowns and full recovery.
    for key in [keys[0],keys[35]]:
        f=m.FixedTopFlow(key);foreign=m.FixedTopFlow(key).token()
        refuse(lambda:f.set_top(foreign,top_choice(f)),'C foreign instance',m.Refusal,lambda:deepcopy(f.__dict__))
        for field,bad in [('key','foreign'),('literal_top','D' if f.card['literal_top']!='D' else 'C'),('own_instrument',1)]:
            p=top_choice(f);p[field]=bad;refuse(lambda p=p:f.set_top(f.token(),p),'C malformed top '+field,m.Refusal,lambda:deepcopy(f.__dict__))
        p=top_choice(f);p['contact']['fret']=True;refuse(lambda:f.set_top(f.token(),p),'C boolean fret',m.Refusal,lambda:deepcopy(f.__dict__))
        f.set_top(f.token(),top_choice(f));f.sing_top(f.token(),{'sung_before_voicing':'uncertain','notes':'Retained unknown singing.'})
        refuse(lambda:f.finish(f.token()),'C uncertain singing no finish',m.Refusal,lambda:deepcopy(f.__dict__))
        old=deepcopy(f.response_history);f.diagnose(f.token(),'Retry singing before forming any chord.');check(f.response_history==old,'C unknown singing history retained')
        f.sing_top(f.token(),deepcopy(SING));p=plan(f)
        for field,bad in [('key','foreign'),('stage','full_voicing'),('harmony','D7' if f.current()['harmony']!='D7' else 'Cmaj7')]:
            q=deepcopy(p);q[field]=bad;refuse(lambda q=q:f.choose_voicing(f.token(),q),'C wrongchoice '+field,m.Refusal,lambda:deepcopy(f.__dict__))
        q=deepcopy(p);q['contacts'][0]['midi']+=1;q['contacts'][0]['fret']+=1
        refuse(lambda:f.choose_voicing(f.token(),q),'C shifted fixedtop',m.Refusal,lambda:deepcopy(f.__dict__))
        f.choose_voicing(f.token(),p);f.name_role(f.token(),{'role':None,'notes':'Retained unknown chord role.'});f.play(f.token(),True)
        refuse(lambda:f.report(f.token(),{}),'C report cannot skiprelease',m.Refusal,lambda:deepcopy(f.__dict__))
        f.release(f.token(),{'learner_released':True});r=report(f);r['attack_counts'][0]=None;r['diagnosis']='Retained unknown role and contact attack.';f.report(f.token(),r)
        refuse(lambda:f.advance(f.token()),'C unknown role/count cannotadvance',m.Refusal,lambda:deepcopy(f.__dict__))
        old=deepcopy(f.response_history);f.diagnose(f.token(),'Repeat the same complete texture.');check(f.response_history==old,'C unknown role/count histories retained')
        remaining(f);check(f.state=='completed','C unknownrole/count recovery reaches completion')
        # Unknown audit recovery occurs after complete systems.
        a=m.FixedTopFlow(key);a.set_top(a.token(),top_choice(a))
        while a.state!='audit':
            if a.state=='need_additional':
                extra=next(h for h in a.contract['source_sibling_candidates'] if h not in a.card['source_harmonies'])
                for bad in [a.card['source_harmonies'][0],'foreign','B7' if a.card['literal_top']!='B' else 'D7']:
                    refuse(lambda bad=bad:a.choose_additional(a.token(),{'key':a.key,'harmony':bad,'rationale':'Synthetic.'}),'C malformed/duplicate extra',m.Refusal,lambda:deepcopy(a.__dict__))
                a.choose_additional(a.token(),{'key':a.key,'harmony':extra,'rationale':'Explicit additional source-compatible chosen substitute.'})
            texture(a)
        a.audit(a.token(),audit_payload(a,True));old=deepcopy(a.audit_history)
        refuse(lambda:a.finish(a.token()),'C unknown audit cannotfinish',m.Refusal,lambda:deepcopy(a.__dict__))
        a.diagnose(a.token(),'Repeat explicit source-choice audit.');check(a.state=='audit' and a.audit_history==old,'C audit retry retains completed system/history');a.audit(a.token(),audit_payload(a));a.finish(a.token())
        check(a.state=='completed','C unknownaudit complete recovery')
    # Low register impossible: entire chosen-register replacement, not fabricated low notes.
    f=m.FixedTopFlow(keys[0]);f.set_top(f.token(),top_choice(f,48));texture(f);f.sing_top(f.token(),deepcopy(SING));f.cannot_realize(f.token(),'No lower root in this chosen finite guitar register.')
    before=deepcopy(f.__dict__);choice=top_choice(f);choice['diagnosis']='Choose a feasible whole-attempt register and repeat all textures.';f.restart_top(f.token(),choice)
    check(f.history[:len(before['history'])]==before['history'] and f.response_history==before['response_history'],'C fullregister restart retains old responses/source')
    check(remaining(f)==4 and f.state=='completed','C fullregister recovery completes fourreplacement textures')
    # Lost melody must reduce, then repeat interrupted texture and finish.
    lost=m.FixedTopFlow(keys[0]);lost.set_top(lost.token(),top_choice(lost));texture(lost)
    def loss(r):r['duties']['melody_clear']='no';r['diagnosis']='Melody was lost; immediate bass+melody reduction required.'
    texture(lost,modify_report=loss);check(lost.state=='needs_reduction','C declared melodyloss requires reduction')
    original=deepcopy(lost);stage=lost.stage_index;lost.diagnose(lost.token(),'Reduce to bass+melody, then restore interrupted texture.');check(lost.current()['stage']=='bass_melody_reduction','C immediate reduction target')
    texture(lost);check(lost.stage_index==stage and not lost.recovery and lost.state=='need_sing','C reduction preserves interrupted stage')
    check(remaining(lost)==3 and lost.state=='completed','C melodyloss recovery all remaining textures complete')
    # Bounded causal negative: a register restart may not bypass declared immediate reduction.
    choice=top_choice(original);choice['diagnosis']='Try another register after declared lost melody.'
    refusal=refuse(lambda:original.restart_top(original.token(),choice),'C lostmelody restart cannotbypass reduction',m.Refusal,lambda:deepcopy(original.__dict__))
    return {'all_key_legal_paths':41,'complete_textures':textures,'distinct_legal_stage_classes':len(unique),'causal_reduction_restart_refusal':refusal}

def main():
    freeze=read(sys.argv[1]);out=ROOT/sys.argv[2]
    check(freeze['coordinator_behavior_release'] is True,'exact coordinator frozen behavior release')
    for r in freeze['inputs']:pin(r)
    results={};t0=time.perf_counter()
    for family_id,funcs in [('B167',(b_source,b_behavior)),('C41',(c_source,c_behavior))]:
        if family_id not in freeze.get('run_families',['B167','C41']):continue
        release=freeze['families'][family_id];m=module(release['model']['path'],'independent_'+family_id+'_r03')
        c0,r0=checks,refusals;start=time.perf_counter();sections={}
        state=None
        for name,fn in zip(('source_integrity','behavior'),funcs):
            try:
                value=fn(m,release['packet']) if name=='source_integrity' else fn(m,state)
                if name=='source_integrity':state=value
                sections[name]={'outcome':'PASS','details':value if name=='behavior' else None}
            except Exception as e:
                sections[name]={'outcome':'FAIL','error':type(e).__name__+': '+str(e),'traceback':traceback.format_exc()}
                if state is None:break
        results[family_id]={'decision':'Accept' if all(x['outcome']=='PASS' for x in sections.values()) and len(sections)==2 else 'Correct','sections':sections,'checks':checks-c0,'refusals':refusals-r0,'elapsed_seconds':time.perf_counter()-start,'model':release['model'],'packet':release['packet'],'refusal_identity':m.Refusal.__module__+'.'+m.Refusal.__qualname__}
    for r in freeze['inputs']:pin(r)
    report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'/root/private_source_bulk_review','phase':'independent B affected reviewer-driver correction r03','families':results,'checks':checks,'refusals':refusals,'refusal_criteria':labels,'elapsed_seconds':time.perf_counter()-t0,'source_preparation_reused_by_hash':freeze['source_preparation'],'inputs':freeze['inputs'],'synthetic_reports_are_observations':False,'official_runtime_acceptance_increments':0,'command':'PYTHONDONTWRITEBYTECODE=1 bundled-python '+str(Path(__file__).relative_to(ROOT))+' '+sys.argv[1]+' '+sys.argv[2]}
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['inputs','refusal_criteria']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
