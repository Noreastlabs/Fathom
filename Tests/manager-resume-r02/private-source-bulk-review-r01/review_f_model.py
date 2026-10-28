"""Independent source-row, answer/order/retry/release checks for all14 keys."""
from copy import deepcopy
from source_oracles import F_ROWS,PC,TUNING_NAME

PLAN={'prerequisites':{'original_workbook':True,'own_instrument':True},
      'cue_provider':{'kind':'external_human','reference':'Independent synthetic cue fixture','ready':True}}
COMMON=('chord_context_correct','target_placed_inside_chord','sung_before_playing','single_silent_setup','no_searching','selected_string_set_used')
TRANSFER=('same_chord_role','same_target_pitch_class','second_string_set_used')

def contact(string,pc):
    fret=next(f for f in range(25) if (TUNING_NAME[string]+f)%12==pc)
    return {'string':string,'fret':fret,'midi':TUNING_NAME[string]+fret}

def choices(pc):
    a,b=contact('D',pc),contact('e',pc)
    return {'string_set_1':{'strings':['D'],'target':a,'voicing':[a]},
            'string_set_2':{'strings':['e'],'target':b,'voicing':[b]}}

def confirm(f):
    chord,role,_=F_ROWS[f.index]
    return {'key':f.key,'chord':chord,'role':role,'ready':True}

def initial(f,m,name=None,pc=None):
    wanted=F_ROWS[f.index][2].split(' / ')[0]
    if name is None:name=wanted
    if pc is None:pc=PC[wanted]
    f.set_plan(f.token(),PLAN);f.begin(f.token(),confirm(f))
    f.heard(f.token(),{'heard_chord_and_role':'yes'})
    f.sung_name(f.token(),{'pitch_name':name,'singing_attempted':True})
    f.choose_arrangements(f.token(),choices(pc))

def play(f):
    f.setup_target(f.token(),True);f.attack(f.token(),True);f.release(f.token(),True)
    if f.stage==0:f.reveal(f.token())

def report(f,diagnosis='',common='yes',count=1,speed='immediate'):
    chord,role,_=F_ROWS[f.index]
    return {'key':f.key,'chord':chord,'role':role,'string_set':('string_set_1','string_set_2')[f.stage],
      'target':f.target()['arrangement']['target'],'named_pitch':f.named_pitch,'attack_count':count,
      'common':dict.fromkeys(COMMON,common),
      'stage_duties':dict.fromkeys(('sung_pitch_correct',) if f.stage==0 else TRANSFER,'yes'),
      'response_speed':speed,'diagnosis':diagnosis,'notes':'Independent synthetic manual report; no actual observation.'}

def run(m,keys,q):
    q.check(len(keys)==14 and len(set(keys))==14,'F fourteen exact existing keys')
    for index,key in enumerate(keys):
        q.check(tuple(m.RAW[index])==F_ROWS[index],f'F row{index+1} original exact fields')
        f=m.ChordToneFlow(key);q.check('reference_pitch' not in f.learner_view(),'F withheld initial source answer')
        initial(f,m)
        q.check(f.state=='silent_setup' and 'reference_pitch' not in f.learner_view(),'F response remains blind before playing')
        q.refuse(lambda:f.reveal(f.token()),m.Refusal,'F early reveal',f)
        q.refuse(lambda:f.finish(f.token()),m.Refusal,'F early finish',f)
        before=f.token();f.setup_target(f.token(),True)
        q.refuse(lambda:f.attack(before,True),m.Refusal,'F stale action owner',f)
        f.attack(f.token(),True)
        q.refuse(lambda:f.report(f.token(),report(f)),m.Refusal,'F report before physical release/reveal',f)
        f.release(f.token(),True);f.reveal(f.token())
        q.check(f.learner_view()['reference_pitch']==F_ROWS[index][2],'F exact post-play reveal')
        bad=report(f);bad['attack_count']=True
        q.refuse(lambda:f.report(f.token(),bad),m.Refusal,'F bool attack count',f)
        bad=report(f);bad['credit_awarded']=True
        q.refuse(lambda:f.report(f.token(),bad),m.Refusal,'F hidden response credit',f)
        f.report(f.token(),report(f,speed='slow'))
        q.check(f.state=='reported' and f.history[-1]['data']['source_priority_guidance']==m.PRIORITY,'F source priority after manual slow response')
        q.check(f.history[-1]['data']['performance_verified'] is False,'F no performance observation')
        f.next_set(f.token());f.begin(f.token());play(f)
        f.report(f.token(),report(f));q.refuse(lambda:f.next_set(f.token()),m.Refusal,'F no third set',f)
        f.finish(f.token());q.check(f.state=='completed','F full two-set completion')
        q.check(f.history[-1]['data']['mastery_awarded'] is False and f.history[-1]['data']['performance_verified'] is False,'F completed manual/no mastery')
        q.refuse(lambda:f.attack(f.token(),True),m.Refusal,'F no attack after terminal',f)
        # All14 source rows take the wrong-response/diagnosis/retry branch.
        wrong=m.ChordToneFlow(key);wanted=PC[F_ROWS[index][2].split(' / ')[0]]
        wrongname=next(n for n in ['C','D','E','F','G','A','B'] if PC[n]!=wanted)
        initial(wrong,m,wrongname,PC[wrongname]);q.check('reference_pitch' not in wrong.learner_view(),'F wrong answer remains playable before reveal')
        play(wrong);q.refuse(lambda:wrong.report(wrong.token(),report(wrong)),m.Refusal,'F wrong answer needs diagnosis',wrong)
        wrong.report(wrong.token(),report(wrong,diagnosis='Compare after playing, then retry without searching.'))
        q.check(wrong.state=='needs_retry' and wrong.named_pitch==wrongname,'F original wrong response retained')
        wrong.retry(wrong.token(),'Explicit correction attempt.')
        q.check(wrong.state=='ready' and wrong.named_pitch is None and wrong.arrangements is None,'F retry clears initial choices, keeps history')
        q.check(wrong.response_history[0]['pitch_name']==wrongname,'F retry preserves wrong-answer evidence')
    # Unknown hearing and name, then diagnosed inability; no filled answer.
    f=m.ChordToneFlow(keys[0]);f.set_plan(f.token(),PLAN);f.begin(f.token(),confirm(f))
    f.heard(f.token(),{'heard_chord_and_role':'uncertain'});f.sung_name(f.token(),{'pitch_name':None,'singing_attempted':True})
    q.check(f.named_pitch is None,'F explicit unknown sung response')
    f.cannot_respond(f.token(),'Unable to locate the unknown response.',True)
    q.check(f.state=='needs_retry' and f.named_pitch is None,'F inability requires diagnosis without inventing answer')
    # Representative every reachable successful state: cancel/reopen requires release.
    f=m.ChordToneFlow(keys[0]);states=[deepcopy(f)]
    transitions=[lambda:f.set_plan(f.token(),PLAN),lambda:f.begin(f.token(),confirm(f)),
      lambda:f.heard(f.token(),{'heard_chord_and_role':'yes'}),
      lambda:f.sung_name(f.token(),{'pitch_name':'E','singing_attempted':True}),
      lambda:f.choose_arrangements(f.token(),choices(4)),lambda:f.setup_target(f.token(),True),
      lambda:f.attack(f.token(),True),lambda:f.release(f.token(),True),lambda:f.reveal(f.token()),
      lambda:f.report(f.token(),report(f)),lambda:f.next_set(f.token()),lambda:f.begin(f.token()),
      lambda:f.setup_target(f.token(),True),lambda:f.attack(f.token(),True),lambda:f.release(f.token(),True),
      lambda:f.report(f.token(),report(f)),lambda:f.finish(f.token())]
    for action in transitions:action();states.append(deepcopy(f))
    stable={'setup','ready','reporting','reported','needs_retry','completed'}
    for at in states:
        old=at.token();original=at.state
        at.cancel(at.token());q.check(at.state=='cancelled','F cancel '+original)
        q.refuse(lambda:at.reopen(old),m.Refusal,'F stale token after cancel',at)
        at.reopen(at.token());q.check(at.state=='reopen_release','F release fence '+original)
        q.refuse(lambda:at.release(at.token(),False),m.Refusal,'F no false release',at)
        at.release(at.token(),True)
        q.check(at.state==(original if original in stable else 'ready'),'F safe resume '+original)
    foreign=m.ChordToneFlow(keys[0]);fresh=m.ChordToneFlow(keys[0])
    q.refuse(lambda:fresh.set_plan(foreign.token(),PLAN),m.Refusal,'F foreign instance token',fresh)
    for patch in [dict(PLAN,clock=120),dict(PLAN,cue_provider={'kind':'app_audio','reference':'fixture','ready':True})]:
        q.refuse(lambda:fresh.set_plan(fresh.token(),patch),m.Refusal,'F unsupported plan fields/provider',fresh)
    for bad in [choices(4)]:
        bad['string_set_2']=deepcopy(bad['string_set_1'])
        q.refuse(lambda:m.validate_arrangements(bad),m.Refusal,'F duplicate chosen string set')
