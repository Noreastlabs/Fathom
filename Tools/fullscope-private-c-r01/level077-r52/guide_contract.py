"""Named guide tones sung before a selected shell; all performance is manual."""
from copy import deepcopy
from uuid import uuid4
RAW=(('Cmaj7','E','3','B','7'),('Dm7','F','b3','C','b7'),('G7','B','3','F','b7'),('Fmaj7','A','3','E','7'),
 ('AmMaj7','C','b3','G#','7'),('Bm7b5','D','b3','A','b7'),('E7','G#','3','D','b7'),('Dm7','F','b3','C','b7'))
SPEC=((7,1,'cmaj7',67),(7,2,'dm7',68),(7,3,'g7',69),(7,6,'fmaj7',71),
      (8,1,'ammaj7',73),(8,2,'bm7b5',74),(8,3,'e7',75),(8,6,'dm7',77))
KEYS=tuple(f'exercise-completeness-r01/level077/modulec/p{p:03d}-t1-r{row}/{slug}' for p,row,slug,_ in SPEC)
ROOT=('C','D','G','F','A','B','E','D');PC={'C':0,'D':2,'E':4,'F':5,'G':7,'G#':8,'A':9,'B':11}
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};ROLES=('root','guide1','guide2');YN=('yes','no','uncertain')
DUTIES=('guide1_sung_correct','guide2_sung_correct','both_sung_before_hand_movement','single_silent_setup','no_searching','selected_shell_played','source_order')
NO_SEARCH='After the target is sung, use one silent setup and one attack. Diagnose a wrong attack; do not slide around until the note is found.'
HEADINGS=('THE THIRD AND SEVENTH ARE SUNG BEFORE THE CHORD IS PLAYED','HEAR THE RAISED LEADING TONE BEFORE THE HAND MOVES')
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(o,keys):require(type(o) is dict and set(o)==set(keys),'exact typed field set')
def text(v):return type(v) is str and bool(v.strip())
def source_guides(i):return [{'pitch_class':RAW[i][1],'role':RAW[i][2]},{'pitch_class':RAW[i][3],'role':RAW[i][4]}]
def validate_plan(p,i):
    require(type(i) is int and 0<=i<8,'exact row index');fields(p,('prerequisites','sung_midi','shell_form','shell_contacts'))
    fields(p['prerequisites'],('own_instrument','original_workbook'));require(all(x is True for x in p['prerequisites'].values()),'instrument/workbook prerequisites')
    fields(p['sung_midi'],('guide1','guide2'))
    for role,pitch in [('guide1',RAW[i][1]),('guide2',RAW[i][3])]:
        n=p['sung_midi'][role];require(type(n) is int and 0<=n<=127 and n%12==PC[pitch],'chosen sung guide MIDI matches source pitch class')
    require(p['shell_form']=='root_third_seventh','explicit authored shell form')
    contacts=p['shell_contacts'];fields(contacts,ROLES);strings=[]
    for role,pitch in zip(ROLES,(ROOT[i],RAW[i][1],RAW[i][3])):
        c=contacts[role];fields(c,('string','fret'));s=c['string'];f=c['fret']
        require(type(s) is str and s in TUNING and type(f) is int and 0<=f<=24 and (TUNING[s]+f)%12==PC[pitch],'selected role contact matches source/derived pitch class')
        strings.append(s)
    require(len(set(strings))==3,'three distinct strings for selected shell')
class GuideFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact eight unquarantined rows');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.cycle=self.action=0;self.state='setup';self.plan=None;self.history=[];self.resume=None
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/instance/generation/action token');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','ready','reported','needs_retry','completed'));validate_plan(p,self.index);self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.record('plan',p,'ready')
    def view(self):
        out={'chord':RAW[self.index][0],'guides':source_guides(self.index),'task':'sing both -> play shell',
          'source_heading':HEADINGS[0 if self.index<4 else 1],'audio_supplied':False,'source_fixed_note_events':[],
          'whole_chord_quality_automatically_verified':False,'selected_shell_omits_fifth':True,'state':self.state}
        if self.plan is not None:out['chosen_realization']=deepcopy(self.plan)
        return out
    def begin(self,t,ready):self.check(t,('ready',));require(ready is True,'current learner/instrument readiness');self.cycle+=1;self.record('begin',{},'read_cue')
    def cue_read(self,t,ack):self.check(t,('read_cue',));require(ack is True,'named chord/guide cue read');self.record('cue_read',{},'sing_guide1')
    def sing_guide(self,t,which,ack):
        require(type(which) is int and which in (1,2),'guide index');self.check(t,('sing_guide'+str(which),));require(ack is True,'guide singing attempted')
        self.record('sing_guide'+str(which),{'source_guide':source_guides(self.index)[which-1]},'sing_guide2' if which==1 else 'silent_setup')
    def setup_target(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'single silent hand setup');self.record('silent_setup',{},'attack')
    def attempt_attack(self,t,ack):self.check(t,('attack',));require(ack is True,'one shell attack attempted');self.record('attack_attempt',{'actual_attack_count_observed':None},'await_release')
    def release(self,t,ack):
        self.check(t,('await_release','reopen_release'));require(ack is True,'manual physical release')
        if self.state=='await_release':self.record('release',{},'reporting')
        else:
            state=self.resume;require(state is not None,'resume state');self.resume=None;self.record('reopen_release',{},state)
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('chord','source_guides','chosen_contacts','attack_count','duties','diagnosis','notes'));fields(r['duties'],DUTIES)
        require(r['chord']==RAW[self.index][0] and r['source_guides']==source_guides(self.index) and r['chosen_contacts']==self.plan['shell_contacts'],'source chord/guide/selected-contact binding')
        fields(r['chosen_contacts'],ROLES)
        for c in r['chosen_contacts'].values():fields(c,('string','fret'));require(type(c['fret']) is int,'typed contact fret')
        require(type(r['attack_count']) is int and r['attack_count']>=0 and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'full typed manual report')
        ok=r['attack_count']==1 and all(x=='yes' for x in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/uncertain/count/search diagnosis')
        self.record('report',{'response':r,'manual_requirements_reported':ok,'performance_verified':False,'whole_chord_quality_verified':False,'automatic_score':False},'reported' if ok else 'needs_retry')
    def retry(self,t,diagnosis):self.check(t,('reported','needs_retry'));require(text(diagnosis),'explicit retry diagnosis');self.record('retry',{'diagnosis':diagnosis},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        self.check(t,('setup','ready','read_cue','sing_guide1','sing_guide2','silent_setup','attack','await_release','reporting','reported','needs_retry','completed','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in ('setup','ready','reported','needs_retry','completed') else 'ready'
        self.generation+=1;self.record('cancel',{},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')
def contract(i):
    chord,g1,r1,g2,r2=RAW[i]
    return {'schema_version':'fathom-private-sung-guide-shell-manual.1','key':KEYS[i],
      'source_fields':{'Chord':chord,'Guide 1':g1,'Role 1':r1,'Guide 2':g2,'Role 2':r2,'Task':'sing both -> play shell'},
      'source_heading':HEADINGS[0 if i<4 else 1],'source_page_extent':'10 VOICES | 60 SUNG TARGETS','source_no_search':NO_SEARCH,
      'source_note_events':[],'source_fixed_octave_fret_timing':None,'source_role_tokens_are_rests':False,
      'plan_schema':{'prerequisites':['own instrument','original workbook'],'sung_midi':'explicit chosen MIDI for each printed guide pitch class',
        'selected_shell_form':'root_third_seventh','selected_contacts':'three distinct standard-tuning strings/frets0..24, roles root/guide1/guide2',
        'derived_root_pitch_class':ROOT[i],'source_exclusive_shell_definition':False},
      'response_schema':{'binding':'exact source chord/guides and chosen contacts','attack_count':'nonnegative integer; positive manual outcome exactly one',
        'manual_duties':list(DUTIES),'manual_enum':list(YN),'failure':'required diagnosis and explicit repeat, no search-until-correct shortcut'},
      'authored_policies':['Guide1 then guide2 is a selected presentation order; source says sing both. Both are sung before silent hand setup and shell attack.',
        'Chosen root/third/seventh shell is an authored realization, not source-fixed notes or an exclusive definition of shell.',
        'Selected shell omits fifth. For Bm7b5 this cannot distinguish half-diminished from minor-seventh quality by shell alone; full source label remains unchanged.',
        'Actual pitch/hearing-before-hand/attack correctness is self-report, not microphone observation. No preceding app chord playback is supplied or required.',
        'Current-action/release/cancel/reopen/new-plan fences; interrupted row repeats after release with plan/history retained.',
        'Page voice-leading/transposition/dominant tests belong to separate supplement children, not completed by this individual-row contract.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
