"""Two source duration classes; chosen two-bar reference and isolated-layer review."""
from copy import deepcopy
from fractions import Fraction
from uuid import uuid4
import math,re
KEYS=tuple(f'exercise-completeness-r01/level077/moduled/p010-t1-r{i}/{i}' for i in (1,2))
DEGREES=(('1','2','3','5','3','2','1'),('5','6','5','3','2','1'))
PITCHES=(('C','D','E','G','E','D','C'),('G','A','G','E','D','C'))
PC={'C':0,'D':2,'E':4,'G':7,'A':9};DURATION=(Fraction(1),Fraction(1,2));LABELS=('quarters','eighths')
YN=('yes','no','uncertain');CONFIDENCE=('low','medium','high','uncertain');STAGES=('clap_rhythm','sing_without_rhythm','recombine')
DICTATION_DUTIES=('heard_same_chosen_phrase','pitch_and_rhythm_written_separately','heard_source_order')
DUTIES={'clap_rhythm':('clapped_rhythm_without_pitch','all_chosen_onsets_and_durations','chosen_rests_preserved'),
 'sing_without_rhythm':('sung_source_pitch_order','correct_pitches','without_imposing_rhythm_layer'),
 'recombine':('sung_source_pitch_order','correct_pitches','correct_chosen_rhythm','chosen_rests_preserved','both_isolated_layers_previously_reported')}
FOOTER='Verification: clap the rhythm without pitch; sing the melody without rhythm; then recombine. If either isolated layer fails, do not blame the combined phrase.'
class Refusal(ValueError):pass
def require(ok,msg):
    if not ok:raise Refusal(msg)
def fields(x,n):require(type(x) is dict and set(x)==set(n),'exact typed fields')
def text(x):return type(x) is str and bool(x.strip())
def rational(x):
    require(type(x) is list and len(x)==2 and all(type(v) is int and v>0 for v in x),'positive rational pair')
    require(math.gcd(*x)==1,'canonical rational pair');return Fraction(*x)
def rhythm_signature(r):
    fields(r,('meter_quarters','bar_count','slots'));meter=rational(r['meter_quarters'])
    require(type(r['bar_count']) is int and r['bar_count']>0 and type(r['slots']) is list and bool(r['slots']),'typed bar count and nonempty rhythm')
    pos=Fraction(0);notes=[]
    for s in r['slots']:
        fields(s,('kind','duration'));require(type(s['kind']) is str and s['kind'] in ('note','rest'),'note/rest slot');dur=rational(s['duration'])
        if s['kind']=='note':notes.append((pos,dur))
        pos+=dur
    return meter,r['bar_count'],tuple(notes),pos
def validate_plan(p,i):
    require(type(i) is int and 0<=i<2,'only two exact duration prescriptions');fields(p,('original_workbook','provider'))
    require(p['original_workbook'] is True,'original source accessible');v=p['provider'];fields(v,('kind','reference','ready','chosen_midi','chosen_rhythm'))
    require(v['kind']=='external_human' and text(v['reference']) and v['ready'] is True,'actual external human source player')
    m=v['chosen_midi'];require(type(m) is list and len(m)==len(PITCHES[i]) and all(type(x) is int and 0<=x<=127 for x in m),'chosen source MIDI sequence')
    require([x%12 for x in m]==[PC[x] for x in PITCHES[i]],'source pitch-class order')
    meter,bars,notes,total=rhythm_signature(v['chosen_rhythm'])
    require(bars==2 and total==meter*2 and len(notes)==len(m),'complete chosen two-bar realization with exact source note count')
    require(all(d==DURATION[i] for _,d in notes),'printed quarter/eighth duration for every source note; rests remain chosen')

class RhythmFlow:
    def __init__(self,key):
        require(type(key) is str and key in KEYS,'exact first two page10 keys only');self.key=key;self.index=KEYS.index(key);self.instance=uuid4().hex
        self.generation=self.layer=self.stage=self.cycle=self.action=0;self.state='setup';self.plan=None;self.resume=None
        self.answers={};self.answer_history=[];self.history=[];self.current_revealed=self.ever_revealed=False
        self.source_release_required=self.source_stop_requested=False
    def token(self):return (self.instance,self.key,self.generation,self.layer,self.stage,self.cycle,self.action,self.state)
    def check(self,t,states):require(type(t) is tuple and t==self.token(),'current phrase/pass/stage/action owner');require(self.state in states,'wrong state')
    def record(self,kind,data,state):
        self.history.append({'kind':kind,'generation':self.generation,'layer':self.layer,'stage':self.stage,'cycle':self.cycle,'data':deepcopy(data)});self.action+=1;self.state=state
    def set_plan(self,t,p):
        self.check(t,('setup','dictation_retry','completed'));require(not self.source_release_required,'pending source stop');validate_plan(p,self.index)
        self.plan=deepcopy(p);self.generation+=1;self.layer=self.stage=self.cycle=0;self.answers={};self.current_revealed=False;self.record('chosen_plan',p,'ready_listen')
    def source_player_view(self):
        return {'key':self.key,'printed_context':'C major','printed_degrees':list(DEGREES[self.index]),'derived_pitches_confirmed_by_paired_txt':list(PITCHES[self.index]),
          'printed_rhythm_label':LABELS[self.index],'chosen_realization':None if self.plan is None else deepcopy(self.plan['provider']),
          'source_fixed_meter_rest_octave':None,'audio_supplied_by_app':False,'source_release_required':self.source_release_required,'source_stop_requested':self.source_stop_requested,
          'instruction':'Stop source sound and confirm manually' if self.source_stop_requested else 'Supply the same chosen two-bar phrase for separate pitch and rhythm transcription.'}
    def learner_view(self):
        v={'state':self.state,'printed_context':'C major','printed_rhythm_label':LABELS[self.index],'current_written_layer':('pitch','rhythm')[self.layer],'verification_stage':STAGES[self.stage],
          'answers':deepcopy(self.answers),'previously_revealed':self.ever_revealed,'prior_answers_retained':bool(self.answer_history),'blind_assessment_claim':False}
        if self.current_revealed:v['reference_answer']=self.source_player_view()
        return v
    def begin_listening(self,t,c):
        self.check(t,('ready_listen',));fields(c,('key','ready','same_chosen_phrase'));require(c['key']==self.key and c['ready'] is True and c['same_chosen_phrase'] is True,'current external source readiness')
        self.cycle+=1;self.source_release_required=True;self.source_stop_requested=False;self.record('listen',{'manual_confirmation':c,'audio_observed':False},'listening')
    def end_listening(self,t,ack):
        self.check(t,('listening',));require(ack is True,'hearing ended/request source stop');self.source_stop_requested=True;self.record('stop_request',{'actual_stop_observed':False},'listening_release')
    def release(self,t,r):
        self.check(t,('listening_release','verification_release','reopen_release'));fields(r,('learner_released','source_stopped'))
        require(r['learner_released'] is True,'manual learner release');require(r['source_stopped'] is True if self.source_release_required else r['source_stopped'] is None,'manual pending source stopped; no invented source confirmation')
        self.source_release_required=self.source_stop_requested=False
        if self.state=='reopen_release':
            s=self.resume;require(s is not None,'resume state');self.resume=None
        else:s='writing' if self.state=='listening_release' else 'verification_report'
        self.record('release',{'manual_confirmation':r,'actual_stop_verified':False},s)
    def commit(self,t,kind,value,confidence):
        self.check(t,('writing',));require(type(kind) is str and kind==('pitch','rhythm')[self.layer],'current separate written layer')
        require(type(confidence) is str and confidence in CONFIDENCE,'manual confidence')
        if kind=='pitch':require(type(value) is list and len(value)==len(DEGREES[self.index]) and all(type(x) is str and (x=='?' or re.fullmatch(r'(?:#|b)?[1-7]',x)) for x in value),'ordered degree tokens or explicit unknown')
        elif value is not None:rhythm_signature(value)
        r={'value':deepcopy(value),'confidence':confidence};self.answers[kind]=r;self.answer_history.append({'generation':self.generation,'cycle':self.cycle,'kind':kind,'response':deepcopy(r)})
        s='committed' if self.layer==1 else 'ready_listen'
        if self.layer==0:self.layer=1
        self.record('commit_'+kind,r,s)
    def reveal(self,t):
        self.check(t,('committed',));require(set(self.answers)=={'pitch','rhythm'},'both separate commits');self.current_revealed=self.ever_revealed=True;self.record('reveal',{'reference':self.source_player_view()},'dictation_report')
    def report_dictation(self,t,r):
        self.check(t,('dictation_report',));fields(r,('key','duties','diagnosis','notes'));fields(r['duties'],DICTATION_DUTIES)
        require(r['key']==self.key and all(type(x) is str and x in YN for x in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete manual hearing report')
        v=self.answers['rhythm']['value'];matches={'pitch':self.answers['pitch']['value']==list(DEGREES[self.index]),'rhythm':v is not None and rhythm_signature(v)==rhythm_signature(self.plan['provider']['chosen_rhythm'])}
        ok=all(matches.values()) and all(v=='yes' for v in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'wrong/unknown/uncertain layer diagnosis')
        self.record('dictation_report',{'response':r,'symbolic_matches':matches,'manual_requirements_reported':ok,'acoustic_performance_verified':False},'verification_ready' if ok else 'dictation_retry')
    def repeat_dictation(self,t,diagnosis):
        self.check(t,('dictation_retry',));require(text(diagnosis),'repeat diagnosis');self.layer=self.stage=0;self.answers={};self.current_revealed=False;self.record('repeat_separate_layers',{'diagnosis':diagnosis},'ready_listen')
    def begin_verification(self,t,c):
        self.check(t,('verification_ready',));fields(c,('stage','ready'));require(c['stage']==STAGES[self.stage] and c['ready'] is True,'current ordered verification stage')
        self.cycle+=1;self.record('begin_verification',c,'verifying')
    def end_verification(self,t,ack):self.check(t,('verifying',));require(ack is True,'manual clap/sing/recombine attempt ended');self.record('end_verification',{'performance_observed':False},'verification_release')
    def report_verification(self,t,r):
        self.check(t,('verification_report',));stage=STAGES[self.stage];fields(r,('key','stage','duties','diagnosis','notes'));fields(r['duties'],DUTIES[stage])
        require(r['key']==self.key and r['stage']==stage and all(type(v) is str and v in YN for v in r['duties'].values()) and type(r['diagnosis']) is str and text(r['notes']),'complete current layer report')
        ok=all(v=='yes' for v in r['duties'].values())
        if not ok:require(text(r['diagnosis']),'isolate failure or combined phrase diagnosis')
        self.record('verification_report',{'response':r,'manual_requirements_reported':ok,'acoustic_performance_verified':False},'verification_reported' if ok else 'verification_retry')
    def next_stage(self,t):
        self.check(t,('verification_reported',));require(self.stage<2,'only three verification stages');self.stage+=1;self.record('next_stage',{},'verification_ready')
    def repeat_stage(self,t,diagnosis):self.check(t,('verification_retry','verification_reported'));require(text(diagnosis),'same-stage diagnosis');self.record('repeat_current_stage',{'diagnosis':diagnosis},'verification_ready')
    def finish(self,t):self.check(t,('verification_reported',));require(self.stage==2,'both isolated layers then recombination required');self.record('finish',{'manual_only':True,'credit_awarded':False,'source_acceptance':False},'completed')
    def cancel(self,t):
        stable=('setup','ready_listen','writing','committed','dictation_report','dictation_retry','verification_ready','verification_reported','verification_retry','completed')
        self.check(t,stable+('listening','listening_release','verifying','verification_release','verification_report','reopen_release'))
        if self.state!='reopen_release':self.resume=self.state if self.state in stable else 'ready_listen' if self.state in ('listening','listening_release') else 'verification_ready'
        if self.source_release_required:self.source_stop_requested=True
        self.generation+=1;self.record('cancel',{'manual_source_stop_requested':self.source_stop_requested,'actual_stop_observed':False},'cancelled')
    def reopen(self,t):self.check(t,('cancelled',));self.generation+=1;self.record('reopen',{},'reopen_release')

def contract(i):
    return {'schema_version':'fathom-private-rhythm-pitch-dictation-manual.1','key':KEYS[i],'printed_context':'C major',
      'printed_degrees':list(DEGREES[i]),'derived_pitch_names_confirmed_in_paired_txt':list(PITCHES[i]),'printed_rhythm_label':LABELS[i],
      'source_duration_class_quarters':[DURATION[i].numerator,DURATION[i].denominator],
      'printed_heading':'PITCH AND RHYTHM ARE TRANSCRIBED SEPARATELY, THEN RECOMBINED','printed_footer':FOOTER,
      'source_extent_header':'8 TWO-BAR CELLS | 64 TONES','page_actual_degree_tokens':53,'selected_row_note_count':len(DEGREES[i]),
      'source_note_events':[],'source_fixed_octave_meter_rest_fret_map':None,
      'plan_schema':{'source_player':'actual external human with reference/readiness and chosen MIDI matching exact source order',
        'chosen_rhythm':'positive canonical rational meter in quarters; two bars; ordered note/rest slots with positive rational durations; exact source-note count with printed duration class; total exactly2 chosen bars',
        'authored_choices':['absolute registers','meter','all rest placement/duration','two external hearings']},
      'response_schema':{'separate_written':['N degree tokens or ?','typed rhythm map or explicit None unknown'],'confidence':list(CONFIDENCE),
        'dictation_duties':list(DICTATION_DUTIES),'verification_stages':list(STAGES),'verification_duties':deepcopy(DUTIES),'manual_enum':list(YN)},
      'authored_policies':['No default realization. Source note durations are quarter/eighth classes; full meter/register/rest map belongs to external performer choice and is not promoted to source timing.',
        'Pitch then rhythm are heard and committed separately. Source stop/release precedes each written commit; explicit reveal only after both. Source-player script remains available; prior answer/reveal history is retained.',
        'Symbolic reference comparison uses meter, cumulative note onsets/durations and total; splitting an adjacent rest does not change the rhythm. This is not acoustic assessment or a numeric outcome.',
        'Clap rhythm without pitch, sing melody without rhythm, then recombine vocally. Each isolated layer needs positive manual report before recombination; a failed/uncertain stage is diagnosed and repeated itself.',
        'Source footer does not require a guitar realization on this page; no guitar contact/attack is invented. Broader workbook no-search rule remains contextual.',
        'Current owner/pass/stage/action tokens, explicit external-stop requests and manual release; no app sound-control claim.',
        'Only two existing page10 rows implemented; remaining six rhythm shorthand rows remain Pending, not declared source conflicts.53 printed degree tokens versus literal64 heading retained.'],
      'automatic_evaluation':False,'performance_observed':False,'audio_supplied':False,'audio_inspected':False,'timing_scheduled':False,
      'credit_awarded':False,'mastery_awarded':False,'persistence':False,'canonical_binding':None}
