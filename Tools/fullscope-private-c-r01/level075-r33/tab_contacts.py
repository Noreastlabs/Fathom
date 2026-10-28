"""Bounded ASCII TAB source recovery. Coordinates are source layout, never a clock."""
import re
from copy import deepcopy

ORDER = ('e', 'B', 'G', 'D', 'A', 'E')
TUNING = {'e': 64, 'B': 59, 'G': 55, 'D': 50, 'A': 45, 'E': 40}
COUNT = ('1', '&', '2', '&', '3', '&', '4', '&')
KEYS = tuple('exercise-completeness-r01/level075/moduleb/'+s for s in (
    'p004-card01/cleantriadrole', 'p004-card02/mutedverserole',
    'p004-card03/openchorusrole', 'p004-card04/fillafterspacerole'))

class Refusal(ValueError):
    pass

def require(ok, why):
    if not ok:
        raise Refusal(why)

def parse_tab(text):
    require(type(text) is str and bool(text), 'TAB text required')
    lines = text.splitlines(); rows = []; symbols = []
    for line_number, line in enumerate(lines, 1):
        if '|' not in line:
            continue
        match = re.fullmatch(r'([eBGDAE])\|([0-9x-]+)\|', line.strip())
        require(match is not None, 'unsupported or malformed TAB row')
        string, body = match.groups()
        require(string not in [r['string'] for r in rows], 'duplicate string row')
        row = {'string': string, 'source_line_in_region': line_number, 'body': body,
               'source_text': line, 'body_columns': len(body)}
        rows.append(row)
        for token in re.finditer(r'\d+|x', body):
            literal = token.group(); fret = None if literal == 'x' else int(literal)
            require(fret is None or (str(fret) == literal and 0 <= fret <= 24), 'unsupported fret')
            symbols.append({'string': string, 'fret': fret, 'source_literal': literal,
                            'source_line_in_region': line_number, 'source_column_zero_based': token.start(),
                            'source_token_width': len(literal)})
    require(bool(rows) and bool(symbols), 'no supported TAB contacts')
    require([ORDER.index(r['string']) for r in rows] == sorted(ORDER.index(r['string']) for r in rows), 'string rows out of order')
    columns = sorted({s['source_column_zero_based'] for s in symbols})
    for symbol in symbols:
        start = symbol['source_column_zero_based']; width = symbol['source_token_width']
        require(not any(start < c < start+width for c in columns), 'misaligned multi-digit contact columns')
    events = []
    for group, column in enumerate(columns, 1):
        members = sorted((s for s in symbols if s['source_column_zero_based'] == column),
                         key=lambda s: ORDER.index(s['string']))
        for symbol in members:
            midi = None if symbol['fret'] is None else TUNING[symbol['string']]+symbol['fret']
            events.append({**symbol, 'source_order': len(events)+1, 'attack_group': group,
                           'kind': 'muted_string_stroke' if midi is None else 'pitched_string_contact',
                           'midi': midi, 'derived_pitch_name': None if midi is None else
                           ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')[midi % 12]+str(midi//12-1),
                           'is_rest': False, 'finger': None, 'onset_q': None, 'duration_q': None,
                           'sounded_duration_q': None, 'timing_kind': 'SOURCE_ORDER_ONLY',
                           'pitch_derivation': 'printed standard tuning + numeric fret' if midi is not None else None})
    return {'rows': rows, 'events': events, 'attack_group_count': len(columns)}

def muted_verse_grid(key, events, count_line):
    require(key == KEYS[1], 'finite muted-verse grid owner only')
    require(type(count_line) is str and tuple(count_line.split()) == COUNT, 'exact eighth-count labels required')
    require(type(events) is list and len(events) == 24, '24 source string contacts required')
    groups = []
    for i in range(8):
        group = events[i*3:(i+1)*3]
        require([e['attack_group'] for e in group] == [i+1]*3, 'eight ordered attack groups')
        require([e['string'] for e in group] == ['B', 'G', 'D'], 'printed string group')
        require([e['source_order'] for e in group] == list(range(i*3+1, i*3+4)), 'source order')
        expected = ['1', '0', '2'] if i % 2 == 0 else ['x']*3
        require([e['source_literal'] for e in group] == expected, 'printed pitched/muted alternation')
        require([e['source_column_zero_based'] for e in group] == [2+2*i]*3, 'printed uniform TAB columns')
        for e in group:
            expected_fret = None if e['source_literal'] == 'x' else int(e['source_literal'])
            expected_midi = None if expected_fret is None else TUNING[e['string']]+expected_fret
            require(e['fret'] == expected_fret and e['midi'] == expected_midi and e['is_rest'] is False, 'contact content drift')
        groups.append(group)
    result = deepcopy(events)
    for e in result:
        i = e['attack_group']-1
        e['onset_q'] = [i//2, 1] if i % 2 == 0 else [i, 2]
        e['duration_q'] = [1, 2]
        e['timing_kind'] = 'SOURCE_RELATIVE_RHYTHMIC_SLOT_NOT_SOUND_GATE'
        e['count_label'] = COUNT[i]
        e['sounded_duration_q'] = None
    return result
