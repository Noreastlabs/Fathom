#!/usr/bin/env python3
"""Project the pinned whole Level 50 workbook as a detached review candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.2.1-level050-whole-r01')
STEM = 'Guitar_Exercises_Section_VI_Level_50_Chord_Transitions_Common_Finger_and_Guide_Finger_Movement_Anticipated_Changes_and_Uninterrupted_Progressions'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', 'c2a1e88fdc69545f17f7439b109fdad6a4b652285704ea730d0b8dae89a4306e', 23789)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', 'eec11800419be73416833d09a0bd46b42785cc050afc716b44d3b0129d0e2afc', 50728)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
OPEN = (40, 45, 50, 55, 59, 64)  # low E through high e
SPELLING = {'Em': ('E', 'G', 'B'), 'E': ('E', 'G#', 'B'), 'Am': ('A', 'C', 'E'), 'A': ('A', 'C#', 'E'), 'Dm': ('D', 'F', 'A'), 'D': ('D', 'F#', 'A'), 'C': ('C', 'E', 'G'), 'G': ('G', 'B', 'D')}
PC = {'C': 0, 'C#': 1, 'D': 2, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'B': 11}
PAGES = {'A': [3], 'B': [4, 5], 'C': [6], 'D': [7], 'E': [8, 9], 'F': [10, 11], 'G': [12, 13], 'H': [14], 'I': [15, 16], 'J': [17, 18]}
COUNTS = {'A': 80, 'B': 64, 'C': 48, 'D': 64, 'E': 80, 'F': 96, 'G': 96, 'H': 64, 'I': 128, 'J': 128}
ITEM_COUNTS = {'A': 10, 'B': 8, 'C': 6, 'D': 8, 'E': 8, 'F': 6, 'G': 6, 'H': 4, 'I': 4, 'J': 2}
ATTACKS_PER_ITEM = {'B': 8, 'C': 8, 'D': 8, 'E': 10, 'F': 16, 'G': 16, 'H': 16, 'I': 32, 'J': 64}
CHORD_RE = re.compile(r'Em|Am|Dm|MUTE|[EADCG](?=-)')


class SourceError(ValueError):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise SourceError(message)


def pinned(root: Path, spec: tuple[str, str, int]) -> bytes:
    rel, digest, size = spec
    path = root / rel
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise SourceError(f'missing pinned source: {rel}') from exc
    need(not path.is_symlink() and resolved.is_relative_to(root) and resolved.is_file(), f'unsafe source: {rel}')
    raw = path.read_bytes()
    need(len(raw) == size and hashlib.sha256(raw).hexdigest() == digest, f'pin drift: {rel}')
    return raw


def ref(start: int, end: int | None = None) -> str:
    return f'L50-TXT-L{start}' if end is None else f'L50-TXT-L{start}-{end}'


def grid_tokens(row: str, prefix: str) -> list[str]:
    need(row.startswith(prefix + '|') and row.endswith('|'), f'{prefix} grid shape')
    body = row.split('|', 1)[1]
    if prefix == 'Chd':
        tokens = CHORD_RE.findall(body)
    elif prefix in ('Str', 'Atk'):
        tokens = re.findall(r'[DUxB](?=-)', body)
    elif prefix == 'Hnd':
        tokens = re.findall(r'[PR](?=-)', body)
    else:
        raise SourceError(f'unsupported grid: {prefix}')
    need(tokens, f'empty {prefix} grid')
    return tokens


def sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-J]) - ', row).group(1)) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-J]) - ', row)]
    need([key for _, key in heads] == list('ABCDEFGHIJ'), 'module order/coverage')
    result = {}
    for n, (start, key) in enumerate(heads):
        stop = heads[n + 1][0] - 1 if n < 9 else next(i for i, row in enumerate(lines) if row == 'PRACTICE PROGRESSION AND ERROR REPAIR') - 1
        need(lines[start - 1].startswith('=') and lines[start + 1].startswith('='), f'module {key} framing')
        result[key] = {'heading': lines[start], 'start_line': start + 1, 'end_line': stop, 'txt_ref': ref(start + 1, stop), 'pdf_pages': PAGES[key], 'raw_lines': lines[start:stop], 'content_start': start + 2, 'content_stop': stop}
    return result


def blocks(lines: list[str], section: dict[str, Any]) -> list[tuple[int, list[str]]]:
    out: list[tuple[int, list[str]]] = []
    start: int | None = None
    for i in range(section['content_start'], section['content_stop']):
        row = lines[i]
        if row and not row.startswith('='):
            if start is None:
                start = i
        elif start is not None:
            out.append((start, lines[start:i]))
            start = None
    if start is not None:
        out.append((start, lines[start:section['content_stop']]))
    return out


def chord_reference(lines: list[str]) -> dict[str, Any]:
    standard = {}
    for n, name in enumerate(SPELLING):
        i = 12 + n
        m = re.fullmatch(r'([A-Za-z]+): frets ([0-9x ]+) \| fingers ([0-9Ox ]+) \| spelling ([A-G# ]+) \| attack (.+)', lines[i])
        need(m is not None and m.group(1) == name, f'chord {name} reference')
        frets, fingers = m.group(2).split(), m.group(3).split()
        need(len(frets) == len(fingers) == 6, f'{name} six strings')
        for fret, finger in zip(frets, fingers):
            need((fret == 'x' and finger == 'x') or (fret == '0' and finger == 'O') or (fret not in ('x', '0') and finger in ('1', '2', '3', '4')), f'{name} fret/finger coherence')
        pitches = {(base + int(fret)) % 12 for base, fret in zip(OPEN, frets) if fret != 'x'}
        need(pitches == {PC[p] for p in SPELLING[name]} and tuple(m.group(4).split()) == SPELLING[name], f'{name} pitch-class triad')
        expected_zone = 'all 6 strings' if name in ('Em', 'E', 'G') else 'D string through high e' if name in ('Dm', 'D') else 'A string through high e'
        need(m.group(5) == expected_zone, f'{name} attack zone')
        standard[name] = {'frets_low_to_high': frets, 'fingers_low_to_high': fingers, 'spelling': list(SPELLING[name]), 'attack_zone': m.group(5), 'txt_ref': ref(i + 1), 'raw': lines[i]}
    alternate = {}
    for i, name, base in ((22, 'Em-alt', 'Em'), (23, 'E-alt', 'E')):
        m = re.fullmatch(r'([A-Za-z-]+): frets ([0-9x ]+) \| fingers ([0-9Ox ]+) \| (.+)', lines[i])
        need(m is not None and m.group(1) == name, f'{name} alternate')
        frets, fingers = m.group(2).split(), m.group(3).split()
        need(frets == standard[base]['frets_low_to_high'] and len(fingers) == 6 and fingers != standard[base]['fingers_low_to_high'], f'{name} voicing/fingering')
        alternate[name] = {'voicing_symbol': base, 'frets_low_to_high': frets, 'fingers_low_to_high': fingers, 'usage': m.group(4), 'txt_ref': ref(i + 1), 'raw': lines[i]}
    return {'standard': standard, 'alternate': alternate}


def grid_item(start: int, block: list[str], key: str, expected: int) -> dict[str, Any]:
    grids = {prefix: row for row in block for prefix in ('Cnt', 'Chd', 'Str', 'Atk', 'Hnd', 'Bar') if row.startswith(prefix + '|')}
    chords = grid_tokens(grids['Chd'], 'Chd')
    attack_prefix = 'Atk' if key == 'D' else 'Str'
    attacks = grid_tokens(grids[attack_prefix], attack_prefix)
    need(len(chords) == len(attacks) == expected, f'{key} grid attack count at line {start + 1}')
    need(all(c in SPELLING or c == 'MUTE' for c in chords), f'{key} chord vocabulary')
    item = {'title': block[0], 'raw_lines': block, 'txt_ref': ref(start + 1, start + len(block)), 'grids': grids, 'chord_symbols': chords, 'attack_symbols': attacks, 'printed_attacks': expected}
    if key == 'D':
        hand = grid_tokens(grids['Hnd'], 'Hnd')
        need(chords[3::4] == ['MUTE', 'MUTE'] and attacks == ['D', 'D', 'D', 'x'] * 2 and hand == ['P', 'P', 'P', 'R'] * 2, 'D release/mute semantics')
        item['hand_states'] = hand
        item['pitched_attacks'] = 6
        item['muted_attacks'] = 2
        item['attack_zone_raw'] = block[-1]
    elif key == 'E':
        need(attacks == ['D'] * 4 + ['U'] + ['D'] * 4 + ['U'], 'E anticipation attacks')
        need(block[-1] == 'Pass 2: let the anticipated chord ring through beat 1 and resume on beat 2.', 'E pass 2')
        item['anticipated_positions_one_based'] = [5, 10]
        item['pass_2_raw'] = block[-1]
    elif key == 'F':
        need(attacks == ['D', 'U'] * 8 and block[-1] == 'One two-bar burst, full relaxation, then repeat.', 'F eighth/repeat')
        item['optional_repeat_raw'] = block[-1]
    elif key == 'G':
        need(attacks == ['D'] * 16 and chords == chords[:4] * 4, 'G repeated four-chord order')
    elif key == 'I':
        need(attacks == ['D'] * 32 and all(chords[j:j + 4] == [chords[j]] * 4 for j in range(0, 32, 4)), 'I quarter/bar sequence')
        need(block[-1] == 'Pass 1 sustained quarters. Pass 2 clip beat 4. Pass 3 anticipate bars 5 and 8.', 'I alternatives')
        item['bar_chords'] = chords[::4]
        item['passes_raw'] = block[-1]
    elif key in ('B', 'C'):
        need(attacks == ['D'] * 8 and chords == chords[:2] * 4, f'{key} alternating pair')
        item['motion_instruction_raw'] = block[1]
    return item


def module_items(lines: list[str], section_map: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    modules: dict[str, list[dict[str, Any]]] = {}
    a = blocks(lines, section_map['A'])
    need(len(a) == 1 and len(a[0][1]) == 12 and a[0][1][0].startswith('Count 1:'), 'A mechanics block')
    need(a[0][1][-1].startswith('Audit:'), 'A no-strum audit')
    modules['A'] = []
    for i, row in enumerate(a[0][1][1:-1], a[0][0] + 1):
        m = re.fullmatch(r'(.+): (.+); 8 silent landings\.', row)
        need(m is not None, 'A transition/landing row')
        modules['A'].append({'transition': m.group(1), 'motion': m.group(2), 'silent_landings': 8, 'raw': row, 'txt_ref': ref(i + 1)})
    for key in 'BCDEFGI':
        group = blocks(lines, section_map[key])
        if key == 'D':
            need(len(group) == 9 and len(group[-1][1]) == 1 and group[-1][1][0].startswith('P = normal pressure.'), 'D legend')
            group = group[:-1]
        need(len(group) == ITEM_COUNTS[key], f'{key} item coverage')
        expected_len = {'B': 5, 'C': 5, 'D': 6, 'E': 5, 'F': 5, 'G': 4, 'I': 7}[key]
        modules[key] = []
        for start, block in group:
            need(len(block) == expected_len, f'{key} block shape at {start + 1}')
            item = grid_item(start, block, key, ATTACKS_PER_ITEM[key])
            if key == 'I':
                item['route_type'] = block[0]
                item['harmonic_description_raw'] = block[1]
            if key == 'G':
                item['harmonic_description_raw'] = block[0]
            modules[key].append(item)
    h = blocks(lines, section_map['H'])
    need(len(h) == 1 and len(h[0][1]) == 6 and h[0][1][0] == 'Progression: | Am | C | G | Em |' and h[0][1][-1] == 'Each complete four-bar pass contains 16 attacks.', 'H progression/count')
    modules['H'] = []
    for n, row in enumerate(h[0][1][1:5], 1):
        m = re.fullmatch(r'(H[1-4]) (.+): Atk\|([DUxB-]+)\|; (.+)', row)
        need(m is not None and m.group(1) == f'H{n}', 'H pattern row')
        attacks = re.findall(r'[DUxB](?=-)', m.group(3))
        need(attacks == [['D'] * 4, ['D'] * 4, ['D', 'x', 'D', 'x'], ['B', 'D', 'B', 'D']][n - 1], 'H distinct pattern')
        modules['H'].append({'name': m.group(1), 'description': m.group(2), 'attack_symbols_per_bar': attacks, 'four_bar_progression': ['Am', 'C', 'G', 'Em'], 'printed_attacks': 16, 'instruction': m.group(4), 'raw': row, 'txt_ref': ref(h[0][0] + n + 1)})
    j = blocks(lines, section_map['J'])
    need(len(j) == 2 and all(len(block) == 15 for _, block in j), 'J capstone blocks')
    modules['J'] = []
    for index, (start, block) in enumerate(j):
        need(block[0] == ('MAJOR CAPSTONE' if index == 0 else 'MINOR CAPSTONE'), 'J capstone order')
        expected_progression = ['G', 'D', 'Em', 'C', 'G', 'D', 'C', 'D', 'Em', 'C', 'G', 'D', 'G', 'C', 'D', 'G'] if index == 0 else ['Am', 'C', 'G', 'Em', 'Am', 'Dm', 'E', 'Am', 'C', 'G', 'Am', 'Em', 'Dm', 'Am', 'E', 'Am']
        need(block[1].startswith('| ') and block[1].endswith(' |'), 'J progression notation')
        bar_symbols = re.findall(r'Em|Am|Dm|[EADCG]', block[1])
        need(bar_symbols == expected_progression, 'J 16-bar progression')
        systems = []
        for s in range(4):
            trio = block[2 + 3 * s:5 + 3 * s]
            need([row[:4] for row in trio] == ['Bar|', 'Cnt|', 'Chd|'], 'J system rows')
            chords = grid_tokens(trio[2], 'Chd')
            need(len(chords) == 16 and chords[::4] == expected_progression[s * 4:s * 4 + 4] and all(chords[k:k + 4] == [chords[k]] * 4 for k in range(0, 16, 4)), 'J system chord sequence')
            systems.append({'bars': [s * 4 + n for n in range(1, 5)], 'raw_rows': trio, 'chord_symbols': chords, 'printed_attacks': 16, 'txt_ref': ref(start + 3 + 3 * s, start + 5 + 3 * s)})
        modules['J'].append({'name': block[0], 'bar_chords': expected_progression, 'systems': systems, 'performance_alternatives_raw': block[-1], 'printed_attacks': 64, 'raw_lines': block, 'txt_ref': ref(start + 1, start + len(block))})
    return modules


def check_pdf_grids(modules: dict[str, list[dict[str, Any]]], pages: list[list[str]]) -> None:
    """Bind every TXT grid to the counterpart PDF page, not only the source hash."""
    page_for = {'B': (4, 4), 'C': (6, 6), 'D': (7, 8), 'E': (8, 4), 'F': (10, 3), 'G': (12, 3), 'I': (15, 2)}
    for key, (first_page, first_count) in page_for.items():
        for index, item in enumerate(modules[key]):
            page = first_page + (index >= first_count)
            for row in item['grids'].values():
                need(row in pages[page - 1], f'{key} grid PDF p{page}: {item["txt_ref"]}')
            item['pdf_page'] = page
            if key == 'E':
                guidance = pages[page - 1][4]
                need('Pass 1 re-strums the new chord on beat 1.' in guidance and 'Pass 2 lets the anticipation ring through beat 1 and resumes on beat 2.' in guidance, 'E PDF pass alternatives')
                item['pdf_pass_1_and_2_guidance'] = guidance
    for index, capstone in enumerate(modules['J']):
        page = 17 + index
        for system in capstone['systems']:
            need(all(row in pages[page - 1] for row in system['raw_rows']), f'J grid PDF p{page}: {system["txt_ref"]}')
        capstone['pdf_page'] = page


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pinned(root, TXT), 'pdf': pinned(root, PDF), 'source_map': pinned(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(page.extract_text() or '').splitlines() for page in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 439 and len(pages) == 20, 'TXT/PDF extent drift')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION VI, LEVEL 50', 'CHORD TRANSITIONS, COMMON-FINGER AND GUIDE-FINGER MOVEMENT, ANTICIPATED CHANGES, AND UNINTERRUPTED PROGRESSIONS'], 'TXT title')
    need(all(page[0] == 'Guitar Exercises - Section VI, Level 50' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need(lines[6] == 'COMPLETE NOTATED WORKLOAD: 768 strum or pick attacks plus 80 silent chord landings before optional repeats.' and pages[0][2] == '80 SILENT LANDINGS | 768 ATTACKS', 'printed total declaration')
    rows = source_map.get('rows')
    need(isinstance(rows, list), 'source-map rows')
    mapped = next((r for r in rows if r.get('level') == 50), None)
    need(mapped is not None and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.2.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['admitted'] and not mapped['imported'] and not mapped['runtime_eligible'], 'source-map Level50 status')
    need(mapped['txt_path'] == TXT[0] and mapped['txt_sha256'] == TXT[1] and mapped['txt_bytes'] == TXT[2] and mapped['pdf_path'] == PDF[0] and mapped['pdf_sha256'] == PDF[1] and mapped['pdf_bytes'] == PDF[2], 'source-map Level50 identity')
    section_map = sections(lines)
    chords = chord_reference(lines)
    modules = module_items(lines, section_map)
    check_pdf_grids(modules, pages)
    computed = {'A': sum(x['silent_landings'] for x in modules['A'])}
    computed.update({key: sum(x['printed_attacks'] for x in modules[key]) for key in 'BCDEFGHIJ'})
    need(computed == COUNTS and sum(computed[key] for key in 'BCDEFGHIJ') == 768, 'module workload reconciliation')
    need([len(modules[key]) for key in 'ABCDEFGHIJ'] == list(ITEM_COUNTS.values()), 'module item reconciliation')
    need([int(pages[0][i]) for i in range(26, 45, 2)] == list(COUNTS.values()) and pages[0][45:47] == ['ATTACK TOTAL', '768'], 'PDF workload table')
    need('Clean-transition tests' in pages[18] and 'Quarter-note clean/min' in pages[18] and 'Anticipated clean/min' in pages[18] and 'Half-beat burst clean' in pages[18] and 'Add 2 BPM after three clean loops. When two errors occur, return to the previous timing window.' in pages[18], 'PDF-only clean tests')
    need('Completion audit and practice log' in pages[19] and 'Weak finger / bass / bar' in pages[19], 'PDF-only completion audit')
    need(lines[403] == 'PRACTICE PROGRESSION AND ERROR REPAIR' and lines[426] == 'MASTERY GATE BEFORE LEVEL 51' and lines[437] == 'NEXT LEVEL', 'guidance boundaries')
    source = {name: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for name, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level050.detached-source-candidate.1', 'wbs': '2.3.1.2.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'audible_voicing_events': None, 'bass_note_midi_for_H4': None, 'optional_repeat_attack_count': None, 'source': source, 'source_map_row': mapped, 'chord_reference': chords, 'module_sections': section_map, 'modules': modules, 'silent_landings': 80, 'notated_attacks_by_module': {key: computed[key] for key in 'BCDEFGHIJ'}, 'notated_attack_total': 768, 'source_differences': [{'kind': 'alternate_fingering_header_vs_symbol_grid', 'detail': 'Em-alt/E-alt transition headers and guidance print Em/E in Chd rows; symbol alone does not select a fingering.', 'txt_refs': [ref(23, 24), ref(69, 80), ref(115, 126)]}, {'kind': 'PDF_only_E_pass_1_confirmation', 'pdf_ref': 'L50-PDF-p8-L5', 'pdf_text': pages[7][4], 'txt_equivalent': 'TXT prints only Pass 2 ring-through instruction per cell'}, {'kind': 'PDF_only_clean_transition_tests', 'pdf_ref': 'L50-PDF-p19-L33-51', 'pdf_text': pages[18][32:51], 'txt_equivalent': None}, {'kind': 'PDF_only_completion_audit_and_log', 'pdf_ref': 'L50-PDF-p20-L14-31', 'pdf_text': pages[19][13:31], 'txt_equivalent': None}, {'kind': 'PDF_expanded_next_level_guidance', 'pdf_ref': 'L50-PDF-p20-L32-34', 'pdf_text': pages[19][31:34], 'txt_ref': ref(438, 439)}, {'kind': 'PDF_visual_panel_border_overlap', 'pdf_ref': 'L50-PDF-p19', 'inspection': 'Rendered page 19 shows checkbox rows of ten-phase list extending past the lower panel border; source-layout observation only.'}], 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_practice_mastery_next_lines': lines[403:], 'pdf_practice_mastery_pages': pages[18:]}}


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
    value = build_candidate(ROOT)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encode(value))
    print(f'{target.relative_to(ROOT)} bytes={target.stat().st_size} sha256={hashlib.sha256(target.read_bytes()).hexdigest()}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
