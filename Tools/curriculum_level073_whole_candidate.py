#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level73 modulation source candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.3.1-level073-whole-r01')
STEM = 'Guitar_Exercises_Section_X_Level_73_Common_Tone_and_Guide_Tone_Modulation_Pivot_Chords_Chromatic_Mediants_and_Key_Center_Navigation'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', '63fed22776f4fcfd61ac9b7783b456c8996f2b438c06886d585bff2ee01afd15', 30640)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', '7cc4c0098855c8e6d4b90063fb947b763e32a4225d66b77821f9e23f763779f9', 52388)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
KEYS = tuple('ABCDEFGHI')
CELL_COUNTS = {'A': 8, 'B': 6, 'D': 6, 'E': 6, 'F': 5, 'G': 8, 'H': 4, 'I': 12}
CELL_TONES = {'A': 8, 'B': 16, 'D': 12, 'E': 16, 'F': 12, 'G': 16, 'H': 16, 'I': 2}
EXPECTED = {'A': 64, 'B': 96, 'C': 48, 'D': 72, 'E': 96, 'F': 60, 'G': 128, 'H': 64, 'I': 24}
PDF_PAGES = {'A': (3, 4), 'B': (5, 6), 'D': (8, 9), 'E': (10, 11), 'F': (12,), 'G': (13, 14, 15, 16), 'H': (17, 18), 'I': (19,)}
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
OPEN = {'e': 64, 'B': 59, 'G': 55, 'D': 50, 'A': 45, 'E': 40}
ROLE_OFFSET = {'R': 0, '1': 0, '2': 2, '9': 2, 'b2': 1, 'b9': 1, '3': 4, 'b3': 3, '5': 7, '7': 11, 'M7': 11, 'b7': 10}
NOTE = re.compile(r'[A-G](?:#|b)?(?=-|\|)')


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


def ref(first: int, last: int | None = None) -> str:
    return f'L73-TXT-L{first}' if last is None else f'L73-TXT-L{first}-{last}'


def segments(row: str) -> list[str]:
    return [part.rstrip('-') for part in row.split('|')[1:] if part != '']


def chord_root(chord: str) -> str:
    match = re.match(r'[A-G](?:#|b)?', chord)
    need(match is not None and match.group() in PC, f'invalid chord: {chord}')
    return match.group()


def chord_pcs(chord: str) -> set[int]:
    root = PC[chord_root(chord)]
    suffix = chord[len(chord_root(chord)):]
    need(suffix in ('maj7', 'm7', '7'), f'unhandled chord quality: {chord}')
    intervals = (0, 4, 7, 11) if suffix == 'maj7' else (0, 3, 7, 10) if suffix == 'm7' else (0, 4, 7, 10)
    return {(root + step) % 12 for step in intervals}


def section_blocks(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-I]) - ', row).group(1), row) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-I]) - ', row)]
    need(len(heads) == 9 and tuple(letter for _, letter, _ in heads) == KEYS, 'module heading order')
    out = {}
    for n, (start, letter, heading) in enumerate(heads):
        stop = heads[n + 1][0] - 1 if n < 8 else next(i for i, row in enumerate(lines) if row == 'PRACTICE PROGRESSION, ERROR REPAIR, AND MASTERY') - 1
        need(lines[start - 1].startswith('=') and lines[start + 1].startswith('='), f'{letter} frame')
        out[letter] = {'heading': heading, 'start_line': start + 1, 'end_line': stop, 'txt_ref': ref(start + 1, stop), 'raw_lines': lines[start:stop]}
    return out


def parse_cell(lines: list[str], at: int, letter: str, ordinal: int, context: list[str]) -> tuple[dict[str, Any], int]:
    need(lines[at].startswith('Nte|') and lines[at + 1].startswith('Rol|'), f'{letter} note/role pair at {at + 1}')
    end = at + 2
    while end < len(lines) and re.match(r'^  [eBGDAE]\|', lines[end]):
        end += 1
    rows = lines[at:end]
    need(len(rows) >= 3 and len({row[2] for row in rows[2:]}) == len(rows) - 2, f'{letter} TAB rows at {at + 1}')
    bodies = [row.split('|', 1)[1] for row in rows]
    need(len(set(map(len, bodies))) == 1, f'{letter} aligned width at {at + 1}')
    matches = list(NOTE.finditer(bodies[0]))
    need(len(matches) == CELL_TONES[letter], f'{letter} note count at {at + 1}')
    frets = [(m.start(), row[2], int(m.group())) for row, body in zip(rows[2:], bodies[2:]) for m in re.finditer(r'\d+', body)]
    need(sorted(m.start() for m in matches) == sorted(col for col, _, _ in frets), f'{letter} note/TAB columns at {at + 1}')
    by_col = {col: (string, fret) for col, string, fret in frets}
    events = []
    for n, m in enumerate(matches):
        col = m.start()
        name, (string, fret) = m.group(), by_col[col]
        need(name in PC and (OPEN[string] + fret) % 12 == PC[name], f'{letter} note/TAB pitch at {at + 1}, column {col}')
        next_col = matches[n + 1].start() if n + 1 < len(matches) else len(bodies[0])
        events.append({'note': name, 'string': string, 'fret': fret, 'pitch_class': PC[name], 'role_slot_raw': bodies[1][col:next_col], 'source_column': col, 'source_bar_ordinal': bodies[0][:col].count('|') + 1})
    out = {'ordinal': ordinal + 1, 'note_names': [e['note'] for e in events], 'role_row_raw': rows[1], 'tab_rows': rows[2:], 'events': events, 'printed_tones': len(events), 'context_raw': context, 'raw_lines': rows, 'txt_ref': ref(at + 1, end)}
    return out, end


def parse_cells(lines: list[str], section: dict[str, Any], letter: str) -> list[dict[str, Any]]:
    start, stop = section['start_line'], section['end_line']
    positions = [i for i in range(start, stop) if lines[i].startswith('Nte|')]
    need(len(positions) == CELL_COUNTS[letter], f'{letter} Nte cell count')
    result = []
    prior_end = start + 1
    for n, at in enumerate(positions):
        cell, prior_end = parse_cell(lines, at, letter, n, lines[prior_end:at])
        result.append(cell)
    return result


def parse_guide_sheet(lines: list[str], at: int, ordinal: int) -> dict[str, Any]:
    need(lines[at].startswith('Chd|'), f'C chord grid at {at + 1}')
    heads = lines[at - 2:at]
    need(len(heads) == 2 and ' -> ' in heads[0] and heads[1].startswith('Chords: '), f'C route heading at {at + 1}')
    chords = segments(lines[at])
    need(len(chords) == 4, f'C four chords at {at + 1}')
    voices = []
    for number, first in ((1, at + 1), (2, at + 4)):
        note_row, role_row, fret_row = lines[first:first + 3]
        need(note_row.startswith(f'V{number}N|') and role_row.startswith(f'V{number}R|') and re.match(fr'^V{number}[eBGDAE]\|', fret_row) is not None, f'C voice {number} rows at {at + 1}')
        string = fret_row[2]
        names = segments(note_row)
        roles = segments(role_row)
        fret_tokens = segments(fret_row)
        need(len(names) == len(roles) == len(fret_tokens) == 4, f'C voice {number} four bars at {at + 1}')
        entries = []
        for bar, (name, role, fret_raw, chord) in enumerate(zip(names, roles, fret_tokens, chords), 1):
            need(name in PC and role in ROLE_OFFSET and fret_raw.isdigit(), f'C voice {number} notation at {at + 1}, bar {bar}')
            fret = int(fret_raw)
            need((OPEN[string] + fret) % 12 == PC[name], f'C voice {number} note/fret at {at + 1}, bar {bar}')
            need((PC[chord_root(chord)] + ROLE_OFFSET[role]) % 12 == PC[name] and PC[name] in chord_pcs(chord), f'C voice {number} chord role at {at + 1}, bar {bar}')
            entries.append({'bar': bar, 'chord': chord, 'note': name, 'role': role, 'string': string, 'fret': fret, 'pitch_class': PC[name]})
        voices.append({'voice': number, 'string': string, 'events': entries, 'note_row_raw': note_row, 'role_row_raw': role_row, 'fret_row_raw': fret_row, 'txt_ref': ref(first + 1, first + 3)})
    return {'ordinal': ordinal + 1, 'route': heads[0], 'chords_raw': heads[1], 'chords': chords, 'chord_row_raw': lines[at], 'voices': voices, 'printed_tones': 8, 'txt_ref': ref(at - 1, at + 7), 'raw_lines': lines[at - 2:at + 7]}


def parse_guide_sheets(lines: list[str], section: dict[str, Any], pdf_page: list[str]) -> list[dict[str, Any]]:
    positions = [i for i in range(section['start_line'], section['end_line']) if lines[i].startswith('Chd|')]
    need(len(positions) == 6, 'C six guide-tone worksheets')
    sheets = [parse_guide_sheet(lines, at, n) for n, at in enumerate(positions)]
    pdf_chords = [row for row in pdf_page if row.startswith('Chd|')]
    need(len(pdf_chords) == 6, 'C PDF worksheet count')
    for sheet, raw in zip(sheets, pdf_chords):
        need(sheet['chord_row_raw'] == raw, f'C PDF chord grid {sheet["route"]}')
        for voice in sheet['voices']:
            need(all(row in pdf_page for row in (voice['note_row_raw'], voice['role_row_raw'], voice['fret_row_raw'])), f'C PDF voice rows {sheet["route"]}')
        sheet['pdf_ref'] = 'L73-PDF-p7'
    return sheets


def pdf_note_correspondence(modules: dict[str, list[dict[str, Any]]], pages: list[list[str]]) -> None:
    for letter, page_nums in PDF_PAGES.items():
        rows = [(page_num, j + 1, line) for page_num in page_nums for j, line in enumerate(pages[page_num - 1]) if line.startswith('Nte|')]
        cells = modules[letter]
        need(len(rows) == len(cells), f'{letter} PDF Nte row count')
        for cell, (page_num, line, raw) in zip(cells, rows):
            names = [m.group() for m in NOTE.finditer(raw.split('|', 1)[1])]
            need(names == cell['note_names'], f'{letter} PDF/TXT notes at p{page_num}:L{line}')
            pdf_rows = {row.rstrip('|') for row in pages[page_num - 1]}
            need(all(source_row.rstrip('|') in pdf_rows for source_row in cell['raw_lines']), f'{letter} PDF/TXT notation rows at p{page_num}:L{line}')
            cell['pdf_ref'] = f'L73-PDF-p{page_num}-L{line}'
            cell['pdf_note_row_raw'] = raw


def check_chord_route(cells: list[dict[str, Any]], chord_lists: list[list[str]], letter: str) -> None:
    for cell, chords in zip(cells, chord_lists):
        need(len(cell['events']) == 4 * len(chords), f'{letter} bar/chord count')
        for n, event in enumerate(cell['events']):
            chord = chords[n // 4]
            role = event['role_slot_raw'].strip('-|')
            need(role in ROLE_OFFSET and (PC[chord_root(chord)] + ROLE_OFFSET[role]) % 12 == event['pitch_class'] and event['pitch_class'] in chord_pcs(chord), f'{letter} chord role at {cell["txt_ref"]}, event {n + 1}')
            need(event['source_bar_ordinal'] == n // 4 + 1, f'{letter} bar marker at {cell["txt_ref"]}')
        cell['chords'] = chords


def progression(context: list[str], prefix: str) -> list[str]:
    matches = [row for row in context if row.startswith(prefix)]
    need(len(matches) == 1, f'missing {prefix} progression')
    return [part.strip() for part in re.findall(r'\|([^|]+)', matches[0])]


def check_modules(modules: dict[str, list[dict[str, Any]]], sheets: list[dict[str, Any]], pages: list[list[str]]) -> list[dict[str, Any]]:
    ambiguities = []
    for cell in modules['A']:
        route = next((row for row in cell['context_raw'] if re.fullmatch(r'[^ ]+ -> [^ ]+', row)), None)
        need(route is not None, 'A route heading')
        old, new = route.split(' -> ')
        common = {name for name in cell['note_names'] if PC[name] in chord_pcs(old) & chord_pcs(new)}
        ct = {event['note'] for event in cell['events'] if event['role_slot_raw'].strip('-|') == 'CT'}
        need(ct and ct <= common and cell['note_names'][:4] and cell['note_names'][4:], 'A common-tone labels')
        cell['route'] = route
        cell['printed_common_tones'] = sorted(ct)
        cell['barline_repeats_note'] = cell['note_names'][3] == cell['note_names'][4]
        if not cell['barline_repeats_note']:
            ambiguities.append({'kind': 'A_PDF_barline_sustain_conflicts_with_printed_note_change', 'status': 'pending_curriculum_review', 'route': route, 'txt_ref': cell['txt_ref'], 'pdf_ref': cell['pdf_ref'], 'printed_barline_notes': cell['note_names'][3:5], 'pdf_instruction_ref': 'L73-PDF-p4-L4-5'})
    need(len(ambiguities) == 3 and all('PDF-p4' in item['pdf_ref'] for item in ambiguities), 'A three barline conflicts')
    check_chord_route(modules['B'], [progression(cell['context_raw'], 'Progression:') for cell in modules['B']], 'B')
    for cell in modules['D']:
        route = next((row for row in cell['context_raw'] if re.fullmatch(r'[^ ]+ -> [^ ]+', row)), None)
        need(route is not None, 'D chromatic-mediant route')
        old, new = route.split(' -> ')
        notes = cell['note_names']
        need(all(name == notes[4] for name in notes[4:8]) and PC[notes[4]] in chord_pcs(old) & chord_pcs(new), 'D four-register common-tone bridge')
        need(all(PC[name] in chord_pcs(old) for name in notes[:4]) and all(PC[name] in chord_pcs(new) for name in notes[8:]), 'D source/destination arpeggios')
        need(all(event['role_slot_raw'].strip('-|') == 'CT' for event in cell['events'][4:8]), 'D CT roles')
        cell['route'] = route
        cell['bridge_note'] = notes[4]
    for cell in modules['E']:
        role_halves = [[e['role_slot_raw'].strip('-|') for e in cell['events'][start:start + 8]] for start in (0, 8)]
        need(role_halves[0] == role_halves[1] and role_halves[0] in (['1', '3', '5', '7', '5', '3', '2', '1'], ['1', 'b3', '5', 'b7', '5', 'b3', '2', '1']), 'E motif contour')
        cell['degree_formula'] = role_halves[0]
    check_chord_route(modules['F'], [progression(cell['context_raw'], 'Bridge:') for cell in modules['F']], 'F')
    for study in range(4):
        first, second = modules['G'][2 * study:2 * study + 2]
        chords = progression(first['context_raw'], 'Progression:')
        need(len(chords) == 8 and second['context_raw'][-1] == 'Bars 5-8', 'G eight-bar study context')
        check_chord_route([first, second], [chords[:4], chords[4:]], 'G')
        first['study_number'] = second['study_number'] = study + 1
        first['absolute_bars'] = [1, 2, 3, 4]
        second['absolute_bars'] = [5, 6, 7, 8]
    route = progression(modules['H'][0]['context_raw'], 'Progression:')
    need(len(route) == 16, 'H sixteen-bar route')
    check_chord_route(modules['H'], [route[n * 4:n * 4 + 4] for n in range(4)], 'H')
    for n, cell in enumerate(modules['H']):
        cell['absolute_bars'] = list(range(4 * n + 1, 4 * n + 5))
    for card in modules['I']:
        heading = next((row for row in card['context_raw'] if re.match(r'^[A-G](?:#|b)?(?:maj7|m7|7): ', row)), None)
        need(heading is not None, 'I recovery heading')
        match = re.fullmatch(r'([^:]+): ([A-G](?:#|b)?) -> ([A-G](?:#|b)?)   ([#bMR0-9]+) -> ([#bMRa-z0-9]+)', heading)
        need(match is not None, 'I recovery notation')
        chord, weak, target, weak_role, target_role = match.groups()
        printed_roles = [weak_role, 'R' if target_role == 'root' else target_role]
        need(card['note_names'] == [weak, target] and [e['role_slot_raw'].strip('-|') for e in card['events']] == printed_roles, 'I recovery TXT note/role')
        need(all(role in ROLE_OFFSET and (PC[chord_root(chord)] + ROLE_OFFSET[role]) % 12 == PC[note] for note, role in zip((weak, target), printed_roles)), 'I recovery pitch roles')
        card['chord'] = chord
        card['weak_note'] = weak
        card['target_note'] = target
    need(len(sheets) == 6 and sum(s['printed_tones'] for s in sheets) == 48, 'C six two-voice sheets')
    need(pages[3][3] == 'THE NOTE AT THE BARLINE STAYS; ITS HARMONIC ROLE CHANGES' and pages[3][4].startswith('Play each cell as two bars of quarter notes. Sustain the common tone'), 'A PDF barline instruction')
    return ambiguities


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 668 and len(pages) == 20, 'TXT/PDF extent')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION X, LEVEL 73', 'COMMON-TONE AND GUIDE-TONE MODULATION, PIVOT CHORDS, CHROMATIC MEDIANTS, AND KEY-CENTER NAVIGATION'], 'TXT title')
    need(all(page[0] == 'Guitar Exercises - Section X, Level 73' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need('COMPLETE WRITTEN WORKOUT: 652 sounding tones before repeats.' in lines and pages[0][2] == '9 MODULES  |  652 TONES  |  SECTION X BEGINS', 'workout declaration')
    mapped = next((r for r in source_map['rows'] if r.get('level') == 73), None)
    need(mapped is not None and mapped['section'] == 'X' and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.3.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map status')
    need(all(mapped[f'{key}_path'] == spec[0] and mapped[f'{key}_sha256'] == spec[1] and mapped[f'{key}_bytes'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair identity')
    sections = section_blocks(lines)
    modules = {letter: parse_cells(lines, sections[letter], letter) for letter in CELL_COUNTS}
    sheets = parse_guide_sheets(lines, sections['C'], pages[6])
    pdf_note_correspondence(modules, pages)
    ambiguities = check_modules(modules, sheets, pages)
    need(sum(len(group) for group in modules.values()) == 55, 'all 55 note/TAB cells')
    counts = {letter: sum(c['printed_tones'] for c in modules[letter]) if letter != 'C' else sum(s['printed_tones'] for s in sheets) for letter in KEYS}
    need(counts == EXPECTED and sum(counts.values()) == 652, '652-tone module reconciliation')
    need([int(pages[0][i]) for i in range(28, 46, 2)] == list(EXPECTED.values()) and pages[0][45:47] == ['TOTAL', '652'], 'PDF workload table')
    need(lines[636] == 'PRACTICE PROGRESSION, ERROR REPAIR, AND MASTERY' and lines[657] == 'MASTERY GATE', 'TXT guidance bounds')
    need('Three-pass improvisation ladder' in pages[18] and 'Practice log' in pages[19] and 'Session protocol' in pages[0], 'PDF guidance anchors')
    source = {key: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level073.detached-source-candidate.1', 'wbs': '2.3.1.3.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'sounding_midi_events': None, 'source': source, 'source_map_row': mapped, 'source_sections': sections, 'modules': modules, 'guide_tone_worksheets': sheets, 'printed_tones_by_module': counts, 'printed_sounding_tones': 652, 'source_ambiguities': ambiguities, 'source_differences': [{'kind': 'PDF_A_barline_sustain_conflicts_with_three_printed_cells', 'pdf_ref': 'L73-PDF-p4-L4-5', 'txt_refs': [item['txt_ref'] for item in ambiguities], 'pdf_text': pages[3][3:5]}, {'kind': 'PDF_only_modulation_atlas_and_session_test', 'pdf_refs': ['L73-PDF-p1', 'L73-PDF-p2'], 'pdf_text': pages[0] + pages[1]}, {'kind': 'PDF_only_guide_ear_test_and_recovery_ladder', 'pdf_refs': ['L73-PDF-p7', 'L73-PDF-p19'], 'pdf_text': pages[6] + pages[18]}, {'kind': 'PDF_only_completion_log', 'pdf_ref': 'L73-PDF-p20', 'pdf_text': pages[19]}], 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_practice_mastery_next_lines': lines[636:], 'pdf_mastery_page': pages[19]}}


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
