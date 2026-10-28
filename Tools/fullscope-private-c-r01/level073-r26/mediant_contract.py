"""Private manual source/cadence contract. No audio, grading, clock or persistence."""
from dataclasses import dataclass
from copy import deepcopy
@dataclass(frozen=True)
class Token:
    instance: object
    route: str
    generation: int
    pass_number: int
    action: int
    stage: str
class MediantSession:
    def __init__(self, contract):
        self.c=deepcopy(contract);self.instance=object();self.generation=1;self.pass_number=1;self.action=0
        self.stage='setup' if self.c['complete_manual_contract'] else 'source_extent_pending'
        self.choice=None;self.cell=None;self.cadence=None;self.history=[];self.cancelled=False
    def token(self):return Token(self.instance,self.c['package_key'],self.generation,self.pass_number,self.action,self.stage)
    def guard(self,t,stages):
        if self.cancelled or type(t) is not Token or t!=self.token() or self.stage not in stages:raise ValueError('exact current instance/route/generation/pass/action required')
    def move(self,s):self.stage=s;self.action+=1
    @staticmethod
    def text(v):
        if type(v) is not str or not v.strip():raise ValueError('nonempty learner text required')
    @staticmethod
    def report(v):
        if type(v) is not str or v not in ('yes','no','uncertain'):raise ValueError('explicit yes/no/uncertain required')
    def configure(self,t,own_instrument,dominant_realization,tonic_realization,timing_plan,destination_v_i):
        self.guard(t,('setup','choice_review','ready'))
        if own_instrument is not True:raise ValueError('learner-supplied instrument required; app supplies no audio')
        for v in (dominant_realization,tonic_realization,timing_plan):self.text(v)
        self.report(destination_v_i)
        if self.choice is not None:self.history.append({'kind':'replaced_choice','choice':deepcopy(self.choice)})
        self.choice={'own_instrument_self_report':True,'dominant_realization':dominant_realization,'tonic_realization':tonic_realization,
                     'timing_plan':timing_plan,'destination_v_i_self_report':destination_v_i,'origin':'learner-supplied realization, not printed source notes','harmonic_validation_supplied':False}
        self.move('ready' if destination_v_i=='yes' else 'choice_review')
    def begin(self,t):self.guard(t,('ready',));self.move('perform_printed_cell')
    def report_cell(self,t,played_as_printed,common_tone_continuity,no_diatonic_pivot,explanation):
        self.guard(t,('perform_printed_cell',))
        for v in (played_as_printed,common_tone_continuity,no_diatonic_pivot):self.report(v)
        self.text(explanation)
        self.cell={'source_orders':list(range(1,13)),'played_as_printed_self_report':played_as_printed,
                   'common_tone_continuity_self_report':common_tone_continuity,'no_diatonic_pivot_self_report':no_diatonic_pivot,
                   'explanation_self_report':explanation,'performance_observed':False}
        self.move('perform_chosen_cadence' if all(v=='yes' for v in (played_as_printed,common_tone_continuity,no_diatonic_pivot)) else 'manual_release')
    def report_cadence(self,t,played_chosen_cadence,destination_confirmed,explanation):
        self.guard(t,('perform_chosen_cadence',));self.report(played_chosen_cadence);self.report(destination_confirmed);self.text(explanation)
        self.cadence={'played_chosen_cadence_self_report':played_chosen_cadence,'destination_confirmed_self_report':destination_confirmed,
                      'explanation_self_report':explanation,'performance_observed':False,'automatically_graded':False}
        self.move('manual_release')
    def release(self,t,released):
        self.guard(t,('manual_release',))
        if released is not True:raise ValueError('manual instrument release required')
        self.history.append({'kind':'released_pass','pass':self.pass_number,'choice':deepcopy(self.choice),'cell':deepcopy(self.cell),'cadence':deepcopy(self.cadence),'manual_release_self_report':True})
        good=self.cadence is not None and self.cadence['played_chosen_cadence_self_report']=='yes' and self.cadence['destination_confirmed_self_report']=='yes'
        self.move('complete_manual_reports' if good else 'retry_required')
    def request_retry(self,t,reason):
        self.guard(t,('ready','perform_printed_cell','perform_chosen_cadence','manual_release','retry_required','complete_manual_reports'));self.text(reason)
        self.history.append({'kind':'retry_requested','pass':self.pass_number,'reason':reason,'cell':deepcopy(self.cell),'cadence':deepcopy(self.cadence),'choice':deepcopy(self.choice)})
        self.move('retry_release')
    def retry_release(self,t,released):
        self.guard(t,('retry_release',))
        if released is not True:raise ValueError('release before replay')
        self.history.append({'kind':'retry_release','pass':self.pass_number,'manual_release_self_report':True});self.generation+=1;self.pass_number+=1;self.cell=None;self.cadence=None;self.move('ready')
    def cancel(self,t):
        self.guard(t,('setup','choice_review','ready','perform_printed_cell','perform_chosen_cadence','manual_release','retry_required','retry_release','complete_manual_reports','source_extent_pending'))
        self.history.append({'kind':'cancel','instruction':'Stop and release your own instrument; no app audio exists.'});self.cancelled=True;self.generation+=1;self.action+=1
    def reopen(self,t,released):
        if not self.cancelled or type(t) is not Token or t!=self.token():raise ValueError('current cancelled instance required')
        if released is not True:raise ValueError('manual release before reopening')
        self.cancelled=False;self.generation+=1;self.action+=1;self.history.append({'kind':'reopen','manual_release_self_report':True})
    def snapshot(self):
        return deepcopy({'stage':self.stage,'pass_number':self.pass_number,'source_script':self.c['source_script'],'register_extent':self.c['register_extent'],
                         'choice':self.choice,'cell':self.cell,'cadence':self.cadence,'history':self.history,'cancelled':self.cancelled,
                         'manual_reports_complete':not self.cancelled and self.stage=='complete_manual_reports','performance_observed':False,
                         'app_audio_supplied':False,'harmonic_validation_supplied':False,'Attempt_credit':False,'mastery_awarded':False,'persistence_supplied':False})
