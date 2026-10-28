"""External-source manual rhythm dictation; no acoustic assessment or playback."""
import copy


class RhythmDictationSession:
    def __init__(self, contract):
        self.c = copy.deepcopy(contract)
        self.source = None
        self.hearing_reports = []
        self.contacts = None
        self.stability = []
        self.pitch_or_chord = None
        self.history = []
        self.disclosed = False
        self.prior_source_study = False
        self.cancelled = False

    def active(self):
        if self.cancelled:
            raise ValueError('reopen cancelled dictation first')

    @staticmethod
    def text(x):
        if not isinstance(x, str) or not x.strip():
            raise ValueError('explicit text/self-report required; uncertainty is allowed')

    def bind_external_source(self, description, surface, performer_realization, prior_learner_study=False):
        self.active()
        self.text(description)
        self.text(performer_realization)
        if self.source is not None or surface not in ('unpitched_contacts', 'external_pitch_or_chord'):
            raise ValueError('one explicit external sound source required')
        if type(prior_learner_study) is not bool:
            raise ValueError('source-study report must be bool')
        self.source = {'description_self_report': description, 'surface': surface,
                       'performer_realization_self_report': performer_realization,
                       'realization_origin': 'external performer, not printed pitch/tempo authority',
                       'source_available_verified': False, 'app_audio_supplied': False}
        self.prior_source_study = self.prior_source_study or prior_learner_study

    def source_player_view(self):
        self.active()
        return {'rhythm_script': self.c['source_rhythm_string'],
                'instructions': self.c['source_instruction'], 'external_realization': copy.deepcopy(self.source),
                'script_timing_unit': None, 'app_audio_supplied': False}

    def report_hearing(self, description):
        self.active()
        self.text(description)
        if self.source is None:
            raise ValueError('declare the external source before hearing report')
        self.hearing_reports.append({'self_report': description, 'audio_observed': False})

    def submit_contacts(self, transcript, grouping_and_ties_description):
        self.active()
        self.text(transcript)
        self.text(grouping_and_ties_description)
        if not self.hearing_reports or self.contacts is not None:
            raise ValueError('source-hearing report and explicit revision if replacing contacts required')
        self.contacts = {'transcript': transcript, 'grouping_ties_self_report': grouping_and_ties_description,
                         'prior_reference_disclosure': self.disclosed,
                         'prior_source_study_self_report': self.prior_source_study,
                         'correctness_verified': False}

    def report_rhythm_stability(self, stable, rationale):
        self.active()
        self.text(rationale)
        if self.contacts is None or type(stable) is not bool:
            raise ValueError('contacts first and explicit stable/not-stable report required')
        if self.pitch_or_chord is not None:
            self.history.append({'kind': 'pitch_response_invalidated_by_new_stability_report',
                                 'previous_pitch_response': copy.deepcopy(self.pitch_or_chord)})
            self.pitch_or_chord = None
        self.stability.append({'stable_self_report': stable, 'rationale': rationale,
                               'acoustic_stability_verified': False})

    def submit_pitch_or_chord(self, answer):
        self.active()
        self.text(answer)
        if self.source is None or self.source['surface'] != 'external_pitch_or_chord':
            raise ValueError('no invented pitch answer for an unpitched contact source')
        if not self.stability or not self.stability[-1]['stable_self_report']:
            raise ValueError('identify pitch/chord only after rhythm is self-reported stable')
        if self.pitch_or_chord is not None:
            raise ValueError('explicit response revision required')
        self.pitch_or_chord = {'answer_self_report': answer, 'source_pitch_answer_printed': False,
                              'correctness_verified': False}

    def learner_view(self):
        self.active()
        return {'learner_contacts': copy.deepcopy(self.contacts),
                'rhythm_reference': self.c['source_rhythm_string'] if self.disclosed and self.contacts else None,
                'prior_reference_disclosure': self.disclosed,
                'prior_source_study_self_report': self.prior_source_study,
                'stability_self_reports': copy.deepcopy(self.stability),
                'pitch_answer': copy.deepcopy(self.pitch_or_chord), 'automatic_score': None}

    def reveal_rhythm_reference(self):
        self.active()
        if self.contacts is None:
            raise ValueError('own contact transcription before reference disclosure')
        self.disclosed = True
        return self.learner_view()

    def revise_contacts(self, reason):
        self.active()
        self.text(reason)
        self.history.append({'kind': 'manual_response_revision', 'reason': reason,
                             'contacts': copy.deepcopy(self.contacts), 'stability': copy.deepcopy(self.stability),
                             'pitch_or_chord': copy.deepcopy(self.pitch_or_chord),
                             'hearing_reports': copy.deepcopy(self.hearing_reports),
                             'prior_reference_disclosure': self.disclosed})
        self.contacts, self.pitch_or_chord = None, None
        self.stability, self.hearing_reports = [], []

    def manual_responses_complete(self):
        return bool(self.contacts and self.stability and self.stability[-1]['stable_self_report']
                    and (self.source['surface'] == 'unpitched_contacts' or self.pitch_or_chord))

    def cancel(self):
        self.cancelled = True

    def reopen(self):
        self.cancelled = False

    def snapshot(self):
        return copy.deepcopy({'source': self.source, 'contacts': self.contacts,
                              'hearing_reports': self.hearing_reports, 'stability': self.stability,
                              'pitch_or_chord': self.pitch_or_chord, 'history': self.history,
                              'prior_reference_disclosure': self.disclosed,
                              'prior_source_study_self_report': self.prior_source_study,
                              'cancelled': self.cancelled, 'manual_responses_complete': self.manual_responses_complete(),
                              'performance_observed': False, 'app_audio_supplied': False,
                              'Attempt_credit': False, 'mastery_awarded': False})
