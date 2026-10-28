"""Private manual guide: source order, reports and explicit release; no clock/audio/credit."""
from dataclasses import dataclass
from copy import deepcopy


@dataclass(frozen=True)
class ActionToken:
    instance: object
    route: str
    generation: int
    pass_number: int
    revision: int
    stage: str


class PivotRouteSession:
    def __init__(self, contract):
        self.c = deepcopy(contract)
        self._instance = object()
        self.generation = 1
        self.revision = 0
        self.pass_number = 1
        self.stage = 'setup'
        self.context = None
        self.bars = []
        self.summary = None
        self.history = []
        self.cancelled = False

    def token(self):
        return ActionToken(self._instance, self.c['package_key'], self.generation,
                           self.pass_number, self.revision, self.stage)

    def guard(self, token, stage):
        if self.cancelled or type(token) is not ActionToken or token != self.token() or self.stage not in stage:
            raise ValueError('current instance, route, generation, pass and displayed action required')

    @staticmethod
    def text(value):
        if type(value) is not str or not value.strip():
            raise ValueError('nonempty learner text required')

    @staticmethod
    def report(value):
        if value not in ('yes', 'no', 'uncertain') or type(value) is not str:
            raise ValueError('explicit yes/no/uncertain self-report required')

    def changed(self, stage):
        self.revision += 1
        self.stage = stage

    def setup(self, token, own_instrument_available, pulse_description, hold_placement_plan, pivot_restatement):
        self.guard(token, ('setup',))
        if own_instrument_available is not True:
            raise ValueError('own instrument required; the app supplies no sound')
        for v in (pulse_description, hold_placement_plan, pivot_restatement):
            self.text(v)
        self.context = {'own_instrument_available_self_report': True,
                        'pulse_description_self_report': pulse_description,
                        'hold_placement_plan_self_report': hold_placement_plan,
                        'pivot_function_restatement_self_report': pivot_restatement,
                        'origin': 'learner manual choices and interpretation, not printed fixed timing',
                        'performance_observed': False}
        self.changed('ready')

    def begin_pass(self, token):
        self.guard(token, ('ready',))
        self.changed('bar')

    def current_bar(self):
        if self.cancelled or self.stage != 'bar':
            return None
        return deepcopy(self.c['bars'][len(self.bars)])

    def report_bar(self, token, bar_number, played_as_shown, explanation,
                   pivot_extra_beat=None, hold_placement=None):
        self.guard(token, ('bar',))
        bar = self.current_bar()
        if type(bar_number) is not int or bar_number != bar['bar_number']:
            raise ValueError('report the displayed four-tone bar in source order')
        self.report(played_as_shown)
        self.text(explanation)
        pivot = self.pass_number == 1 and bar_number == 2
        if pivot:
            self.report(pivot_extra_beat)
            self.text(hold_placement)
        elif pivot_extra_beat is not None or hold_placement is not None:
            raise ValueError('extra-beat report belongs only to first-pass pivot bar')
        self.bars.append({'bar_number': bar_number, 'source_orders': bar['source_orders'],
                          'played_as_shown_self_report': played_as_shown,
                          'explanation_self_report': explanation,
                          'pivot_extra_beat_self_report': pivot_extra_beat,
                          'hold_placement_self_report': hold_placement,
                          'performance_observed': False})
        self.changed('summary' if len(self.bars) == 4 else 'bar')

    def report_pass(self, token, four_bar_count_preserved, tonic_confirmation, explanation,
                    extra_emphasis_removed=None, harmony_only_comparison=None):
        self.guard(token, ('summary',))
        for value in (four_bar_count_preserved, tonic_confirmation):
            self.report(value)
        self.text(explanation)
        if self.pass_number == 2:
            self.report(extra_emphasis_removed)
            self.text(harmony_only_comparison)
        elif extra_emphasis_removed is not None or harmony_only_comparison is not None:
            raise ValueError('harmony-only comparison belongs to second pass')
        self.summary = {'four_bar_count_preserved_self_report': four_bar_count_preserved,
                        'tonic_confirmation_self_report': tonic_confirmation,
                        'explanation_self_report': explanation,
                        'extra_emphasis_removed_self_report': extra_emphasis_removed,
                        'harmony_only_comparison_self_report': harmony_only_comparison,
                        'performance_observed': False}
        self.changed('release')

    def reports_satisfied(self):
        if len(self.bars) != 4 or self.summary is None:
            return False
        return (all(b['played_as_shown_self_report'] == 'yes' for b in self.bars)
                and self.summary['four_bar_count_preserved_self_report'] == 'yes'
                and self.summary['tonic_confirmation_self_report'] == 'yes'
                and (self.bars[1]['pivot_extra_beat_self_report'] == 'yes' if self.pass_number == 1
                     else self.summary['extra_emphasis_removed_self_report'] == 'yes'))

    def release(self, token, instrument_released):
        self.guard(token, ('release',))
        if instrument_released is not True:
            raise ValueError('explicit manual instrument release before next pass or retry')
        report = {'kind': 'released_pass', 'pass_number': self.pass_number,
                  'bars': deepcopy(self.bars), 'summary': deepcopy(self.summary),
                  'manual_release_self_report': True, 'reports_satisfied': self.reports_satisfied()}
        self.history.append(report)
        if not report['reports_satisfied']:
            self.changed('retry_required')
        elif self.pass_number == 1:
            self.pass_number = 2
            self.bars, self.summary = [], None
            self.changed('ready')
        else:
            self.changed('complete_manual_reports')

    def request_retry(self, token, reason):
        self.guard(token, ('bar', 'summary', 'release', 'retry_required', 'complete_manual_reports'))
        self.text(reason)
        self.history.append({'kind': 'retry_requested', 'pass_number': self.pass_number,
                             'reason': reason, 'bars': deepcopy(self.bars), 'summary': deepcopy(self.summary)})
        self.changed('retry_release')

    def retry_after_release(self, token, instrument_released):
        self.guard(token, ('retry_release',))
        if instrument_released is not True:
            raise ValueError('explicit release before manual retry')
        self.history.append({'kind': 'retry_release', 'pass_number': self.pass_number,
                             'manual_release_self_report': True})
        self.generation += 1
        self.bars, self.summary = [], None
        self.changed('ready')

    def cancel(self, token):
        self.guard(token, ('setup', 'ready', 'bar', 'summary', 'release', 'retry_required',
                           'retry_release', 'complete_manual_reports'))
        self.history.append({'kind': 'cancel', 'stage': self.stage,
                             'instruction': 'Stop and release your instrument. No app sound is running.'})
        self.cancelled = True
        self.generation += 1
        self.revision += 1

    def reopen(self, token, instrument_released):
        if not self.cancelled or type(token) is not ActionToken or token != self.token():
            raise ValueError('current cancelled instance token required')
        if instrument_released is not True:
            raise ValueError('confirm manual release before reopening')
        self.cancelled = False
        self.generation += 1
        self.revision += 1
        self.history.append({'kind': 'reopen', 'manual_release_self_report': True})

    def snapshot(self):
        return deepcopy({'route': self.c['package_key'], 'pass_number': self.pass_number,
                         'stage': self.stage, 'context': self.context, 'bars': self.bars,
                         'summary': self.summary, 'history': self.history, 'cancelled': self.cancelled,
                         'manual_task_reports_complete': not self.cancelled and self.stage == 'complete_manual_reports',
                         'performance_observed': False, 'app_audio_supplied': False,
                         'Attempt_credit': False, 'mastery_awarded': False, 'persistence_supplied': False})
