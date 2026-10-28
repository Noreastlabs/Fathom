from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r45')
s=importlib.util.spec_from_file_location('fillrole',R/'Tools'/L/'fill_role_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def refuse(f,fn,label):
    global refusals
    before=deepcopy(f.__dict__)
    try:fn()
    except m.Refusal:refusals+=1
    else:raise AssertionError('accepted '+label)
    check(f.__dict__==before,'atomic refusal '+label)
def plan():return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':80,
    'chosen_note_beats':[[i,8] for i in range(25,36)],'chosen_ending_beat':[9,2],
    'descriptions':{x:'Chosen '+x for x in m.DESCRIPTIONS}}
def ready():
    f=m.FillRoleFlow(m.KEY);f.set_plan(f.token(),plan());return f
def reporting(f):f.begin(f.token());f.end_take(f.token(),True);f.release(f.token(),True)
def response():return {'source_contacts':[{'source_order':i,'string':s,'fret':f,'played':'yes'} for i,(s,f) in enumerate(m.CONTACTS,1)],
    'common':dict.fromkeys(m.COMMON,'yes'),'notes':'Synthetic self-report; actual notes/timing not observed.'}
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'fill-role-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()];check(len(rows)==1,'one key');row=rows[0]
old=json.loads((R/'Build/fullscope-private-c-r01/level075-r33/role-contact-overlay.jsonl').read_text().splitlines()[3]);events=row['implementation']['events'];c=row['implementation']['task']['contract']
for field in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[field]==old[field],'immutable '+field)
check(events==old['implementation']['events'],'eleven event objects unchanged')
check([(e['string'],e['fret']) for e in events]==[('G',4),('G',5),('G',7),('B',5),('B',6),('B',8),('e',5),('e',7),('e',8),('e',7),('e',5)],'independent contact order')
check([e['midi'] for e in events]==[59,60,62,64,65,67,69,71,72,71,69],'independent standard-tuning MIDI')
for e in events:
    check(e['onset_q'] is None and e['duration_q'] is None and e['sounded_duration_q'] is None and e['is_rest'] is False,'source timing/gates/rest unchanged')
check(c['source_target'] is None and c['source_role_mapping'] is None,'no borrowed target/context truncation')
check(c['source_instruction']=='fill begins after beat 3' and c['source_context_header']=='8 ROLE CELLS | 128 CONTACTS','source literal obligations')
check(len(c['source_role_context'])==5 and len(c['source_contacts'])==11,'context2–4answer does not truncate eleven-note fill')
for k in ('automatic_evaluation','performance_observed','source_fixed_timing','audio_supplied','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
f=ready();p=plan();f.set_plan(f.token(),p);p['chosen_note_beats'][0][0]=0;check(f.plan['chosen_note_beats'][0]==[25,8],'plan deep custody')
t=f.token();f.begin(t);refuse(f,lambda:f.begin(t),'duplicate begin');refuse(f,lambda:f.report(f.token(),response()),'early report')
refuse(f,lambda:f.release(f.token(),True),'end bypass');refuse(f,lambda:f.set_plan(f.token(),plan()),'active plan');refuse(f,lambda:f.end_take(f.token(),False),'ongoing take')
f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response()),'release bypass');refuse(f,lambda:f.release(f.token(),1),'release exact true')
f.release(f.token(),True);t=f.token();r=response();f.report(t,r);r['source_contacts'][0]['played']='no';check(f.history[-1]['data']['response']['source_contacts'][0]['played']=='yes','reply custody')
check(f.history[-1]['data']['performance_verified'] is False and f.history[-1]['data']['automatic_score'] is False,'manual not acoustic outcome')
refuse(f,lambda:f.report(t,response()),'duplicate report');f.finish(f.token());check(f.state=='completed','manual completion')
history=deepcopy(f.history);p=plan();p['bpm']=86;f.set_plan(f.token(),p);check(f.state=='ready' and f.cycle==0 and f.history[:len(history)]==history,'plan reset with history')
for target in m.COMMON:
    for outcome in ('no','uncertain'):
        g=ready();reporting(g);r=response();r['common'][target]=outcome;g.report(g.token(),r);check(g.state=='needs_retry','negative common')
        refuse(g,lambda:g.finish(g.token()),'negative finish');g.retry(g.token(),'Adjust chosen realization');check(g.state=='ready','explicit retry')
for i in range(11):
    for outcome in ('no','uncertain'):
        g=ready();reporting(g);r=response();r['source_contacts'][i]['played']=outcome;g.report(g.token(),r)
        check(g.state=='needs_retry','negative contact');refuse(g,lambda:g.finish(g.token()),'unplayed contact finish')
mutations=[]
for v in (0,-1,True,'80',None,float('inf'),float('nan')):mutations.append(('tempo',lambda p,v=v:p.update(bpm=v)))
for k in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,k=k:p['prerequisites'].update({k:False})))
for k in m.DESCRIPTIONS:mutations.append(('description',lambda p,k=k:p['descriptions'].update({k:''})))
mutations.extend([('short source',lambda p:p['chosen_note_beats'].pop()),('extra source',lambda p:p['chosen_note_beats'].append([35,8])),
    ('start exactly3',lambda p:p['chosen_note_beats'].__setitem__(0,[3,1])),('before3',lambda p:p['chosen_note_beats'].__setitem__(0,[2,1])),
    ('duplicate onset',lambda p:p['chosen_note_beats'].__setitem__(1,p['chosen_note_beats'][0])),('reversed',lambda p:p['chosen_note_beats'].reverse()),
    ('finish equalslast',lambda p:p.update(chosen_ending_beat=[35,8])),('finish after5',lambda p:p.update(chosen_ending_beat=[6,1]))])
for v in ([1,0],[1,-2],[True,2],[1,True],[3.5,1],['7',2],[1],[1,2,3],None):
    mutations.append(('note rational',lambda p,v=v:p['chosen_note_beats'].__setitem__(0,v)))
    mutations.append(('end rational',lambda p,v=v:p.update(chosen_ending_beat=v)))
for label,mutate in mutations:
    g=ready();p=plan();mutate(p);refuse(g,lambda:g.set_plan(g.token(),p),label)
for beats,end in (([[i,8] for i in range(25,36)],[5,1]),([[i,16] for i in range(49,60)],[4,1]),([[i*2,16] for i in range(25,36)],[9,2])):
    g=ready();p=plan();p['chosen_note_beats']=beats;p['chosen_ending_beat']=end;g.set_plan(g.token(),p)
    check(g.plan['chosen_note_beats']==beats,'alternative rational choices not source grid')
g=ready();reporting(g);mutations=[('notes',lambda r:r.update(notes='')),('short source',lambda r:r['source_contacts'].pop()),
    ('extra target',lambda r:r['source_contacts'].append(deepcopy(r['source_contacts'][-1]))),('enum',lambda r:r['common'].update(space_before_fill=True)),
    ('missing duty',lambda r:r['common'].pop('started_after_beat_three'))]
for i in range(11):
    mutations.extend([('source order',lambda r,i=i:r['source_contacts'][i].update(source_order=0)),('bool order',lambda r,i=i:r['source_contacts'][i].update(source_order=True)),
      ('wrong string',lambda r,i=i:r['source_contacts'][i].update(string='D')),('wrong fret',lambda r,i=i:r['source_contacts'][i].update(fret=0)),
      ('boolean fret',lambda r,i=i:r['source_contacts'][i].update(fret=True)),('reply',lambda r,i=i:r['source_contacts'][i].update(played='maybe'))])
for label,mutate in mutations:
    r=response();mutate(r);refuse(g,lambda:g.report(g.token(),r),label)
for state in ('setup','ready','performing','await_release','reporting','reported','needs_retry','completed'):
    h=m.FillRoleFlow(m.KEY)
    if state!='setup':h.set_plan(h.token(),plan())
    if state in ('performing','await_release','reporting','reported','needs_retry','completed'):h.begin(h.token())
    if state in ('await_release','reporting','reported','needs_retry','completed'):h.end_take(h.token(),True)
    if state in ('reporting','reported','needs_retry','completed'):h.release(h.token(),True)
    if state in ('reported','needs_retry','completed'):
        r=response()
        if state=='needs_retry':r['common']['space_before_fill']='uncertain'
        h.report(h.token(),r)
    if state=='completed':h.finish(h.token())
    check(h.state==state,'fixture state');history=deepcopy(h.history);p=deepcopy(h.plan);t=h.token();h.cancel(t)
    refuse(h,lambda:h.cancel(t),'duplicate cancel');h.reopen(h.token());h.cancel(h.token());h.reopen(h.token());refuse(h,lambda:h.begin(h.token()),'reopen release bypass')
    h.release(h.token(),True);target='ready' if state in ('performing','await_release','reporting') else state
    check(h.state==target and h.plan==p and h.history[:len(history)]==history,'cancel/reopen custody and repeat')
g=ready();foreign=ready();refuse(g,lambda:g.begin(foreign.token()),'foreign instance');t=g.token();g.set_plan(g.token(),plan());refuse(g,lambda:g.begin(t),'stale generation')
refuse(g,lambda:g.begin(list(g.token())),'token type');reporting(g);g.report(g.token(),response());refuse(g,lambda:g.retry(g.token(),''),'empty retry')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'fill_role_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
