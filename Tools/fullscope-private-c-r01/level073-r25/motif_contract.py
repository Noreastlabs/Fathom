"""Manual performer/listener motif comparison; typed order is not acoustic assessment."""
from copy import deepcopy
from dataclasses import dataclass

@dataclass(frozen=True)
class Token:
    instance: object
    route: str
    generation: int
    pass_number: int
    revision: int
    stage: str

class MotifSession:
    def __init__(self,contract):
        self.c=deepcopy(contract);self.instance=object();self.generation=1;self.pass_number=1;self.revision=0
        self.stage='setup';self.context=None;self.performance=[];self.recognition=None;self.key_response=None
        self.comparison=None;self.reference_revealed=False;self.history=[];self.cancelled=False

    def token(self):return Token(self.instance,self.c['package_key'],self.generation,self.pass_number,self.revision,self.stage)
    def guard(self,token,stages):
        if self.cancelled or type(token) is not Token or token!=self.token() or self.stage not in stages:
            raise ValueError('exact current instance/route/generation/pass/action required')
    def move(self,stage):self.stage=stage;self.revision+=1
    @staticmethod
    def text(v):
        if type(v) is not str or not v.strip():raise ValueError('nonempty manual text required')
    @staticmethod
    def report(v):
        if type(v) is not str or v not in ('yes','no','uncertain'):raise ValueError('explicit yes/no/uncertain self-report required')

    def setup(self,token,own_instrument,external_listener,rhythm,articulation,phrase_length):
        self.guard(token,('setup',))
        if own_instrument is not True or external_listener is not True:
            raise ValueError('selected manual delivery needs own instrument and external human listener; app supplies neither')
        for v in (rhythm,articulation,phrase_length):self.text(v)
        self.context={'own_instrument_self_report':True,'external_listener_self_report':True,
                      'rhythm_plan':rhythm,'articulation_plan':articulation,'phrase_length_plan':phrase_length,
                      'origin':'performer choices, not printed fixed timing'}
        self.move('ready')

    def begin(self,token):self.guard(token,('ready',));self.move('perform_source')

    def performer_view(self):
        return deepcopy({'source_script':self.c['source_script'],'current_motif':
                         'source' if self.stage=='perform_source' and not self.cancelled else
                         'destination' if self.stage=='perform_destination' and not self.cancelled else None,
                         'plan':self.context,'cancelled':self.cancelled,'app_audio_supplied':False})

    def listener_view(self):
        # This projection deliberately excludes route IDs/labels, formula and source-player notes.
        return deepcopy({'title':'Motif comparison','stage':self.stage,'cancelled':self.cancelled,
                         'prompt':{'recognition':'Did you recognize the same motif? Record this before identifying a key.',
                                   'key_response':'Name the new key in your own words.',
                                   'reveal':'Your key response is recorded. You may now reveal the reference.',
                                   'comparison':'Compare your own key response with the source reference.'}.get(self.stage,''),
                         'recognition_response':self.recognition,'key_response':self.key_response,
                         'reference':self.c['destination_key'] if self.reference_revealed else None,
                         'reference_previously_revealed':self.reference_revealed,
                         'fresh_unseen_listening_claim':False,'app_audio_supplied':False})

    def report_source(self,token,played_as_shown,explanation):
        self.guard(token,('perform_source',));self.report(played_as_shown);self.text(explanation)
        self.performance.append({'motif':'source','source_orders':list(range(1,9)),
                                 'played_as_shown_self_report':played_as_shown,'explanation_self_report':explanation,'performance_observed':False})
        self.move('perform_destination')

    def report_destination(self,token,played_as_shown,rhythm_unchanged,articulation_unchanged,phrase_length_unchanged,explanation):
        self.guard(token,('perform_destination',))
        for v in (played_as_shown,rhythm_unchanged,articulation_unchanged,phrase_length_unchanged):self.report(v)
        self.text(explanation)
        self.performance.append({'motif':'destination','source_orders':list(range(9,17)),
                                 'played_as_shown_self_report':played_as_shown,'rhythm_unchanged_self_report':rhythm_unchanged,
                                 'articulation_unchanged_self_report':articulation_unchanged,'phrase_length_unchanged_self_report':phrase_length_unchanged,
                                 'explanation_self_report':explanation,'performance_observed':False})
        self.move('performance_release')

    def release(self,token,released):
        self.guard(token,('performance_release',))
        if released is not True:raise ValueError('manual instrument release before listener response')
        self.history.append({'kind':'released_performance','pass':self.pass_number,'performance':deepcopy(self.performance),'manual_release_self_report':True})
        good=self.performance[0]['played_as_shown_self_report']=='yes' and all(self.performance[1][k]=='yes' for k in
            ('played_as_shown_self_report','rhythm_unchanged_self_report','articulation_unchanged_self_report','phrase_length_unchanged_self_report'))
        self.move('recognition' if good else 'retry_required')

    def recognize(self,token,same_motif,explanation):
        self.guard(token,('recognition',));self.report(same_motif);self.text(explanation)
        self.recognition={'same_motif_self_report':same_motif,'explanation_self_report':explanation,
                          'response_origin':'external listener, manually entered','performance_observed':False}
        self.move('key_response' if same_motif=='yes' else 'retry_required')

    def name_key(self,token,key_text):
        self.guard(token,('key_response',));self.text(key_text)
        self.key_response={'key_text':key_text,'response_origin':'external listener, manually entered','automatically_graded':False}
        self.move('reveal')

    def reveal(self,token):
        self.guard(token,('reveal',));self.reference_revealed=True
        self.history.append({'kind':'reference_revealed','pass':self.pass_number,'key_response':deepcopy(self.key_response)})
        self.move('comparison')

    def compare(self,token,agrees_with_reference,explanation):
        self.guard(token,('comparison',));self.report(agrees_with_reference);self.text(explanation)
        self.comparison={'agrees_with_reference_self_report':agrees_with_reference,'explanation_self_report':explanation,
                         'automatically_graded':False,'performance_observed':False}
        self.move('complete_manual_reports' if agrees_with_reference=='yes' else 'retry_required')

    def request_retry(self,token,reason):
        self.guard(token,('perform_source','perform_destination','performance_release','recognition','key_response',
                          'reveal','comparison','retry_required','complete_manual_reports'))
        self.text(reason)
        self.history.append({'kind':'retry_requested','pass':self.pass_number,'reason':reason,'performance':deepcopy(self.performance),
                             'recognition':deepcopy(self.recognition),'key_response':deepcopy(self.key_response),'comparison':deepcopy(self.comparison),
                             'reference_previously_revealed':self.reference_revealed})
        self.move('retry_release')

    def retry_release(self,token,released):
        self.guard(token,('retry_release',))
        if released is not True:raise ValueError('manual instrument release before replay')
        self.history.append({'kind':'retry_release','manual_release_self_report':True})
        self.generation+=1;self.pass_number+=1;self.performance=[];self.recognition=None;self.key_response=None;self.comparison=None
        # Deliberately do not erase prior answer exposure or performer context.
        self.move('ready')

    def cancel(self,token):
        self.guard(token,('setup','ready','perform_source','perform_destination','performance_release','recognition','key_response',
                          'reveal','comparison','retry_required','retry_release','complete_manual_reports'))
        self.history.append({'kind':'cancel','instruction':'Stop/release your own instrument; the app has no active sound.'})
        self.cancelled=True;self.generation+=1;self.revision+=1

    def reopen(self,token,released):
        if not self.cancelled or type(token) is not Token or token!=self.token():raise ValueError('current cancelled instance token required')
        if released is not True:raise ValueError('confirm manual release before reopening')
        self.cancelled=False;self.generation+=1;self.revision+=1;self.history.append({'kind':'reopen','manual_release_self_report':True})

    def snapshot(self):
        return deepcopy({'stage':self.stage,'pass_number':self.pass_number,'context':self.context,'performance':self.performance,
                         'recognition':self.recognition,'key_response':self.key_response,'comparison':self.comparison,
                         'reference_revealed':self.reference_revealed,'history':self.history,'cancelled':self.cancelled,
                         'manual_task_reports_complete':not self.cancelled and self.stage=='complete_manual_reports',
                         'performance_observed':False,'app_audio_supplied':False,'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
