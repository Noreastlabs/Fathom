from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r44')
s=importlib.util.spec_from_file_location('cue',R/'Tools'/L/'cue_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(kind):
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':80,'sections':{'old':'chosen old section','new':'chosen new section'},
      'old_attacks':[[{'string':'G','fret':x}] for x in (0,2,4,5)],'destination_entry':[{'string':'e','fret':8}],
      'new_continuation':'continue chosen new-section material','diagram_timing_unresolved_ack':True,
      'cue':{'kind':kind,'pattern':m.PATTERNS[kind][0],'source_preparation':m.TABLE[kind][2],'source_execution':m.TABLE[kind][3],
      'provider':{'kind':m.PROVIDERS[kind][0],'reference':'Known available external source, not supplied by app','ready':True},
      'parameters':deepcopy({'visual':{'look_on_beat':3,'destination_beat':1},'count':{'listen_while_playing':True,'keep_tempo':True},
      'musical':{'recognition_description':'known fill contour','destination_preparation':'prepare chosen next entry'},
      'chart':{'rehearsal_mark':'B','current_bar':8,'destination_bar':9}}[kind])}}
def ready(i,kind):
    f=m.CueFlow(m.KEYS[i]);f.set_plan(f.token(),plan(kind));return f
def reporting(f):f.begin(f.token(),True);f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):
    kind=f.plan['cue']['kind'];return {'cue_kind':kind,'old_attacks':[{'source_beat':i,'symbol':'P','chosen_realization_followed':'yes'} for i in range(1,5)],
      'destination_beat':1,'common':dict.fromkeys(m.COMMON,'yes'),'source_duties':dict.fromkeys(m.DUTIES[kind],'yes'),
      'notes':'Synthetic manual report, no performance/cue observed.'}
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
base=[json.loads(x) for x in (R/'Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl').read_text().splitlines()]
packet=Path('Build')/L/'cue-cell-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
expected={'visual':['Visual','head nod / hand lift','look on beat 3','change on next bar 1'],
 'count':['Count','spoken 4 / 2-bar count','hear while playing','do not slow to listen'],
 'musical':['Musical','drum fill / held chord','recognize pattern','prepare destination'],
 'chart':['Chart','rehearsal mark','know bar number','eyes return before change']}
check(len(rows)==4 and [r['package_key'] for r in rows]==list(m.KEYS),'four exact cards')
for i,row in enumerate(rows):
    old=base[14+i];c=row['implementation']['task']['contract']
    for field in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[field]==old[field],'immutable '+field)
    check(row['implementation']['events']==old['implementation']['events']==[],'no source note event change')
    check(c['source_table']==expected,'all source methods retained independently of card number')
    check(c['source_prose']=='Keep playing while the eyes or ears receive the cue. The fretting hand begins moving only after the final old-section attack.','full joined source prose')
    check(c['source_prose'] in ' '.join(source['matched_cards'][i]['original_full_block'].split()),'exact original block match')
    check(c['source_diagram']==['Count|1---2---3---4---|','Play |P---P---P---P---|','Look |------------>---|','Move |--------------->|'],'literal diagrams')
    check(c['source_context_header']=='12 CUE CELLS | 96 CONTACTS' and c['source_fixed_contact_count'] is None,'header retained without invented contacts')
    check(c['numbered_card_to_cue_kind_mapping'] is None,'no numbered mode mapping')
    check([a['source_beat_label'] for a in c['source_abstract_attacks']]==[1,2,3,4] and all(a['symbol']=='P' and a['source_pitch'] is None and a['source_fret'] is None and a['gate'] is None for a in c['source_abstract_attacks']),'four abstract attacks not pitched contacts')
    count=c['source_diagram'][0].split('|')[1];look=c['source_diagram'][2].split('|')[1];q=c['source_interpretation_questions'][0]
    check(look.index('>')==12 and count[12]=='4' and q['absolute_diagram_look_time'] is None and q['table_literal']=='look on beat 3','literal discrepancy retained not adjudicated')
    for k in ('automatic_evaluation','performance_observed','source_complete_timing','audio_supplied','timing_scheduled','cue_measured','credit_awarded','mastery_awarded','persistence'):check(c[k] is False,k)
    for kind in ('visual','count','musical','chart'):
        f=ready(i,kind);p=plan(kind);f.set_plan(f.token(),p);p['old_attacks'][0][0]['fret']=21
        check(f.plan['old_attacks'][0][0]['fret']==0,'plan deep custody')
        for v in (False,1,'yes',None):refuse(f,lambda v=v:f.begin(f.token(),v),'current external readiness')
        t=f.token();f.begin(t,True);refuse(f,lambda:f.begin(t,True),'duplicate begin')
        check(f.history[-1]['data']['audio_supplied'] is False and f.history[-1]['data']['clock_used'] is False and f.history[-1]['data']['diagram_timing_resolved'] is False,'no supplied source or resolved diagram')
        refuse(f,lambda:f.report(f.token(),response(f)),'early report');refuse(f,lambda:f.release(f.token(),True),'take-end bypass')
        refuse(f,lambda:f.set_plan(f.token(),plan(kind)),'active plan replacement');refuse(f,lambda:f.end_take(f.token(),False),'not ended')
        f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'release bypass');refuse(f,lambda:f.release(f.token(),1),'release boolean')
        f.release(f.token(),True);r=response(f);t=f.token();f.report(t,r);r['common']['cue_received_while_playing']='no'
        check(f.history[-1]['data']['response']['common']['cue_received_while_playing']=='yes','report deep custody')
        check(all(f.history[-1]['data'][x] is False for x in ('performance_verified','cue_measured','diagram_timing_resolved','automatic_score')),'manual report only')
        refuse(f,lambda:f.report(t,response(f)),'duplicate response');f.finish(f.token());check(f.state=='completed','all16card-mode routes')
        history=deepcopy(f.history);p=plan(kind);p['bpm']=96;f.set_plan(f.token(),p)
        check(f.state=='ready' and f.cycle==0 and f.history[:len(history)]==history,'new plan resets completion with history')
        for field,names in (('common',m.COMMON),('source_duties',m.DUTIES[kind])):
            for name in names:
                for outcome in ('no','uncertain'):
                    g=ready(i,kind);reporting(g);r=response(g);r[field][name]=outcome;g.report(g.token(),r)
                    check(g.state=='needs_retry','negative source duty');refuse(g,lambda:g.finish(g.token()),'negative finish')
                    g.retry(g.token(),'Repair source duty');check(g.state=='ready','explicit retry')
        for attack in range(4):
            for outcome in ('no','uncertain'):
                g=ready(i,kind);reporting(g);r=response(g);r['old_attacks'][attack]['chosen_realization_followed']=outcome;g.report(g.token(),r)
                check(g.state=='needs_retry','attack negative');refuse(g,lambda:g.finish(g.token()),'unmet attack finish')
        mutations=[]
        for v in (0,-1,True,'80',None,float('inf'),float('nan')):mutations.append(('tempo',lambda p,v=v:p.update(bpm=v)))
        for name in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,name=name:p['prerequisites'].update({name:False})))
        mutations.extend([('unresolved ack',lambda p:p.update(diagram_timing_unresolved_ack=False)),('old section',lambda p:p['sections'].update(old='')),
          ('new section',lambda p:p['sections'].update(new='')),('continuation',lambda p:p.update(new_continuation='')),
          ('three old attacks',lambda p:p['old_attacks'].pop()),('extra old attack',lambda p:p['old_attacks'].append([{'string':'e','fret':0}])),
          ('wrong source preparation',lambda p:p['cue'].update(source_preparation='invented')),('wrong source execution',lambda p:p['cue'].update(source_execution='invented')),
          ('pattern',lambda p:p['cue'].update(pattern='invented')),('provider app',lambda p:p['cue']['provider'].update(kind='app_audio')),
          ('unready provider',lambda p:p['cue']['provider'].update(ready=False)),('provider reference',lambda p:p['cue']['provider'].update(reference=''))])
        for part in ('old_attacks','destination_entry'):
            def vchange(p,part,fn):
                if part=='old_attacks':p[part][0]=fn(p[part][0])
                else:p[part]=fn(p[part])
            for bad in ([],[{'string':'X','fret':0}],[{'string':'e','fret':True}],[{'string':'e','fret':25}],[{'string':'e','fret':-1}],[{'string':'e','fret':0},{'string':'e','fret':2}]):
                mutations.append(('voicing '+part,lambda p,part=part,bad=bad:vchange(p,part,lambda x:deepcopy(bad))))
        if kind=='visual':
            mutations.extend([('wrong lookbeat',lambda p:p['cue']['parameters'].update(look_on_beat=4)),('boolean lookbeat',lambda p:p['cue']['parameters'].update(look_on_beat=True)),('destinationbeat',lambda p:p['cue']['parameters'].update(destination_beat=2))])
        elif kind=='count':
            for k in ('listen_while_playing','keep_tempo'):mutations.append(('count obligation',lambda p,k=k:p['cue']['parameters'].update({k:False})))
        elif kind=='musical':
            for k in ('recognition_description','destination_preparation'):mutations.append(('musical preparation',lambda p,k=k:p['cue']['parameters'].update({k:''})))
        else:
            mutations.extend([('mark',lambda p:p['cue']['parameters'].update(rehearsal_mark='')),('oldbar',lambda p:p['cue']['parameters'].update(current_bar=0)),('boolean bar',lambda p:p['cue']['parameters'].update(current_bar=True)),('destinationbar',lambda p:p['cue']['parameters'].update(destination_bar=10))])
        for label,mutate in mutations:
            g=ready(i,kind);p=plan(kind);mutate(p);refuse(g,lambda:g.set_plan(g.token(),p),label)
        for provider in m.PROVIDERS[kind]:
            for pattern in m.PATTERNS[kind]:
                g=ready(i,kind);p=plan(kind);p['cue']['provider']['kind']=provider;p['cue']['pattern']=pattern;g.set_plan(g.token(),p)
                check(g.plan['cue']['provider']['kind']==provider and g.plan['cue']['pattern']==pattern,'every eligible external provider/pattern')
        g=ready(i,kind);reporting(g)
        bad=[('mode',lambda r:r.update(cue_kind='other')),('destination',lambda r:r.update(destination_beat=2)),('bool destination',lambda r:r.update(destination_beat=True)),
          ('notes',lambda r:r.update(notes='')),('source duties',lambda r:r['source_duties'].pop(next(iter(r['source_duties'])))),
          ('common enum',lambda r:r['common'].update(cue_received_while_playing=True)),('short attacks',lambda r:r['old_attacks'].pop())]
        for b in range(4):
            bad.extend([('attackbeat',lambda r,b=b:r['old_attacks'][b].update(source_beat=0)),('attackboolean',lambda r,b=b:r['old_attacks'][b].update(source_beat=True)),
              ('attack symbol',lambda r,b=b:r['old_attacks'][b].update(symbol='R')),('attack reply',lambda r,b=b:r['old_attacks'][b].update(chosen_realization_followed='maybe'))])
        for label,mutate in bad:
            r=response(g);mutate(r);refuse(g,lambda:g.report(g.token(),r),label)
        for state in ('setup','ready','performing','await_release','reporting','reported','needs_retry','completed'):
            h=m.CueFlow(m.KEYS[i])
            if state!='setup':h.set_plan(h.token(),plan(kind))
            if state in ('performing','await_release','reporting','reported','needs_retry','completed'):h.begin(h.token(),True)
            if state in ('await_release','reporting','reported','needs_retry','completed'):h.end_take(h.token(),True)
            if state in ('reporting','reported','needs_retry','completed'):h.release(h.token(),True)
            if state in ('reported','needs_retry','completed'):
                r=response(h)
                if state=='needs_retry':r['common']['move_only_after_final_old_attack']='uncertain'
                h.report(h.token(),r)
            if state=='completed':h.finish(h.token())
            check(h.state==state,'fixture state');history=deepcopy(h.history);p=deepcopy(h.plan);t=h.token();h.cancel(t)
            refuse(h,lambda:h.cancel(t),'duplicate cancel');h.reopen(h.token());h.cancel(h.token());h.reopen(h.token())
            refuse(h,lambda:h.begin(h.token(),True),'reopen release bypass');h.release(h.token(),True)
            target='ready' if state in ('performing','await_release','reporting') else state
            check(h.state==target and h.plan==p and h.history[:len(history)]==history,'cancel/reopen custody')
        g=ready(i,kind);foreign=ready(i,kind);refuse(g,lambda:g.begin(foreign.token(),True),'foreign instance')
        token=g.token();g.set_plan(g.token(),plan(kind));refuse(g,lambda:g.begin(token,True),'stale generation');refuse(g,lambda:g.begin(list(g.token()),True),'token type')
        reporting(g);g.report(g.token(),response(g));refuse(g,lambda:g.retry(g.token(),''),'empty retry')
correction=json.loads((R/'Results'/L/'prior-contract-correction.json').read_text())
check(correction['prior_contract']['response_fields'][0]['source_prompt']=='Chart rehearsal mark know bar number','old omission honestly retained')
check(correction['newly_complete_count_for_this_key']==0,'strengthening not counted twice')
try:m.CueFlow('exercise-completeness-r01/level075/modulec/p006-card05/cuecell5oldsectionnewsection')
except m.Refusal:checks+=1;refusals+=1
else:raise AssertionError('invented fifth card accepted')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'cue_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance':False,'audio_used':False,
 'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
