"""Private manual source-task model. No clock, audio, storage or evaluated outcome."""
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


class StudySession:
    def __init__(self, contract):
        if not contract.get('complete_manual_contract'):
            raise ValueError('incomplete contract')
        self.contract = deepcopy(contract)
        self.instance = object()
        self.route = contract['package_key']
        self.generation = self.pass_number = 1
        self.action = 0
        self.stage = 'setup'
        self.choice = self.report = self.resume_stage = None
        self.history = []

    def token(self):
        return Token(self.instance, self.route, self.generation,
                     self.pass_number, self.action, self.stage)

    def _check(self, token, stages):
        if token != self.token() or self.stage not in stages:
            raise ValueError('stale/foreign action or invalid stage')

    def _move(self, stage):
        self.stage = stage
        self.action += 1

    @staticmethod
    def _text(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('explicit nonempty choice/reason required')

    def configure(self, token, own_instrument, timing_plan):
        self._check(token, ('setup', 'ready'))
        if own_instrument is not True:
            raise ValueError('own instrument prerequisite')
        self._text(timing_plan)
        if self.choice is not None:
            self.history.append({'kind': 'prior_choice', 'choice': deepcopy(self.choice)})
        self.choice = {'own_instrument': True, 'timing_plan': timing_plan}
        self._move('ready')

    def begin(self, token):
        self._check(token, ('ready',))
        self._move('perform_eight_bars')

    def release(self, token, instrument_released):
        self._check(token, ('perform_eight_bars',))
        if instrument_released is not True:
            raise ValueError('explicit manual release required')
        self._move('report')

    def respond(self, token, response):
        self._check(token, ('report',))
        flags = ('printed_order', 'four_tones_each_bar', 'modulation_route_addressed',
                 'destination_confirmed')
        required = set(flags) | {'destination_bars', 'audit_response', 'exact_bar', 'reflection'}
        if not isinstance(response, dict) or set(response) != required:
            raise ValueError('exact response schema required')
        if any(response[k] not in ('yes', 'no', 'uncertain') for k in flags):
            raise ValueError('manual response must be yes/no/uncertain')
        bars = response['destination_bars']
        if (not isinstance(bars, list) or any(type(x) is not int or x < 1 or x > 8 for x in bars)
                or len(set(bars)) != len(bars)):
            raise ValueError('distinct original source bars 1..8 required')
        audit, exact = response['audit_response'], response['exact_bar']
        if audit not in ('named', 'uncertain', 'not_heard'):
            raise ValueError('explicit audit response required')
        if audit == 'named':
            if type(exact) is not int or exact < 1 or exact > 8:
                raise ValueError('exact source bar 1..8 required')
        elif exact is not None:
            raise ValueError('unresolved audit must not invent exact bar')
        if not isinstance(response['reflection'], str):
            raise ValueError('reflection must be text; empty is permitted')
        self.report = deepcopy(response)
        self.history.append({'kind': 'manual_report', 'pass': self.pass_number,
                             'response': deepcopy(response)})
        satisfied = (all(response[k] == 'yes' for k in flags)
                     and len(bars) >= 3 and audit == 'named')
        self._move('complete_manual_reports' if satisfied else 'retry_required')

    def request_retry(self, token, reason):
        self._check(token, ('complete_manual_reports', 'retry_required'))
        self._text(reason)
        self.history.append({'kind': 'retry_requested', 'pass': self.pass_number, 'reason': reason})
        self._move('retry_release')

    def retry_release(self, token, instrument_released):
        self._check(token, ('retry_release',))
        if instrument_released is not True:
            raise ValueError('explicit manual release required')
        self.pass_number += 1
        self.report = None
        self._move('ready')

    def cancel(self, token):
        self._check(token, ('setup', 'ready', 'perform_eight_bars', 'report',
                            'complete_manual_reports', 'retry_required', 'retry_release'))
        self.resume_stage = self.stage
        self.generation += 1
        self._move('cancelled')

    def reopen(self, token, instrument_released):
        self._check(token, ('cancelled',))
        if instrument_released is not True:
            raise ValueError('manual release before reopening required')
        stage, self.resume_stage = self.resume_stage, None
        self.generation += 1
        self._move(stage)

    def snapshot(self):
        return deepcopy({'route': self.route, 'stage': self.stage, 'generation': self.generation,
                         'pass': self.pass_number, 'action': self.action,
                         'resume_stage': self.resume_stage, 'choice': self.choice,
                         'report': self.report, 'history': self.history,
                         'source_script': self.contract['source_script'],
                         'manual_reports_complete': self.stage == 'complete_manual_reports',
                         'performance_observed': False, 'app_audio_supplied': False,
                         'automatic_evaluation': False, 'Attempt_credit': False,
                         'mastery_awarded': False, 'persistence_supplied': False})
