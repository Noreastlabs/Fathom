"""Two delayed auditory-memory tasks with chord naming or chosen transposition; external pulse and manual reports only."""
from copy import deepcopy
from fractions import Fraction
from uuid import uuid4
import math
QUESTIONS=(('E','G#','B','D'),('A','C','E','G#'))
KEYS=tuple(f'exercise-completeness-r01/level077/modulee/p012-t1-r{i}/{i}' for i in (7,8))
DELAYS=('2 bars + name chord','4 bars + transpose');PC={'C':0,'D':2,'E':4,'F':5,'G':7,'G#':8,'A':9,'B':11}
QUALITIES=('major','minor','diminished','augmented','dominant7','major7','minor7','minor_major7','half_diminished7','diminished7','unknown')
TUNING={'E':40,'A':45,'D':50,'G':55,'B':59,'e':64};YN=('yes','no','uncertain')
BEAT_DUTIES=('hands_unformed','auditory_memory','counted')
DELAY_DUTIES=('external_pulse_followed','full_required_delay_elapsed','hands_not_formed','auditory_memory_maintained','counted')
PLAY_DUTIES=('remembered_phrase_sung','hand_formed_only_after_response_began','one_silent_setup_per_target','no_searching','pitches_correct','rhythm_correct','source_order')
def play_duties(i):return PLAY_DUTIES+(('chord_named_before_hand',) if i==0 else ('chosen_transposition_attempted',))
FOOTER='Do not silently finger the phrase during the delay. Keep the memory auditory: sing internally, count, and form the hand only when the response begins.'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,n):require(type(x) is dict and set(x)==set(n),'exact typed field set')
def text(x):return type(x) is str and bool(x.strip())
def qtime(x,zero=False):
    require(type(x) is list and len(x)==2 and all(type(v) is int for v in x) and x[1]>0 and (x[0]>=0 if zero else x[0]>0) and math.gcd(*x)==1,'canonical rational quantity')
    return Fraction(*x)
def rhythm_signature(r):
    fields(r,('onsets_q','durations_q','length_q'));on=r['onsets_q'];dur=r['durations_q'];length=qtime(r['length_q'])
    require(type(on) is list and type(dur) is list and len(on)==len(dur)==4,'four rhythm targets')
    starts=tuple(qtime(x,True) for x in on);spans=tuple(qtime(x) for x in dur)
    require(all(a+d<=length for a,d in zip(starts,spans)) and all(starts[i]+spans[i]<=starts[i+1] for i in range(3)),'ordered nonoverlap inside chosen phrase')
    return starts,spans,length
def midi4(m):require(type(m) is list and len(m)==4 and all(type(x) is int and 40<=x<=88 for x in m),'four playable chosen MIDI targets')
def validate_plan(p,i):
    require(type(i) is int and 0<=i<2,'exact two source indices')
    fields(p,('prerequisites','provider','external_pulse','task_choice'));fields(p['prerequisites'],('original_workbook','own_instrument'));require(all(v is True for v in p['prerequisites'].values()),'manual prerequisites')
    v=p['provider'];fields(v,('kind','reference','ready','question_midi','question_rhythm'))
    require(v['kind']=='external_human' and text(v['reference']) and v['ready'] is True,'actual external source player');midi4(v['question_midi'])
    require([x%12 for x in v['question_midi']]==[PC[x] for x in QUESTIONS[i]],'exact source pitch-class order');rhythm_signature(v['question_rhythm'])
    e=p['external_pulse'];fields(e,('reference','beats_per_bar','beat_unit_q'));require(text(e['reference']) and type(e['beats_per_bar']) is int and 1<=e['beats_per_bar']<=16,'explicit external pulse and chosen finite meter');qtime(e['beat_unit_q'])
    if i==0:require(p['task_choice'] is None,'naming task has no transposition choice')
    else:
        c=p['task_choice'];fields(c,('semitones','rhythm_policy'));n=c['semitones']
        require(type(n) is int and -24<=n<=24 and n%12!=0 and c['rhythm_policy']=='same_as_question','explicit finite non-octave transposition and same-rhythm option')
        require(all(40<=x+n<=88 for x in v['question_midi']),'chosen transposed targets playable')
def validate_recalled(p):
    fields(p,('midi','rhythm','contacts'));midi4(p['midi']);rhythm_signature(p['rhythm']);require(type(p['contacts']) is list and len(p['contacts'])==4,'four recalled target contacts')
    for x,n in zip(p['contacts'],p['midi']):
        fields(x,('string','fret'));require(type(x['string']) is str and x['string'] in TUNING and type(x['fret']) is int and 0<=x['fret']<=24 and TUNING[x['string']]+x['fret']==n,'contact matches learner-entered MIDI, not hidden source correctness')

class DelayFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact two page12 naming/transposition keys');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.cycle=self.beat_count=self.action=0;self.state='setup';self.plan=self.recalled=self.resume=None
        self.history=[];self.beat_reports=[];self.recall_history=[];self.chord_history=[];self.named_chord=None;self.delay_start_hands=None;self.current_revealed=self.ever_revealed=False
        self.source_release_required=self.source_stop_requested=False
    def token(self):return (self.instance,self.key,self.generation,self.cycle,self.beat_count,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current source/cycle/beat/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'cycle':self.cycle,'beat':self.beat_count,'data':deepcopy(data)});self.action+=1;self.state=state
    def required_beats(self):
        require(self.plan is not None,'source plan required');b=self.plan['external_pulse']['beats_per_bar'];return (2*b,4*b)[self.index]
    def reset_current(self):self.named_chord=None;self.beat_count=0;self.beat_reports=[];self.delay_start_hands=None;self.recalled=None;self.current_revealed=False
    def set_plan(self,t,p):
        self.check(t,('setup','completed'));validate_plan(p,self.index);require(not self.source_release_required,'source release pending')
        self.plan=deepcopy(p);self.generation+=1;self.cycle=0;self.reset_current();self.record('chosen_source_plan',p,'ready')
    def expected_midi(self):
        require(self.plan is not None,'current plan');shift=0 if self.index==0 else self.plan['task_choice']['semitones']
        return [x+shift for x in self.plan['provider']['question_midi']]
    def source_player_view(self):
        return {'key':self.key,'printed_question':list(QUESTIONS[self.index]),'printed_delay':DELAYS[self.index],
          'chosen_question':None if self.plan is None else deepcopy(self.plan['provider']),'chosen_pulse':None if self.plan is None else deepcopy(self.plan['external_pulse']),
          'required_beats':None if self.plan is None else self.required_beats(),'manual_stop_requested':self.source_stop_requested,'manual_source_release_required':self.source_release_required,
          'instruction':'Stop source sound and confirm manually' if self.source_stop_requested else 'Supply the chosen question; mark its actual end as the external silent-delay boundary. Continue external pulse; no learner hand formation until response begins.',
          'audio_supplied_by_app':False,'clock_owned':False,'task_choice':None if self.plan is None else deepcopy(self.plan['task_choice']),
          'reference_answer':{'root_pitch_class':4,'quality':'dominant7'} if self.index==0 else (None if self.plan is None else {'derived_transposed_midi':self.expected_midi()})}
    def learner_view(self):
        out={'state':self.state,'printed_delay':DELAYS[self.index],'required_beats':None if self.plan is None else self.required_beats(),'manual_beat_reports':self.beat_count,
          'previously_revealed':self.ever_revealed,'prior_recall_retained':bool(self.recall_history),'blind_assessment_claim':False,
          'hand_formation_allowed':self.state in ('recall_plan','sing_response','silent_setup','play_response','response_release','reveal','reporting','reported','completed')}
        out['chosen_task']=None if self.plan is None else deepcopy(self.plan['task_choice'])
        out['learner_named_chord']=deepcopy(self.named_chord);out['previous_chord_response_retained']=bool(self.chord_history)
        if self.current_revealed:out['reference_answer']={'root_pitch_class':4,'quality':'dominant7'} if self.index==0 else {'derived_transposed_midi':self.expected_midi()}
        if self.recalled is not None:out['learner_entered_recall']=deepcopy(self.recalled)
        if self.current_revealed:out['reference_question']={'notes':list(QUESTIONS[self.index]),'chosen_midi':deepcopy(self.plan['provider']['question_midi']),'chosen_rhythm':deepcopy(self.plan['provider']['question_rhythm'])}
        return out
    def begin_question(self,t,c):
        self.check(t,('ready',));fields(c,('key','ready','same_chosen_question'));require(c['key']==self.key and c['ready'] is True and c['same_chosen_question'] is True,'current external source confirmation')
        self.cycle+=1;self.reset_current();self.source_release_required=True;self.source_stop_requested=False;self.record('question_started',{'confirmation':c,'audio_observed':False},'listening')
    def source_ended_start_delay(self,t,c):
        self.check(t,('listening',));fields(c,('source_stopped','hands_unformed'));require(c['source_stopped'] is True and type(c['hands_unformed']) is str and c['hands_unformed'] in YN,'manual source end boundary and truthful hand report')
        self.source_release_required=self.source_stop_requested=False;self.delay_start_hands=c['hands_unformed']
        self.record('manual_source_end_delay_boundary',{'confirmation':c,'actual_elapsed_time_measured':False,'source_stop_acoustically_verified':False},'delay')
    def beat(self,t,r):
        self.check(t,('delay',));fields(r,('ordinal','duties'));fields(r['duties'],BEAT_DUTIES)
        require(type(r['ordinal']) is int and r['ordinal']==self.beat_count+1 and r['ordinal']<=self.required_beats(),'next exact external-beat ordinal')
        require(all(type(x) is str and x in YN for x in r['duties'].values()),'manual auditory/hand/count reports')
        self.beat_count+=1;self.beat_reports.append(deepcopy(r));self.record('manual_external_beat',r,'delay_review' if self.beat_count==self.required_beats() else 'delay')
    def review_delay(self,t,r):
        self.check(t,('delay_review',));fields(r,('key','beats','duties','diagnosis','notes'));fields(r['duties'],DELAY_DUTIES)
        require(r['key']==self.key and type(r['beats']) is int and r['beats']==self.required_beats() and all(type(v) is str and v in YN for v in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual elapsed-delay review')
        ok=self.delay_start_hands=='yes' and all(v=='yes' for b in self.beat_reports for v in b['duties'].values()) and all(v=='yes' for v in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'failed/uncertain delay diagnosis')
        self.record('delay_review',{'response':r,'manual_requirements_reported':ok,'elapsed_time_measured':False,'physical_hand_observed':False},('name_chord' if self.index==0 else 'response_ready') if ok else 'needs_retry')
    def name_chord(self,t,r):
        self.check(t,('name_chord',));fields(r,('root_pitch_class','quality'));root=r['root_pitch_class']
        require((root is None or (type(root) is int and 0<=root<=11)) and type(r['quality']) is str and r['quality'] in QUALITIES,'typed heard-chord response, including unknown')
        self.named_chord=deepcopy(r);self.chord_history.append({'generation':self.generation,'cycle':self.cycle,'response':deepcopy(r)})
        self.record('heard_chord_response',{'response':r,'compared_to_hidden_source':False},'response_ready')
    def begin_response(self,t,ready):self.check(t,('response_ready',));require(ready is True,'response begins before hand formation');self.record('response_begins',{},'recall_plan')
    def cannot_recall(self,t,diagnosis,learner_released):
        self.check(t,('recall_plan',));require(text(diagnosis) and learner_released is True,'unable-to-recall diagnosis and manual release')
        self.record('unable_to_recall',{'diagnosis':diagnosis,'learner_released':True,'invented_response':False},'needs_retry')
    def set_recalled_plan(self,t,p):
        self.check(t,('recall_plan',));validate_recalled(p);self.recalled=deepcopy(p);self.recall_history.append({'generation':self.generation,'cycle':self.cycle,'recalled':deepcopy(p)})
        self.record('learner_recalled_plan',{'recalled':p,'compared_to_hidden_source':False},'sing_response')
    def sung(self,t,ack):self.check(t,('sing_response',));require(ack is True,'remembered phrase singing attempted');self.record('sung',{},'silent_setup')
    def setup_targets(self,t,ack):self.check(t,('silent_setup',));require(ack is True,'silent target preparation after response begins');self.record('silent_setup',{},'play_response')
    def play(self,t,ack):self.check(t,('play_response',));require(ack is True,'four remembered targets attempted');self.record('play_attempt',{'actual_attack_counts_observed':None},'response_release')
    def release(self,t,c):
        self.check(t,('response_release','reopen_release'));fields(c,('learner_released','source_stopped'));require(c['learner_released'] is True,'manual learner physical release')
        require(c['source_stopped'] is True if self.source_release_required else c['source_stopped'] is None,'manual pending source stop, no invented source confirmation')
        self.source_release_required=self.source_stop_requested=False
        if self.state=='reopen_release':
            s=self.resume;require(s is not None,'resume state');self.resume=None
            if s=='ready':self.reset_current()
        else:s='reveal'
        self.record('release',{'confirmation':c,'actual_sound_stop_observed':False},s)
    def reveal_reference(self,t):self.check(t,('reveal',));self.current_revealed=self.ever_revealed=True;self.record('post_performance_reveal',{},'reporting')
    def report(self,t,r):
        self.check(t,('reporting',));fields(r,('key','recalled_midi','attack_counts','duties','diagnosis','notes'));fields(r['duties'],play_duties(self.index));midi4(r['recalled_midi'])
        require(r['key']==self.key and r['recalled_midi']==self.recalled['midi'],'exact captured learner recall binding')
        require(type(r['attack_counts']) is list and len(r['attack_counts'])==4 and all(type(v) is int and v>=0 for v in r['attack_counts']),'four actual nonnegative attack counts')
        require(all(type(v) is str and v in YN for v in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual recall performance report')
        matches={'midi':self.recalled['midi']==self.expected_midi(),'rhythm':rhythm_signature(self.recalled['rhythm'])==rhythm_signature(self.plan['provider']['question_rhythm'])}
        if self.index==0:matches['named_chord']=self.named_chord=={'root_pitch_class':4,'quality':'dominant7'}
        ok=all(matches.values()) and all(v==1 for v in r['attack_counts']) and all(v=='yes' for v in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong memory/count/manual duty diagnosis')
        self.record('recall_report',{'response':r,'symbolic_reference_matches':matches,'manual_requirements_reported':ok,'acoustic_performance_verified':False,'elapsed_delay_verified':False},'reported' if ok else 'needs_retry')
    def retry(self,t,diagnosis):self.check(t,('needs_retry','reported'));require(text(diagnosis),'full question/delay retry diagnosis');self.reset_current();self.record('retry_full_question_delay',{'diagnosis':diagnosis},'ready')
    def finish(self,t):self.check(t,('reported',));self.record('finish',{'manual_only':True,'mastery_awarded':False,'source_acceptance':False,'timed_delay_verified':False},'completed')
    def cancel(self,t):
        stable=('setup','ready','reporting','reported','needs_retry','completed')
        self.check(t,stable+('name_chord','listening','delay','delay_review','response_ready','recall_plan','sing_response','silent_setup','play_response','response_release','reveal','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in stable else 'ready'
        if self.source_release_required:self.source_stop_requested=True
        self.generation+=1;self.record('cancel',{'manual_source_stop_requested':self.source_stop_requested,'actual_sound_stop_observed':False},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    return {'schema_version':'fathom-private-delayed-memory-naming-transposition.1','key':KEYS[i],'printed_question':list(QUESTIONS[i]),'printed_required_delay':DELAYS[i],
      'printed_heading':'THE PHRASE MUST SURVIVE A SILENT DELAY BEFORE THE HAND MOVES','printed_footer':FOOTER,
      'source_extent_header':'8 MEMORY DELAYS | 64 TONES','actual_page_question_tokens':32,'source_note_events':[],'source_fixed_midi_rhythm_meter_frets':None,
      'additional_task_schema':{'kind':'name_heard_chord','root_pitch_class':'integer0..11 or null/unknown','qualities':list(QUALITIES),'compare_after_playing':True} if i==0 else {'kind':'chosen_transposition','semitones':'integer-24..24 excluding multiples12','rhythm_policy':'same_as_question','compare_after_playing':True},
      'plan_schema':{'source':'actual external human, four chosen source MIDI in playable40..88, chosen rational question rhythm',
        'external_pulse':'reference, chosen beats_per_bar1..16, positive rational beat_unit_q; required counts2B/4B',
        'recalled_response':'four learner-entered playable MIDI, remembered rational rhythm and matching contacts; hidden-source correctness not checked before playing'},
      'response_schema':{'beat_duties':list(BEAT_DUTIES),'delay_review_duties':list(DELAY_DUTIES),'play_duties':list(play_duties(i)),'manual_enum':list(YN),
        'attack_counts':'four nonnegative integers; positive report requires each exactly1','unable_to_recall':'diagnosis and manual release, then full retry without invented response'},
      'authored_policies':['Timing is external. Typed sequential beat reports and elapsed-delay confirmation are manual statements, not a clock, timing test or observed physical interval.',
        'Source end marks the declared external delay boundary. No hand formation until full positive delay review and explicit response begin. No/uncertain hand/memory/count reports are retained and require full retry.',
        'Source-player script remains available; learner source reference withheld until after playing and explicit reveal. Prior reveal/recall history retained; no blind/security claim.',
        'Wrong recalled pitch/rhythm plans are structurally accepted and played before reference comparison; no answer feedback or silent correction during the memory test.',
        'One setup/attack per target, no search and exact memory are manually reported after reveal. Failed memory/count/duty requires diagnosis and full question/delay repeat.',
        'Interrupted delay/response repeats the whole take after release. Source stop requests do not claim observed silence. Current owner/beat/action tokens reject stale and duplicate reports.',
        'Only existing rows7/8 implemented. Row6 sing-tonic remains Pending; no tonic inferred from B-D-F-A.32printed question tokens kept distinct from literal64heading.',
        'Row7: after full delay and before hand formation, capture heard chord root pitch class/quality including unknown. Wrong answers remain unrevealed until after playing; exact TXT supports E7, root4 dominant7.',
        'Row8: explicit signed semitone choice within-24..24 excluding0/octaves, uniform across original chosen MIDI and guitar-playable; same chosen rhythm. Finite authored option, no source-fixed transposition or claim that octave transposition is invalid.',
        'Only after performance derive/compare expected transposed MIDI or chord identity; original note occurrences remain unchanged.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,'elapsed_delay_measured':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
