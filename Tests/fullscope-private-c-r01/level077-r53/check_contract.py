from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level077-r53')
s=importlib.util.spec_from_file_location('voiceleading',R/'Tools'/L/'voiceleading_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def contact(note,alternate=False):
    choices=[{'string':s,'fret':note-n} for s,n in m.TUNING.items() if 0<=note-n<=24]
    return choices[-1 if alternate else 0]
def plan(sung='lower',common='hold'):
    out={'prerequisites':{'own_instrument':True,'original_workbook':True},'keys':{}}
    for key in m.TONICS:
        offset=m.PC[key];x=53+offset;y=60+offset;midis={'lower':[x,x,x-1],'upper':[y,y-1,y-1]}
        out['keys'][key]={'combined_sung_voice':sung,'midi':midis,'contacts':{v:[contact(n) for n in ns] for v,ns in midis.items()},
          'articulations':{'lower':['attack',common,'attack'],'upper':['attack','attack',common]}}
    return out
def response(f):
    key=m.TONICS[f.key_index];ref=m.reference(key);a=f.assignment()
    r={'key':key,'mode':m.MODES[f.phase],'chords':ref['chords'],'sung_voice':a['sung'],'played_voice':a['played'],
      'duties':dict.fromkeys(m.COMMON,'yes'),'diagnosis':'','notes':'Synthetic manual source-order and singing/playing report, no sound observed.'}
    if f.phase==2:r.update(played_contacts=deepcopy(f.plan['keys'][key]['contacts'][a['played']]),actual_attack_counts=f.expected_counts(),combined_duties=dict.fromkeys(m.COMBINED,'yes'))
    return r
def perform_to_report(f):
    f.begin(f.token(),True)
    for j in range(3):
        cue=f.view()['current_cue'];f.cue_read(f.token(),cue['chord'],cue['function']);f.perform_station(f.token(),True)
    f.end_take(f.token(),True);f.release(f.token(),True)
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
packet=Path('Build')/L/'major-voiceleading-overlay.jsonl';row=json.loads((R/packet).read_text());old=json.loads((R/'Build/fullscope-private-c-r01/level077-r06/implementation-packet.jsonl').read_text().splitlines()[71])
c=row['implementation']['task']['contract'];check(row['package_key']==m.KEY,'exact one supplement')
for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
check(row['implementation']['events']==old['implementation']['events']==[] and row['implementation']['task']['table_fields']==old['implementation']['task']['table_fields'],'raw and empty source events retained')
check(c['source_practice']=='Sing each line alone; then sing one while playing the other.','complete two solo and combined instruction')
check(c['source_transposition']=='Transposition command: move the ii-V-I guide-tone pair through G, D, A, E, and F major. The voice must be sung from the chord name and function, not copied by fret distance.','full transposition/function/no-fret-copy obligation')
check(c['printed_guide_pitch_class_occurrences']==6 and c['derived_transposed_guide_targets']==30 and len(c['derived_requested_transpositions'])==5,'source versus derived counts')
for k in ('automatic_evaluation','performance_observed','audio_supplied','audio_inspected','timing_scheduled','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
expected={'C':(['Dm7','G7','Cmaj7'],['F','F','E'],['C','B','B']),
 'G':(['Am7','D7','Gmaj7'],['C','C','B'],['G','F#','F#']),
 'D':(['Em7','A7','Dmaj7'],['G','G','F#'],['D','C#','C#']),
 'A':(['Bm7','E7','Amaj7'],['D','D','C#'],['A','G#','G#']),
 'E':(['F#m7','B7','Emaj7'],['A','A','G#'],['E','D#','D#']),
 'F':(['Gm7','C7','Fmaj7'],['Bb','Bb','A'],['F','E','E'])}
for key,(chords,lo,hi) in expected.items():
    v=m.reference(key);check((v['chords'],v['lower'],v['upper'])==(chords,lo,hi),'independent six-key transposition')
    check(v['functions']==['ii','V','I'] and v['lower_roles']==['b3','b7','3'] and v['upper_roles']==['b7','3','7'],'changing guide roles')
    check((v['provenance']=='printed C source')==(key=='C') and v['onset_duration'] is None,'printed/derived authority and no pulse invention')
cache={}
for sung in ('lower','upper'):
    for common in ('hold','rearticulate'):
        f=m.VoiceLeadingFlow(m.KEY);f.set_plan(f.token(),plan(sung,common))
        for subpass in range(18):
            key_index,phase=divmod(subpass,3);check(f.key_index==key_index and f.phase==phase and f.station==0,'source-list key/phase order')
            if sung=='lower' and common=='hold':cache[subpass]=deepcopy(f)
            view=f.view();a=f.assignment();check(a['sung']==('lower' if phase==0 else 'upper' if phase==1 else sung),'solo/selected combined sung assignment')
            check(a['played']==(None if phase<2 else 'upper' if sung=='lower' else 'lower'),'other played voice, none for solos')
            refuse(f,lambda:f.finish(f.token()),'no early whole completion');refuse(f,lambda:f.next_subpass(f.token()),'no early subpass')
            if phase<2:refuse(f,lambda:f.expected_counts(),'no forced solo attack counts')
            for bad in (False,1,None,'yes'):refuse(f,lambda bad=bad:f.begin(f.token(),bad),'current readiness')
            t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin');refuse(f,lambda:f.set_plan(f.token(),plan(sung,common)),'active plan')
            for j in range(3):
                check(f.station==j and f.state=='cue','three ordered harmonic stations')
                cue=f.view()['current_cue'];ref=expected[m.TONICS[key_index]]
                check(cue['chord']==ref[0][j] and cue['source_station']==j+1,'actual named chord cue')
                refuse(f,lambda:f.perform_station(f.token(),True),'named cue before perform');refuse(f,lambda:f.cue_read(f.token(),'wrong',cue['function']),'wrong chord cue');refuse(f,lambda:f.cue_read(f.token(),cue['chord'],'wrong'),'wrong function cue')
                f.cue_read(f.token(),cue['chord'],cue['function']);refuse(f,lambda:f.end_take(f.token(),True),'not before all three stations');t=f.token();f.perform_station(t,True);refuse(f,lambda:f.perform_station(t,True),'duplicate station')
            check(f.state=='end_take','whole subpass end before report');refuse(f,lambda:f.report(f.token(),response(f)),'report before end/release');f.end_take(f.token(),True)
            refuse(f,lambda:f.report(f.token(),response(f)),'release fence');refuse(f,lambda:f.release(f.token(),1),'release bool');f.release(f.token(),True)
            if phase==2:check(f.expected_counts()==([1,1,0 if common=='hold' else 1] if sung=='lower' else [1,0 if common=='hold' else 1,1]),'chosen played voice common articulation counts')
            r=response(f);t=f.token();f.report(t,r);r['chords'][0]='outside';check(f.history[-1]['data']['response']['chords'][0]!='outside','report copy custody')
            check(f.history[-1]['data']['source_fixed_attack_count'] is False and f.history[-1]['data']['performance_verified'] is False,'chosen/manual counts not source/acoustic facts')
            refuse(f,lambda:f.report(t,response(f)),'duplicate report')
            if subpass<17:refuse(f,lambda:f.finish(f.token()),'all six keys and phases required');f.next_subpass(f.token())
            else:refuse(f,lambda:f.next_subpass(f.token()),'no extra key');f.finish(f.token())
        check(f.state=='completed' and sum(x['kind']=='report' for x in f.history)==18 and sum(x['kind']=='perform_station' for x in f.history)==54,'exact complete eighteen-subpass campaign')
        h=deepcopy(f.history);f.set_plan(f.token(),plan());check(f.state=='ready' and f.key_index==f.phase==f.station==0 and f.history[:len(h)]==h,'new plan resets C with prior history')
for subpass,ready in cache.items():
    phase=subpass%3;mutations=[]
    for group,names in [('duties',m.COMMON)]+([('combined_duties',m.COMBINED)] if phase==2 else []):
        for name in names:
            for value in ('no','uncertain'):mutations.append((name,lambda r,group=group,name=name,value=value:r[group].update({name:value})))
    if phase==2:
        for j in range(3):mutations.append(('wrong actual attack count',lambda r,j=j:r['actual_attack_counts'].__setitem__(j,r['actual_attack_counts'][j]+1)))
    for label,mutate in mutations:
        f=deepcopy(ready);perform_to_report(f);r=response(f);mutate(r);refuse(f,lambda:f.report(f.token(),r),'failure diagnosis '+label)
        r['diagnosis']='Reported source/coordination/attack issue; retry current subpass';f.report(f.token(),r);check(f.state=='needs_retry','failed manual report retained')
        refuse(f,lambda:f.next_subpass(f.token()),'failure cannot advance');refuse(f,lambda:f.finish(f.token()),'failure cannot finish');refuse(f,lambda:f.retry(f.token(),''),'retry diagnostic text')
        key_index=f.key_index;f.retry(f.token(),'Explicit retry after diagnosis');check(f.key_index==key_index and f.phase==phase and f.station==0,'retry current key/phase from station1')
    f=deepcopy(ready);perform_to_report(f)
    for field,value in [('key','wrong'),('mode','wrong'),('sung_voice','wrong'),('played_voice','wrong'),('notes','')]:
        r=response(f);r[field]=value;refuse(f,lambda:f.report(f.token(),r),'bound typed response '+field)
    r=response(f);r['duties']['source_order']=True;refuse(f,lambda:f.report(f.token(),r),'explicit outcome enum')
    if phase==2:
        for bad in ([True,1,0],[-1,1,0],[1.0,1,0],[1,1]):
            r=response(f);r['actual_attack_counts']=bad;refuse(f,lambda:f.report(f.token(),r),'typed actual count triple')
        r=response(f);r['played_contacts'][0]['fret']+=1;refuse(f,lambda:f.report(f.token(),r),'played contact binding')
    states=[];f=deepcopy(ready);states.append(deepcopy(f));f.begin(f.token(),True)
    for j in range(3):
        states.append(deepcopy(f));cue=f.view()['current_cue'];f.cue_read(f.token(),cue['chord'],cue['function']);states.append(deepcopy(f));f.perform_station(f.token(),True)
    states.append(deepcopy(f));f.end_take(f.token(),True);states.append(deepcopy(f));f.release(f.token(),True);states.append(deepcopy(f));f.report(f.token(),response(f));states.append(deepcopy(f))
    for f in states:
        priorstate=f.state;h=deepcopy(f.history);p=deepcopy(f.plan);oldkey=f.key_index;oldphase=f.phase;t=f.token();f.cancel(t);refuse(f,lambda:f.cancel(t),'duplicate cancel')
        f.reopen(f.token());f.cancel(f.token());f.reopen(f.token());refuse(f,lambda:f.begin(f.token(),True),'reopen release');f.release(f.token(),True)
        target=priorstate if priorstate in ('ready','reported') else 'ready'
        check(f.state==target and f.key_index==oldkey and f.phase==oldphase and f.plan==p and f.history[:len(h)]==h and (f.station==0 if target=='ready' else f.station==2),'cancel/reopen repeats interrupted subpass, retains context')
        refuse(f,lambda:f.begin(t,True),'stale pre-cancel token')
f=m.VoiceLeadingFlow(m.KEY);f.set_plan(f.token(),plan());mutations=[]
for field in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,field=field:p['prerequisites'].update({field:False})))
mutations.append(('missing required key',lambda p:p['keys'].pop('F')))
for key in m.TONICS:
    mutations.append(('unknown sung voice',lambda p,key=key:p['keys'][key].update(combined_sung_voice='both')))
    for voice in m.VOICES:
        mutations.extend([('wrong pitch',lambda p,key=key,voice=voice:p['keys'][key]['midi'][voice].__setitem__(0,p['keys'][key]['midi'][voice][0]+1)),
          ('MIDI bool',lambda p,key=key,voice=voice:p['keys'][key]['midi'][voice].__setitem__(0,True)),
          ('wrong contact',lambda p,key=key,voice=voice:p['keys'][key]['contacts'][voice][0].update(fret=p['keys'][key]['contacts'][voice][0]['fret']+1)),
          ('fret bool',lambda p,key=key,voice=voice:p['keys'][key]['contacts'][voice][0].update(fret=True)),
          ('negative fret',lambda p,key=key,voice=voice:p['keys'][key]['contacts'][voice][0].update(fret=-1)),
          ('overbound fret',lambda p,key=key,voice=voice:p['keys'][key]['contacts'][voice][0].update(fret=25)),
          ('invalid string',lambda p,key=key,voice=voice:p['keys'][key]['contacts'][voice][0].update(string='x')),
          ('hold initial',lambda p,key=key,voice=voice:p['keys'][key]['articulations'][voice].__setitem__(0,'hold'))])
        j=1 if voice=='lower' else 2
        def move_held(p,key=key,voice=voice,j=j):p['keys'][key]['contacts'][voice][j]=contact(p['keys'][key]['midi'][voice][j],True)
        mutations.append(('held common cannot change contact',move_held))
        p=plan();move_held(p);p['keys'][key]['articulations'][voice][j]='rearticulate';f.set_plan(f.token(),p);check(f.plan==p,'rearticulation can choose other position at same exact MIDI')
for label,mutate in mutations:
    p=plan();mutate(p);refuse(f,lambda:f.set_plan(f.token(),p),label)
g=m.VoiceLeadingFlow(m.KEY);g.set_plan(g.token(),plan());refuse(f,lambda:f.begin(g.token(),True),'foreign instance');t=f.token();p=plan();f.set_plan(f.token(),p);p['keys']['C']['midi']['lower'][0]=0;check(f.plan['keys']['C']['midi']['lower'][0]!=0,'plan custody');refuse(f,lambda:f.begin(t,True),'stale plan generation')
v=f.view();v['source_reference']['chords'][0]='wrong';check(f.view()['source_reference']['chords'][0]!='wrong','view custody')
for key in ('exercise-completeness-r01/level077/modulec/p007-t1-r5/fmaj7','exercise-completeness-r01/level077/modulec/p008-t1-r5/dm7','exercise-completeness-r01/level077/modulec/p008-supplement01/minoriivivoiceleading'):refuse(f,lambda key=key:m.VoiceLeadingFlow(key),'excluded other identity')
f=m.VoiceLeadingFlow(m.KEY);f.cancel(f.token());f.reopen(f.token());f.release(f.token(),True);check(f.state=='setup','unconfigured cancel/reopen')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
  'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'voiceleading_contract.py'),
  'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance_verified':False,'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
