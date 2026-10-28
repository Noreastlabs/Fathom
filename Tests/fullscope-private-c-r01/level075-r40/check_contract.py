from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r40')
s=importlib.util.spec_from_file_location('handoff',R/'Tools'/L/'handoff_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
checks=refusals=0
def check(ok,label):
    global checks
    checks+=1
    if not ok:raise AssertionError(label)
def refuse(f,fn,label):
    global refusals
    prior=deepcopy(f.__dict__)
    try:fn()
    except m.Refusal:refusals+=1
    else:raise AssertionError('accepted '+label)
    check(f.__dict__==prior,'atomic refusal '+label)
def choice(i):
    return deepcopy(({'old_chord':'G7','old_local_bar':8,'beat4_plan':'intentional_no_rhythm_attack_space','lead_entry_local_bar':9,'lead_material':'Chosen lead motif'},
        {'old_chord':'Cmaj7','old_local_bar':4,'resolution_beat':[5,2],'resolution_pitch_class':'E','register':'chosen middle','harmonic_rationale':'E relates to chosen Cmaj7','next_bar_comp':'chosen comp voicing'},
        {'guide_tone_midi':[59,60,62],'old_register_anchor_midi':48,'upper_triad_midi':[64,67,72],'harmonic_basis':'Learner harmony reference; actual correctness unverified'},
        {'sustained_top_midi':72,'destination_root_midi':48,'verse_harmony_root_rationale':'chosenC/rootC','sustain_handoff_description':'hold chosen top then move to low root'},
        {'final_accent_realization':'chosen final accent','rest_beats':[1,2],'motif_pitch_classes':['C','E','G'],'motif_rhythm_description':'chosen motif after half-beat rest'},
        {'target_beat':3,'target_pitch_class':'C','harmonic_rationale':'chosenCtarget','groove_entry':'next_barline','full_groove_realization':'chosen full rhythm texture'})[i])
def plan(i):return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':80,'old_material_texture':'learner old material','destination_material_texture':'learner destination material','choice':choice(i)}
def ready(i):
    f=m.HandoffFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i));return f
def reporting(f):f.begin(f.token());f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):return {'common':dict.fromkeys(m.COMMON,'yes'),'source_duties':dict.fromkeys(m.DUTIES[f.index],'yes'),'notes':'Synthetic self-report; no actual performance.'}
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl');base=[json.loads(x) for x in (R/basepath).read_text().splitlines()]
packet=Path('Build')/L/'role-handoff-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
expected=[('Rhythm -> lead','G7 bar 8','leave beat 4 open','lead enters bar 9'),('Lead -> rhythm','Cmaj7 bar 4','resolve by beat 3','comp enters next bar'),
 ('Low -> upper','pre-chorus','guide-tone climb','upper triad on chorus 1'),('Upper -> low','chorus end','sustain top voice','low root on verse 1'),
 ('Dense -> sparse','bridge -> solo','final accent','rest then motif'),('Sparse -> dense','solo -> chorus','target on beat 3','full groove barline')]
check(len(rows)==6 and [r['package_key'] for r in rows]==list(m.KEYS),'six exact source children')
check(all('supplement' not in r['package_key'] for r in rows),'separate handoffcell untouched')
for index,row in enumerate(rows):
    old=base[54+index];c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source note/gate invention')
    check(tuple(c['source_row'][k] for k in ('handoff','location','preparation','destination'))==expected[index],'independent full source row')
    check(source['original_page_text'].count('\n'.join(expected[index]))==1,'exact unique original literal')
    check(c['source_context_header']=='240 CONTACTS' and c['fixed_source_contact_count'] is None,'no invented source contact count')
    check(c['source_local_bars_are_master_indices'] is False,'local bar namespace preserved')
    for k in ('automatic_evaluation','performance_observed','harmonic_correctness_verified','audio_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):
        check(c[k] is False,k)
    f=ready(index);t=f.token();f.begin(t);refuse(f,lambda:f.begin(t),'duplicate begin')
    refuse(f,lambda:f.report(f.token(),response(f)),'before end');refuse(f,lambda:f.release(f.token(),True),'end bypass')
    refuse(f,lambda:f.end_take(f.token(),False),'ongoing take');refuse(f,lambda:f.set_plan(f.token(),plan(index)),'active plan')
    f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'before release');refuse(f,lambda:f.release(f.token(),False),'false release')
    f.release(f.token(),True);t=f.token();r=response(f);f.report(t,r);r['notes']='outside';check(f.history[-1]['data']['response']['notes']!='outside','reply custody')
    refuse(f,lambda:f.report(t,response(f)),'duplicate reply');f.finish(f.token());check(f.state=='completed','manual outcome')
    history=deepcopy(f.history);p=plan(index);p['bpm']=86;f.set_plan(f.token(),p);p['choice'][next(iter(p['choice']))]='outside'
    check(f.state=='ready' and f.history[:-1]==history and f.plan['choice']==choice(index),'plan reset and copy custody')
    for group,names in (('common',m.COMMON),('source_duties',m.DUTIES[index])):
        for name in names:
            for value in ('no','uncertain'):
                g=ready(index);reporting(g);r=response(g);r[group][name]=value;g.report(g.token(),r)
                check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'each failed duty retained')
                refuse(g,lambda:g.finish(g.token()),'missing source duty');refuse(g,lambda:g.begin(g.token()),'explicit retry')
                g.retry(g.token(),'Repeat source preparation.');check(g.state=='ready','retry same source')
    for state in ('setup','ready','performing','await_release','reporting','reported','needs_retry','completed'):
        g=m.HandoffFlow(m.KEYS[index])
        if state!='setup':g.set_plan(g.token(),plan(index))
        if state in ('performing','await_release','reporting','reported','needs_retry','completed'):g.begin(g.token())
        if state in ('await_release','reporting','reported','needs_retry','completed'):g.end_take(g.token(),True)
        if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
        if state in ('reported','needs_retry','completed'):
            r=response(g)
            if state=='needs_retry':r['common']['pulse_and_tempo_held']='no'
            g.report(g.token(),r)
        if state=='completed':g.finish(g.token())
        check(g.state==state,'cancellation fixture');history=deepcopy(g.history);p=deepcopy(g.plan);t=g.token()
        g.cancel(t);g.reopen(g.token());refuse(g,lambda:g.begin(t),'stale callback');refuse(g,lambda:g.begin(g.token()),'reopen release')
        g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.state==('ready' if state in ('performing','await_release','reporting') else state),'repeat interrupted take')
        check(g.plan==p and g.history[:len(history)]==history,'history/plan retained')
    # Every distinct choice field is meaningful: remove it to cause atomic refusal.
    g=m.HandoffFlow(m.KEYS[index])
    for field in m.CHOICE_FIELDS[index]:
        p=plan(index);p['choice'].pop(field);refuse(g,lambda p=p:g.set_plan(g.token(),p),'missing case-specific choice')

mutations={0:[('old_chord','C7'),('old_local_bar',4),('old_local_bar',True),('beat4_plan','play_fill'),('lead_entry_local_bar',8),('lead_material','')],
 1:[('old_chord','G7'),('old_local_bar',8),('resolution_beat',[7,2]),('resolution_beat',[1,2]),('resolution_beat',[1,0]),('resolution_beat',[True,1]),('resolution_pitch_class','H'),('register',''),('harmonic_rationale',''),('next_bar_comp','')],
 2:[('guide_tone_midi',[59]),('guide_tone_midi',[60,59]),('guide_tone_midi',[59,59]),('guide_tone_midi',[True,62]),('upper_triad_midi',[48,60,64]),('upper_triad_midi',[64,67]),('upper_triad_midi',[67,64,72]),('upper_triad_midi',[64,67,128]),('old_register_anchor_midi',True),('harmonic_basis','')],
 3:[('sustained_top_midi',True),('destination_root_midi',72),('destination_root_midi',-1),('verse_harmony_root_rationale',''),('sustain_handoff_description','')],
 4:[('rest_beats',[0,1]),('rest_beats',[-1,2]),('rest_beats',[1,0]),('rest_beats',[True,1]),('motif_pitch_classes',[]),('motif_pitch_classes',['H']),('final_accent_realization',''),('motif_rhythm_description','')],
 5:[('target_beat',2),('target_beat',True),('target_pitch_class','H'),('groove_entry','mid_bar'),('harmonic_rationale',''),('full_groove_realization','')]}
for index,changes in mutations.items():
    g=m.HandoffFlow(m.KEYS[index])
    for name,value in changes:
        p=plan(index);p['choice'][name]=value;refuse(g,lambda p=p:g.set_plan(g.token(),p),'invalid '+name)
# Exact source boundary alternatives remain learner choices, not one fabricated answer.
for beat in ([1,1],[3,1]):
    g=m.HandoffFlow(m.KEYS[1]);p=plan(1);p['choice']['resolution_beat']=beat;g.set_plan(g.token(),p);check(g.state=='ready','inclusive resolve deadline')
for duration in ([1,16],[3,2]):
    g=m.HandoffFlow(m.KEYS[4]);p=plan(4);p['choice']['rest_beats']=duration;g.set_plan(g.token(),p);check(g.state=='ready','different positive rest choice')
for index,name in ((1,'resolution_pitch_class'),(5,'target_pitch_class')):
    for pc in m.PCS:
        g=m.HandoffFlow(m.KEYS[index]);p=plan(index);p['choice'][name]=pc;g.set_plan(g.token(),p)
        reporting(g);r=response(g);r['source_duties']['resolution_fits_harmony' if index==1 else 'target_fits_harmony']='uncertain';g.report(g.token(),r)
        check(g.state=='needs_retry' and not g.history[-1]['data']['harmonic_correctness_verified'],'pitch token alone cannot establish harmonic performance')
g=m.HandoffFlow(m.KEYS[0])
for value in (0,-1,True,'80',float('inf'),float('nan'),10**1000):
    p=plan(0);p['bpm']=value;refuse(g,lambda p=p:g.set_plan(g.token(),p),'invalid BPM')
for field in ('own_instrument','original_workbook'):
    p=plan(0);p['prerequisites'][field]=False;refuse(g,lambda p=p:g.set_plan(g.token(),p),'missing prerequisite')
for field in ('old_material_texture','destination_material_texture'):
    p=plan(0);p[field]='';refuse(g,lambda p=p:g.set_plan(g.token(),p),'missing material')
g=ready(0);t=g.token()
for i in range(6):
    a=list(t);a[i]='foreign' if type(t[i]) is str else 99;refuse(g,lambda a=tuple(a):g.begin(a),'token field')
refuse(g,lambda:g.begin(ready(0).token()),'foreign instance');reporting(g)
for group in ('common','source_duties'):
    r=response(g);r[group].pop(next(iter(r[group])));refuse(g,lambda r=r:g.report(g.token(),r),'missing response obligation')
r=response(g);r['source_duties']['beat4_left_open']='verified';refuse(g,lambda:g.report(g.token(),r),'unknown response enum')
g.report(g.token(),response(g));g.finish(g.token());check(g.state=='completed','current report after refusals')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
 'finite_existing_keys':6,'source_contacts_invented':0,'packet':pin(packet),'base':pin(basepath),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'native_runs':0,'app_runs':0,'actual_performances':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
