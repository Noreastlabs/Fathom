from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r43')
s=importlib.util.spec_from_file_location('contrast',R/'Tools'/L/'contrast_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(i):
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},'bpm':80,'harmony':'Cmaj7',
        'source_dynamic_transition':m.ROWS[i][4],'states':{side:{'source_texture':m.ROWS[i][2+n],
          'voicing':[{'string':'D','fret':9},{'string':'G','fret':9},{'string':'B','fret':8},{'string':'e','fret':8}],
          'controls':{k:'Chosen '+side+' '+k for k in m.CONTROLS},'source_accent_groups':[3,3,2] if i==3 and side=='old' else []}
          for n,side in enumerate(('old','new'))}}
def ready(i):
    f=m.ContrastFlow(m.KEYS[i]);f.set_plan(f.token(),plan(i));return f
def reporting(f):f.begin(f.token());f.end_take(f.token(),True);f.release(f.token(),True)
def response(f):return {'bars':[{'bar':i+1,'side':side,'source_texture':f.plan['states'][side]['source_texture'],
    'duties':dict.fromkeys(m.BAR_DUTIES,'yes')} for i,side in enumerate(('old','new','new','old'))],
    'common':dict.fromkeys(m.COMMON,'yes'),'notes':'Synthetic self-report, no performed or heard audio.'}
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl');base=[json.loads(x) for x in (R/basepath).read_text().splitlines()]
packet=Path('Build')/L/'texture-contrast-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
expected=[('Verse -> Chorus','muted 8ths','open 16ths','p -> f','same tempo'),
 ('Chorus -> Verse','wide triads','low partials','f -> mp','same tempo'),
 ('Pre -> Chorus','rising quarters','full groove','crescendo','same tempo'),
 ('Bridge -> Solo','3+3+2 comp','sparse lead','mf -> space','same tempo'),
 ('Solo -> Chorus','lead register','rhythm register','f -> f','same tempo')]
check(len(rows)==5 and [r['package_key'] for r in rows]==list(m.KEYS),'five exact existing children')
for index,row in enumerate(rows):
    old=base[30+index];c=row['implementation']['task']['contract']
    for k in ('package_key','source_identity','source_refs','source_payload','timing_authority'):check(row[k]==old[k],'preserved '+k)
    check(row['implementation']['events']==old['implementation']['events']==[],'source events unchanged')
    check(tuple(c['source_row'][k] for k in ('change','old_texture','new_texture','dynamic','audit'))==expected[index],'independent source five columns')
    check(source['original_page_text'].count('\n'.join(expected[index]))==1,'exact original PDF source row')
    check(c['source_example_footer']=='Repeat the same Cmaj7 harmony while changing only attack zone, muting, subdivision, and dynamics. Then reverse the order without inserting a setup pause.','full joined footer')
    check(c['source_example_lines']==['BAR 1 - VERSE','Count|1 & 2 & 3 & 4 &|','Play |P x P x P x P x|','BAR 2 - CHORUS','Count|1e&a2e&a3e&a4e&a|','Play |P-x-P-x-P-x-P-x-|'],'literal example')
    check(c['source_context_sixth_row']==dict(zip(('change','old_texture','new_texture','dynamic','audit'),('Chorus -> Outro','dense 16ths','quarters / whole','f -> pp','same tempo'))),'sixth context preserved')
    check(c['new_context_key_created'] is False and c['fixed_source_contact_count'] is None and c['source_note_events']==[],'no invented context child/contact')
    check(c['example_pulse_grid_adopted'] is False and 'not rest' in c['example_symbol_reference']['x'],'muted attacks not silence')
    for k in ('automatic_evaluation','performance_observed','audio_supplied','timing_scheduled','audible_contrast_measured','mastery_awarded','credit_awarded','persistence'):check(c[k] is False,k)
    f=ready(index);p=plan(index);f.set_plan(f.token(),p);p['states']['old']['voicing'][0]['fret']=0
    check(f.plan['states']['old']['voicing'][0]['fret']==9,'deep plan custody')
    start=f.token();f.begin(start);check(f.history[-1]['data']['continuous_side_order']==['old','new','new','old'],'continuous source-bound route')
    check(f.history[-1]['data']['report_between_directions'] is False and not hasattr(f,'advance'),'no direction-break workflow')
    refuse(f,lambda:f.begin(start),'duplicate begin');refuse(f,lambda:f.report(f.token(),response(f)),'report before take end')
    refuse(f,lambda:f.release(f.token(),True),'take-end bypass');refuse(f,lambda:f.set_plan(f.token(),plan(index)),'active plan replacement')
    for no in (False,1,'yes',None):refuse(f,lambda no=no:f.end_take(f.token(),no),'non-true end')
    f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'report before physical release')
    for no in (False,1,'yes',None):refuse(f,lambda no=no:f.release(f.token(),no),'non-true release')
    f.release(f.token(),True);t=f.token();r=response(f);f.report(t,r);r['bars'][0]['duties']['harmony_held']='no'
    check(f.history[-1]['data']['response']['bars'][0]['duties']['harmony_held']=='yes','deep report custody')
    check(all(f.history[-1]['data'][k] is False for k in ('performance_verified','audible_contrast_measured','automatic_score')),'manual outcome only')
    refuse(f,lambda:f.report(t,response(f)),'duplicate reply');f.finish(f.token());check(f.state=='completed','all five manual completion routes')
    before=deepcopy(f.history);p=plan(index);p['bpm']=86;f.set_plan(f.token(),p)
    check(f.state=='ready' and f.cycle==0 and f.history[:len(before)]==before,'new plan resets completion with history')
    for name in m.COMMON:
        for outcome in ('no','uncertain'):
            g=ready(index);reporting(g);r=response(g);r['common'][name]=outcome;g.report(g.token(),r)
            check(g.state=='needs_retry','negative common '+name);refuse(g,lambda:g.finish(g.token()),'negative common finish')
            g.retry(g.token(),'Repair chosen realization');check(g.state=='ready','explicit retry')
    for bar in range(4):
        for name in m.BAR_DUTIES:
            for outcome in ('no','uncertain'):
                g=ready(index);reporting(g);r=response(g);r['bars'][bar]['duties'][name]=outcome;g.report(g.token(),r)
                check(g.state=='needs_retry','negative each bar duty');refuse(g,lambda:g.finish(g.token()),'negative bar finish')
    # Every source-bound plan field is causally exercised, not just field presence.
    mutations=[]
    for v in (0,-1,True,None,'80',float('inf'),float('nan')):mutations.append(('tempo',lambda p,v=v:p.update(bpm=v)))
    for name in ('own_instrument','original_workbook'):mutations.append(('prerequisite',lambda p,name=name:p['prerequisites'].update({name:False})))
    mutations.extend([('harmony',lambda p:p.update(harmony='Am7')),('dynamic',lambda p:p.update(source_dynamic_transition='invented'))])
    for side in ('old','new'):
        mutations.extend([('texture',lambda p,side=side:p['states'][side].update(source_texture='invented')),
          ('empty voicing',lambda p,side=side:p['states'][side].update(voicing=[])),
          ('duplicate string',lambda p,side=side:p['states'][side].update(voicing=[{'string':'e','fret':8},{'string':'e','fret':12}])),
          ('wrong pitch',lambda p,side=side:p['states'][side].update(voicing=[{'string':'e','fret':9}])),
          ('accent groups',lambda p,side=side:p['states'][side].update(source_accent_groups=[2,3,3])),
          ('accent boolean',lambda p,side=side:p['states'][side].update(source_accent_groups=[True,3,2]))])
        for v in (-1,25,True,9.0,'9'):mutations.append(('fret',lambda p,side=side,v=v:p['states'][side]['voicing'][0].update(fret=v)))
        for v in ('X','b',None):mutations.append(('string',lambda p,side=side,v=v:p['states'][side]['voicing'][0].update(string=v)))
        for name in m.CONTROLS:
            mutations.append(('empty control',lambda p,side=side,name=name:p['states'][side]['controls'].update({name:' '})))
            mutations.append(('missing control',lambda p,side=side,name=name:p['states'][side]['controls'].pop(name)))
    for label,mutate in mutations:
        g=ready(index);p=plan(index);mutate(p);refuse(g,lambda:g.set_plan(g.token(),p),label)
    # Boundary and partial voicings are permitted choices, not proof of harmony/texture.
    for string,fret in [('E',0),('E',24),('A',3),('D',2),('G',0),('B',0),('e',8)]:
        g=ready(index);p=plan(index);p['states']['old']['voicing']=[{'string':string,'fret':fret}];g.set_plan(g.token(),p)
        check(g.plan['states']['old']['voicing']==p['states']['old']['voicing'],'alternative partial chord-tone choice')
    g=ready(index);reporting(g)
    bad=[]
    for bar in range(4):
        bad.extend([('bar number',lambda r,bar=bar:r['bars'][bar].update(bar=0)),
          ('bar boolean',lambda r,bar=bar:r['bars'][bar].update(bar=True)),
          ('side',lambda r,bar=bar:r['bars'][bar].update(side='new' if r['bars'][bar]['side']=='old' else 'old')),
          ('texture',lambda r,bar=bar:r['bars'][bar].update(source_texture='other')),
          ('duty enum',lambda r,bar=bar:r['bars'][bar]['duties'].update(harmony_held=True))])
    bad.extend([('short take',lambda r:r['bars'].pop()),('extra bar',lambda r:r['bars'].append(deepcopy(r['bars'][-1]))),
        ('wrong order',lambda r:r['bars'].reverse()),('notes',lambda r:r.update(notes='')),
        ('common enum',lambda r:r['common'].update(no_setup_pause='maybe')),('missing common',lambda r:r['common'].pop('no_setup_pause'))])
    for label,mutate in bad:
        r=response(g);mutate(r);refuse(g,lambda:g.report(g.token(),r),label)
    for target in ('setup','ready','performing','await_release','reporting','reported','needs_retry','completed'):
        h=m.ContrastFlow(m.KEYS[index])
        if target!='setup':h.set_plan(h.token(),plan(index))
        if target in ('performing','await_release','reporting','reported','needs_retry','completed'):h.begin(h.token())
        if target in ('await_release','reporting','reported','needs_retry','completed'):h.end_take(h.token(),True)
        if target in ('reporting','reported','needs_retry','completed'):h.release(h.token(),True)
        if target in ('reported','needs_retry','completed'):
            r=response(h)
            if target=='needs_retry':r['common']['no_setup_pause']='uncertain'
            h.report(h.token(),r)
        if target=='completed':h.finish(h.token())
        check(h.state==target,'fixture state');history=deepcopy(h.history);p=deepcopy(h.plan);t=h.token();h.cancel(t)
        refuse(h,lambda:h.cancel(t),'duplicate cancel');h.reopen(h.token());h.cancel(h.token());h.reopen(h.token())
        refuse(h,lambda:h.begin(h.token()),'reopen release bypass');h.release(h.token(),True)
        expected_resume='ready' if target in ('performing','await_release','reporting') else target
        check(h.state==expected_resume and h.plan==p and h.history[:len(history)]==history,'cancel/reopen custody and interrupted take restart')
    g=ready(index);foreign=ready(index);refuse(g,lambda:g.begin(foreign.token()),'foreign same-key instance')
    token=g.token();g.set_plan(g.token(),plan(index));refuse(g,lambda:g.begin(token),'stale generation')
    refuse(g,lambda:g.begin(list(g.token())),'token type');reporting(g);g.report(g.token(),response(g));t=g.token()
    refuse(g,lambda:g.retry(g.token(),''),'empty retry');g.retry(g.token(),'again');refuse(g,lambda:g.finish(t),'stale action')
try:m.ContrastFlow('exercise-completeness-r01/level075/moduled/p009-t1-r6/chorusoutro')
except m.Refusal:checks+=1;refusals+=1
else:raise AssertionError('invented sixth child accepted')
result={'result':'PASS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'causal_refusals':refusals,
 'packet':pin(packet),'test_source':pin(Path('Tests')/L/'check_contract.py'),'model':pin(Path('Tools')/L/'contrast_contract.py'),
 'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_performance':False,'audio_used':False,
 'native_valid':0,'integrated':0,'reviewed':0,'Accepted':0}
out=R/'Results'/L/'integrity.json';assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
