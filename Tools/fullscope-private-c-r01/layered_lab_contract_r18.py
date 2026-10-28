"""Private manual lab prototype. Role reports are not observed audio or credit."""
import copy


class LayeredLabSession:
    def __init__(self, contract):
        self.c = copy.deepcopy(contract)
        self.source = None
        self.worksheet = {}
        self.scores = {}
        self.verifications = []
        self.listens = []
        self.relistened = set()
        self.repair = None
        self.history = []
        self.disclosed = False
        self.external_exposure = False
        self.cancelled = False

    def active(self):
        if self.cancelled:
            raise ValueError('reopen cancelled lab first')

    @staticmethod
    def text(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('nonempty manual text required; uncertainty is permitted')

    @staticmethod
    def confidence(value):
        if type(value) is not int or value not in (0, 1, 2):
            raise ValueError('integer confidence or score 0, 1 or 2 required')

    @staticmethod
    def block(value):
        if type(value) is not int or value not in (1, 2, 3, 4):
            raise ValueError('one of four source blocks required')

    def complete(self):
        return list(self.worksheet) == self.c['worksheet_layer_order']

    def bind_source(self, mode, description, performed_or_recorded_report,
                    recording_reference=None, prior_learner_exposure=False):
        self.active()
        self.text(description)
        self.text(performed_or_recorded_report)
        if self.source is not None or mode not in ('partner', 'recording'):
            raise ValueError('bind one external partner or once-recorded source')
        if type(prior_learner_exposure) is not bool:
            raise ValueError('explicit prior source exposure self-report required')
        if recording_reference is not None:
            self.text(recording_reference)
        if mode == 'partner' and recording_reference is not None:
            raise ValueError('partner route does not claim a recording')
        self.source = {'mode': mode, 'description_self_report': description,
                       'performed_or_recorded_self_report': performed_or_recorded_report,
                       'recording_reference': recording_reference,
                       'recording_reference_required_by_printed_source': False,
                       'audio_observed': False, 'availability_verified': False}
        self.external_exposure = prior_learner_exposure

    def report_prior_learner_source_exposure(self, explanation):
        self.active()
        self.text(explanation)
        self.external_exposure = True
        self.history.append({'kind': 'reported_external_source_exposure',
                             'explanation_self_report': explanation})

    def source_player_view(self):
        self.active()
        return {'role': 'external_source_player',
                'bars': copy.deepcopy(self.c['source_bars']),
                'instructions': copy.deepcopy(self.c['source_player_instructions']),
                'app_audio_supplied': False, 'learner_view_does_not_supply_this_script': True}

    def commit_layer(self, layer, sixteen_bar_responses, four_confidences):
        self.active()
        if self.source is None:
            raise ValueError('external source prerequisite must be declared')
        order = self.c['worksheet_layer_order']
        if self.complete() or layer != order[len(self.worksheet)]:
            raise ValueError('complete each printed layer across sixteen bars in source order')
        if not isinstance(sixteen_bar_responses, list) or len(sixteen_bar_responses) != 16:
            raise ValueError('sixteen explicit bar responses required')
        for value in sixteen_bar_responses:
            self.text(value)
        if not isinstance(four_confidences, list) or len(four_confidences) != 4:
            raise ValueError('confidence for each four-bar block required')
        for value in four_confidences:
            self.confidence(value)
        self.worksheet[layer] = {'bar_responses': copy.deepcopy(sixteen_bar_responses),
                                'block_confidence_self_reports': list(four_confidences),
                                'prior_reference_disclosure': self.disclosed,
                                'prior_external_source_exposure': self.external_exposure}

    def relisten_priority(self):
        self.active()
        return [{'layer': layer, 'block': i + 1}
                for layer, row in self.worksheet.items()
                for i, value in enumerate(row['block_confidence_self_reports'])
                if value == 0 and (layer, i + 1) not in self.relistened]

    def report_relisten(self, layer, block, explanation):
        self.active()
        self.text(explanation)
        self.block(block)
        if layer not in self.worksheet:
            raise ValueError('worksheet response precedes targeted re-listen report')
        priority = self.relisten_priority()
        target = {'layer': layer, 'block': block}
        if priority and target not in priority:
            raise ValueError('re-listen to confidence-zero blocks first')
        self.listens.append({**target, 'description_self_report': explanation,
                             'audio_observed': False})
        self.relistened.add((layer, block))

    def learner_view(self):
        self.active()
        return {'next_layer': None if self.complete() else self.c['worksheet_layer_order'][len(self.worksheet)],
                'worksheet': copy.deepcopy(self.worksheet),
                'reference': copy.deepcopy(self.c['verification_reference']) if self.complete() and self.disclosed else None,
                'source_bars': copy.deepcopy(self.c['source_bars']) if self.complete() and self.disclosed else None,
                'prior_reference_disclosure': self.disclosed,
                'prior_external_source_exposure': self.external_exposure,
                'manual_scores': copy.deepcopy(self.scores), 'automatic_score': None}

    def reveal_reference(self):
        self.active()
        if not self.complete():
            raise ValueError('reference check only after all seven worksheet layers are complete')
        self.disclosed = True
        return self.learner_view()

    def score_layer(self, layer, score, explanation):
        self.active()
        self.confidence(score)
        self.text(explanation)
        if not self.complete() or layer not in self.c['manual_score_layers'] or self.repair is not None:
            raise ValueError('score a source layer only after worksheet completion and repair replay')
        previous = copy.deepcopy(self.scores.get(layer))
        if previous is not None:
            self.history.append({'kind': 'manual_score_revision', 'layer': layer, 'previous': previous})
        self.scores[layer] = {'score_self_report': score, 'rationale_self_report': explanation,
                              'correctness_verified': False}

    def report_verification(self, name, explanation):
        self.active()
        self.text(explanation)
        if not self.complete() or name not in self.c['verification_passes'] or self.repair is not None:
            raise ValueError('named source verification pass after worksheet and repair replay required')
        self.verifications.append({'pass': name, 'report': explanation, 'performance_observed': False})

    def begin_repair(self, error_class, worksheet_layer, block, explanation):
        self.active()
        self.block(block)
        self.text(explanation)
        mapping = self.c['error_to_worksheet_layers']
        if not self.complete() or self.repair is not None:
            raise ValueError('complete worksheet and prior full-block repair replay first')
        if error_class not in mapping or worksheet_layer not in mapping[error_class]:
            raise ValueError('classify the faulty source layer before changing its responses')
        self.repair = {'error_class': error_class, 'layer': worksheet_layer, 'block': block,
                       'classification_self_report': explanation,
                       'before_worksheet': copy.deepcopy(self.worksheet),
                       'before_scores': copy.deepcopy(self.scores), 'corrected': False}

    def correct_faulty_block(self, four_bar_responses, confidence):
        self.active()
        self.confidence(confidence)
        if self.repair is None or self.repair['corrected']:
            raise ValueError('one classified repair must await complete-block replay')
        if not isinstance(four_bar_responses, list) or len(four_bar_responses) != 4:
            raise ValueError('only the selected four-bar block may be replaced')
        for value in four_bar_responses:
            self.text(value)
        layer, block = self.repair['layer'], self.repair['block']
        start = 4 * (block - 1)
        self.worksheet[layer]['bar_responses'][start:start + 4] = copy.deepcopy(four_bar_responses)
        self.worksheet[layer]['block_confidence_self_reports'][block - 1] = confidence
        self.relistened.discard((layer, block))
        self.scores.pop(self.c['error_to_score_layer'][self.repair['error_class']], None)
        self.repair['corrected'] = True

    def report_complete_block_replay(self, explanation, previously_correct_layer_damaged):
        self.active()
        self.text(explanation)
        if type(previously_correct_layer_damaged) is not bool:
            raise ValueError('explicit manual damage-check outcome required')
        if self.repair is None or not self.repair['corrected']:
            raise ValueError('classified correction before complete-block replay report')
        self.history.append({'kind': 'classified_layer_repair', **copy.deepcopy(self.repair),
                             'complete_block_replay_self_report': explanation,
                             'previously_correct_layer_damaged_self_report': previously_correct_layer_damaged,
                             'followup_classification_needed': previously_correct_layer_damaged,
                             'performance_observed': False, 'after_worksheet': copy.deepcopy(self.worksheet)})
        self.repair = None

    def restart_worksheet(self, reason):
        self.active()
        self.text(reason)
        if self.repair is not None:
            raise ValueError('resolve the active correction and block replay before restarting')
        self.history.append({'kind': 'worksheet_revision', 'reason': reason,
                             'previous_worksheet': copy.deepcopy(self.worksheet),
                             'previous_scores': copy.deepcopy(self.scores),
                             'prior_reference_disclosure': self.disclosed,
                             'previous_verifications': copy.deepcopy(self.verifications),
                             'previous_listens': copy.deepcopy(self.listens)})
        self.worksheet, self.scores, self.verifications, self.listens = {}, {}, [], []
        self.relistened.clear()

    def cancel(self):
        self.cancelled = True

    def reopen(self):
        self.cancelled = False

    def snapshot(self):
        return copy.deepcopy({'source': self.source, 'worksheet': self.worksheet,
                              'scores': self.scores, 'verifications': self.verifications,
                              'listens': self.listens, 'active_repair': self.repair,
                              'history': self.history, 'prior_reference_disclosure': self.disclosed,
                              'prior_external_source_exposure': self.external_exposure,
                              'cancelled': self.cancelled, 'app_audio_supplied': False,
                              'performance_observed': False, 'Attempt_credit': False,
                              'mastery_awarded': False, 'automatic_pass_threshold': None})
