"""Exact one-key source-reviewed correction; r62 history and the other thirteen keys untouched."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_path = Path(__file__).resolve().parents[1] / 'coherent-batch-resume-r62/chord_tone_contract.py'
_spec = importlib.util.spec_from_file_location('fathom_c_r62_chord_reference', _path)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
KEY = base.OCCLUDED_KEY
PC, COMMON, TRANSFER, SETS = base.PC, base.COMMON, base.TRANSFER, base.SETS
Refusal, require, fields = base.Refusal, base.require, base.fields
DECISION = 'Results/manager-resume-r02/private-source-bulk-review-r01/source-decisions.json'
DECISION_SHA = '80abbfbaedf4393d44fe2aac21329ca2382892263e23f69c1943037a41bad8d0'

def source_authority():
    data = (ROOT / DECISION).read_bytes()
    require(len(data) == 6619 and hashlib.sha256(data).hexdigest() == DECISION_SHA,
            'exact independent source decision identity')
    row = next((row for row in json.loads(data)['decisions'] if row['package_key'] == KEY), None)
    require(row is not None and row['source_decision'] == 'Accept'
            and row['producer_r62_disposition_decision'] == 'Correct'
            and row['exact_source_literal'] == ['G#7alt', '3', 'B# / C'],
            'exact one-key source Accept and r62 disposition Correct')
    return {'path': DECISION, 'bytes': len(data), 'sha256': DECISION_SHA,
            'source_decision': 'Accept', 'producer_r62_disposition_decision': 'Correct'}

class SourceReviewedChordToneFlow(base.ChordToneFlow):
    def __init__(self, key):
        require(type(key) is str and key == KEY, 'exact already-reserved final chord-tone child only')
        self.source_decision = source_authority()
        super().__init__(key)

    def begin(self, token, confirmation=None):
        self.check(token, ('ready',))
        # The source decision is mandatory, exact and immutable; no caller approval flag.
        source_authority()
        if self.stage == 0:
            fields(confirmation, ('key', 'chord', 'role', 'ready'))
            require(confirmation == {'key': self.key, 'chord': 'G#7alt', 'role': '3', 'ready': True}
                    and confirmation['ready'] is True, 'exact current G#7alt/third cue confirmation')
            self.clear_initial()
            state = 'hearing'
        else:
            require(confirmation is None and self.first_reported, 'first string-set report before transfer')
            state = 'silent_setup'
        self.cycle += 1
        self.record('begin_source_reviewed_row', {'cue_confirmation': confirmation,
                    'source_decision': deepcopy(self.source_decision), 'hearing_observed': False}, state)

    def source_player_view(self):
        view = super().source_player_view()
        view['source_visibility'] = 'ORIGINAL_RENDER_OCCLUDED_SOURCE_AUTHORITY_ACCEPTED'
        view['independent_source_decision'] = deepcopy(self.source_decision)
        return view

    def learner_view(self):
        view = super().learner_view()
        view['source_visibility'] = 'ORIGINAL_RENDER_OCCLUDED_SOURCE_AUTHORITY_ACCEPTED'
        return view

def contract():
    result = base.contract(13)
    result['schema_version'] = 'fathom-private-source-reviewed-chord-tone-realization.1'
    result['source_visibility'] = 'ORIGINAL_RENDER_OCCLUDED_SOURCE_AUTHORITY_ACCEPTED'
    result['independent_source_decision'] = source_authority()
    result['manual_model'] = 'SourceReviewedChordToneFlow'
    result['authored_policies'] = [p for p in result['authored_policies'] if 'practice start refuses' not in p]
    result['authored_policies'].append('Final official row15 identity and B# / C literal remain exact. Independent source Accept enables the same private manual task; the original visual occlusion remains provenance and source clocks/voicing/contacts remain unknown.')
    result['complete_manual_contract'] = True
    return result
