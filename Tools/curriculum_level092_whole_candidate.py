#!/usr/bin/env python3
"""Build a pinned, non-admitted whole-Level92 PDF-expanded semantic candidate."""
from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader, __version__ as PYPDF_VERSION

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('Build/parallel-11/2.3.1.3.1-level092-whole-r01')
STEM = 'Guitar_Exercises_Section_XIII_Level_92_Rakes_Grace_Notes_Double_Stop_Slides_Harmonics_Volume_Swells_Muted_Attacks_and_Articulation_Chains'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', 1675, '67ddb7a03c84f727f78ced578853b21b2ecf22eb81a72deedfe1d16bd9ab8e1a')
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', 43299, 'c2068c5c2a52366fcd53526a0ae32a82a4aaabde9252be17599726bf8f01beff')
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 199753, 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6')
KEYS = tuple('ABCDEFGHIJ')
EVENTS = (128, 128, 144, 112, 112, 112, 112, 160, 256, 64)
MODULE_PAGES = {'A': (3, 4), 'B': (5, 6), 'C': (7, 8), 'D': (9,), 'E': (10,), 'F': (11,), 'G': (12,), 'H': (13, 14), 'I': (15,), 'J': (16,)}
SPECS = {
    2: (('Symbol', 'Meaning', 'Primary control'), 8),
    3: (('Cell', 'Direction', 'Target', 'Rule'), 8),
    4: (('Pass', 'Muted contacts', 'Target'), 6),
    5: (('Cell', 'Figure', 'Goal'), 8),
    6: (('Window', 'Ornament begins', 'Target lands'), 6),
    7: (('Cell', 'Shape', 'Motion'), 8),
    8: (('Pass', 'Top voice', 'Lower voice'), 6),
    9: (('Node', 'Approximate result', 'Practice'), 6),
    10: (('Cell', 'Fretted note', 'Pick-hand task'), 8),
    11: (('Cell', 'Attack method', 'Volume motion'), 8),
    12: (('Cell', 'Pattern', 'Function'), 8),
    13: (('Chain', 'Articulation order', 'Primary risk'), 8),
    14: (('Function', 'Recommended chain'), 8),
    15: (('Bars', 'Harmony', 'Expression focus', 'Dynamic'), 8),
    16: (('Failure', 'Immediate repair'), 8),
}
CHORD = re.compile(r'[A-G](?:#|b)?(?:maj7|m7|5|7|m)?')


class SourceError(ValueError):
    pass


def need(ok: bool, message: str) -> None:
    if not ok:
        raise SourceError(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pin(root: Path, spec: tuple[str, int, str]) -> bytes:
    rel, size, digest = spec
    path = root
    for part in Path(rel).parts:
        path = path / part
        need(not path.is_symlink(), f'source symlink: {rel}')
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise SourceError(f'missing pinned source: {rel}') from exc
    need(resolved.is_relative_to(root) and resolved.is_file(), f'unsafe source: {rel}')
    raw = resolved.read_bytes()
    need(len(raw) == size and sha(raw) == digest, f'pin drift: {rel}')
    return raw


def one_line(lines: list[str], value: str) -> int:
    matches = [n for n, row in enumerate(lines, 1) if row == value]
    need(len(matches) == 1, f'TXT line missing/repeated: {value}')
    return matches[0]


def table(lines: list[str], page: int) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    columns, count = SPECS[page]
    starts = [i for i in range(len(lines) - len(columns) + 1) if tuple(lines[i:i + len(columns)]) == columns]
    need(len(starts) == 1, f'PDF page {page} table heading')
    start = starts[0]
    first = start + len(columns)
    end = first + count * len(columns)
    need(end <= len(lines), f'PDF page {page} table extent')
    rows = []
    for n in range(count):
        offset = first + n * len(columns)
        fields = lines[offset:offset + len(columns)]
        need(len(fields) == len(columns) and all(fields), f'PDF page {page} row {n + 1}')
        rows.append({'ordinal': n + 1, 'fields': dict(zip(columns, fields)), 'raw_fields': fields,
                     'pdf_ref': f'L92-PDF-p{page}-L{offset + 1}-{offset + len(columns)}',
                     'declared_events_for_row': None, 'performed_events': None})
    for row in rows:
        label = row['raw_fields'][0]
        if columns[0] in ('Cell', 'Pass'):
            need(label == str(row['ordinal']), f'PDF page {page} ordinal {row["ordinal"]}')
        if columns[0] == 'Chain':
            need(label == f'Chain {row["ordinal"]}', f'PDF page {page} chain ordinal')
    return rows, lines[:start], lines[end:]


def stages(value: str) -> list[str]:
    return [part.strip() for part in value.split(' -> ')]


def annotate(page: int, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        f = row['fields']
        n = row['ordinal']
        if page == 2:
            row['semantic'] = {'symbol': f['Symbol'], 'meaning': f['Meaning'], 'control': f['Primary control']}
        elif page == 3:
            row['semantic'] = {'direction': f['Direction'], 'pitched_target_raw': f['Target'],
                               'muted_contact_count': {1: 3, 2: 4, 3: 2, 6: 1, 7: 2}.get(n),
                               'target_arrival_raw': {6: 'next 16th', 7: 'beat', 8: 'beat 4'}.get(n),
                               'sequence_raw': f['Rule'],
                               'ordered_actions': {4: ['rake ends', 'bend begins'], 5: ['pitch centers', 'vibrato begins'],
                                                   6: ['single muted contact', 'target'],
                                                   7: ['two muted contacts', 'target'],
                                                   8: ['silent rest', 'rake', 'target']}.get(n, ['muted contacts', 'target']),
                               'pitch': None}
            if n in (1, 2, 3):
                need(f['Rule'] == f"{row['semantic']['muted_contact_count']} muted strings + target", f'A contact relation {n}')
            if n == 4:
                need(f['Rule'] == 'rake ends before bend begins', 'A rake/bend order')
            if n == 5:
                need(f['Rule'] == 'vibrato begins after pitch centers', 'A vibrato order')
            if n in (6, 7, 8):
                need(row['semantic']['target_arrival_raw'] in f['Target'], f'A target arrival {n}')
        elif page == 4:
            row['semantic'] = {'muted_dynamic_raw': f['Muted contacts'], 'target_dynamic_raw': f['Target'],
                               'relation': 'diagnostic_flat' if n == 5 else 'target_emphasis'}
        elif page == 5:
            row['semantic'] = {'figure_stages': stages(f['Figure']), 'goal_raw': f['Goal'],
                               'target_pitch': None, 'actual_arrival': None}
        elif page == 6:
            row['semantic'] = {'window': f['Window'], 'ornament_begins_raw': f['Ornament begins'],
                               'target_lands_raw': f['Target lands'],
                               'target_before_ornament': f['Window'] == 'Delayed ornament',
                               'ornament_omitted': f['Window'] == 'No ornament', 'onset_q': None}
        elif page == 7:
            motion = f['Motion']
            moving = ('lower',) if 'lower voice slides' in motion else ('upper',) if 'upper voice slides' in motion else ('both',) if 'both voices move' in f['Shape'] else None
            row['semantic'] = {'dyad_shape_raw': f['Shape'], 'motion_raw': motion,
                               'moving_voice_raw': moving, 'top_pitch': None, 'lower_pitch': None}
        elif page == 8:
            row['semantic'] = {'top_voice_action': f['Top voice'], 'lower_voice_action': f['Lower voice'],
                               'simultaneous_voice_task': True, 'durations': None}
        elif page == 9:
            node = f['Node']
            row['semantic'] = {'node_raw': node, 'approximate_result': f['Approximate result'],
                               'node_sequence': stages(node) if ' -> ' in node else None,
                               'practice_raw': f['Practice'], 'harmonic_pitch': None}
        elif page == 10:
            row['semantic'] = {'fretted_note_raw': f['Fretted note'], 'pick_hand_task': f['Pick-hand task'],
                               'harmonic_node': None, 'produced_pitch': None}
        elif page == 11:
            row['semantic'] = {'attack_method': f['Attack method'], 'volume_motion_raw': f['Volume motion'],
                               'volume_stages': stages(f['Volume motion']), 'device_choice': None}
        elif page == 12:
            pattern = f['Pattern']
            row['semantic'] = {'pattern_raw': pattern, 'sequence_tokens': stages(pattern) if ' -> ' in pattern else pattern.split(),
                               'phrase_function': f['Function'], 'chosen_pitches': None}
        elif page == 13:
            row['semantic'] = {'articulation_stages': stages(f['Articulation order']),
                               'primary_risk_raw': f['Primary risk'], 'chosen_pitches': None}
        elif page == 14:
            row['semantic'] = {'phrase_function': f['Function'],
                               'recommended_stages': stages(f['Recommended chain']),
                               'alternatives': f['Recommended chain'].split(' or ') if ' or ' in f['Recommended chain'] else None,
                               'chain_ordinal': None}
        elif page == 15:
            m = re.fullmatch(r'(\d+)-(\d+)', f['Bars'])
            need(m is not None, f'I bar range {n}')
            first, last = map(int, m.groups())
            chords = f['Harmony'].split('-')
            need(len(chords) == last - first + 1 == 4 and all(CHORD.fullmatch(chord) for chord in chords), f'I harmony {n}')
            row['semantic'] = {'start_bar': first, 'end_bar': last, 'chords': chords,
                               'expression_focus_raw': f['Expression focus'], 'dynamic_raw': f['Dynamic'],
                               'note_attacks': None, 'voicings': None}
        elif page == 16:
            row['semantic'] = {'failure': f['Failure'], 'immediate_repair': f['Immediate repair'],
                               'performed_recovery': None}


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    raw = {'txt': pin(root, TXT), 'pdf': pin(root, PDF), 'source_map': pin(root, MAP)}
    need(PYPDF_VERSION == '6.10.0', f'PDF extractor drift: {PYPDF_VERSION}')
    try:
        lines = raw['txt'].decode('utf-8').splitlines()
        pages = [(page.extract_text() or '').splitlines() for page in PdfReader(BytesIO(raw['pdf']), strict=True).pages]
        source_map = json.loads(raw['source_map'])
    except Exception as exc:
        raise SourceError('source decode failure') from exc
    need(len(lines) == 44 and len(pages) == 16, 'TXT/PDF extent')
    need(lines[0] == 'GUITAR EXERCISES - SECTION XIII, LEVEL 92' and pages[0][0] == 'Guitar Exercises - Section XIII, Level 92', 'Level/section identity')
    need(one_line(lines, 'COMPLETE WRITTEN WORKLOAD: 1328 events') == 10, 'TXT total declaration')
    row = next((r for r in source_map['rows'] if r.get('level') == 92), None)
    need(row is not None and row['section'] == 'XIII' and row['wbs_owner'] == '2.3.1.3.1' and row['pair_status'] == 'exact_stem_pair' and row['review'] == 'Pending' and row['conversion_status'] == 'not_converted' and not row['stable_ids_assigned'] and not row['runtime_eligible'] and not row['imported'] and not row['admitted'], 'source-map status')
    need(all(row[f'{key}_path'] == spec[0] and row[f'{key}_bytes'] == spec[1] and row[f'{key}_sha256'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair')
    need(pages[0][6:9] == ['Module', 'Exercise', 'Events'], 'PDF overview heading')
    modules: dict[str, dict[str, Any]] = {}
    for index, key in enumerate(KEYS):
        pdf_key, name, count = pages[0][9 + index * 3:12 + index * 3]
        need(pdf_key == key and int(count) == EVENTS[index], f'PDF overview {key}')
        matches = [(n, line) for n, line in enumerate(lines, 1) if line.startswith(f'{key}. ') and line.endswith(f' - {count} events')]
        need(len(matches) == 1 and matches[0][1][3:].rsplit(' - ', 1)[0].casefold() == name.casefold(), f'TXT/PDF overview {key}')
        txt_line = matches[0][0]
        modules[key] = {'name': name, 'declared_events': EVENTS[index], 'txt_ref': f'L92-TXT-L{txt_line}',
                        'pdf_overview_ref': f'L92-PDF-p1-L{10 + index * 3}-{12 + index * 3}',
                        'pdf_pages': list(MODULE_PAGES[key]), 'tables': [], 'per_task_event_allocation': None}
    need(pages[0][39:41] == ['TOTAL', '1328'] and sum(EVENTS) == 1328, 'PDF/TXT workload total')
    parsed = {}
    for page in SPECS:
        parsed[page], _, tail = table(pages[page - 1], page)
        annotate(page, parsed[page])
        need(tail, f'PDF page {page} closing instruction')
    symbols = parsed[2]
    need([r['fields']['Symbol'] for r in symbols] == ['r', 'gr', '/ or \\', 'h / p', '<>', 'PH', 'sw', 'x'], 'articulation symbol legend')
    need('target pitch -> rhythmic placement -> dynamic level -> articulation detail.' in pages[1][-1], 'priority order')
    for key in KEYS:
        modules[key]['tables'] = [{'page': page, 'columns': list(SPECS[page][0]), 'rows': parsed[page],
                                    'page_intro': table(pages[page - 1], page)[1],
                                    'page_closing': table(pages[page - 1], page)[2]}
                                   for page in MODULE_PAGES[key]]
    capstone = parsed[15]
    need([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in capstone] == [(n, n + 3) for n in range(1, 33, 4)], 'I full 32-bar form')
    need([chord for r in capstone for chord in r['semantic']['chords']][-4:] == ['Am7', 'Dm7', 'E7', 'Am7'], 'I outro harmony')
    pass_line = ' '.join(pages[14][next(i for i, line in enumerate(pages[14]) if line.startswith('Pass 1: ')):])
    passes = re.findall(r'Pass (\d): (.*?)(?:\. |\.$)', pass_line)
    need([int(n) for n, _ in passes] == list(range(1, 6)), 'I five passes')
    mastery_start = next(i for i, line in enumerate(pages[15]) if line.startswith('Mastery: 14/16'))
    mastery_end = next(i for i, line in enumerate(pages[15]) if line.startswith('Next: '))
    mastery = ' '.join(pages[15][mastery_start:mastery_end])
    categories = ['rake control', 'ornament timing', 'double-stop clarity', 'harmonic production', 'volume-swell timing', 'phrase-function choice', 'density control', 'recovery']
    need(all(category in mastery for category in categories) and 'No zero in target timing, harmonic clarity, phrase-function choice, or recovery.' in mastery, 'mastery category and gate')
    mastery_score_line = one_line(lines, '14/16 or better on two separate days.')
    mastery_zero_line = one_line(lines, 'No zero in target timing, harmonic clarity, phrase-function choice, or recovery.')
    capstone_line = one_line(lines, '32 bars combining rakes, grace notes, double-stop slides, harmonics, swells, muted attacks, and multi-articulation chains.')
    source = {key: {'path': spec[0], 'bytes': spec[1], 'sha256': spec[2]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level092.detached-source-task-candidate.1', 'wbs': '2.3.1.3.1', 'level': 92, 'section': 'XIII',
            'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None, 'onset_q': None,
            'duration_q': None, 'fixed_bpm': None, 'executable_events': None, 'sounding_midi_events': None,
            'performed_event_count': None, 'rubric_outcome': None, 'source': source, 'source_map_row': row,
            'txt_full_lines': lines, 'pdf_full_extracted_pages': pages, 'symbol_legend': symbols, 'modules': modules,
            'declared_workload_total': 1328, 'declared_workload_by_module': dict(zip(KEYS, EVENTS)),
            'capstone': {'section_blocks': capstone, 'printed_bars': 32, 'txt_ref': f'L92-TXT-L{capstone_line}',
                         'passes': [{'ordinal': int(n), 'instruction': instruction, 'pdf_ref': 'L92-PDF-p15'} for n, instruction in passes]},
            'mastery': {'txt_refs': [f'L92-TXT-L{mastery_score_line}', f'L92-TXT-L{mastery_zero_line}'], 'pdf_ref': 'L92-PDF-p16', 'required_score': 14,
                        'maximum_score': 16, 'separate_days': 2, 'categories': categories,
                        'score_descriptors': None,
                        'no_zero_categories': ['target timing', 'harmonic clarity', 'phrase-function choice', 'recovery'],
                        'raw': mastery},
            'source_ambiguities': [
                {'kind': 'PDF_only_task_expansion', 'status': 'pending_curriculum_review', 'detail': 'TXT names the ten modules and workloads but omits detailed PDF table rows; all task semantics are PDF-only.'},
                {'kind': 'workload_without_printed_note_events', 'status': 'pending_curriculum_review', 'detail': 'The 1328 workload events are declared, but the PDF describes task cells and an eight-block form without exact attack pitches, voices, onsets, durations or per-cell event allocation.'},
                {'kind': 'mastery_scale_undefined', 'status': 'pending_curriculum_review', 'detail': 'The source lists eight categories and a 14/16 gate but does not print category score descriptors or a scored performance.'},
                {'kind': 'mastery_no_zero_label_mismatch', 'status': 'pending_curriculum_review', 'detail': 'The no-zero gate names target timing and harmonic clarity, while the eight scored dimensions are named ornament timing and harmonic production; the source does not define a precise mapping.'},
            ]}


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
    print(f'{target.relative_to(ROOT)} bytes={target.stat().st_size} sha256={sha(target.read_bytes())}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
