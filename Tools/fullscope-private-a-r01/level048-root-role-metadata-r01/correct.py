"""Delete only proven harmonic root hints from untyped rest metadata."""
import copy


def removable(block):
    roles = {t['column'] for row in block['notation_rows'] if row['label'] in ('Rol', 'Job')
             for t in row['tokens'] if t['text'] == 'R'}
    candidates = roles & set(block['printed_rest_columns'])
    notes = {}
    for row in block['notation_rows']:
        if row['label'] == 'Nte':
            for token in row['tokens']:
                notes.setdefault(token['column'], []).append(token['text'])
    for col in candidates:
        if col not in notes or len(notes[col]) != 1 or notes[col][0] not in ('A', 'D', 'E'):
            raise ValueError('Root hint lacks one corresponding source sounding tonic; retain for review')
    return candidates


def correct(record):
    result = copy.deepcopy(record)
    removed = []
    for block in result['source_payload']['notation_blocks']:
        columns = removable(block)
        removed.extend({'block_index': block['block_index'], 'column': col} for col in sorted(columns))
        block['printed_rest_columns'] = [col for col in block['printed_rest_columns'] if col not in columns]
    return result, removed


def validate(before, after):
    expected, _ = correct(before)
    actual = copy.deepcopy(after)
    actual['provenance'].pop('root_role_metadata_correction', None)
    if actual != expected:
        raise ValueError('Change exceeds proved source_payload rest-hint correction')
