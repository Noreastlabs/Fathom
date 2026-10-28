#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level79 performance-task candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.3.1-level079-whole-r01')
STEM = 'Guitar_Exercises_Section_X_Level_79_Complete_Performance_Improvisation_Long_Form_Dynamic_Arcs_Multi_Key_Navigation_Rhythmic_Displacement_Ensemble_Cues_and_Ear_Led_Recovery'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', '56e42cd4324af9178b85d2525c38241e85b7c91c9cb75d9bfc7c7013664793fe', 15147)
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', '00a75f782c15ef8e8aaa8239b64f96cd272e90fca74ccc3ad09da362ad12aebb', 52949)
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6', 199753)
KEYS = tuple('ABCDEFGH')
WORKLOAD = dict(zip(KEYS, (128, 144, 128, 96, 160, 96, 256, 192)))
PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'Bb': 10, 'B': 11}
ROLE = {'R': 0, '3': 4, 'b3': 3, 'b5': 6, 'b7': 10}


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
    return f'L79-TXT-L{first}' if last is None else f'L79-TXT-L{first}-{last}'


def chord_pcs(chord: str) -> set[int]:
    match = re.fullmatch(r'([A-G](?:#|b)?)(maj7|m7b5|m7|7)', chord)
    need(match is not None and match.group(1) in PC, f'chord spelling: {chord}')
    intervals = {'maj7': (0, 4, 7, 11), 'm7': (0, 3, 7, 10), 'm7b5': (0, 3, 6, 10), '7': (0, 4, 7, 10)}[match.group(2)]
    return {(PC[match.group(1)] + step) % 12 for step in intervals}


def sections(lines: list[str]) -> dict[str, dict[str, Any]]:
    heads = [(i, re.match(r'^MODULE ([A-H]) - ', row).group(1), row) for i, row in enumerate(lines) if re.match(r'^MODULE ([A-H]) - ', row)]
    need(len(heads) == 8 and tuple(letter for _, letter, _ in heads) == KEYS, 'module heading order')
    out = {}
    for n, (start, letter, heading) in enumerate(heads):
        stop = heads[n + 1][0] - 1 if n < 7 else next(i for i, row in enumerate(lines) if row == 'SCORING') - 1
        need(lines[start - 1].startswith('=') and lines[start + 1].startswith('='), f'{letter} frame')
        out[letter] = {'heading': heading, 'start_line': start + 1, 'end_line': stop, 'txt_ref': ref(start + 1, stop), 'raw_lines': lines[start:stop]}
    return out


def parse_master(lines: list[str], pages: list[list[str]]) -> tuple[list[dict[str, Any]], list[str]]:
    start = lines.index('MASTER 48-BAR FORM')
    stop = lines.index('MODULE A - LONG-FORM DYNAMIC ARC')
    rows = [(i + 1, row) for i, row in enumerate(lines[start:stop], start) if re.match(r'^[A-Z ]+ bars \d+-\d+ \|', row)]
    need(len(rows) == 7, 'seven master sections')
    sections_out, all_chords = [], []
    previous = 0
    for line, raw in rows:
        parts = [part.strip() for part in raw.split('|')]
        m = re.fullmatch(r'([A-Z ]+) bars (\d+)-(\d+)', parts[0])
        need(m is not None and len(parts) >= 7, f'master row {line}')
        name, first, last = m.group(1), int(m.group(2)), int(m.group(3))
        chords = parts[2:-3]
        need(first == previous + 1 and last >= first and len(chords) == last - first + 1 and all(chord_pcs(chord) for chord in chords), f'master bar/chord parity {line}')
        need(parts[-3].startswith('dynamic ') and parts[-2].startswith('role ') and parts[-1].startswith('exit cue: '), f'master metadata {line}')
        sections_out.append({'section': name, 'start_bar': first, 'end_bar': last, 'key_center_raw': parts[1], 'chords': chords, 'dynamic_raw': parts[-3][8:], 'role_raw': parts[-2][5:], 'exit_cue_raw': parts[-1][10:], 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p2', 'raw': raw})
        all_chords.extend(chords)
        previous = last
    need(previous == 48 and len(all_chords) == 48, 'complete 48-bar form')
    pdf = pages[1]
    need(all(section['section'] in pdf and section['key_center_raw'] in pdf and section['exit_cue_raw'] in pdf for section in sections_out), 'master PDF section metadata')
    need(all(' | '.join(section['chords']) in pdf for section in sections_out), 'master PDF chord sequences')
    return sections_out, all_chords


def numbered_rows(lines: list[str], section: dict[str, Any]) -> list[tuple[int, str]]:
    return [(i + 1, lines[i]) for i in range(section['start_line'] + 1, section['end_line']) if lines[i] and not lines[i].startswith('=')]


def parse_a(lines: list[str], section: dict[str, Any], master: list[dict[str, Any]], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    dynamic = []
    for line, raw in rows:
        if not re.match(r'^\d+-\d+ \|', raw):
            continue
        parts = [x.strip() for x in raw.split('|')]
        need(len(parts) == 6, f'A dynamic row {line}')
        dynamic.append({'bars': parts[0], 'section': parts[1], 'dynamic': parts[2], 'contacts_per_bar_raw': parts[3], 'register': parts[4], 'instruction': parts[5], 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p3', 'raw': raw})
    need(len(dynamic) == 8 and [r['bars'] for r in dynamic] == ['1-4', '5-12', '13-16', '17-24', '25-32', '33-40', '41-44', '45-48'], 'A eight dynamic ranges')
    need([r['section'] for r in dynamic[:6]] == [s['section'].title() for s in master[:6]], 'A master section names')
    for index, item in enumerate(dynamic):
        pdf_row = pages[2][10 + index * 6:16 + index * 6]
        need(pdf_row == [item['bars'], item['section'], item['dynamic'], item['contacts_per_bar_raw'], item['register'], item['instruction']], f'A PDF dynamic row {index + 1}')
    pdf = pages[3]
    extras = []
    for i in range(4, 28, 3):
        name, register, texture = pdf[i:i + 3]
        need(register.startswith('Register: ') and texture.startswith('Texture: '), f'A PDF register cell {i}')
        extras.append({'name': name, 'register': register[10:], 'texture': texture[9:], 'pdf_ref': f'L79-PDF-p4-L{i + 1}-{i + 3}'})
    need(len(extras) == 8, 'A eight PDF register cells')
    return {'dynamic_arc': dynamic, 'pdf_register_texture_cells': extras, 'practice_raw': [r for _, r in rows if r.startswith('Practice the arc')], 'pdf_refs': ['L79-PDF-p3', 'L79-PDF-p4']}


def parse_b(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    targets = []
    chains = []
    for line, raw in rows:
        if ' -> target ' in raw:
            m = re.fullmatch(r'([^:]+): ([^ ]+) -> target ([A-G](?:#|b)?) \(([^)]+)\)\. Sing, silently locate, then play in two registers\.', raw)
            need(m is not None, f'B target syntax {line}')
            context, chord, target, role_text = m.groups()
            role = role_text.split(' ', 1)[0]
            need(role in ROLE and target in PC and (PC[chord[:2]] if chord[:2] in PC else PC[chord[0]]) is not None, f'B target role {line}')
            root = re.match(r'[A-G](?:#|b)?', chord).group()
            need((PC[root] + ROLE[role]) % 12 == PC[target] and PC[target] in chord_pcs(chord), f'B target/chord pitch {line}')
            targets.append({'context': context, 'chord': chord, 'target': target, 'role_raw': role_text, 'role': role, 'action': 'sing; silently locate; one attack in two registers', 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p5', 'raw': raw})
        elif ' | voice 1 ' in raw:
            parts = raw.split(' | ')
            need(len(parts) == 3 and ': ' in parts[0] and parts[1].startswith('voice 1 ') and parts[2].startswith('voice 2 '), f'B chain syntax {line}')
            route, chords_raw = parts[0].split(': ', 1)
            chords = chords_raw.split(' -> ')
            voices = [parts[1][8:].split(' -> '), parts[2][8:].split(' -> ')]
            need(len(chords) == 3 and all(len(v) == 3 for v in voices), f'B three-chord chain {line}')
            need(all(note in PC and PC[note] in chord_pcs(chord) for voice in voices for note, chord in zip(voice, chords)), f'B guide-tone chord membership {line}')
            chains.append({'route': route, 'chords': chords, 'voices': voices, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p6', 'raw': raw})
    need(len(targets) == 24 and len(chains) == 6, 'B 24 targets and six chains')
    need(all(t['chord'] in pages[4] and t['target'] in pages[4] for t in targets), 'B PDF target coverage')
    need(all(c['route'] in pages[5] and ' -> '.join(c['chords']) in pages[5] for c in chains), 'B PDF chain coverage')
    return {'targets': targets, 'pivot_dominant_chains': chains}


def parse_c(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    motif = next(raw for _, raw in rows if raw.startswith('Motif: '))[7:]
    notes = motif.split('-')
    need(notes == ['C', 'E', 'G', 'B', 'A', 'G', 'E', 'D'], 'C eight-note motif')
    offsets = []
    for line, raw in rows:
        m = re.fullmatch(r'(\d)\. Start on (.+); keep the Cmaj7 barline and chord change fixed\.', raw)
        if m:
            offsets.append({'ordinal': int(m.group(1)), 'start_raw': m.group(2), 'motif_notes': notes, 'fixed_chord': 'Cmaj7', 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p7', 'raw': raw})
    need(len(offsets) == 8 and [r['ordinal'] for r in offsets] == list(range(1, 9)), 'C eight displacement starts')
    devices_raw = next(raw for _, raw in rows if raw.startswith('Section devices: '))[17:]
    devices = ['group of 3', 'group of 5', '3+3+2', 'one-bar quintuplets', 'sixteenth-note metric displacement', 'straight-time release']
    need(all(device in devices_raw for device in devices), 'C six section devices')
    pdf_studies = []
    for i in range(8, 32, 4):
        location, device, grid, instruction = pages[7][i:i + 4]
        pdf_studies.append({'location': location, 'device': device, 'grid': grid, 'instruction': instruction, 'pdf_ref': f'L79-PDF-p8-L{i + 1}-{i + 4}'})
    need(len(pdf_studies) == 6 and ['group of 3', 'group of 5', '3+3+2', 'quintuplet beat', 'metric displacement', 'return to straight'] == [s['device'] for s in pdf_studies], 'C six PDF section studies')
    need(all(f"{r['ordinal']}. Start on {r['start_raw']}" in pages[6] for r in offsets), 'C PDF displacement coverage')
    return {'motif_notes': notes, 'offset_cells': offsets, 'section_devices': [{'name': d, 'txt_ref': section['txt_ref'], 'pdf_ref': 'L79-PDF-p8'} for d in devices], 'devices_raw': devices_raw, 'pdf_section_studies': pdf_studies}


def parse_d(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    cues, conversions = [], []
    in_conversion = False
    for line, raw in rows:
        if raw == 'CUE-TO-ROLE CONVERSION':
            in_conversion = True
            continue
        if not in_conversion and ' | lead time ' in raw:
            parts = raw.split(' | ')
            need(len(parts) == 4 and parts[1].startswith('lead time ') and parts[2].startswith('response ') and parts[3].startswith('if missed: '), f'D cue row {line}')
            cues.append({'cue': parts[0], 'lead_time_raw': parts[1][10:], 'response': parts[2][9:], 'if_missed': parts[3][11:], 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p9', 'raw': raw})
        elif in_conversion and ': ' in raw and ' -> ' in raw:
            m = re.fullmatch(r'([^:]+): ([A-Z ]+) -> ([A-Z ]+)\. (.+)\. Keep the current bar count\.', raw)
            need(m is not None, f'D role conversion {line}')
            cue, from_role, to_role, action = m.groups()
            conversions.append({'cue': cue, 'from_role': from_role, 'to_role': to_role, 'action': action, 'bar_count_preserved': True, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p10', 'raw': raw})
    need(len(cues) == 12 and len(conversions) == 8, 'D cue/conversion counts')
    need(all(c['cue'] in pages[8] for c in cues) and all(f"{c['cue']}: {c['from_role']} -> {c['to_role']}" in pages[9] for c in conversions), 'D PDF cue coverage')
    return {'cue_response_matrix': cues, 'cue_to_role_cells': conversions}


def parse_e(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    circuits, studies = [], []
    in_matrix = False
    for line, raw in rows:
        if raw == 'DENSITY / REGISTER MATRIX':
            in_matrix = True
            continue
        if not in_matrix and ' | role map ' in raw:
            parts = raw.split(' | ')
            need(len(parts) == 3 and ': ' in parts[0] and parts[1].startswith('role map '), f'E role circuit {line}')
            key, progression = parts[0].split(': ', 1)
            chords, roles = progression.split('-'), parts[1][9:].split()
            need(len(chords) == len(roles) == 4 and set(roles) <= {'C', 'L'} and all(chord_pcs(c) for c in chords), f'E four-bar roles {line}')
            circuits.append({'key_center_raw': key, 'chords': chords, 'roles': roles, 'role_legend': parts[2], 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p11', 'raw': raw})
        elif in_matrix and ': outgoing ' in raw:
            m = re.fullmatch(r'(.+): outgoing (.+); incoming (.+); register (.+)', raw)
            need(m is not None, f'E density study {line}')
            name, outgoing, incoming, register = m.groups()
            studies.append({'name': name, 'outgoing': outgoing, 'incoming': incoming, 'register': register, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p12', 'raw': raw})
    need(len(circuits) == len(studies) == 8, 'E eight circuits/studies')
    need(all(c['key_center_raw'] in pages[10] and '-'.join(c['chords']) in pages[10] for c in circuits), 'E PDF circuit coverage')
    need(all(s['name'] in pages[11] for s in studies), 'E PDF density coverage')
    return {'role_switch_circuits': circuits, 'density_register_studies': studies}


def parse_f(lines: list[str], section: dict[str, Any], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    repairs, scenarios = [], []
    randomized = False
    for line, raw in rows:
        if raw == 'RANDOMIZED SCENARIOS':
            randomized = True
            continue
        if not randomized and ': immediate repair = ' in raw:
            m = re.fullmatch(r'([^:]+): immediate repair = (.+); next action = (.+)\.', raw)
            need(m is not None, f'F repair syntax {line}')
            failure, immediate, next_action = m.groups()
            repairs.append({'failure': failure, 'immediate_repair': immediate, 'next_action': next_action, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p13', 'raw': raw})
        elif randomized and ': ' in raw:
            ending = '; continue through the section exit.'
            need(raw.endswith(ending), f'F scenario syntax {line}')
            setting, repair = raw.removesuffix(ending).rsplit(': ', 1)
            scenarios.append({'setting': setting, 'repair_sequence': repair, 'continue_through_section_exit': True, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p14', 'raw': raw})
    need(len(repairs) == 12 and len(scenarios) == 8, 'F repair/scenario counts')
    need(all(r['failure'] in pages[12] for r in repairs) and all(s['setting'] in pages[13] for s in scenarios), 'F PDF coverage')
    return {'recovery_cards': repairs, 'randomized_scenarios': scenarios}


def parse_g(lines: list[str], section: dict[str, Any], master_chords: list[str], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    groups = []
    for line, raw in rows:
        m = re.fullmatch(r'Bars (\d+)-(\d+): (.+)', raw)
        if m:
            groups.append({'start_bar': int(m.group(1)), 'end_bar': int(m.group(2)), 'section_raw': m.group(3), 'chords': [], 'txt_ref': ref(line), 'raw': raw})
        elif raw.startswith('|'):
            need(bool(groups), 'G chord line without group')
            groups[-1]['chords'].extend([part.strip() for part in raw.split('|')[1:-1]])
    need(len(groups) == 6 and [(g['start_bar'], g['end_bar']) for g in groups] == [(1, 12), (13, 16), (17, 24), (25, 32), (33, 40), (41, 48)], 'G six section-study blocks')
    need(all(len(g['chords']) == g['end_bar'] - g['start_bar'] + 1 and g['chords'] == master_chords[g['start_bar'] - 1:g['end_bar']] for g in groups), 'G master chord parity')
    for g in groups:
        g['pdf_ref'] = 'L79-PDF-p15' if g['start_bar'] <= 16 else 'L79-PDF-p16' if g['start_bar'] <= 32 else 'L79-PDF-p17'
        page = pages[int(g['pdf_ref'].rsplit('p', 1)[1]) - 1]
        heading = next(i for i, row in enumerate(page) if row.startswith(f"Bars {g['start_bar']}-{g['end_bar']} - "))
        next_heading = next((i for i in range(heading + 1, len(page)) if page[i].startswith('Bars ')), len(page))
        pdf_chords = []
        for row in page[heading + 1:next_heading]:
            if '|' in row and (row.startswith('|') or row.startswith('INTRO ') or row.startswith('VERSE ') or row.lstrip().startswith('|')):
                pdf_chords.extend(part.strip() for part in row.split('|')[1:-1])
        need(pdf_chords == g['chords'], f'G PDF/TXT chord parity bars {g["start_bar"]}-{g["end_bar"]}')
    badges = [pages[p - 1][2] for p in (15, 16, 17)]
    need(all('16 BARS  |  64 EVENTS' in badge for badge in badges), 'G three 64-event page badges')
    return {'section_studies': groups, 'printed_bars': 48, 'pdf_page_event_declarations': [64, 64, 64], 'pdf_page_event_sum': 192, 'four_per_bar_reference': 192}


def parse_h(lines: list[str], section: dict[str, Any], master: list[dict[str, Any]], pages: list[list[str]]) -> dict[str, Any]:
    rows = numbered_rows(lines, section)
    passes = [(line, raw) for line, raw in rows if re.match(r'^Pass \d+: ', raw)]
    need(len(passes) == 5 and [int(raw[5]) for _, raw in passes] == list(range(1, 6)), 'H five performance passes')
    required = next(raw for _, raw in rows if raw.startswith('Required events: '))[17:].rstrip('.').split('; ')
    need(len(required) == 9, 'H nine required-event clauses')
    for note, chord in [('C#', 'A7'), ('F#', 'D7'), ('D#', 'B7'), ('G#', 'E7'), ('F', 'Bm7b5')]:
        need(any(f'{note} over {chord}' in item for item in required) and PC[note] in chord_pcs(chord), f'H required harmonic target {note}/{chord}')
    need('48 BARS  |  192 EVENTS' in pages[17][2] and pages[17][44].startswith('Pass 1: roots only.'), 'H PDF capstone declarations')
    pdf_form = pages[17]
    for index, item in enumerate(master):
        pdf_row = pdf_form[9 + index * 5:14 + index * 5]
        need(pdf_row[:3] == [f"{item['start_bar']}-{item['end_bar']}", item['section'], item['key_center_raw']], f'H PDF/master form row {index + 1}')
    return {'passes': [{'ordinal': n + 1, 'instruction': raw.split(': ', 1)[1].rstrip('.'), 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p18', 'raw': raw} for n, (line, raw) in enumerate(passes)], 'required_event_clauses': required, 'required_events_ref': section['txt_ref'], 'master_section_refs': [s['txt_ref'] for s in master], 'declared_bars': 48, 'declared_events': 192}


def parse_scoring(lines: list[str], pages: list[list[str]]) -> dict[str, Any]:
    first, last = lines.index('SCORING'), lines.index('PASSING STANDARD')
    rows = [(i + 1, row) for i, row in enumerate(lines[first:last], first) if re.match(r'^[A-Za-z /-]+: 0 ', row)]
    need(len(rows) == 9, 'nine scoring categories')
    rubric = []
    for line, raw in rows:
        category, levels = raw.split(': ', 1)
        parts = levels.split(' | ')
        need(len(parts) == 3 and all(part.startswith(str(n) + ' ') for n, part in enumerate(parts)), f'rubric 0-2 scale {line}')
        rubric.append({'category': category, 'scores': {str(n): part[2:] for n, part in enumerate(parts)}, 'txt_ref': ref(line), 'pdf_ref': 'L79-PDF-p19', 'raw': raw})
    need(all(r['category'] in pages[18] for r in rubric), 'PDF rubric categories')
    passing = lines[last + 1]
    need(passing == '16/18 or better on two separate days. No zero in pulse, form, cue response, or recovery.', 'passing standard')
    return {'rubric': rubric, 'passing_standard': passing, 'maximum_score': 18, 'required_score': 16, 'separate_days': 2, 'hard_zero_categories': ['pulse', 'form', 'cue response', 'recovery']}


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(p.extract_text() or '').splitlines() for p in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 220 and len(pages) == 20, 'TXT/PDF extent')
    need(lines[:2] == ['GUITAR EXERCISES - SECTION X, LEVEL 79', 'COMPLETE-PERFORMANCE IMPROVISATION: LONG-FORM DYNAMIC ARCS, MULTI-KEY NAVIGATION, RHYTHMIC DISPLACEMENT, ENSEMBLE CUES, AND EAR-LED RECOVERY'], 'TXT title')
    need(all(page[0] == 'Guitar Exercises - Section X, Level 79' and page[-1] == f'Page {n} of 20' for n, page in enumerate(pages, 1)), 'PDF page identity')
    need('COMPLETE WRITTEN WORKLOAD: 1,200 events plus the uninterrupted capstone take.' in lines, 'TXT workload declaration')
    mapped = next((row for row in source_map['rows'] if row.get('level') == 79), None)
    need(mapped is not None and mapped['section'] == 'X' and mapped['pair_status'] == 'exact_stem_pair' and mapped['wbs_owner'] == '2.3.1.3.1' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'not_converted' and not mapped['stable_ids_assigned'] and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map status')
    need(all(mapped[f'{key}_path'] == spec[0] and mapped[f'{key}_sha256'] == spec[1] and mapped[f'{key}_bytes'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair identity')
    blocks = sections(lines)
    master, chords = parse_master(lines, pages)
    modules = {'A': parse_a(lines, blocks['A'], master, pages), 'B': parse_b(lines, blocks['B'], pages), 'C': parse_c(lines, blocks['C'], pages), 'D': parse_d(lines, blocks['D'], pages), 'E': parse_e(lines, blocks['E'], pages), 'F': parse_f(lines, blocks['F'], pages), 'G': parse_g(lines, blocks['G'], chords, pages), 'H': parse_h(lines, blocks['H'], master, pages)}
    scoring = parse_scoring(lines, pages)
    pdf_workload = [int(pages[0][i].replace(',', '')) for i in range(26, 42, 2)]
    need(pdf_workload == list(WORKLOAD.values()) and pages[0][41:43] == ['TOTAL', '1,200'] and sum(pdf_workload) == 1200, 'PDF overview workload')
    discrepancy = WORKLOAD['G'] - modules['G']['pdf_page_event_sum']
    need(discrepancy == 64 and modules['G']['four_per_bar_reference'] == 192, 'G source workload discrepancy')
    need('SECTION X COMPLETION' in lines and 'NEXT LEVEL' in lines and 'Section X mastery gate' in pages[19], 'completion bounds')
    source = {key: {'path': spec[0], 'bytes': spec[2], 'sha256': spec[1]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level079.detached-source-task-candidate.1', 'wbs': '2.3.1.3.1', 'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'sounding_midi_events': None, 'performed_event_count': None, 'rubric_outcome': None, 'source': source, 'source_map_row': mapped, 'source_sections': blocks, 'master_form': master, 'master_chords': chords, 'modules': modules, 'declared_workload_by_module': WORKLOAD, 'declared_workload_total': 1200, 'source_ambiguities': [{'kind': 'G_overview_256_vs_three_64_event_study_pages_192', 'status': 'pending_curriculum_review', 'overview_ref': 'L79-PDF-p1-L38-40', 'study_page_refs': ['L79-PDF-p15', 'L79-PDF-p16', 'L79-PDF-p17'], 'txt_ref': blocks['G']['txt_ref'], 'overview_events': 256, 'study_page_events': 192, 'difference': discrepancy, 'detail': 'The overview assigns G 256 events, while its three 16-bar study pages declare 64 each and the TXT prints 48 bars. No additional 64-event source cell is printed.'}], 'scoring': scoring, 'guidance': {'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'txt_control_hierarchy': lines[6:15], 'txt_completion_next_lines': lines[213:], 'pdf_completion_page': pages[19]}}


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
