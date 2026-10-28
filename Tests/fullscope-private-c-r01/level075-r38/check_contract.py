from pathlib import Path
from copy import deepcopy
import datetime,hashlib,importlib.util,json,resource
R=Path(__file__).resolve().parents[3];L=Path('fullscope-private-c-r01/level075-r38')
s=importlib.util.spec_from_file_location('recovery',R/'Tools'/L/'recovery_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
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
def plan(blocks=1,kind='external_partner'):
    return {'prerequisites':{'own_instrument':True,'original_workbook':True},
        'external_source':{'kind':kind,'reference':'Synthetic external provider, no delivered audio.',
            'capabilities':dict.fromkeys(m.CAPABILITIES,True)},'bpm':72,'material':'Synthetic chosen Cmaj7 rehearsal',
        'meter':'chosen4/4, not inferred source meter','eight_bar_blocks':blocks,
        'bar_reference':[{'bar':i,'active_chord':'Cmaj7','root_or_shell':'C E B','nearest_chord_tone_options':'C E G B',
            'texture':'learner chosen quarters','section':f'S{(i-1)//8+1}','section_boundary':i%8==1} for i in range(1,blocks*8+1)]}
def ready(index=0,blocks=1):
    f=m.RecoveryFlow(m.KEYS[index]);f.set_plan(f.token(),plan(blocks));return f
def reporting(f):f.begin(f.token(),True);f.end_take(f.token(),True);f.release(f.token(),True)
def response(f,others=None):
    kinds=[m.BANK[f.index]]*f.plan['eight_bar_blocks'] if others is None else others
    return {'global':dict.fromkeys(m.GLOBAL,'yes'),'notes':'Synthetic manual reply, no actual performance.',
        'blocks':[{'block':i,'bar_in_block':8,'failure':kind,'duties':dict.fromkeys(m.LOCAL,'yes'),
            'ladder':[{'step':j,'source_instruction':x,'followed':'yes'} for j,x in enumerate(m.LADDER,1)],
            'impact_measures':[1,2],'recovery_account':'Synthetic report referring to source action and deadline.'} for i,kind in enumerate(kinds,1)]}
def pin(p):
    p=Path(p);b=(R/p).read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
basepath=Path('Build/fullscope-private-c-r01/level075-r06/implementation-packet.jsonl')
base=[json.loads(x) for x in (R/basepath).read_text().splitlines()]
packet=Path('Build')/L/'recovery-overlay.jsonl';rows=[json.loads(x) for x in (R/packet).read_text().splitlines()]
source=json.loads((R/'Build'/L/'source-check.json').read_text())
expected=[('Wrong note','nearest chord tone','same beat'),('Wrong chord','shell of active chord','next beat'),
    ('Missed cue','stay current texture','join next bar'),('Lost subdivision','quarter notes','keep bar count'),
    ('Lost bar count','listen for harmonic landmark','rejoin at section boundary'),
    ('Broken string / gear','mute / simplify','preserve ensemble time'),('Lead phrase overrun','stop phrase','enter rhythm next bar')]
check(len(rows)==7 and [r['package_key'] for r in rows]==list(m.KEYS),'seven exact retained keys')
check('Fill too long\ndrop final notes\nprotect beat 1' in source['original_page_text'],'eighth row retained context')
check(source['context_eighth_row']['no_new_key'] and len(set(m.KEYS))==7,'no eighth official child')
check(source['full_footer'].endswith('less than one measure of the performance.'),'full strict source criterion')
check(source['recovery_order_txt_lines'][-1]=='6. Review only after the take ends.' and '6. REVIEW ONLY AFTER TAKE ENDS' in source['original_page_text'],'TXT and PDF wording both retained, no false exact equivalence')
for index,row in enumerate(rows):
    old=base[62+index];c=row['implementation']['task']['contract'];e=expected[index]
    for field in ('package_key','source_identity','source_refs','source_payload','timing_authority'):
        check(row[field]==old[field],'original '+field)
    check(row['implementation']['events']==old['implementation']['events']==[],'no note contacts invented')
    check(tuple(c['source_recovery_row'][x] for x in ('failure','immediate_action','deadline'))==e,'independent literal source fields')
    check(c['source_recovery_row']['priority'] is None,'unknown fourth column retained')
    check(source['original_page_text'].count('\n'.join(e))==1,'unique exact original row')
    check(c['source_context_header']=='240 CONTACTS' and c['fixed_source_contact_count'] is None,'no240 invented contacts')
    check(len(c['source_ladder'])==6 and len(c['source_context_failure_bank'])==8,'whole ladder and context bank')
    check(c['source_ladder'][-1]['instruction']=='REVIEW ONLY AFTER TAKE ENDS','full final instruction')
    for flag in ('automatic_evaluation','performance_observed','audio_supplied','failure_cues_supplied','timing_scheduled','mastery_awarded','credit_awarded','persistence'):
        check(c[flag] is False,flag)
    f=ready(index);p=plan();t=f.token()
    refuse(f,lambda:f.begin(t,False),'external source unavailable')
    refuse(f,lambda:f.begin(t,1),'readiness must be explicit bool')
    f.begin(t,True);check(f.state=='performing','fresh ready opens external rehearsal')
    check(not f.history[-1]['data']['audio_supplied'] and not f.history[-1]['data']['failure_cues_supplied'],'no app source claim')
    refuse(f,lambda:f.begin(t,True),'duplicate begin')
    refuse(f,lambda:f.set_plan(f.token(),p),'active plan change')
    refuse(f,lambda:f.report(f.token(),response(f)),'review before take end')
    refuse(f,lambda:f.release(f.token(),True),'release cannot bypass end take')
    refuse(f,lambda:f.end_take(f.token(),False),'take still running')
    f.end_take(f.token(),True);refuse(f,lambda:f.report(f.token(),response(f)),'before physical release')
    refuse(f,lambda:f.release(f.token(),False),'false release');refuse(f,lambda:f.set_plan(f.token(),p),'unreleased plan change')
    f.release(f.token(),True);refuse(f,lambda:f.set_plan(f.token(),p),'held report plan change')
    t=f.token();r=response(f);f.report(t,r);r['blocks'][0]['recovery_account']='outside mutation'
    check(f.history[-1]['data']['response']['blocks'][0]['recovery_account']!='outside mutation','response deep custody')
    refuse(f,lambda:f.report(t,response(f)),'duplicate report');f.finish(f.token());check(f.state=='completed','manual outcome only')
    saved=deepcopy(f.history);p=plan();p['bpm']=80;f.set_plan(f.token(),p);p['bar_reference'][0]['active_chord']='outside'
    check(f.state=='ready' and f.history[:-1]==saved and f.plan['bar_reference'][0]['active_chord']=='Cmaj7','new plan reset and custody')
    # Contextual cue choice never changes the bound key; chosen target must occur.
    for other in m.BANK:
        g=ready(index,2);reporting(g);r=response(g,[m.BANK[index],other]);g.report(g.token(),r)
        check(g.state=='reported' and g.key==m.KEYS[index],'any contextual second failure, exact key remains')
        check(all(not x['performance_verified'] for x in g.history[-1]['data']['comparisons']),'not acoustic verification')
    g=ready(index);reporting(g);r=response(g,[m.BANK[(index+1)%8]]);g.report(g.token(),r)
    check(g.state=='needs_retry' and not g.history[-1]['data']['target_failure_reported'],'unseen key not silently covered')
    refuse(g,lambda:g.finish(g.token()),'missing source target')
    for duty in [*m.GLOBAL,*m.LOCAL,*range(6)]:
        for value in ('no','uncertain'):
            g=ready(index);reporting(g);r=response(g)
            if duty in m.GLOBAL:r['global'][duty]=value
            elif duty in m.LOCAL:r['blocks'][0]['duties'][duty]=value
            else:r['blocks'][0]['ladder'][duty]['followed']=value
            g.report(g.token(),r);check(g.state=='needs_retry' and g.history[-1]['data']['response']==r,'failed source duty retained')
            refuse(g,lambda:g.finish(g.token()),'incomplete duty');refuse(g,lambda:g.begin(g.token(),True),'retry must be explicit')
            g.retry(g.token(),'Retry the failed source duty with external provider.')
            refuse(g,lambda:g.begin(g.token(),False),'readiness expires between takes')
    for measures,success in [([0,1],True),([999,1000],True),([2,2],False),([3,2],False),(None,False)]:
        g=ready(index);reporting(g);r=response(g);r['blocks'][0]['impact_measures']=measures;g.report(g.token(),r)
        check((g.state=='reported')==success,'strict <one measure from self-report only')
        check(g.history[-1]['data']['response']['blocks'][0]['impact_measures']==measures,'long/uncertain impact preserved')
    for state in ('setup','ready','performing','await_release','reporting','reported','needs_retry','completed'):
        g=m.RecoveryFlow(m.KEYS[index])
        if state!='setup':g.set_plan(g.token(),plan())
        if state in ('performing','await_release','reporting','reported','needs_retry','completed'):g.begin(g.token(),True)
        if state in ('await_release','reporting','reported','needs_retry','completed'):g.end_take(g.token(),True)
        if state in ('reporting','reported','needs_retry','completed'):g.release(g.token(),True)
        if state in ('reported','needs_retry','completed'):
            r=response(g)
            if state=='needs_retry':r['blocks'][0]['impact_measures']=[1,1]
            g.report(g.token(),r)
        if state=='completed':g.finish(g.token())
        check(g.state==state,'cancellation fixture');history=deepcopy(g.history);oldplan=deepcopy(g.plan);t=g.token()
        g.cancel(t);refuse(g,lambda:g.cancel(g.token()),'duplicate cancel');g.reopen(g.token())
        refuse(g,lambda:g.begin(t,True),'stale old cycle');refuse(g,lambda:g.begin(g.token(),True),'reopen release fence')
        g.cancel(g.token());g.reopen(g.token());g.release(g.token(),True)
        check(g.state==('ready' if state in ('performing','await_release','reporting') else state),'interrupted take restarts')
        check(g.plan==oldplan and g.history[:len(history)]==history,'all previous replies/reveals and choices retained')

f=m.RecoveryFlow(m.KEYS[0]);p=plan();mutants=[]
def bad(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
for v in (0,-1,True,'72',float('inf'),float('nan'),10**1000):bad('invalid BPM',lambda q,v=v:q.__setitem__('bpm',v))
for k in p['prerequisites']:bad('missing prerequisite',lambda q,k=k:q['prerequisites'].__setitem__(k,False))
for k in m.CAPABILITIES:bad('incapable external source',lambda q,k=k:q['external_source']['capabilities'].__setitem__(k,False))
for k,v in [('kind','app_audio'),('reference','')]:bad('invalid external provider',lambda q,k=k,v=v:q['external_source'].__setitem__(k,v))
for k in ('material','meter'):bad('missing choice',lambda q,k=k:q.__setitem__(k,''))
for v in (0,-1,True,1.5):bad('invalid block count',lambda q,v=v:q.__setitem__('eight_bar_blocks',v))
bad('missing reference bar',lambda q:q['bar_reference'].pop())
bad('duplicate bar',lambda q:q['bar_reference'][1].__setitem__('bar',1))
bad('boolean bar',lambda q:q['bar_reference'][0].__setitem__('bar',True))
for k in ('active_chord','root_or_shell','nearest_chord_tone_options','texture','section'):
    bad('missing reference role',lambda q,k=k:q['bar_reference'][0].__setitem__(k,''))
bad('no section boundary',lambda q:[b.__setitem__('section_boundary',False) for b in q['bar_reference']])
bad('untyped boundary',lambda q:q['bar_reference'][0].__setitem__('section_boundary',1))
bad('hidden future schedule not accepted',lambda q:q.__setitem__('future_failures',['wrongnote']))
for label,q in mutants:refuse(f,lambda q=q:f.set_plan(f.token(),q),label)
f.set_plan(f.token(),plan(1,'external_practice_track'));check(f.state=='ready','capable external track supported')
f=ready();t=f.token()
for i in range(6):
    x=list(t);x[i]='foreign' if type(t[i]) is str else 99;refuse(f,lambda x=tuple(x):f.begin(x,True),'token owner component')
refuse(f,lambda:f.begin(ready().token(),True),'foreign instance');reporting(f)
mutants=[];p=response(f)
def bad_report(label,fn):
    q=deepcopy(p);fn(q);mutants.append((label,q))
bad_report('missing global',lambda q:q.__setitem__('global',{}));bad_report('missing note',lambda q:q.__setitem__('notes',''))
bad_report('missing failure',lambda q:q['blocks'].clear());bad_report('extra failure',lambda q:q['blocks'].append(deepcopy(q['blocks'][0])))
for k,v in [('block',2),('block',True),('bar_in_block',0),('bar_in_block',9),('bar_in_block',True),('failure','invented_failure'),('recovery_account','')]:
    bad_report('invalid block field',lambda q,k=k,v=v:q['blocks'][0].__setitem__(k,v))
for v in ([1,0],[-1,2],[True,2],[1,-1],[1,True],[.5,1],(1,2),'1/2'):
    bad_report('invalid impact shape',lambda q,v=v:q['blocks'][0].__setitem__('impact_measures',v))
bad_report('missing ladder duty',lambda q:q['blocks'][0]['ladder'].pop())
bad_report('reordered ladder',lambda q:q['blocks'][0]['ladder'].reverse())
bad_report('changed source ladder',lambda q:q['blocks'][0]['ladder'][5].__setitem__('source_instruction','Review during take'))
bad_report('bool ladder step',lambda q:q['blocks'][0]['ladder'][0].__setitem__('step',True))
bad_report('unknown manual reply',lambda q:q['blocks'][0]['duties'].__setitem__('pulse_preserved','verified'))
for label,q in mutants:refuse(f,lambda q=q:f.report(f.token(),q),label)
f.report(f.token(),response(f));check(f.state=='reported','valid current response after refusals')
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,'causal_refusals':refusals,
    'finite_existing_keys':7,'context_failure_kinds':8,'cross_key_context_combinations_tested':56,'source_contacts_invented':0,
    'packet':pin(packet),'base':pin(basepath),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    'native_runs':0,'app_runs':0,'audio_or_failure_cues_supplied':0,'actual_performances':0}
p=R/'Results'/L/'integrity.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
