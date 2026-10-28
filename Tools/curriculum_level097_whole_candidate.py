#!/usr/bin/env python3
"""Build a pinned, detached whole-Level97 recording-led task candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.3.1-level097-whole-r01')
STEM = 'Guitar_Exercises_Section_XIV_Level_97_Recording_Led_Repertoire_Reconstruction_Audio_to_Form_Harmony_Groove_Riffs_Arrangement_and_Performance'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', 1623, 'afb5b139ae7f24a1ce62b6deed53e4c5d09970e87f67be5024b25894f3ba506d')
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', 45729, '208d88c99d8c1c81d68ff2dcb3b396b1092153254ef280fe567e1b3c3741b307')
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 199753, 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6')
KEYS = tuple('ABCDEFGHIJ')
EVENTS = (96, 144, 128, 144, 96, 128, 112, 192, 320, 64)
MODULE_PAGES = {'A': (3, 4), 'B': (5, 6), 'C': (7, 8), 'D': (9, 10), 'E': (11,), 'F': (12, 13), 'G': (14, 15), 'H': (16, 17), 'I': (18,), 'J': (19,)}
SPECS = {
    2: (('Pass', 'Listen for', 'Do not solve yet'), 7),
    3: (('Question', 'Allowed answer'), 8),
    4: (('Pass', 'Deliverable'), 7),
    5: (('Stage', 'Task'), 7),
    6: (('Evidence', 'Likely question'), 7),
    7: (('Layer', 'Write'), 7),
    8: (('Evidence', 'Arrangement inference'), 7),
    9: (('Pass', 'Task'), 7),
    10: (('Fill type', 'Treatment'), 7),
    11: (('Detail', 'Structural test'), 8),
    12: (('Version', 'Contains'), 6),
    13: (('Source clue', 'First voicing test'), 7),
    14: (('Difference', 'Accept if...', 'Revise if...'), 7),
    15: (('Score', 'Meaning'), 4),
    16: (('Pass', 'Deliverable'), 6),
    17: (('Pass', 'Deliverable'), 6),
    18: (('Bars', 'Section', 'Input', 'Student task'), 8),
    19: (('Category', '0', '1', '2'), 8),
}
RUBRIC_CATEGORIES = ['Form', 'Bass/function', 'Harmony', 'Groove', 'Signature material', 'Structural judgment', 'Performance', 'Recovery']
DIVERGENCE_CATEGORIES = ['form', 'bass', 'harmony', 'groove', 'signature material', 'texture', 'ending']
CAPSTONE_DELIVERABLES = ['one-page form map', 'root/function chart', 'groove map', 'S/C/O detail classification', 'performance arrangement', 'reduced fallback', 'one uninterrupted memory take']


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
        label = fields[0]
        if columns[0] in ('Pass', 'Stage'):
            need(label == str(n + 1), f'PDF page {page} ordinal {n + 1}')
        if columns[0] == 'Score':
            need(label == str(n), f'PDF page {page} divergence score {n}')
        rows.append({'ordinal': n + 1, 'fields': dict(zip(columns, fields)), 'raw_fields': fields,
                     'pdf_ref': f'L97-PDF-p{page}-L{offset + 1}-{offset + len(columns)}',
                     'declared_events_for_row': None, 'observed_answer': None, 'performed_events': None})
    return rows, lines[:start], lines[end:]


def annotate(page: int, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        f, n = row['fields'], row['ordinal']
        if page == 2:
            row['semantic'] = {'pass': n, 'listen_for': f['Listen for'], 'defer': f['Do not solve yet'], 'observed_result': None}
        elif page == 3:
            raw = f['Allowed answer']
            row['semantic'] = {'question': f['Question'], 'allowed_answer_raw': raw,
                               'answer_options': re.split(r', | / ', raw) if n in (1, 2, 3, 7, 8) else None,
                               'student_answer': None}
        elif page in (4, 16, 17):
            row['semantic'] = {'pass': n, 'deliverable': f['Deliverable'], 'completed_deliverable': None}
        elif page == 5:
            row['semantic'] = {'stage': n, 'bass_root_task': f['Task'], 'inferred_pitch_or_degree': None}
        elif page == 6:
            row['semantic'] = {'audio_evidence': f['Evidence'], 'harmonic_question': f['Likely question'], 'inferred_chord': None}
        elif page == 7:
            row['semantic'] = {'layer': f['Layer'], 'write': f['Write'], 'transcribed_value': None,
                               'requires_primary_contact_map': f['Layer'] == 'Ghosts/mutes'}
        elif page == 8:
            row['semantic'] = {'audio_evidence': f['Evidence'], 'candidate_arrangement_inference': f['Arrangement inference'],
                               'verified_in_source': None}
        elif page == 9:
            row['semantic'] = {'pass': n, 'riff_task': f['Task'], 'transcribed_riff': None}
        elif page == 10:
            row['semantic'] = {'fill_type': f['Fill type'], 'treatment': f['Treatment'], 'source_fill_found': None}
        elif page == 11:
            row['semantic'] = {'detail': f['Detail'], 'structural_test': f['Structural test'],
                               'classification': None, 'classification_options': ['S', 'C', 'O']}
        elif page == 12:
            row['semantic'] = {'version': f['Version'], 'required_contents_raw': f['Contains'],
                               'contents': [part.strip() for part in f['Contains'].split(' + ')],
                               'performed_version': None}
        elif page == 13:
            row['semantic'] = {'source_clue': f['Source clue'], 'first_voicing_test': f['First voicing test'],
                               'selected_voicing': None}
        elif page == 14:
            row['semantic'] = {'difference': f['Difference'], 'accept_if': f['Accept if...'], 'revise_if': f['Revise if...'],
                               'audit_decision': None}
        elif page == 15:
            row['semantic'] = {'score': n - 1, 'meaning': f['Meaning'], 'awarded': None}
        elif page == 18:
            match = re.fullmatch(r'(\d+)-(\d+)', f['Bars'])
            need(match is not None, f'I bar range {n}')
            first, last = map(int, match.groups())
            need(f['Input'] == 'audio only', f'I input {n}')
            row['semantic'] = {'start_bar': first, 'end_bar': last, 'section_label': f['Section'],
                               'input': f['Input'], 'student_task': f['Student task'],
                               'observed_harmony': None, 'observed_groove': None, 'performance_result': None}
        elif page == 19:
            row['semantic'] = {'category': f['Category'], 'anchors': {str(score): f[str(score)] for score in range(3)},
                               'awarded_score': None}


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
    need(len(lines) == 43 and len(pages) == 19, 'TXT/PDF extent')
    need(lines[0] == 'GUITAR EXERCISES - SECTION XIV, LEVEL 97' and pages[0][0] == 'Guitar Exercises - Section XIV, Level 97', 'Level/section identity')
    need(one_line(lines, 'COMPLETE WRITTEN WORKLOAD: 1424 events') == 10, 'TXT total declaration')
    mapped = next((r for r in source_map['rows'] if r.get('level') == 97), None)
    need(mapped is not None and mapped['section'] == 'XIV' and mapped['wbs_owner'] == '2.3.1.3.1' and mapped['pair_status'] == 'exact_stem_pair' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'converted_candidate_reference' and mapped['stable_ids_assigned'] and mapped['representative_item_id'] == 'fg:item:000012' and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map representative status')
    need(all(mapped[f'{key}_path'] == spec[0] and mapped[f'{key}_bytes'] == spec[1] and mapped[f'{key}_sha256'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair')
    need(pages[0][6:9] == ['Module', 'Exercise', 'Events'], 'PDF overview heading')
    modules: dict[str, dict[str, Any]] = {}
    for index, key in enumerate(KEYS):
        pdf_key, name, count = pages[0][9 + index * 3:12 + index * 3]
        need(pdf_key == key and int(count) == EVENTS[index], f'PDF overview {key}')
        matches = [(n, line) for n, line in enumerate(lines, 1) if line.startswith(f'{key}. ') and line.endswith(f' - {count} events')]
        need(len(matches) == 1 and matches[0][1][3:].rsplit(' - ', 1)[0].casefold() == name.casefold(), f'TXT/PDF overview {key}')
        modules[key] = {'name': name, 'declared_events': EVENTS[index], 'txt_ref': f'L97-TXT-L{matches[0][0]}',
                        'pdf_overview_ref': f'L97-PDF-p1-L{10 + index * 3}-{12 + index * 3}',
                        'pdf_pages': list(MODULE_PAGES[key]), 'tables': [], 'per_task_event_allocation': None}
    need(pages[0][39:41] == ['TOTAL', '1424'] and sum(EVENTS) == 1424, 'PDF/TXT workload total')
    parsed = {}
    page_parts = {}
    for page in SPECS:
        rows, intro, closing = table(pages[page - 1], page)
        annotate(page, rows)
        parsed[page], page_parts[page] = rows, {'intro': intro, 'closing': closing}
    need([r['semantic']['pass'] for r in parsed[2]] == list(range(1, 8)), 'seven listening passes')
    need(parsed[2][0]['semantic']['defer'] == 'exact chords' and parsed[2][-1]['semantic']['defer'] == 'micro-details', 'listening priority bounds')
    for key in KEYS:
        modules[key]['tables'] = [{'page': page, 'columns': list(SPECS[page][0]), 'rows': parsed[page],
                                    'page_intro': page_parts[page]['intro'], 'page_closing': page_parts[page]['closing']}
                                   for page in MODULE_PAGES[key]]
    need('No guitar during Pass 1. Tap, count, and write only.' in page_parts[3]['closing'], 'A no-guitar Pass 1')
    need('Label each discovered detail S = structural, C = color, O = optional.' in page_parts[11]['closing'][0], 'E S/C/O legend')
    need([r['fields']['Version'] for r in parsed[12]] == ['Skeleton', 'Functional', 'Identity', 'Performance', 'Reduced', 'Emergency'], 'F six versions')
    need('50% fewer fills/ornaments' == parsed[12][4]['fields']['Contains'], 'F reduced fallback')
    need([r['semantic']['score'] for r in parsed[15]] == [0, 1, 2, 3], 'G divergence scale')
    need(all(name in page_parts[15]['closing'][0] for name in DIVERGENCE_CATEGORIES), 'G seven divergence domains')
    studies = []
    for page in (16, 17):
        intro = page_parts[page]['intro']
        need(len(intro) == 3 and intro[1].startswith('16 bars. No chart.') and intro[2].startswith('Reconstruct '), f'H study brief {page}')
        studies.append({'ordinal': page - 15, 'pdf_ref': f'L97-PDF-p{page}-L1-3', 'brief': intro[1],
                        'reconstruction_goal': intro[2], 'passes': parsed[page], 'audio_supplied': False,
                        'observed_form': None, 'observed_harmony': None, 'performed_study': None})
    need(studies[0]['brief'] != studies[1]['brief'] and 'bar 9' in studies[0]['brief'] and 'secondary dominant' in studies[1]['brief'], 'H distinct briefs')
    blocks = parsed[18]
    need([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in blocks] == [(1, 4), (5, 12), (13, 16), (17, 24), (25, 32), (33, 40), (41, 44), (45, 48)], 'I complete 48-bar section form')
    need([r['semantic']['section_label'] for r in blocks] == ['Intro', 'A', 'B', "A'", 'C', 'Solo/support', 'Return', 'Outro'], 'I section labels')
    capstone_closing = ' '.join(page_parts[18]['closing'])
    need('unfamiliar 48-bar recording or self/partner-created source' in capstone_closing and 'No chord chart.' in capstone_closing and all(item in capstone_closing for item in CAPSTONE_DELIVERABLES), 'I source and seven outputs')
    rubric = parsed[19]
    need([r['semantic']['category'] for r in rubric] == RUBRIC_CATEGORIES, 'J eight scoring categories')
    passing = page_parts[19]['closing'][0]
    need(passing == 'Pass Level 97: 14/16 or better on two separate unfamiliar excerpts, with no zero in form, bass/function, groove, or recovery.', 'J passing gate')
    need(one_line(lines, '14/16 or better on two separate unfamiliar excerpts.') == 39 and one_line(lines, 'No zero in form, bass/function, groove, or recovery.') == 40, 'TXT mastery gate')
    capstone_txt = one_line(lines, '48-bar unfamiliar recording with no chord chart. Produce a one-page map, functional arrangement, reduced fallback, and uninterrupted performance.')
    source = {key: {'path': spec[0], 'bytes': spec[1], 'sha256': spec[2]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level097.detached-source-task-candidate.1', 'wbs': '2.3.1.3.1', 'level': 97, 'section': 'XIV',
            'status': 'non_admitted', 'admitted': False, 'canonical_id': None, 'exercise_id': None,
            'existing_representative_item_id_read_only': mapped['representative_item_id'],
            'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None,
            'sounding_midi_events': None, 'performed_event_count': None, 'rubric_outcome': None,
            'source': source, 'source_map_row': mapped, 'txt_full_lines': lines, 'pdf_full_extracted_pages': pages,
            'reference_listening_passes': parsed[2], 'reference_page_intro': page_parts[2]['intro'],
            'reference_page_closing': page_parts[2]['closing'], 'modules': modules,
            'declared_workload_total': 1424, 'declared_workload_by_module': dict(zip(KEYS, EVENTS)),
            'studies': studies,
            'capstone': {'txt_ref': f'L97-TXT-L{capstone_txt}', 'pdf_ref': 'L97-PDF-p18', 'section_blocks': blocks,
                         'printed_bars': 48, 'source_options': ['unfamiliar recording', 'self/partner-created source'],
                         'chord_chart_allowed': False, 'required_deliverables': CAPSTONE_DELIVERABLES,
                         'source_audio_supplied': False, 'observed_chords': None, 'observed_riffs': None, 'performed_take': None,
                         'raw_closing': capstone_closing},
            'mastery': {'txt_refs': ['L97-TXT-L39', 'L97-TXT-L40'], 'pdf_ref': 'L97-PDF-p19',
                        'rubric': rubric, 'required_score': 14, 'maximum_score': 16,
                        'unfamiliar_excerpt_count': 2, 'no_zero_categories': ['Form', 'Bass/function', 'Groove', 'Recovery'],
                        'raw_passing': passing, 'observed_scores': None},
            'source_ambiguities': [
                {'kind': 'PDF_only_task_expansion', 'status': 'pending_curriculum_review', 'detail': 'TXT lists the modules/workloads and capstone but omits the detailed PDF task rows.'},
                {'kind': 'audio_not_supplied', 'status': 'pending_source_selection', 'detail': 'The PDF supplies two audio briefs and allows an unfamiliar or self/partner-created 48-bar capstone source, but the pinned TXT/PDF pair contains no playable recording or observed musical findings.'},
                {'kind': 'workload_without_printed_note_events', 'status': 'pending_curriculum_review', 'detail': 'The 1424 events are declared workload, not 1424 printed pitches/onsets; task rows have no event allocation.'},
                {'kind': 'representative_scope_is_selected_case_only', 'status': 'pending_whole_workbook_review', 'detail': 'The source map identifies existing representative fg:item:000012. This detached whole-source output does not inherit that identity or prove whole-workbook completion or admission.'},
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
