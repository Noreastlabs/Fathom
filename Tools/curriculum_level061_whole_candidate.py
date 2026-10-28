#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level61 note/TAB source candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.2.1-level061-whole-r01')
STEM = 'Guitar_Exercises_Section_VII_Level_61_Chord_Tone_Soloing_Chromatic_Approaches_Enclosures_Delayed_Resolutions_and_Progression_Specific_Phrase_Construction'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', '5f0b335578a2dea138122faa6d2c4b49dd37b22a340fb828bae3bfc07f7282aa', 45153)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', 'c99cb38a504977808f56f8998136d8ac0243e12f3770231ffa296d48cd77e619', 57226)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'E#': 5, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11, 'B#': 0}
OPEN = {'e': 64, 'B': 59, 'G': 55, 'D': 50, 'A': 45, 'E': 40}
STRINGS = ('e', 'B', 'G', 'D', 'A', 'E')
NOTE = re.compile(r'[A-G](?:#|b)?(?=-)')
SECTION_KEYS = ('A', 'B_chromatic', 'B_diatonic', 'C', 'D', 'E', 'F', 'G', 'H', 'I_major', 'I_minor', 'J_major', 'J_minor')
CELL_COUNTS = {'A': 16, 'B_chromatic': 12, 'B_diatonic': 12, 'C': 16, 'D': 12, 'E': 6, 'F': 6, 'G': 5, 'H': 6, 'I_major': 3, 'I_minor': 3, 'J_major': 4, 'J_minor': 4}
TONES_PER_CELL = {'A': 4, 'B_chromatic': 5, 'B_diatonic': 5, 'C': 4, 'D': 4, 'E': 12, 'F': 12, 'G': 16, 'H': 8, 'I_major': 16, 'I_minor': 16, 'J_major': 16, 'J_minor': 16}
PDF_START = {'A': (3, 8), 'B_chromatic': (5, 12), 'B_diatonic': (6, 12), 'C': (7, 8), 'D': (9, 12), 'E': (10, 3), 'F': (12, 3), 'G': (14, 2), 'H': (16, 6), 'I_major': (17, 3), 'I_minor': (18, 3), 'J_major': (19, 4), 'J_minor': (19, 4)}
EXPECTED_WORKLOAD = {'A': 64, 'B': 120, 'C': 64, 'D': 48, 'E': 72, 'F': 72, 'G': 80, 'H': 72, 'I': 96, 'J': 128}
TARGETS = {'Cmaj7': {'R': 'C', '3': 'E', '5': 'G', '7': 'B'}, 'G7': {'R': 'G', '3': 'B', '5': 'D', 'b7': 'F'}, 'Dm7': {'R': 'D', 'b3': 'F', '5': 'A', 'b7': 'C'}, 'Bm7b5': {'R': 'B', 'b3': 'D', 'b5': 'F', 'b7': 'A'}}
DIATONIC_C = ('C', 'D', 'E', 'F', 'G', 'A', 'B')


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
    return f'L61-TXT-L{start}' if end is None else f'L61-TXT-L{start}-{end}'


def source_sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-J]) - ', row).group(1), row) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-J]) - ', row)]
    need(len(heads) == len(SECTION_KEYS) and [key for _, key, _ in heads] == ['A', 'B', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'I', 'J', 'J'], 'source section occurrence/order')
    out = {}
    for n, (i, letter, heading) in enumerate(heads):
        next_i = heads[n + 1][0] if n < len(heads) - 1 else next(j for j, row in enumerate(lines) if row == 'PRACTICE PROGRESSION AND MASTERY')
        stop = next_i - 1
        need(lines[i - 1].startswith('=') and lines[i + 1].startswith('='), f'{SECTION_KEYS[n]} framing')
        out[SECTION_KEYS[n]] = {'module_letter': letter, 'heading': heading, 'start_line': i + 1, 'end_line': stop, 'txt_ref': ref(i + 1, stop), 'raw_lines': lines[i:stop], 'content_start': i + 2, 'content_stop': stop}
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


def page_for(key: str, index: int) -> int:
    first, before_second = PDF_START[key]
    return first + int(index >= before_second)


def note_names(row: str) -> list[str]:
    need(row.startswith('Nte|'), 'Nte row')
    body = row.split('|', 1)[1]
    return [m.group() for m in NOTE.finditer(body)]


def parse_cell(start: int, block: list[str], key: str, index: int, page: list[str]) -> dict[str, Any]:
    nte_index = next((j for j, row in enumerate(block) if row.startswith('Nte|')), None)
    need(nte_index is not None and len(block) - nte_index == 9 and nte_index in (1, 2), f'{key} cell shape at {start + 1}')
    nte, rol, tag = block[nte_index:nte_index + 3]
    need(rol.startswith('Rol|') and tag.startswith('Tag|'), f'{key} role/tag rows at {start + 1}')
    tab = block[nte_index + 3:nte_index + 9]
    need([row[2] for row in tab] == list(STRINGS) and all(row.startswith('  ' + string + '|') for row, string in zip(tab, STRINGS)), f'{key} six TAB strings at {start + 1}')
    bodies = [row.split('|', 1)[1] for row in (nte, rol, tag, *tab)]
    need(len(set(map(len, bodies))) == 1, f'{key} aligned row width at {start + 1}')
    note_matches = list(NOTE.finditer(bodies[0]))
    need(len(note_matches) == TONES_PER_CELL[key], f'{key} note count at {start + 1}')
    fret_matches = [(m.start(), string, int(m.group())) for string, body in zip(STRINGS, bodies[3:]) for m in re.finditer(r'\d+', body)]
    need(sorted(m.start() for m in note_matches) == sorted(col for col, _, _ in fret_matches), f'{key} note/TAB columns at {start + 1}')
    by_col = {col: (string, fret) for col, string, fret in fret_matches}
    events = []
    for n, m in enumerate(note_matches):
        col = m.start()
        string, fret = by_col[col]
        name = m.group()
        need(name in PC and (OPEN[string] + fret) % 12 == PC[name], f'{key} note/TAB pitch at {start + 1} column {col}')
        next_col = note_matches[n + 1].start() if n + 1 < len(note_matches) else len(bodies[0])
        events.append({'note': name, 'string': string, 'fret': fret, 'pitch_class': PC[name], 'source_column': col, 'role_slot_raw': bodies[1][col:next_col], 'tag_slot_raw': bodies[2][col:next_col]})
    names = [event['note'] for event in events]
    pdf_page = page_for(key, index)
    if not key.startswith('J_'):
        pdf_notes = [note_names(row) for row in page if row.startswith('Nte|')]
        need(names in pdf_notes, f'{key} PDF p{pdf_page} note row {start + 1}')
    else:
        need('-'.join(names) in page, f'{key} PDF p19 capstone phrase {start + 1}')
    return {'headers_raw': block[:nte_index], 'note_names': names, 'role_row_raw': rol, 'tag_row_raw': tag, 'tab_rows': tab, 'events': events, 'printed_tones': len(events), 'raw_lines': block, 'txt_ref': ref(start + 1, start + len(block)), 'pdf_page': pdf_page}


def parse_recovery(start: int, block: list[str], pdf_page: list[str]) -> list[dict[str, Any]]:
    need(len(block) == 13 and block[0] == 'RECOVERY CARDS', 'H recovery card block')
    out = []
    for n, row in enumerate(block[1:], 1):
        m = re.fullmatch(r'([^:]+): ([A-G](?:#|b)?) -> ([A-G](?:#|b)?) \| ([#bR0-9]+) -> ([#bR0-9]+)', row)
        need(m is not None and m.group(2) in PC and m.group(3) in PC, f'H recovery card {n}')
        chord, weak, target, weak_role, target_role = m.groups()
        need(chord in pdf_page and weak in pdf_page and target in pdf_page and f'{weak_role} -> {target_role}' in pdf_page, f'H recovery PDF card {n}')
        out.append({'chord': chord, 'weak_note': weak, 'target_note': target, 'weak_role': weak_role, 'target_role': target_role, 'printed_tones': 2, 'raw': row, 'txt_ref': ref(start + n + 1), 'pdf_page': 16})
    return out


def check_target_semantics(modules: dict[str, Any]) -> None:
    current_chord: str | None = None
    for cell in modules['A']:
        for header in cell['headers_raw']:
            if header in TARGETS:
                current_chord = header
        need(current_chord is not None and cell['headers_raw'][-1].startswith('Target '), 'A target/chord heading')
        role = cell['headers_raw'][-1].split(' ', 1)[1]
        need(role in TARGETS[current_chord] and cell['note_names'][-1] == TARGETS[current_chord][role], 'A final target role')
        need(set(cell['note_names']) == set(TARGETS[current_chord].values()), 'A four chord tones')
        cell['chord'] = current_chord
        cell['final_target_role'] = role
    for key in ('B_chromatic', 'B_diatonic'):
        for cell in modules[key]:
            m = re.fullmatch(r'([^ ]+) -> (R|3|7|b3|b7|b5)', cell['headers_raw'][0])
            need(m is not None and m.group(1) in TARGETS and m.group(2) in TARGETS[m.group(1)], f'{key} target heading')
            chord, role = m.groups()
            notes = cell['note_names']
            need(notes[0] == notes[2] == notes[4] == TARGETS[chord][role], f'{key} five-note target')
            if key == 'B_chromatic':
                need((PC[notes[1]] + 1) % 12 == PC[notes[2]] and (PC[notes[3]] - 1) % 12 == PC[notes[2]], 'B chromatic below/above')
            else:
                position = DIATONIC_C.index(notes[2])
                need(notes[1] == DIATONIC_C[(position - 1) % 7] and notes[3] == DIATONIC_C[(position + 1) % 7], 'B diatonic below/above')
            cell['chord'] = chord
            cell['target_role'] = role
    for cell in modules['C']:
        m = re.fullmatch(r'([^ ]+) (R|3|7|b3|b7|b5) - (above-below|below-above)', cell['headers_raw'][0])
        need(m is not None and m.group(1) in TARGETS, 'C enclosure heading')
        chord, role, direction = m.groups()
        notes = cell['note_names']
        need(notes[2] == notes[3] == TARGETS[chord][role], 'C repeated destination')
        above, below = (notes[0], notes[1]) if direction == 'above-below' else (notes[1], notes[0])
        need((PC[above] - 1) % 12 == PC[notes[2]] and (PC[below] + 1) % 12 == PC[notes[2]], 'C chromatic enclosure sides')
        cell['chord'] = chord
        cell['target_role'] = role
        cell['enclosure_direction'] = direction
    for cell in modules['D']:
        m = re.fullmatch(r'([^:]+): ([^ ]+) -> (R|3|7|b3|b7|b5)', cell['headers_raw'][0])
        need(m is not None and m.group(1) in TARGETS and cell['headers_raw'][1] == 'Count: 1  &  2  3', 'D delayed heading/count')
        chord, _, role = m.groups()
        need(cell['note_names'][1] == TARGETS[chord][role], 'D delayed target on second note')
        cell['chord'] = chord
        cell['resolution_target_role'] = role


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 1295 and len(pages) == 20, 'TXT/PDF extent')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION VII, LEVEL 61', 'CHORD-TONE SOLOING, CHROMATIC APPROACHES, ENCLOSURES, DELAYED RESOLUTIONS, AND PROGRESSION-SPECIFIC PHRASE CONSTRUCTION'], 'TXT title')
    need(all(page[0] == 'Guitar Exercises - Section VII, Level 61' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need(pages[0][2] == '10 MODULES  |  816 TONES' and lines[24] == 'COMPLETE WRITTEN WORKOUT: 816 sounding tones.', 'workout declaration')
    rows = source_map.get('rows')
    need(isinstance(rows, list), 'source-map rows')
    mapped = next((row for row in rows if row.get('level') == 61), None)
    need(mapped is not None and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.2.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map status')
    need(mapped['txt_path'] == TXT[0] and mapped['txt_sha256'] == TXT[1] and mapped['txt_bytes'] == TXT[2] and mapped['pdf_path'] == PDF[0] and mapped['pdf_sha256'] == PDF[1] and mapped['pdf_bytes'] == PDF[2], 'source-map identity')
    sections = source_sections(lines)
    modules: dict[str, Any] = {}
    recovery: list[dict[str, Any]] = []
    for key in SECTION_KEYS:
        group = blocks(lines, sections[key])
        if key == 'H':
            need(len(group) == 7, 'H motif/recovery block count')
            start, block = group[-1]
            recovery = parse_recovery(start, block, pages[15])
            group = group[:-1]
        need(len(group) == CELL_COUNTS[key], f'{key} cell count')
        items = []
        for n, (start, block) in enumerate(group):
            page_number = page_for(key, n)
            items.append(parse_cell(start, block, key, n, pages[page_number - 1]))
        modules[key] = items
    modules['H_recovery_cards'] = recovery
    check_target_semantics(modules)
    need(len(recovery) == 12 and len([row for row in lines if row.startswith('Nte|')]) == 105, 'all note rows and recovery cards')
    computed = {'A': sum(c['printed_tones'] for c in modules['A']), 'B': sum(c['printed_tones'] for k in ('B_chromatic', 'B_diatonic') for c in modules[k]), 'C': sum(c['printed_tones'] for c in modules['C']), 'D': sum(c['printed_tones'] for c in modules['D']), 'E': sum(c['printed_tones'] for c in modules['E']), 'F': sum(c['printed_tones'] for c in modules['F']), 'G': sum(c['printed_tones'] for c in modules['G']), 'H': sum(c['printed_tones'] for c in modules['H']) + sum(c['printed_tones'] for c in recovery), 'I': sum(c['printed_tones'] for k in ('I_major', 'I_minor') for c in modules[k]), 'J': sum(c['printed_tones'] for k in ('J_major', 'J_minor') for c in modules[k])}
    need(computed == EXPECTED_WORKLOAD and sum(computed.values()) == 816, 'module count reconciliation')
    need([int(pages[0][i]) for i in range(29, 48, 2)] == list(EXPECTED_WORKLOAD.values()) and pages[0][48:50] == ['TOTAL', '816'], 'PDF workload table')
    need(len([row for row in pages[18] if row.startswith('Nte|')]) == 0 and 'The complete tablature appears in the text workbook.' in pages[18][4], 'J PDF/TXT representation')
    need(lines[1264] == 'PRACTICE PROGRESSION AND MASTERY' and lines[1285] == 'MASTERY GATE' and lines[1293] == 'NEXT LEVEL', 'guidance boundaries')
    need('Practice log' in pages[19] and 'Target hierarchy' in pages[1], 'PDF additional guidance')
    h1, h2 = modules['H'][0], modules['H'][1]
    need(h1['note_names'] == h2['note_names'] and h1['tab_rows'] == h2['tab_rows'] and h1['headers_raw'] != h2['headers_raw'], 'H1/H2 displacement source ambiguity')
    for major_minor in ('major', 'minor'):
        for k in range(3):
            need(modules[f'I_{major_minor}'][k]['note_names'] == modules[f'J_{major_minor}'][k]['note_names'], f'I/J {major_minor} phrase carryover {k + 1}')
    source = {name: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for name, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level061.detached-source-candidate.1', 'wbs': '2.3.1.2.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'sounding_midi_events': None, 'source': source, 'source_map_row': mapped, 'source_sections': sections, 'modules': modules, 'printed_tones_by_module': computed, 'printed_sounding_tones': 816, 'source_ambiguities': [{'kind': 'H2_rhythmic_displacement_without_printed_timing_difference', 'txt_refs': [h1['txt_ref'], h2['txt_ref']], 'detail': 'H1 and H2 have identical note names and TAB; H2 heading says rhythmic displacement, but the TXT grids do not assign different onsets.', 'status': 'pending_curriculum_review'}], 'source_differences': [{'kind': 'J_PDF_table_omits_TAB_retained_in_TXT', 'pdf_ref': 'L61-PDF-p19-L5-40', 'pdf_text': pages[18][4:40], 'txt_refs': [sections['J_major']['txt_ref'], sections['J_minor']['txt_ref']]}, {'kind': 'PDF_only_target_hierarchy_and_delayed_grid', 'pdf_ref': 'L61-PDF-p2-L5-41', 'pdf_text': pages[1][4:41]}, {'kind': 'PDF_only_session_protocol_and_asterisk_rule', 'pdf_ref': 'L61-PDF-p1-L51-55', 'pdf_text': pages[0][50:55]}, {'kind': 'PDF_only_practice_log', 'pdf_ref': 'L61-PDF-p20-L36-46', 'pdf_text': pages[19][35:46]}], 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_practice_mastery_next_lines': lines[1264:], 'pdf_practice_mastery_page': pages[19]}}


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
