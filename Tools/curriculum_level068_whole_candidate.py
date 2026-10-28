#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level68 source candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.2.1-level068-whole-r01')
STEM = 'Guitar_Exercises_Section_VIII_Level_68_E_Phrygian_Dominant_Diminished_Seventh_Symmetry_Altered_Dominant_Colors_and_Harmonic_Minor_Improvisation_Synthesis'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', 'e270fa9365dfd6e061ce4fd7807df1ba0d82fc52b867dc1b29ec180cb7923f2b', 34071)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', '4db7d55cd64c1b038dfce68dfc3eda60fc82077fcf21532d96ad79457031a378', 53385)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
KEYS = tuple('ABCDEFGHIJK')
CELL_COUNTS = dict(zip(KEYS[:-1], (5, 6, 5, 5, 4, 6, 5, 5, 10, 16)))
CELL_TONES = {'A': 16, 'B': 8, 'C': 10, 'E': 8, 'F': 8, 'G': 16, 'H': 12, 'I': 8, 'J': 4}
EXPECTED = {'A': 80, 'B': 48, 'C': 50, 'D': 64, 'E': 32, 'F': 48, 'G': 80, 'H': 60, 'I': 80, 'J': 64, 'K': 24}
PDF_PAGES = {'A': (3, 4), 'B': (5,), 'C': (6,), 'D': (7, 8), 'E': (9,), 'F': (10,), 'G': (11, 12), 'H': (13, 14), 'I': (15,), 'J': (16, 17)}
PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'G#': 8, 'A': 9, 'B': 11}
DEGREE = {'A': '1', 'B': '2', 'C': 'b3', 'D': '4', 'E': '5', 'F': 'b6', 'G#': '7', 'G': 'b7*'}
E7_ROLE = {'E': 'R', 'F': 'b9', 'G': '#9*', 'G#': '3', 'A': '11', 'B': '5', 'C': 'b13', 'D': 'b7'}
DIM_ROLE = {'G#': '1', 'B': 'b3', 'D': 'b5', 'F': 'bb7'}
OPEN = {'e': 64, 'B': 59, 'G': 55, 'D': 50, 'A': 45, 'E': 40}
STRINGS = ('e', 'B', 'G', 'D', 'A', 'E')
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
    return f'L68-TXT-L{first}' if last is None else f'L68-TXT-L{first}-{last}'


def source_sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-K]) - ', row).group(1), row) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-K]) - ', row)]
    need(len(heads) == 11 and tuple(letter for _, letter, _ in heads) == KEYS, 'module heading order')
    out = {}
    for n, (start, letter, heading) in enumerate(heads):
        stop = heads[n + 1][0] - 1 if n < 10 else next(i for i, row in enumerate(lines) if row == 'PRACTICE PROGRESSION AND MASTERY') - 1
        need(lines[start - 1].startswith('=') and lines[start + 1].startswith('='), f'{letter} frame')
        out[letter] = {'heading': heading, 'start_line': start + 1, 'end_line': stop, 'txt_ref': ref(start + 1, stop), 'raw_lines': lines[start:stop]}
    return out


def parse_cell(lines: list[str], at: int, letter: str, ordinal: int) -> dict[str, Any]:
    rows = lines[at:at + 9]
    need(len(rows) == 9 and rows[0].startswith('Nte|') and rows[1].startswith('Deg|') and rows[2].startswith('Rol|'), f'{letter} rows at {at + 1}')
    need([row[2] for row in rows[3:]] == list(STRINGS) and all(row.startswith('  ' + string + '|') for row, string in zip(rows[3:], STRINGS)), f'{letter} TAB strings at {at + 1}')
    bodies = [row.split('|', 1)[1] for row in rows]
    need(len(set(map(len, bodies))) == 1, f'{letter} aligned width at {at + 1}')
    matches = list(NOTE.finditer(bodies[0]))
    expected = 32 if letter == 'D' and ordinal == 4 else 8 if letter == 'D' else CELL_TONES[letter]
    need(len(matches) == expected, f'{letter} note count at {at + 1}')
    frets = [(m.start(), string, int(m.group())) for string, body in zip(STRINGS, bodies[3:]) for m in re.finditer(r'\d+', body)]
    need(sorted(m.start() for m in matches) == sorted(col for col, _, _ in frets), f'{letter} note/TAB columns at {at + 1}')
    by_col = {col: (string, fret) for col, string, fret in frets}
    events = []
    for n, m in enumerate(matches):
        col = m.start()
        name, (string, fret) = m.group(), by_col[col]
        need(name in PC and (OPEN[string] + fret) % 12 == PC[name], f'{letter} note/TAB pitch at {at + 1}, column {col}')
        need(bodies[1][col:].startswith(DEGREE[name]), f'{letter} harmonic-minor degree at {at + 1}, column {col}')
        end = matches[n + 1].start() if n + 1 < len(matches) else len(bodies[0])
        events.append({'note': name, 'string': string, 'fret': fret, 'pitch_class': PC[name], 'degree': DEGREE[name], 'degree_slot_raw': bodies[1][col:end], 'role_slot_raw': bodies[2][col:end], 'source_column': col, 'source_bar_ordinal': bodies[0][:col].count('|') + 1})
    heading = lines[at - 1]
    out = {'ordinal': ordinal + 1, 'heading_raw': heading, 'note_names': [e['note'] for e in events], 'degree_row_raw': rows[1], 'role_row_raw': rows[2], 'tab_rows': rows[3:], 'events': events, 'printed_tones': len(events), 'txt_ref': ref(at + 1, at + 9), 'raw_lines': rows}
    return out


def check_music(modules: dict[str, list[dict[str, Any]]]) -> None:
    mode = ['E', 'F', 'G#', 'A', 'B', 'C', 'D', 'E']
    for cell in modules['A']:
        need(cell['note_names'] == mode + list(reversed(mode)), 'A mode mirror')
        need([e['role_slot_raw'].strip('-') for e in cell['events']] == [E7_ROLE[n] for n in cell['note_names']], 'A E7 roles')
    pairs = [('F', 'E'), ('G', 'G#'), ('A', 'G#'), ('C', 'B')]
    for cell in modules['B']:
        need(list(zip(cell['note_names'][::2], cell['note_names'][1::2])) == pairs, 'B tension/target pairs')
        need([e['role_slot_raw'].strip('-') for e in cell['events']] == [E7_ROLE[n] for n in cell['note_names']], 'B E7 roles')
    c = ['E', 'G#', 'B', 'D', 'F', 'F', 'D', 'B', 'G#', 'E']
    for cell in modules['C']:
        need(cell['note_names'] == c, 'C E7b9 mirror')
        need([e['role_slot_raw'].strip('-') for e in cell['events']] == [E7_ROLE[n] for n in c], 'C E7b9 roles')
        cell['second_pass_event_ordinals'] = list(range(2, 6)) + list(range(6, 10))
    d = modules['D']
    need(all(set(cell['note_names']) == set(DIM_ROLE) for cell in d), 'D diminished collection')
    for cell in d[:4]:
        need(cell['note_names'][4:] == list(reversed(cell['note_names'][:4])), 'D shape mirror')
        need([e['role_slot_raw'].strip('-') for e in cell['events']] == [DIM_ROLE[n] for n in cell['note_names']], 'D diminished roles')
    need(d[4]['note_names'][:16] == [n for cell in d[:4] for n in cell['note_names'][:4]], 'D cycle ascent')
    need(d[4]['note_names'][16:] == list(reversed(d[4]['note_names'][:16])), 'D cycle reverse')
    for cell, shape in zip(modules['E'], d[:4]):
        need(cell['note_names'][:4] == shape['note_names'][:4] and set(cell['note_names'][4:]) == {'A', 'C', 'E'}, 'E diminished to A minor')
    f = modules['F']
    need([cell['note_names'][0] for cell in f] == ['E'] * 6 and [cell['note_names'][-1] for cell in f] == ['B', 'E', 'E', 'E', 'E', 'E'], 'F dominant phrase endpoints')
    need(['G' in cell['note_names'] for cell in f] == [False, False, False, False, True, True], 'F borrowed G boundary')
    for cell in modules['G']:
        need(cell['note_names'] == ['A', 'C', 'E', 'A', 'D', 'F', 'A', 'C', 'E', 'F', 'D', 'G#', 'A', 'C', 'E', 'A'], 'G i-iv-V7-i phrase')
        need([e['source_bar_ordinal'] for e in cell['events']] == [n for n in range(1, 5) for _ in range(4)], 'G four printed bars')
    for cell in modules['H']:
        need(cell['note_names'] == ['B', 'D', 'F', 'A', 'F', 'D', 'B', 'G#', 'A', 'C', 'E', 'A'], 'H iiø-V7-i phrase')
        need([e['source_bar_ordinal'] for e in cell['events']] == [n for n in range(1, 4) for _ in range(4)], 'H three printed bars')
    for pair in range(5):
        call, answer = modules['I'][2 * pair:2 * pair + 2]
        need(call['heading_raw'] == f'P{pair + 1} CALL' and answer['heading_raw'] == f'P{pair + 1} ANSWER', 'I call/answer headings')
        need(call['note_names'] == ['A', 'C', 'E', 'F', 'E', 'D', 'C', 'A'] and answer['note_names'] == ['E', 'F', 'G#', 'B', 'D', 'C', 'B', 'A'], 'I call/answer notes')
    for n, cell in enumerate(modules['J'], 1):
        need(cell['heading_raw'].startswith(f'BAR {n}: '), 'J bar order')
        cell['bar_number'] = n
    need(modules['J'][13]['heading_raw'] == 'BAR 14: E7#9b13 - P5' and modules['J'][13]['note_names'] == ['E', 'G', 'C', 'G#'], 'J bar-14 borrowed G and dominant third')


def pdf_correspondence(modules: dict[str, list[dict[str, Any]]], pages: list[list[str]]) -> None:
    for letter, page_numbers in PDF_PAGES.items():
        rows = [(p, j + 1, line) for p in page_numbers for j, line in enumerate(pages[p - 1]) if line.startswith('Nte|')]
        cells = modules[letter]
        need(len(rows) == (5 if letter == 'I' else len(cells)), f'{letter} PDF note-row count')
        for n, (p, line, raw) in enumerate(rows):
            names = [m.group() for m in NOTE.finditer(raw.split('|', 1)[1])]
            expected = cells[2 * n]['note_names'] + cells[2 * n + 1]['note_names'] if letter == 'I' else cells[n]['note_names']
            need(names == expected, f'{letter} PDF/TXT notes at p{p}:L{line}')
            for cell in (cells[2 * n:2 * n + 2] if letter == 'I' else [cells[n]]):
                cell['pdf_ref'] = f'L68-PDF-p{p}-L{line}'
                cell['pdf_note_row_raw'] = raw


def recovery_cards(lines: list[str], section: dict[str, Any], page: list[str]) -> list[dict[str, Any]]:
    start = section['start_line']
    stop = section['end_line']
    out = []
    for i in range(start, stop):
        row = lines[i]
        m = re.fullmatch(r'([^:]+): ([A-G](?:#|b)?) -> ([A-G](?:#|b)?)   ([#bR0-9*]+) -> ([A-Za-z0-9 ]+)', row)
        if m:
            chord, weak, target, weak_role, target_role = m.groups()
            need(weak in PC and target in PC and f'{chord}: {weak} -> {target}' in page, f'K PDF recovery {i + 1}')
            need(f'{weak_role} -> {target_role}' in page, f'K PDF recovery roles {i + 1}')
            out.append({'chord': chord, 'weak_note': weak, 'target_note': target, 'weak_role': weak_role, 'target_role': target_role, 'printed_tones': 2, 'txt_ref': ref(i + 1), 'pdf_ref': 'L68-PDF-p19', 'raw': row})
    need(len(out) == 12, 'K twelve recovery pairs')
    return out


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 871 and len(pages) == 20, 'TXT/PDF extent')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION VIII, LEVEL 68', 'E PHRYGIAN DOMINANT, DIMINISHED-SEVENTH SYMMETRY, ALTERED DOMINANT COLORS, AND HARMONIC-MINOR IMPROVISATION SYNTHESIS'], 'TXT title')
    need(all(page[0] == 'Guitar Exercises - Section VIII, Level 68' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need(lines[23] == 'COMPLETE WRITTEN WORKOUT: 630 sounding tones.' and pages[0][2] == 'A HARMONIC MINOR  |  11 MODULES  |  630 TONES', 'workout declaration')
    mapped = next((r for r in source_map['rows'] if r.get('level') == 68), None)
    need(mapped is not None and mapped['section'] == 'VIII' and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.2.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map status')
    need(all(mapped[f'{key}_path'] == spec[0] and mapped[f'{key}_sha256'] == spec[1] and mapped[f'{key}_bytes'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair identity')
    sections = source_sections(lines)
    modules: dict[str, list[dict[str, Any]]] = {}
    for letter in KEYS[:-1]:
        first, last = sections[letter]['start_line'], sections[letter]['end_line']
        positions = [i for i in range(first, last) if lines[i].startswith('Nte|')]
        need(len(positions) == CELL_COUNTS[letter], f'{letter} cell count')
        modules[letter] = [parse_cell(lines, i, letter, n) for n, i in enumerate(positions)]
    check_music(modules)
    pdf_correspondence(modules, pages)
    recovery = recovery_cards(lines, sections['K'], pages[18])
    need(sum(len(v) for v in modules.values()) == 67, 'all 67 note/TAB cells')
    counts = {letter: sum(cell['printed_tones'] for cell in modules[letter]) for letter in KEYS[:-1]}
    counts['K'] = sum(card['printed_tones'] for card in recovery)
    need(counts == EXPECTED and sum(counts.values()) == 630, '630-tone module reconciliation')
    need([int(pages[0][i]) for i in range(30, 52, 2)] == list(EXPECTED.values()) and pages[0][51:53] == ['TOTAL', '630'], 'PDF workload table')
    need(lines[838] == 'PRACTICE PROGRESSION AND MASTERY' and lines[859] == 'MASTERY GATE', 'TXT guidance bounds')
    need('Practice log' in pages[19] and 'Recording rubric - 0, 1, or 2' in pages[17] and 'Ear tests' in pages[18], 'PDF guidance anchors')
    need(modules['F'][0]['note_names'][-1] == 'B' and pages[9][6] == 'B-string dominant phrase; resolve the final E clearly.', 'F1 PDF/TXT endpoint conflict')
    capstone = [row for row in sections['K']['raw_lines'] if row and not row.startswith('=')]
    form = [row for row in capstone if row.startswith('Bars ')]
    passes = [row for row in capstone if row.startswith('PASS ')]
    need(len(form) == 4 and [row.split(':', 1)[0] for row in form] == ['Bars 1-4', 'Bars 5-8', 'Bars 9-12', 'Bars 13-16'], 'K four form groups')
    need(len(passes) == 3 and [row.split(':', 1)[0] for row in passes] == ['PASS 1', 'PASS 2', 'PASS 3'] and 'Require one full-beat rest every four bars and a tonic close in bar 16.' in capstone, 'K pass/rest requirements')
    need(all(row.split(':', 1)[1].strip() in pages[17] for row in form), 'K PDF/TXT capstone progression')
    source = {key: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level068.detached-source-candidate.1', 'wbs': '2.3.1.2.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'sounding_midi_events': None, 'source': source, 'source_map_row': mapped, 'source_sections': sections, 'modules': modules, 'recovery_cards': recovery, 'capstone': {'four_bar_groups_raw': form, 'pass_constraints_raw': passes, 'rest_and_close_raw': 'Require one full-beat rest every four bars and a tonic close in bar 16.', 'pdf_rubric_page_ref': 'L68-PDF-p18'}, 'capstone_lines': capstone, 'printed_tones_by_module': counts, 'printed_sounding_tones': 630, 'source_ambiguities': [{'kind': 'F1_PDF_final_E_instruction_conflicts_with_printed_final_B', 'status': 'pending_curriculum_review', 'txt_ref': modules['F'][0]['txt_ref'], 'pdf_ref': 'L68-PDF-p10-L7', 'printed_final_note': 'B', 'pdf_instruction': pages[9][6], 'detail': 'F1 Nte/TAB ends on B, the E7 fifth; PDF says to resolve the final E. No E landing is printed in F1.'}], 'source_differences': [{'kind': 'PDF_I_combines_call_answer_note_rows', 'pdf_ref': 'L68-PDF-p15', 'txt_ref': sections['I']['txt_ref'], 'pdf_text': pages[14]}, {'kind': 'PDF_K_adds_capstone_rubric_and_phrase_constraints', 'pdf_ref': 'L68-PDF-p18', 'txt_ref': sections['K']['txt_ref'], 'pdf_text': pages[17]}, {'kind': 'PDF_only_recovery_ear_tests_and_practice_log', 'pdf_refs': ['L68-PDF-p19', 'L68-PDF-p20'], 'pdf_text': pages[18] + pages[19]}], 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_practice_mastery_next_lines': lines[838:], 'pdf_capstone_page': pages[17], 'pdf_mastery_page': pages[19]}}


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
