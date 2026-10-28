#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level56 source candidate."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('Build/parallel-11/2.3.1.2.1-level056-whole-r01')
STEM = 'Guitar_Exercises_Section_VI_Level_56_Natural_Minor_Harmony_Minor_Key_Progressions_and_Raised_Seventh_Dominant_Preparation'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', '77c6cf5aa49b3e078f93990b4350abda7dbff38b73b23736df1e5f6df2a729f9', 25514)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', '4cf52fd867a32b9c267de5041ef0c34219cd9563495bb0634c7301affcc69564', 62826)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
KEYS_LADDER = ('A', 'E', 'B', 'F#', 'C#', 'D')
KEYS_CIRCLE = ('D', 'A', 'E', 'B', 'F#', 'C#')
ROMANS = ('i', 'ii°', 'III', 'iv', 'v', 'VI', 'VII')
QUALITIES = ('minor', 'diminished', 'major', 'minor', 'minor', 'major', 'major')
DEGREES = ('1', '2', 'b3', '4', '5', 'b6', 'b7')
OFFSETS = (0, 2, 3, 5, 7, 8, 10)
BASE_PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'E#': 5, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'B#': 0}
STRING_BASES = {'D-G-B': (50, 55, 59), 'E-A-D': (40, 45, 50), 'G-B-e': (55, 59, 64)}
RAISED = {'A': 'G#', 'E': 'D#', 'B': 'A#', 'F#': 'E#', 'C#': 'B#', 'D': 'C#'}
FUNCTION = {'i': 'T', 'ii°': 'P', 'III': 'T', 'iv': 'P', 'v': 'wD', 'VI': 'P/T', 'VII': 'wD', 'V': 'D'}
PROGRESSION_ROMANS = {'C': ('i', 'iv', 'v', 'i'), 'D': ('i', 'iv', 'V', 'i'), 'E': ('i', 'VI', 'III', 'VII'), 'F': ('i', 'VII', 'VI', 'V'), 'G': ('i', 'iv', 'VI', 'V'), 'H': ('ii°', 'V', 'i', 'i')}
MODULE_PAGES = {'A': [2], 'B': [3, 4, 5, 6, 7, 8], 'C': [9], 'D': [10], 'E': [11], 'F': [12], 'G': [13], 'H': [14], 'I': [15, 16], 'J': [17], 'K': [18]}


class SourceError(ValueError):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise SourceError(message)


def pin(root: Path, spec: tuple[str, str, int]) -> bytes:
    rel, digest, size = spec
    target = root / rel
    try:
        resolved = target.resolve(strict=True)
    except OSError as exc:
        raise SourceError(f'missing pinned source: {rel}') from exc
    need(not target.is_symlink() and resolved.is_relative_to(root) and resolved.is_file(), f'unsafe source: {rel}')
    raw = target.read_bytes()
    need(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, f'pin drift: {rel}')
    return raw


def ref(start: int, end: int | None = None) -> str:
    return f'L56-TXT-L{start}' if end is None else f'L56-TXT-L{start}-{end}'


def sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-K]) - ', row).group(1)) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-K]) - ', row)]
    need([key for _, key in heads] == list('ABCDEFGHIJK'), 'eleven-module order')
    out = {}
    for n, (i, key) in enumerate(heads):
        next_i = heads[n + 1][0] if n < 10 else next(j for j, row in enumerate(lines) if row == 'PRACTICE PROGRESSION, ERROR REPAIR, AND MASTERY')
        stop = next_i - 1
        need(lines[i - 1].startswith('=') and lines[i + 1].startswith('='), f'{key} section framing')
        out[key] = {'heading': lines[i], 'start_line': i + 1, 'end_line': stop, 'txt_ref': ref(i + 1, stop), 'raw_lines': lines[i:stop], 'content_start': i + 2, 'content_stop': stop, 'pdf_pages': MODULE_PAGES[key]}
    return out


def blocks(lines: list[str], section: dict[str, Any]) -> list[tuple[int, list[str]]]:
    result: list[tuple[int, list[str]]] = []
    start: int | None = None
    for i in range(section['content_start'], section['content_stop']):
        if lines[i] and not lines[i].startswith('='):
            if start is None:
                start = i
        elif start is not None:
            result.append((start, lines[start:i]))
            start = None
    if start is not None:
        result.append((start, lines[start:section['content_stop']]))
    return result


def pipe_values(row: str, prefix: str) -> list[str]:
    need(row.startswith(prefix + ': '), f'{prefix} row')
    return [part.strip() for part in row.split(': ', 1)[1].split('|')]


def pdf_pipe_values(page: list[str], prefix: str) -> list[list[str]]:
    found = []
    for row in page:
        if row.lstrip().startswith(prefix + '|'):
            found.append([part.strip() for part in row.strip().split('|')[1:-1]])
    return found


def triad_pc(frets: str, string_set: str) -> list[int]:
    pieces = frets.split('-')
    need(len(pieces) == 3 and all(re.fullmatch(r'\d+', p) for p in pieces), 'three-fret triad')
    return [(base + int(fret)) % 12 for base, fret in zip(STRING_BASES[string_set], pieces)]


def chord_name(family: dict[str, Any], roman: str) -> str:
    if roman == 'V':
        natural = family['triads'][4]['chord']
        need(natural.endswith('m'), 'natural v name')
        return natural[:-1]
    return family['triads'][ROMANS.index(roman)]['chord']


def parse_b(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> list[dict[str, Any]]:
    group = blocks(lines, section)
    need(len(group) == 6, 'six B ladders')
    out = []
    for n, (start, b) in enumerate(group):
        need(len(b) == 21 and b[0].startswith(KEYS_LADDER[n] + ' MINOR - '), f'B family {n + 1} shape')
        key = KEYS_LADDER[n]
        raw_rows = [[part.strip() for part in row.split('|')] for row in b[2:9]]
        need(all(len(row) == 7 for row in raw_rows), f'B {key} seven-column table')
        notes = [row[1] for row in raw_rows]
        need([row[0] for row in raw_rows] == list(DEGREES) and [row[2] for row in raw_rows] == list(ROMANS) and [row[4] for row in raw_rows] == list(QUALITIES), f'B {key} degree/quality')
        need(all(note in BASE_PC for note in notes) and [(BASE_PC[note] - BASE_PC[key]) % 12 for note in notes] == list(OFFSETS), f'B {key} natural scale pitch')
        need([note[0] for note in notes] == ["ABCDEFG"[("ABCDEFG".index(key[0]) + i) % 7] for i in range(7)], f'B {key} letter spelling')
        string_set = b[9].split(': ', 1)[1]
        need(string_set in STRING_BASES, f'B {key} string set')
        roman, chord, inv, frets = [pipe_values(b[j], prefix) for j, prefix in ((10, 'Roman'), (11, 'Chord'), (12, 'Inv'), (13, 'Fret'))]
        need(roman == list(ROMANS) and len(chord) == len(inv) == len(frets) == 7 and chord == [row[3] for row in raw_rows], f'B {key} ladder columns')
        triads = []
        for j, row in enumerate(raw_rows):
            spelling = row[5].split('-')
            expected = [notes[(j + step) % 7] for step in (0, 2, 4)]
            need(spelling == expected, f'B {key} diatonic triad {j + 1}')
            pitches = triad_pc(frets[j], string_set)
            need(sorted(pitches) == sorted(BASE_PC[note] for note in spelling), f'B {key} fret/spelling {j + 1}')
            inversion = inv[j]
            need(inversion in ('root', '1st', '2nd') and pitches[0] == BASE_PC[spelling[{'root': 0, '1st': 1, '2nd': 2}[inversion]]], f'B {key} inversion {j + 1}')
            triads.append({'degree': row[0], 'note': row[1], 'roman': row[2], 'chord': row[3], 'quality': row[4], 'spelling': spelling, 'function_raw': row[6], 'inversion': inversion, 'frets_low_middle_high': [int(v) for v in frets[j].split('-')], 'pitch_classes_low_middle_high': pitches, 'txt_ref': ref(start + 3 + j), 'raw': b[2 + j]})
        raised = b[15].split(': ', 1)[1].split(' -> ')
        need(raised == [notes[6], RAISED[key]] and (BASE_PC[raised[1]] - BASE_PC[key]) % 12 == 11, f'B {key} raised seventh')
        natural_v = b[16].split(' = ', 1)[1].split('-')
        strong_v = b[17].split(' = ', 1)[1].split('-')
        seventh = b[18].split(' = ', 1)[1].split('-')
        leading = b[19].split(' = ', 1)[1].split('-')
        need(natural_v == triads[4]['spelling'] and strong_v == [notes[4], raised[1], notes[1]] and seventh == strong_v + [notes[3]] and leading == [raised[1], notes[1], notes[3]], f'B {key} v/V/V7/vii° spelling')
        need(b[20] == 'Exercise: one blocked triad plus low-middle-high arpeggio for every natural degree = 28 attacks.', f'B {key} workload')
        page = pages[n + 2]
        need(page[2].endswith('28 ATTACKS') and all(row[5] in page for row in raw_rows), f'B {key} PDF table')
        need(pdf_pipe_values(page, 'Chd') == [chord] and pdf_pipe_values(page, 'Frt') == [frets], f'B {key} PDF ladder')
        out.append({'key': key, 'header': b[0], 'natural_scale': notes, 'relative_major_and_signature_raw': b[0], 'triad_string_set': string_set, 'triads': triads, 'roman_row': roman, 'chord_row': chord, 'inversion_row': inv, 'fret_row': frets, 'rhythm_voicings_raw': b[14], 'raised_seventh': raised[1], 'natural_v_raw': b[16], 'strong_V_raw': b[17], 'V7_raw': b[18], 'leading_vii_diminished_raw': b[19], 'printed_attacks': 28, 'raw_lines': b, 'txt_ref': ref(start + 1, start + len(b)), 'pdf_page': n + 3})
    return out


def parse_progressions(lines: list[str], sections_map: dict[str, dict[str, Any]], pages: list[list[str]], families: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_key = {f['key']: f for f in families}
    out = {}
    for key in 'CDEFGH':
        group = blocks(lines, sections_map[key])
        need(len(group) == 6 and len(group[0][1]) == 6 and all(len(b) == 5 for _, b in group[1:]), f'{key} six progression cells')
        page = pages[MODULE_PAGES[key][0] - 1]
        pdf_chords = pdf_pipe_values(page, 'Chd')
        pdf_roman = pdf_pipe_values(page, 'Rom')
        pdf_function = pdf_pipe_values(page, 'Func')
        need(len(pdf_chords) == len(pdf_roman) == len(pdf_function) == 6 and page[2].endswith('96 ATTACKS'), f'{key} PDF cells')
        items = []
        for n, (start, b) in enumerate(group):
            if n == 0:
                family_title, cell = b[0], b[1:]
                cell_start = start + 1
            else:
                family_title, cell = group[0][1][0], b
                cell_start = start
            minor_key = KEYS_CIRCLE[n]
            need(cell[0].startswith(minor_key + ' minor: '), f'{key} {minor_key} header')
            chord_symbols = cell[0].split(': ', 1)[1].split(' - ')
            romans = cell[1].split(': ', 1)[1].split(' - ')
            functions = cell[2].split(': ', 1)[1].split(' - ')
            voicings = cell[3].split(': ', 1)[1].split(' | ')
            need(romans == list(PROGRESSION_ROMANS[key]) and functions == [FUNCTION[r] for r in romans] and chord_symbols == [chord_name(by_key[minor_key], r) for r in romans] and len(voicings) == 4, f'{key} {minor_key} harmony')
            need(cell[4] == 'Exercise: one bar per chord, four quarter-note attacks per bar = 16 attacks.', f'{key} {minor_key} workload')
            need(pdf_chords[n] == chord_symbols and pdf_roman[n] == romans and pdf_function[n] == functions, f'{key} {minor_key} PDF harmony')
            items.append({'key': minor_key, 'family_title': family_title, 'chord_symbols': chord_symbols, 'roman_symbols': romans, 'function_symbols': functions, 'voicings_raw': cell[3], 'voicing_alternatives_raw': voicings, 'printed_bars': 4, 'printed_attacks_per_bar': 4, 'printed_attacks': 16, 'raw_lines': cell, 'txt_ref': ref(cell_start + 1, cell_start + 5), 'pdf_page': MODULE_PAGES[key][0]})
        out[key] = items
    return out


def parse_i(lines: list[str], section: dict[str, Any], pages: list[list[str]], families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group = blocks(lines, section)
    need(len(group) == 6, 'I six voice-leading cells')
    by_key = {f['key']: f for f in families}
    out = []
    for n, (start, b) in enumerate(group):
        need(len(b) == 9 and b[0].startswith(KEYS_LADDER[n] + ' minor on '), f'I cell {n + 1}')
        key = KEYS_LADDER[n]
        string_set = b[0].split(' on ', 1)[1]
        chords, inversions, frets = [pipe_values(b[j], prefix) for j, prefix in ((1, 'Chord'), (2, 'Inv'), (3, 'Fret'))]
        need(len(chords) == len(inversions) == len(frets) == 4 and chords == [chord_name(by_key[key], r) for r in ('i', 'iv', 'V', 'i')], f'I {key} chords')
        voice_rows = [[int(v) for v in b[j].split(': ', 1)[1].split('-')] for j in (4, 5, 6)]
        need(all(len(row) == 4 for row in voice_rows), f'I {key} voice rows')
        for j, (chord, inversion, fret) in enumerate(zip(chords, inversions, frets)):
            pitches = triad_pc(fret, string_set)
            spelling = by_key[key]['triads'][ROMANS.index(('i', 'iv', 'v', 'i')[j])]['spelling'] if j != 2 else b_for_strong_V(by_key[key])
            need(sorted(pitches) == sorted(BASE_PC[s] for s in spelling), f'I {key} chord pitch {j + 1}')
            need(pitches[0] == BASE_PC[spelling[{'root': 0, '1st': 1, '2nd': 2}[inversion]]], f'I {key} inversion {j + 1}')
            need([row[j] for row in voice_rows] == [int(v) for v in fret.split('-')], f'I {key} voice/fret {j + 1}')
        need(b[7] == f'Raised seventh inside V: {RAISED[key]}' and b[8] == 'Exercise: one blocked attack plus low-middle-high arpeggio per chord = 16 attacks.', f'I {key} raised seventh/count')
        page_number = 15 if n < 3 else 16
        page = pages[page_number - 1]
        pdf_index = n % 3
        need(pdf_pipe_values(page, 'Chd')[pdf_index] == chords and pdf_pipe_values(page, 'Frt')[pdf_index] == frets, f'I {key} PDF voicing')
        out.append({'key': key, 'string_set': string_set, 'chord_symbols': chords, 'inversions': inversions, 'fret_triplets': frets, 'low_middle_high_fret_sequences': voice_rows, 'raised_seventh': RAISED[key], 'printed_attacks': 16, 'raw_lines': b, 'txt_ref': ref(start + 1, start + 9), 'pdf_page': page_number})
    return out


def b_for_strong_V(family: dict[str, Any]) -> list[str]:
    natural = family['triads'][4]['spelling']
    return [natural[0], family['raised_seventh'], natural[2]]


def parse_j(lines: list[str], section: dict[str, Any], pages: list[list[str]], families: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    group = blocks(lines, section)
    need(len(group) == 1 and len(group[0][1]) == 26, 'J 24 written prompts')
    start, b = group[0]
    need(b[0] == 'ANALYZE' and b[13] == 'TRANSPOSE', 'J prompt groups')
    by_key = {f['key']: f for f in families}
    analysis = []
    conflicts = []
    page = pages[16]
    for n, raw in enumerate(b[1:13], 1):
        m = re.fullmatch(r'(\d+)\. ([A-G#dim-]+) \| answer: key ([A-G#]+) minor; ([ivIV°-]+); ([TPwD/-]+)', raw)
        need(m is not None and int(m.group(1)) == n, f'J analyze {n} shape')
        key, chords, romans, functions = m.group(3), m.group(2).split('-'), m.group(4).split('-'), m.group(5).split('-')
        need(key in by_key and len(chords) == len(romans) == len(functions) == 4 and chords == [chord_name(by_key[key], r) for r in romans], f'J analyze {n} chord/function pattern')
        expected = [FUNCTION[r] for r in romans]
        for position, (found, want) in enumerate(zip(functions, expected), 1):
            if found != want:
                need(romans[position - 1] == 'VI' and found == 'P' and want == 'P/T' and n in (4, 5, 9, 10), f'J analyze {n} unexpected function conflict')
                conflicts.append({'kind': 'VI_function_label_differs_between_progression_and_analysis_key', 'analysis_number': n, 'position': position, 'roman': 'VI', 'progression_label': want, 'analysis_label': found, 'txt_ref': ref(start + 1 + n), 'pdf_ref': 'L56-PDF-p17-self-check', 'status': 'pending_curriculum_review'})
        need(f'{key}: {m.group(4)}; {m.group(5)}' in page, f'J analyze {n} PDF answer')
        analysis.append({'number': n, 'progression_chords': chords, 'answer_key': key, 'answer_romans': romans, 'answer_functions_raw': functions, 'raw': raw, 'txt_ref': ref(start + 1 + n), 'pdf_page': 17})
    transpose = []
    for n, raw in enumerate(b[14:], 1):
        m = re.fullmatch(r'(\d+)\. Move ([ivIV°-]+) from ([A-G#]+) minor to ([A-G#]+) minor \| answer: ([A-G#dim-]+)', raw)
        need(m is not None and int(m.group(1)) == n, f'J transpose {n} shape')
        romans, source_key, target_key, chords = m.group(2).split('-'), m.group(3), m.group(4), m.group(5).split('-')
        need(source_key in by_key and target_key in by_key and len(romans) == len(chords) == 4 and chords == [chord_name(by_key[target_key], r) for r in romans], f'J transpose {n} target harmony')
        need(m.group(5) in page, f'J transpose {n} PDF answer')
        transpose.append({'number': n, 'roman_pattern': romans, 'source_key': source_key, 'target_key': target_key, 'answer_chords': chords, 'raw': raw, 'txt_ref': ref(start + 14 + n), 'pdf_page': 17})
    need(len(conflicts) == 4, 'J expected source function-label differences')
    return {'analysis': analysis, 'transpose': transpose, 'written_prompt_count': 24, 'raw_lines': b, 'txt_ref': ref(start + 1, start + 26), 'pdf_page': 17}, conflicts


def parse_k(lines: list[str], section: dict[str, Any], pages: list[list[str]], progressions_d: list[dict[str, Any]]) -> dict[str, Any]:
    group = blocks(lines, section)
    need(len(group) == 1 and len(group[0][1]) == 39, 'K six-key capstone')
    start, b = group[0]
    page = pages[17]
    pdf_chords = pdf_pipe_values(page, 'Chd')
    need(len(pdf_chords) == 6, 'K PDF six-key cells')
    cells = []
    for n in range(6):
        cell = b[n * 6:n * 6 + 6]
        key = KEYS_CIRCLE[n]
        need(cell[0] == f'Bars {4 * n + 1}-{4 * n + 4}: {key} minor', f'K {key} bar range')
        chords, roman, functions, voicings = [pipe_values(cell[j], prefix) for j, prefix in ((1, 'Chord'), (2, 'Roman'), (3, 'Function'), (4, 'Voicings'))]
        counterpart = progressions_d[n]
        need(chords == counterpart['chord_symbols'] and roman == counterpart['roman_symbols'] and functions == counterpart['function_symbols'] and len(voicings) == 4 and cell[5] == f'Raised seventh: {RAISED[key]}', f'K {key} harmony')
        need(pdf_chords[n] == chords, f'K {key} PDF harmony')
        cells.append({'key': key, 'bars': [4 * n + 1, 4 * n + 2, 4 * n + 3, 4 * n + 4], 'chord_symbols': chords, 'roman_symbols': roman, 'function_symbols': functions, 'voicing_alternatives_raw': cell[4], 'raised_seventh': RAISED[key], 'printed_attacks': 16, 'raw_lines': cell, 'txt_ref': ref(start + n * 6 + 1, start + n * 6 + 6), 'pdf_page': 18})
    passes = b[36:]
    need(passes == ['Pass 1: four quarter-note rhythm attacks per bar = 96 attacks.', 'Pass 2: replace V with V7.', 'Pass 3: use the nearest-inversion triad route and announce the next key during beat 4.'], 'K pass alternatives')
    need(page[2] == '24 BARS  |  D-A-E-B-F#-C#  |  96 ATTACKS', 'K PDF total')
    return {'circle_order': list(KEYS_CIRCLE), 'cells': cells, 'passes_raw': passes, 'printed_bars': 24, 'printed_attacks': 96, 'raw_lines': b, 'txt_ref': ref(start + 1, start + 39), 'pdf_page': 18}


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 590 and len(pages) == 20, 'TXT/PDF coverage')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION VI, LEVEL 56', 'NATURAL-MINOR HARMONY, MINOR-KEY PROGRESSIONS, AND RAISED-SEVENTH DOMINANT PREPARATION'], 'TXT identity')
    need(all(page[0] == 'Guitar Exercises - Section VI, Level 56' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need(pages[0][2] == '6 KEYS  |  11 MODULES  |  936 ATTACKS' and 'COMPLETE SOUNDED WORKOUT: 936 attacks.' in lines, 'workload declaration')
    mapped = next((row for row in source_map['rows'] if row.get('level') == 56), None)
    need(mapped is not None and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.2.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map status')
    need(mapped['txt_path'] == TXT[0] and mapped['txt_sha256'] == TXT[1] and mapped['txt_bytes'] == TXT[2] and mapped['pdf_path'] == PDF[0] and mapped['pdf_sha256'] == PDF[1] and mapped['pdf_bytes'] == PDF[2], 'source-map identity')
    section_map = sections(lines)
    a = blocks(lines, section_map['A'])
    need(len(a) == 1 and len(a[0][1]) == 4 and a[0][1][0] == 'Practice keys in circle order: D -> A -> E -> B -> F# -> C#.', 'A circle order')
    need(pages[0][25:27] == ['A - spelling', '42 silent'] and pages[1][2] == '42 SILENT SPELLINGS  |  6 PRACTICE KEYS', 'A silent count PDF')
    b = parse_b(lines, section_map['B'], pages)
    b_by_key = {family['key']: family for family in b}
    silent_items = [{'practice_key': key, 'degree': triad['degree'], 'scale_note': triad['note'], 'roman': triad['roman'], 'natural_triad_chord': triad['chord'], 'natural_triad_spelling': triad['spelling'], 'source_refs': [ref(a[0][0] + 1, a[0][0] + 4), triad['txt_ref']], 'pdf_page': 2} for key in KEYS_CIRCLE for triad in b_by_key[key]['triads']]
    need(len(silent_items) == 42, 'A explicit six-by-seven silent prompts')
    progression = parse_progressions(lines, section_map, pages, b)
    i = parse_i(lines, section_map['I'], pages, b)
    j, conflicts = parse_j(lines, section_map['J'], pages, b)
    k = parse_k(lines, section_map['K'], pages, progression['D'])
    sounded = 6 * 28 + sum(sum(item['printed_attacks'] for item in progression[key]) for key in 'CDEFGH') + sum(item['printed_attacks'] for item in i) + k['printed_attacks']
    need(sounded == 936 and j['written_prompt_count'] == 24 and 6 * 7 == 42, 'silent/written/sounded reconciliation')
    need(pages[0][25:39] == ['A - spelling', '42 silent', 'B - six ladders', '168', 'C-H - six families', '576', 'I - voice leading', '96', 'J - analysis', '24 written', 'K - circle capstone', '96', 'TOTAL', '936'], 'PDF workload table')
    need('Natural-v versus strong-V ear loop' in pages[18] and 'Advancement rule' in pages[18] and 'Completion audit' in pages[19] and 'Practice log' in pages[19], 'PDF-only guidance')
    need(lines[556] == 'PRACTICE PROGRESSION, ERROR REPAIR, AND MASTERY' and lines[578] == 'MASTERY GATE' and lines[588] == 'NEXT LEVEL', 'TXT guidance boundary')
    source = {name: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for name, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level056.detached-source-candidate.1', 'wbs': '2.3.1.2.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'unique_full_chord_voicings': None, 'optional_pass_attack_count': None, 'source': source, 'source_map_row': mapped, 'module_sections': section_map, 'modules': {'A': {'practice_keys_circle_order': list(KEYS_CIRCLE), 'natural_roman_sequence': list(ROMANS), 'silent_spelling_prompts': 42, 'silent_spelling_items': silent_items, 'raw_lines': a[0][1], 'txt_ref': ref(a[0][0] + 1, a[0][0] + 4), 'pdf_page': 2}, 'B': b, **progression, 'I': i, 'J': j, 'K': k}, 'written_prompts': 24, 'silent_spelling_prompts': 42, 'sounded_attacks_by_module': {'B': 168, **{key: 96 for key in 'CDEFGH'}, 'I': 96, 'K': 96}, 'sounded_attack_total': 936, 'source_conflicts': conflicts, 'source_differences': [{'kind': 'PDF_only_v_V_V7_ear_loop_and_advancement_rule', 'pdf_ref': 'L56-PDF-p19-L31-50', 'pdf_text': pages[18][30:50], 'txt_equivalent': None}, {'kind': 'PDF_only_completion_audit_and_practice_log', 'pdf_ref': 'L56-PDF-p20-L14-31', 'pdf_text': pages[19][13:31], 'txt_equivalent': None}, {'kind': 'PDF_additional_progression_passes_and_voicing_substitutions', 'pdf_pages': list(range(9, 15)), 'detail': 'PDF adds second-pass triad/partial voicing directions and key-by-key function/ear instructions; full page text retained.'}], 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_practice_mastery_next_lines': lines[556:], 'pdf_practice_mastery_pages': pages[18:]}}


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')


def output_path(root: Path, value: str) -> Path:
    root = root.resolve(strict=True)
    rel = Path(value)
    need(not rel.is_absolute() and '..' not in rel.parts and rel.parts[:len(BUILD.parts)] == BUILD.parts and rel.suffix == '.json', 'output outside reserved Build directory')
    path = root
    for part in rel.parts:
        path = path / part
        need(not path.is_symlink(), 'symlink output path')
    need(not path.exists(), 'refusing overwrite')
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    target = output_path(ROOT, args.output)
    candidate = build_candidate(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encode(candidate))
    print(f'{target.relative_to(ROOT)} bytes={target.stat().st_size} sha256={hashlib.sha256(target.read_bytes()).hexdigest()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
