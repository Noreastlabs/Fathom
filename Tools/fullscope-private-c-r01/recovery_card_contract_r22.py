"""Manual source/alternate recovery pair; no timer, sound or scored Attempt."""
import copy


class RecoveryCardSession:
    def __init__(self, contract):
        self.c = copy.deepcopy(contract)
        self.context = None
        self.phase = 'printed_pair'
        self.contact_reports = []
        self.outcome = None
        self.selected_alternate = False
        self.history = []
        self.cancelled = False

    def active(self):
        if self.cancelled:
            raise ValueError('reopen cancelled recovery task first')

    @staticmethod
    def text(v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('nonempty manual context/report required')

    def bind_context(self, active_chord, pulse_description, form_description, next_landmark):
        self.active()
        for v in (pulse_description, form_description, next_landmark):
            self.text(v)
        if self.context is not None or active_chord != self.c['active_chord']:
            raise ValueError('bind the exact stated chord and one explicit manual form context')
        self.context = {'active_chord': active_chord, 'pulse_description_self_report': pulse_description,
                        'form_description_self_report': form_description,
                        'next_harmonic_landmark_self_report': next_landmark,
                        'context_origin': 'performer-supplied surrounding form/pulse; not a fixed printed timing grid',
                        'performance_observed': False}

    def current_contact(self):
        self.active()
        if self.context is None or self.outcome is not None or len(self.contact_reports) == 2:
            return None
        key = 'printed_contacts' if self.phase == 'printed_pair' else 'authored_upper_octave_candidate'
        return copy.deepcopy(self.c[key][len(self.contact_reports)])

    def report_contact(self, phase, source_order, explanation):
        self.active()
        self.text(explanation)
        if self.current_contact() is None or phase != self.phase or type(source_order) is not int or source_order != len(self.contact_reports)+1:
            raise ValueError('report each exact pair contact in source order; explicit manual progression only')
        self.contact_reports.append({'phase': phase, 'mapped_source_order': source_order,
                                     'explanation_self_report': explanation, 'performance_observed': False})

    def report_resolution(self, pulse_and_form_continued, resolved_before_landmark, explanation):
        self.active()
        self.text(explanation)
        if len(self.contact_reports) != 2 or self.outcome is not None:
            raise ValueError('both contacts before one pulse/landmark report; explicit retry for revision')
        if type(pulse_and_form_continued) is not bool or type(resolved_before_landmark) is not bool:
            raise ValueError('two explicit yes/no self-reports required')
        self.outcome = {'pulse_and_form_continued_self_report': pulse_and_form_continued,
                        'resolved_before_landmark_self_report': resolved_before_landmark,
                        'explanation_self_report': explanation, 'timing_or_sound_verified': False}

    def reported_resolution_satisfied(self):
        return bool(self.outcome and self.outcome['pulse_and_form_continued_self_report']
                    and self.outcome['resolved_before_landmark_self_report'])

    def select_upper_octave_candidate(self):
        self.active()
        if self.phase != 'printed_pair' or not self.reported_resolution_satisfied():
            raise ValueError('complete source pair and pulse/landmark reports before explicit alternate selection')
        self.history.append({'kind': 'printed_pair_recorded', 'contacts': copy.deepcopy(self.contact_reports),
                             'resolution': copy.deepcopy(self.outcome)})
        self.selected_alternate = True
        self.phase, self.contact_reports, self.outcome = 'chosen_upper_octave', [], None
        return copy.deepcopy(self.c['authored_upper_octave_candidate'])

    def retry_current_pair(self, reason):
        self.active()
        self.text(reason)
        self.history.append({'kind': 'pair_retry', 'phase': self.phase, 'reason': reason,
                             'prior_contact_reports': copy.deepcopy(self.contact_reports),
                             'prior_outcome': copy.deepcopy(self.outcome)})
        self.contact_reports, self.outcome = [], None

    def cancel(self):
        self.cancelled = True

    def reopen(self):
        self.cancelled = False

    def snapshot(self):
        return copy.deepcopy({'context': self.context, 'phase': self.phase,
                              'contact_reports': self.contact_reports, 'outcome': self.outcome,
                              'selected_alternate': self.selected_alternate, 'history': self.history,
                              'manual_task_reports_complete': self.phase == 'chosen_upper_octave' and self.reported_resolution_satisfied(),
                              'cancelled': self.cancelled, 'sound_or_timing_observed': False,
                              'app_audio_supplied': False, 'Attempt_credit': False, 'mastery_awarded': False})
