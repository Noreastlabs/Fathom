from pathlib import Path
from copy import deepcopy
from fractions import Fraction
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r37')
s=importlib.util.spec_from_file_location('fill',R/'Tools'/L/'fill_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=0;refusals=0
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
def plan(index):
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':72,
        'chosen_note_beats':[[28+i,8] for i in range(11)],
        'spacing_rationale':'Synthetic chosen equal subdivisions from3.5 to4.75; not printed source timing.',
        'target_choice':{'source_pitch_class':m.TARGETS[index],'string':'e','fret':(8,5,10,3)[index],
                         'register_rationale':'Learner chosen register, not printed target fret.'}}
def ready(index):
    f=m.FillFlow(m.KEYS[index]);f.set_plan(f.token(),plan(index));return f
def reporting(f):f.begin(f.token());f.release(f.token(),True)
def response(f):
    return {'source_contacts':[{'source_order':i,'played':'yes'} for i in range(1,12)],
        'target_report':{'source_pitch_class':m.TARGETS[f.index],'matched':'yes'},
        'obligations':dict.fromkeys(m.OBLIGATIONS,'yes'),'notes':'Synthetic manual report only.'}
def pin(p):
    b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
allbase=[json.loads(x) for x in (R/basepath).read_text().splitlines()];lines=[27,30,28,29]
packet=Path('Build')/L/'fill-resolution-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
check(pin(source['frozen_parser']['path'])==source['frozen_parser'],'frozen parser exact')
expected=[('G',4,59),('G',5,60),('G',7,62),('B',5,64),('B',6,65),('B',8,67),
          ('e',5,69),('e',7,71),('e',8,72),('e',7,71),('e',5,69)]
check(len(rows)==4 and [r['package_key'] for r in rows]==list(m.KEYS),'four exact existing keys')
for index,row in enumerate(rows):
    old=allbase[lines[index]-1];c=row['implementation']['task']['contract'];events=row['implementation']['events']
    for field in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
        check(row[field]==old[field],'original '+field)
    check(old['implementation']['events']==[] and len(events)==11,'recovered omission only')
    block=source['matched_cells'][index]['original_full_block'].splitlines()
    for i,(e,oracle) in enumerate(zip(events,expected),1):
        check((e['string'],e['fret'],e['midi'])==oracle,'independent literal/MIDI vector')
        check(e['source_order']==e['attack_group']==i,'ordered single contacts')
        check(all(e[x] is None for x in ('onset_q','duration_q','sounded_duration_q','finger')),'no printed timing/gate/finger invented')
        body=block[e['source_line_in_region']-1].split('|')[1];col=e['source_column_zero_based']
        check(body[col:col+e['source_token_width']]==str(e['fret']),'line relative to retained exact label block')
        check(not e['is_rest'] and e['kind']=='pitched_string_contact','pitched source contacts')
    check(c['source_resolution_target']['pitch_class']==m.TARGETS[index],'exact source resolution')
    check(all(c['source_resolution_target'][x] is None for x in ('octave','string','fret')),'target realization remains unprinted')
    check(c['source_instruction']=='fill begins after beat 3' and c['source_resolution_instruction']==f'Resolve to {m.TARGETS[index]} on next bar 1.','whole source instructions')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):
        check(c[flag] is False,flag)
    f=ready(index);t=f.token();f.begin(t)
    check(not f.history[-1]['data']['chosen_note_beats_are_source_facts'] and not f.history[-1]['data']['audio_scheduled'],'choice/source split')
    refuse(f,lambda:f.begin(t),'duplicate begin');refuse(f,lambda:f.report(f.token(),response(f)),'report before release')
    refuse(f,lambda:f.release(f.token(),False),'release false');refuse(f,lambda:f.set_plan(f.token(),plan(index)),'active plan change')
    f.release(f.token(),True);refuse(f,lambda:f.set_plan(f.token(),plan(index)),'held report plan change')
    t=f.token();r=response(f);f.report(t,r);r['notes']='outside change';check(f.history[-1]['data']['response']['notes']!='outside change','response custody')
    refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.finish(f.token());check(f.state=='completed','manual source duties recorded')
    history=deepcopy(f.history);p=plan(index);p['chosen_note_beats']=[[31+i,10] for i in range(11)]
    f.set_plan(f.token(),p);check(f.state=='ready' and f.history[:-1]==history,'different chosen timing resets completion keeps history')
    p['chosen_note_beats'][0]=[9,2];check(f.plan['chosen_note_beats'][0]==[31,10],'choice custody')
    for field in [f'contact{i}' for i in range(11)]+['target']+list(m.OBLIGATIONS):
        for value in ('no','uncertain'):
            g=ready(index);reporting(g);r=response(g)
            if field.startswith('contact'):r['source_contacts'][int(field[7:])]['played']=value
            elif field=='target':r['target_report']['matched']=value
            else:r['obligations'][field]=value
            g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'failed source duty retained')
            refuse(g,lambda:g.finish(g.token()),'unsatisfied source duty');refuse(g,lambda:g.begin(g.token()),'explicit retry')
            g.retry(g.token(),'Isolate source duty and retry.');check(g.plan==plan(index),'retry retains choice')
    for state in ('setup','ready','performing','reporting','reported','needs_retry','completed'):
        g=m.FillFlow(m.KEYS[index])
        if state!='setup':g.set_plan(g.token(),plan(index))
        if state in ('performing','reporting','reported','needs_retry','completed'):g.begin(g.token())
        if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
        if state in ('reported','needs_retry','completed'):
            r=response(g)
            if state=='needs_retry':r['obligations']['no_overrun']='no'
            g.report(g.token(),r)
        if state=='completed':g.finish(g.token())
        check(g.state==state,'cancellation fixture');history=deepcopy(g.history);oldplan=deepcopy(g.plan);t=g.token()
        g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t),'old callback');refuse(g,lambda:g.begin(g.token()),'reopen release fence')
        g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.state==('ready' if state in ('performing','reporting') else state),'interrupted pass restarts')
        check(g.plan==oldplan and g.history[:len(history)]==history,'reopen history/source choices')
    # Every standard string can realize the target in a chosen register; none is a source target fret.
    for string,open_midi in m.TUNING.items():
        g=m.FillFlow(m.KEYS[index]);p=plan(index);p['target_choice']['string']=string;p['target_choice']['fret']=(m.PCS[index]-open_midi)%12
        g.set_plan(g.token(),p);check(g.state=='ready','alternative target register')
        p['target_choice']['fret']+=1;refuse(g,lambda p=p:g.set_plan(g.token(),p),'wrong target pitch class')

f=m.FillFlow(m.KEYS[0]);p=plan(0);mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,-1,True,'72',float('inf'),float('nan'),10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for name in ('own_instrument','original_workbook'):bad('missing prerequisite',lambda q,name=name:q['prerequisites'].__setitem__(name,False))
bad('missing note',lambda q:q['chosen_note_beats'].pop())
bad('duplicate onset',lambda q:q['chosen_note_beats'].__setitem__(1,q['chosen_note_beats'][0]))
bad('onsets reversed',lambda q:q['chosen_note_beats'].reverse())
for v in ([3,1],[5,2],[True,2],[7,0],[7,-2],[3.5,1],(7,2),'3.5'):
    bad('invalid or early firstbeat',lambda q,v=v:q['chosen_note_beats'].__setitem__(0,v))
for v in ([5,1],[11,2]):bad('at/after structural attack',lambda q,v=v:q['chosen_note_beats'].__setitem__(-1,v))
bad('no spacing rationale',lambda q:q.__setitem__('spacing_rationale',''))
for field,value in [('source_pitch_class','D'),('string','R'),('fret',True),('fret',-1),('fret',25),('register_rationale','')]:
    bad('invalid targetchoice',lambda q,field=field,value=value:q['target_choice'].__setitem__(field,value))
for label,q in mutants:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
f=ready(0);t=f.token()
for i in range(6):
    x=list(t);x[i]='foreign' if type(t[i]) is str else 99;refuse(f,lambda x=tuple(x):f.begin(x),'token owner component')
refuse(f,lambda:f.begin(ready(0).token()),'other instance');reporting(f)
for name,value in [('source_contacts',[]),('obligations',{}),('notes','')]:
    r=response(f);r[name]=value;refuse(f,lambda r=r:f.report(f.token(),r),'incomplete report')
r=response(f);r['source_contacts'][0]['source_order']=True;refuse(f,lambda:f.report(f.token(),r),'boolean source order')
r=response(f);r['target_report']['source_pitch_class']='G';refuse(f,lambda:f.report(f.token(),r),'changed source target')
f.report(f.token(),response(f));check(f.state=='reported','valid current report after refusals')
check(pin(source['frozen_parser']['path'])==source['frozen_parser'],'parser unchanged after tests')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
    'finite_cells':4,'source_contacts':44,'separate_source_pitch_class_targets':4,'chosen_target_string_options_tested':24,
    'source_timing_or_target_frets_invented':0,'packet':pin(packet),'base':pin(basepath),
    'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'native_runs':0,'app_runs':0,'audio_scheduled':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
