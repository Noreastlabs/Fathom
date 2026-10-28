"""Manual vocabulary/memory and external two-cell variation; no playback."""
import copy


class RhythmVocabularySession:
    basic_order = ['clap_cell', 'speak_grid', 'play_one_muted_string']
    variation_response_order = ['attacks', 'rests_ties', 'accents']

    def __init__(self, contract, catalogue):
        self.c = copy.deepcopy(contract)
        self.catalogue = copy.deepcopy(catalogue)
        self.cells = {v['name']: v for v in self.catalogue['cells']}
        if len(self.cells) != 16 or self.c['source_cell'] != self.cells.get(self.c['source_cell']['name']):
            raise ValueError('exact original sixteen-cell catalogue and matching cell required')
        self.basic_reports = []
        self.phase = 'study'
        self.memory_answer = None
        self.memory_disclosed = False
        self.pair = None
        self.external = None
        self.repeat_reports = []
        self.variation_answers = {}
        self.variation_disclosed = False
        self.history = []
        self.cancelled = False

    def active(self):
        if self.cancelled:
            raise ValueError('reopen cancelled source task first')

    @staticmethod
    def text(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('nonempty manual response required; explicit uncertainty allowed')

    def report_basic_step(self, name, explanation):
        self.active()
        self.text(explanation)
        if self.phase != 'study' or len(self.basic_reports) >= 3 or name != self.basic_order[len(self.basic_reports)]:
            raise ValueError('clap, speak grid, then play one muted string in printed order')
        self.basic_reports.append({'step': name, 'explanation_self_report': explanation,
                                   'performance_observed': False})

    def hide_for_memory(self):
        self.active()
        if self.phase != 'study' or len(self.basic_reports) != 3:
            raise ValueError('complete the three practice reports before memory response')
        self.phase = 'write_from_memory'

    def submit_memory(self, response):
        self.active()
        self.text(response)
        if self.phase != 'write_from_memory' or self.memory_answer is not None:
            raise ValueError('hide reference before one written memory response')
        self.memory_answer = {'response': response, 'prior_comparison_disclosure': self.memory_disclosed,
                              'initial_source_study_expected': True, 'correctness_verified': False}
        self.phase = 'memory_response_recorded'

    def reveal_memory_comparison(self):
        self.active()
        if self.memory_answer is None:
            raise ValueError('write from memory before comparing source')
        self.memory_disclosed = True
        self.phase = 'memory_comparison'
        return self.learner_view()

    def begin_variation(self, ordered_two_names, source_description, performer_realization):
        self.active()
        self.text(source_description)
        self.text(performer_realization)
        if self.pair is not None:
            raise ValueError('explicit variation revision before selecting another source pair')
        if not isinstance(ordered_two_names, list) or len(ordered_two_names) != 2 or any(n not in self.cells for n in ordered_two_names):
            raise ValueError('exactly two ordered original catalogue cell selections required')
        self.pair = [copy.deepcopy(self.cells[n]) for n in ordered_two_names]
        self.external = {'source_description_self_report': source_description,
                         'performer_realization_self_report': performer_realization,
                         'performer_choices_are_original_source_facts': False,
                         'availability_verified': False, 'app_audio_supplied': False}

    def source_player_variation_view(self):
        self.active()
        return {'ordered_cell_segments': copy.deepcopy(self.pair),
                'repeat_complete_pair_count': 4, 'external_source': copy.deepcopy(self.external),
                'timing_conversion_performed': False, 'source_instruction': self.catalogue['variation_instruction']}

    def report_variation_repeat(self, repeat_number, explanation):
        self.active()
        self.text(explanation)
        if self.pair is None or type(repeat_number) is not int or repeat_number != len(self.repeat_reports) + 1 or repeat_number > 4:
            raise ValueError('four complete-pair rendition reports in source order required')
        self.repeat_reports.append({'repeat': repeat_number, 'explanation_self_report': explanation,
                                    'audio_observed': False})

    def submit_variation_layer(self, layer, response):
        self.active()
        self.text(response)
        if len(self.repeat_reports) != 4 or len(self.variation_answers) >= 3 or layer != self.variation_response_order[len(self.variation_answers)]:
            raise ValueError('after four renditions write attacks, then rests/ties, then accents')
        self.variation_answers[layer] = {'response': response,
                                         'prior_reference_disclosure': self.variation_disclosed,
                                         'correctness_verified': False}

    def reveal_variation_reference(self):
        self.active()
        if len(self.variation_answers) != 3:
            raise ValueError('all three written layers before pair reference')
        self.variation_disclosed = True
        return self.learner_view()

    def learner_view(self):
        self.active()
        return {'phase': self.phase,
                'source_cell': copy.deepcopy(self.c['source_cell']) if self.phase in ('study', 'memory_comparison') else None,
                'written_memory': copy.deepcopy(self.memory_answer),
                'prior_memory_comparison_disclosure': self.memory_disclosed,
                'variation_answers': copy.deepcopy(self.variation_answers),
                'variation_reference_segments': copy.deepcopy(self.pair) if self.variation_disclosed and len(self.variation_answers) == 3 else None,
                'prior_variation_reference_disclosure': self.variation_disclosed,
                'automatic_score': None}

    def restart_basic(self, reason):
        self.active()
        self.text(reason)
        self.history.append({'kind': 'basic_revision', 'reason': reason,
                             'prior_reports': copy.deepcopy(self.basic_reports),
                             'prior_memory_answer': copy.deepcopy(self.memory_answer),
                             'prior_comparison_disclosure': self.memory_disclosed})
        self.basic_reports, self.memory_answer, self.phase = [], None, 'study'

    def restart_variation(self, reason):
        self.active()
        self.text(reason)
        self.history.append({'kind': 'variation_revision', 'reason': reason,
                             'ordered_pair': copy.deepcopy(self.pair), 'external_source': copy.deepcopy(self.external),
                             'repeat_reports': copy.deepcopy(self.repeat_reports),
                             'answers': copy.deepcopy(self.variation_answers),
                             'prior_reference_disclosure': self.variation_disclosed})
        self.pair, self.external, self.repeat_reports, self.variation_answers = None, None, [], {}

    def cancel(self):
        self.cancelled = True

    def reopen(self):
        self.cancelled = False

    def snapshot(self):
        return copy.deepcopy({'basic_reports': self.basic_reports, 'phase': self.phase,
                              'memory_answer': self.memory_answer, 'memory_disclosed': self.memory_disclosed,
                              'ordered_pair': self.pair, 'external_source': self.external,
                              'repeat_reports': self.repeat_reports, 'variation_answers': self.variation_answers,
                              'variation_disclosed': self.variation_disclosed, 'history': self.history,
                              'cancelled': self.cancelled, 'performance_observed': False,
                              'app_audio_supplied': False, 'Attempt_credit': False, 'mastery_awarded': False})
