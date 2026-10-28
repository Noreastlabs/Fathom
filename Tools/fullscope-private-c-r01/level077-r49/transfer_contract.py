"""Private manual interval/register transfer. No clock, audio, storage or credit."""
from copy import deepcopy
from uuid import uuid4

RAW=(('C','M3'),('F#','P5'),('Bb','m3'),('E','M6'),('Ab','P4'),('D','m7'),
     ('B','M7'),('F','M2'),('C#','TT'),('G','m6'),('Eb','m2'),('A','P8'))
KEYS=tuple(f'exercise-completeness-r01/level077/modulea/p004-t1-r{n}/{n}' for n in range(1,13))
PC={'C':0,'C#':1,'D':2,'Eb':3,'E':4,'F':5,'F#':6,'G':7,'Ab':8,'A':9,'Bb':10,'B':11}
SEMITONES={'m2':1,'M2':2,'m3':3,'M3':4,'P4':5,'TT':6,'P5':7,'m6':8,'M6':9,'m7':10,'M7':11,'P8':12}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64}
REGISTERS=('low','mid','high');YN=('yes','no','uncertain')
COMMON=('target_correct','interval_sound_maintained','single_silent_setup','no_searching','source_order')
INITIAL=('singing_performed','singing_correct')
TRANSFER=('without_re_singing','same_pitch_class','new_sounding_register')
FOOTER='After the first correct note, repeat the same pitch class in two other registers without re-singing. This converts interval hearing into immediate neck navigation.'
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
PURPOSE='Hear -> label -> sing -> locate silently -> play one decisive attack -> verify -> transfer.'

class Refusal(ValueError):pass
def require(ok,message):
    if not ok:raise Refusal(message)
def fields(value,names):require(type(value) is dict and set(value)==set(names),'exact field set')
def text(value):return type(value) is str and bool(value.strip())

def validate_plan(p,i):
    require(type(i) is int and 0<=i<len(KEYS),'source row index')
    fields(p,('prerequisites','provider','direction','root_midi','registers','first_register','transfer_order'))
    fields(p['prerequisites'],('own_instrument','original_workbook'))
    require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    provider=p['provider'];fields(provider,('kind','reference','ready'))
    require(type(provider['kind']) is str and provider['kind'] in ('external_human','external_recording') and text(provider['reference']) and provider['ready'] is True,'capable external root source')
    require(type(p['direction']) is str and p['direction'] in ('up','down'),'explicit authored direction')
    root=p['root_midi'];require(type(root) is int and 0<=root<=127 and root%12==PC[RAW[i][0]],'chosen root matches printed pitch class')
    target=root+SEMITONES[RAW[i][1]]*(1 if p['direction']=='up' else -1)
    require(0<=target<=127,'chosen signed interval within MIDI')
    regs=p['registers'];fields(regs,REGISTERS);midis=[]
    for label in REGISTERS:
        c=regs[label];fields(c,('midi','string','fret'))
        require(type(c['midi']) is int and 0<=c['midi']<=127 and c['midi']%12==target%12,'same destination pitch class')
        require(type(c['string']) is str and c['string'] in TUNING and type(c['fret']) is int and 0<=c['fret']<=24 and TUNING[c['string']]+c['fret']==c['midi'],'chosen standard-tuning sounding contact')
        midis.append(c['midi'])
    require(midis[0]<midis[1]<midis[2],'three distinct sounding registers; same MIDI is not another register')
    first=p['first_register'];require(type(first) is str and first in REGISTERS and regs[first]['midi']==target,'first target is exact signed interval')
    order=p['transfer_order'];require(type(order) is list and len(order)==3 and all(type(x) is str for x in order) and set(order)==set(REGISTERS) and order[0]==first,'first then each other register once')

class TransferFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact twelve source children')
        self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.stage=self.cycle=self.action=0;self.state='setup';self.plan=None
        self.history=[];self.resume=None;self.first_correct=None
    def token(self):return (self.instance,self.key,self.generation,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):
        require(type(t) is tuple and t==self.token(),'current instance/source/generation/stage/action token')
        require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'stage':self.stage,'cycle':self.cycle,'data':deepcopy(data)})
        self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.stage=self.cycle=0;self.first_correct=None
        self.record('plan',p,'ready')
    def target(self):
        require(self.plan is not None,'plan required');label=self.plan['transfer_order'][self.stage]
        return {'register':label,'contact':deepcopy(self.plan['registers'][label])}
    def provider_view(self):
        require(self.plan is not None,'plan required')
        return {'source_root':RAW[self.index][0],'source_interval':RAW[self.index][1],
          'authored_direction_choice':self.plan['direction'],'chosen_root_midi':self.plan['root_midi'],
          'initial_chosen_destination':deepcopy(self.plan['registers'][self.plan['first_register']]),
          'supply':'chosen root reference for initial hearing' if self.stage==0 else 'no new root playback or singing required',
          'audio_supplied':False}
    def begin(self,t,provider_ready=None):
        self.check(t,('ready',))
        if self.stage==0:require(provider_ready is True,'current external root readiness')
        else:
            require(self.first_correct is not None,'first correct manual report required')
            require(provider_ready is None,'transfer retains first target without new required root playback')
        self.cycle+=1;self.record('begin',{'performance_observed':False},'hearing_root' if self.stage==0 else 'silent_setup')
    def heard_root(self,t,ack):
        self.check(t,('hearing_root',));require(ack is True,'root hearing attempted');self.record('heard_root',{},'singing')
    def sung(self,t,ack):
        self.check(t,('singing',));require(ack is True,'initial destination singing attempted');self.record('sung',{},'silent_setup')
    def setup_target(self,t,ack):
        self.check(t,('silent_setup',));require(ack is True,'single silent setup attempted');self.record('silent_setup',self.target(),'attack')
    def attempt_attack(self,t,ack):
        self.check(t,('attack',));require(ack is True,'one decisive attack attempted');self.record('attack_attempt',{'actual_attack_count_observed':None},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual physical release required')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'saved resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('source_interval','register','contact','attack_count','common','stage_duties','diagnosis','notes'))
        fields(r['common'],COMMON);fields(r['stage_duties'],INITIAL if self.stage==0 else TRANSFER)
        fields(r['contact'],('midi','string','fret'));target=self.target()
        require(r['source_interval']==RAW[self.index][1] and r['register']==target['register'] and r['contact']==target['contact'] and type(r['contact']['midi']) is int and type(r['contact']['fret']) is int,'bound source interval/register/contact response')
        require(type(r['attack_count']) is int and r['attack_count']>=0 and all(type(v) is str and v in YN for v in (*r['common'].values(),*r['stage_duties'].values())) and type(r['diagnosis']) is str and text(r['notes']),'complete typed manual report')
        ok=r['attack_count']==1 and all(v=='yes' for v in (*r['common'].values(),*r['stage_duties'].values()))
        if not ok:require(text(r['diagnosis']),'wrong/uncertain/searching/multiple-attack diagnosis')
        if ok and self.stage==0:self.first_correct={'generation':self.generation,'cycle':self.cycle,'target':target,'manual_self_report':True,'performance_verified':False}
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def next_register(self,t):
        self.check(t,('reported',));require(self.stage<2 and self.first_correct is not None,'no fourth register and first-correct gate')
        self.stage+=1;self.cycle=0;self.record('next_register',{},'ready')
    def retry(self,t,diagnosis):
        self.check(t,('reported','needs_retry'));require(text(diagnosis),'explicit retry diagnosis')
        if self.stage==0:self.first_correct=None
        self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):
        self.check(t,('reported',));require(self.stage==2 and self.first_correct is not None,'all three sounding registers required')
        self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','hearing_root','singing','silent_setup','attack','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume='ready' if self.state in ('hearing_root','singing','silent_setup','attack','await_release','reporting') else self.state
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):
        self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    root,quality=RAW[i]
    return {'schema_version':'fathom-private-interval-register-transfer-manual.1','key':KEYS[i],
      'source_fields':{'Card':str(i+1),'Given root':root,'Requested interval':quality,'Sing destination':'','Low / mid / high':''},
      'requested_interval_semitones':SEMITONES[quality],'source_footer':FOOTER,'source_no_search':NO_SEARCH,'source_purpose':PURPOSE,
      'source_extent_header':'12 ROOTS | 48 REALIZATIONS','source_direction':None,'source_register_bounds':None,
      'source_note_events':[],'source_octave_fret_timing':None,
      'plan_schema':{'external_source':['external_human','external_recording'],'direction':['up','down'],
        'registers':'low/mid/high chosen strictly increasing MIDI, same destination pitch class; standard-tuning string/fret0..24',
        'first_register':'exact chosen root plus signed requested interval','order':'first then both other registers, each once'},
      'response_schema':{'common_duties':list(COMMON),'initial_duties':list(INITIAL),'transfer_duties':list(TRANSFER),
        'enum':list(YN),'binding':'exact interval, chosen register/contact and actual attack count; failed or uncertain report needs diagnosis'},
      'authored_policies':['Direction, root octave, low/mid/high relative register bounds, string/fret and transfer order are explicit learner choices, not printed realizations.',
        'Initial hear-root/sing/silent-setup/one-attack/release/report; only manually reported correct initial note opens two other registers.',
        'Later transfers/retries retain initial pitch class, with no re-singing action or required new root playback; same sounding MIDI on another string is not a new register.',
        'Every attack count and actual pitch/singing/no-search result is self-report; diagnosis/retry required for any no/uncertain or count other than one.',
        'Current source/stage/action tokens and physical release fences; cancel/reopen repeats interrupted register and preserves plan/history; new plan resets initial stage.',
        'The 48 REALIZATIONS header is retained literally and is not converted into invented source contacts or source event counts.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,
      'timing_scheduled':False,'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
