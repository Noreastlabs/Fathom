#!/usr/bin/env python3
"""Build a pinned, detached whole-Level105 final-exam task candidate."""
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
BUILD = Path('Build/parallel-11/2.3.1.3.1-level105-whole-r01')
STEM = 'Guitar_Exercises_Level_105_Final_Musicianship_Capstone_Complete_105_Level_Core_Curriculum'
TXT = (f'Notes/music/guitar project/TXT version/{STEM}.txt', 1857, '793cf5eab18d4501b7b1d7317caeb89b91719e4b71d7cadff9f905afb4a56bf5')
PDF = (f'Notes/music/guitar project/PDF version/{STEM}.pdf', 43264, 'e8642650a58154eb0ec2985e05ea2a48bdd417d4d5fc1ac4cd08591d13538a5b')
MAP = ('Results/parallel-01/exercises/inventory/20260922T180500Z-2.3-curriculum-v1-source-inventory-evidence/curriculum-source-map.json', 199753, 'bad5581a04f43ba8baf14db430449e1ccff5cf88f0f7e42198328073b27053d6')
KEYS = tuple('ABCDEFGHIJ')
EVENTS = (160, 160, 160, 160, 160, 160, 144, 160, 128, 480)
MODULE_PAGES = {'A': (4, 5), 'B': (6, 7), 'C': (8, 9), 'D': (10, 11), 'E': (12, 13),
                'F': (14,), 'G': (15,), 'H': (16, 17), 'I': (18, 19),
                'J': (20, 21, 22, 23, 24, 25, 26, 27, 28)}
SPECS = {
    2: (('Domain', 'Not merely...', 'But whether you can...'), 9),
    3: (('Rule', 'Standard'), 8),
    4: (('Station', 'Task'), 8),
    5: (('Prompt', 'Time limit'), 8),
    6: (('Station', 'Task'), 8),
    8: (('Groove engine', 'Required behavior'), 8),
    9: (('Bars', 'Command'), 8),
    10: (('Pass', 'Listen for'), 7),
    11: (('Item', 'Required'), 8),
    12: (('Station', 'Task'), 8),
    13: (('Bars', 'Intensity', 'Allowed focus'), 5),
    14: (('Task', 'Requirement'), 8),
    15: (('Scenario', 'Create guitar role'), 8),
    16: (('Station', 'Task'), 8),
    17: (('Cue', 'Action'), 8),
    18: (('Injected failure', 'Required response'), 8),
    19: (('Prompt', 'Time limit'), 8),
    20: (('Block', 'Minutes', 'Task'), 8),
    21: (('Minute', 'Task'), 4), 22: (('Minute', 'Task'), 4),
    23: (('Minute', 'Task'), 4), 24: (('Minute', 'Task'), 4),
    25: (('Minute', 'Task'), 4), 26: (('Minute', 'Task'), 4),
    27: (('Minute', 'Task'), 3),
    29: (('Domain', '0', '1', '2', '3'), 10),
    30: (('Outcome', 'Requirement'), 6),
    31: (('Weak domain', 'Return to'), 9),
    32: (('From', 'To'), 12),
    33: (('Track', 'Possible focus'), 10),
}
RUBRIC_DOMAINS = ['Technique/fretboard', 'Harmony/voicing', 'Rhythm/groove', 'Ear/transcription', 'Improvisation',
                  'Repertoire', 'Arrangement', 'Composition', 'Recovery', 'Performance']
NO_ZERO = ['Rhythm/Groove', 'Ear/Transcription', 'Recovery', 'Performance']
SCHEDULE = [(0, 8), (8, 16), (16, 24), (24, 32), (32, 40), (40, 48), (48, 56), (56, 60)]
DETAIL_COUNTS = {21: 4, 22: 4, 23: 4, 24: 4, 25: 4, 26: 4, 27: 3}


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
    matches = [n for n, line in enumerate(lines, 1) if line == value]
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
        if columns[0] in ('Station', 'Pass', 'Block'):
            need(fields[0] == str(n + 1), f'PDF page {page} ordinal {n + 1}')
        rows.append({'ordinal': n + 1, 'fields': dict(zip(columns, fields)), 'raw_fields': fields,
                     'pdf_ref': f'L105-PDF-p{page}-L{offset + 1}-{offset + len(columns)}',
                     'declared_events_for_row': None, 'performed_result': None})
    return rows, lines[:start], lines[end:]


def interval(raw: str, label: str) -> tuple[int, int]:
    match = re.fullmatch(r'(\d+)-(\d+)', raw)
    need(match is not None, f'{label} range: {raw}')
    start, stop = map(int, match.groups())
    need(start < stop, f'{label} duration: {raw}')
    return start, stop


def annotate(page: int, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        f, n = row['fields'], row['ordinal']
        if page == 2:
            row['semantic'] = {'domain': f['Domain'], 'mere_skill': f['Not merely...'], 'integrated_ability': f['But whether you can...'], 'observed_ability': None}
        elif page == 3:
            row['semantic'] = {'rule': f['Rule'], 'standard': f['Standard'], 'observed_compliance': None}
        elif page in (4, 6, 12, 16):
            row['semantic'] = {'station': n, 'task': f['Task'], 'performed': None}
        elif page in (5, 19):
            seconds = re.fullmatch(r'(5|8) sec', f['Time limit'])
            need(seconds is not None, f'PDF page {page} reaction limit {n}')
            row['semantic'] = {'prompt': f['Prompt'], 'time_limit_seconds': int(seconds.group(1)),
                               'observed_latency_seconds': None, 'answer': None}
        elif page == 8:
            row['semantic'] = {'groove_engine': f['Groove engine'], 'required_behavior': f['Required behavior'],
                               'performed_groove': None}
        elif page == 9:
            start, stop = interval(f['Bars'], 'C groove switch bars')
            row['semantic'] = {'start_bar': start, 'end_bar': stop, 'command': f['Command'], 'performed_switch': None}
        elif page == 10:
            row['semantic'] = {'pass': n, 'listen_for': f['Listen for'], 'heard_result': None}
        elif page == 11:
            row['semantic'] = {'deliverable': f['Item'], 'required_content': f['Required'], 'submitted_content': None}
        elif page == 13:
            bars = f['Bars']
            if '-' in bars:
                start, stop = interval(bars, 'E expression bars')
            else:
                need(bars.isdigit(), 'E single bar')
                start = stop = int(bars)
            row['semantic'] = {'start_bar': start, 'end_bar': stop, 'intensity_raw': f['Intensity'],
                               'allowed_focus': f['Allowed focus'], 'performed_arc': None}
        elif page == 14:
            row['semantic'] = {'repertoire_task': f['Task'], 'requirement': f['Requirement'], 'performed_version': None}
        elif page == 15:
            row['semantic'] = {'ensemble_scenario': f['Scenario'], 'required_guitar_role': f['Create guitar role'], 'created_role': None}
        elif page == 17:
            row['semantic'] = {'random_cue': f['Cue'], 'required_action': f['Action'], 'observed_response': None}
        elif page == 18:
            row['semantic'] = {'injected_failure': f['Injected failure'], 'required_response': f['Required response'], 'observed_recovery': None}
        elif page == 20:
            start, stop = interval(f['Minutes'], 'J exam block minutes')
            row['semantic'] = {'block': n, 'start_minute': start, 'end_minute': stop,
                               'scheduled_task': f['Task'], 'actual_start': None, 'actual_end': None, 'performed': None}
        elif 21 <= page <= 27:
            start, stop = interval(f['Minute'], f'J detailed block {page - 20}')
            row['semantic'] = {'block': page - 20, 'start_minute': start, 'end_minute': stop,
                               'task': f['Task'], 'actual_start': None, 'actual_end': None, 'performed': None}
        elif page == 29:
            row['semantic'] = {'domain': f['Domain'], 'anchors': {str(score): f[str(score)] for score in range(4)}, 'awarded_score': None}
        elif page == 30:
            row['semantic'] = {'outcome': f['Outcome'], 'requirement': f['Requirement'], 'satisfied': None}
        elif page == 31:
            row['semantic'] = {'weak_domain': f['Weak domain'], 'return_to': f['Return to'], 'remediation_taken': None}
        elif page == 32:
            row['semantic'] = {'from': f['From'], 'to': f['To'], 'observed_milestone': None}
        elif page == 33:
            row['semantic'] = {'specialization_track': f['Track'], 'possible_focus': f['Possible focus'], 'chosen': None}


def special_top_notes(lines: list[str]) -> dict[str, Any]:
    need(lines[:2] == ['Module B - Fixed Melody Reharmonization', 'Top note'] and lines[2] == 'Create at least three supporting harmonies', 'B fixed melody heading')
    notes = lines[3:9]
    need(notes == ['E', 'G', 'C', 'F#', 'Bb', 'A'], 'B six fixed top notes')
    closing = lines[9:]
    need(closing == ['For each top note: state chord function, bass direction, and whether the note acts as chord tone, extension, or controlled tension.'], 'B harmonic explanation')
    return {'pdf_ref': 'L105-PDF-p7', 'required_supporting_harmonies_per_note': 3,
            'top_notes': [{'ordinal': n, 'top_note': note, 'pdf_ref': f'L105-PDF-p7-L{n + 3}',
                           'supporting_harmonies': None, 'stated_chord_function': None,
                           'stated_bass_direction': None, 'note_role': None} for n, note in enumerate(notes, 1)],
            'role_options': ['chord tone', 'extension', 'controlled tension'], 'instruction': closing[0]}


def special_reflection(lines: list[str]) -> dict[str, Any]:
    need(lines[:2] == ['Final Examination - Block 8: Reflection and Final Declaration', 'Question'] and lines[2] == 'Answer in one sentence', 'J reflection heading')
    questions = lines[3:9]
    need(len(questions) == 6 and all(q.endswith('?') for q in questions), 'J six reflection questions')
    need(len(lines) == 10 and lines[9].startswith('The core curriculum ends with self-directed musicianship.'), 'J reflection close')
    return {'pdf_ref': 'L105-PDF-p28', 'answer_format': 'one sentence',
            'questions': [{'ordinal': n, 'question': q, 'answer': None, 'pdf_ref': f'L105-PDF-p28-L{n + 3}'} for n, q in enumerate(questions, 1)],
            'closing': lines[9]}


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
    need(len(lines) == 61 and len(pages) == 34, 'TXT/PDF extent')
    need(lines[0] == 'GUITAR EXERCISES - LEVEL 105' and pages[0][0] == 'Guitar Exercises - Level 105', 'level identity')
    need(one_line(lines, 'COMPLETE WRITTEN WORKLOAD: 1872 events') == 12, 'TXT workload total')
    need(one_line(lines, 'THERE IS NO LEVEL 106 IN THE UNIVERSAL CORE CURRICULUM.') == 7 and one_line(lines, 'THE UNIVERSAL 105-LEVEL CURRICULUM ENDS HERE.') == 61, 'TXT hard stop')
    mapped = next((row for row in source_map['rows'] if row.get('level') == 105), None)
    need(mapped is not None and mapped['section'] == 'Final' and mapped['wbs_owner'] == '2.3.1.3.1' and mapped['pair_status'] == 'exact_stem_pair' and mapped['review'] == 'Pending' and mapped['conversion_status'] == 'converted_candidate_reference' and mapped['stable_ids_assigned'] and mapped['representative_item_id'] == 'fg:item:000013' and not mapped['runtime_eligible'] and not mapped['imported'] and not mapped['admitted'], 'source-map representative status')
    need(all(mapped[f'{key}_path'] == spec[0] and mapped[f'{key}_bytes'] == spec[1] and mapped[f'{key}_sha256'] == spec[2] for key, spec in (('txt', TXT), ('pdf', PDF))), 'source-map pair')
    need(pages[0][6:9] == ['Module', 'Examination area', 'Events'], 'PDF overview heading')
    modules: dict[str, dict[str, Any]] = {}
    for index, key in enumerate(KEYS):
        pdf_key, name, count = pages[0][9 + index * 3:12 + index * 3]
        need(pdf_key == key and int(count) == EVENTS[index], f'PDF overview {key}')
        matches = [(n, line) for n, line in enumerate(lines, 1) if line.startswith(f'{key}. ') and line.endswith(f' - {count} events')]
        need(len(matches) == 1 and matches[0][1][3:].rsplit(' - ', 1)[0].casefold() == name.casefold(), f'TXT/PDF overview {key}')
        modules[key] = {'name': name, 'declared_events': EVENTS[index], 'txt_ref': f'L105-TXT-L{matches[0][0]}',
                        'pdf_overview_ref': f'L105-PDF-p1-L{10 + index * 3}-{12 + index * 3}',
                        'pdf_pages': list(MODULE_PAGES[key]), 'tables': [], 'per_task_event_allocation': None}
    need(pages[0][39:41] == ['TOTAL', '1872'] and sum(EVENTS) == 1872, 'PDF/TXT workload total')
    parsed = {}
    parts = {}
    for page in SPECS:
        rows, intro, closing = table(pages[page - 1], page)
        annotate(page, rows)
        parsed[page], parts[page] = rows, {'intro': intro, 'closing': closing}
    fixed_melody = special_top_notes(pages[6])
    reflection = special_reflection(pages[27])
    for key in KEYS:
        modules[key]['tables'] = [{'page': page, 'columns': list(SPECS[page][0]), 'rows': parsed[page],
                                    'page_intro': parts[page]['intro'], 'page_closing': parts[page]['closing']}
                                   for page in MODULE_PAGES[key] if page in SPECS]
    modules['B']['fixed_melody_reharmonization'] = fixed_melody
    modules['J']['reflection'] = reflection
    need([r['semantic']['start_bar'] for r in parsed[9]] == list(range(1, 16, 2)) and [r['semantic']['end_bar'] for r in parsed[9]] == list(range(2, 17, 2)), 'C 16-bar switching')
    need([(r['semantic']['start_bar'], r['semantic']['end_bar']) for r in parsed[13]] == [(1, 2), (3, 4), (5, 6), (7, 7), (8, 8)], 'E expression arc')
    schedule = parsed[20]
    need([(r['semantic']['start_minute'], r['semantic']['end_minute']) for r in schedule] == SCHEDULE, 'J 60-minute schedule')
    txt_schedule = lines[lines.index('FINAL 60-MINUTE EXAM') + 1:lines.index('FINAL SCORING')]
    txt_schedule = [line for line in txt_schedule if line]
    need(len(txt_schedule) == 8 and all(re.match(rf'^{start}-{stop}\s+', line) and schedule[i]['fields']['Task'] == re.sub(r'^\d+-\d+\s+', '', line) for i, ((start, stop), line) in enumerate(zip(SCHEDULE, txt_schedule))), 'J TXT/PDF schedule parity')
    detailed = []
    for page, count in DETAIL_COUNTS.items():
        rows = parsed[page]
        need(len(rows) == count, f'J detailed count {page}')
        windows = [(r['semantic']['start_minute'], r['semantic']['end_minute']) for r in rows]
        need(windows[0][0] == SCHEDULE[page - 21][0] and windows[-1][1] == SCHEDULE[page - 21][1] and all(a[1] == b[0] for a, b in zip(windows, windows[1:])), f'J detailed minute parity {page}')
        detailed.append({'block': page - 20, 'pdf_ref': f'L105-PDF-p{page}', 'rows': rows, 'closing': parts[page]['closing']})
    need(reflection['questions'] and SCHEDULE[-1] == (56, 60), 'J block 8 reflection')
    rubric = parsed[29]
    need([r['semantic']['domain'] for r in rubric] == RUBRIC_DOMAINS and parts[29]['closing'] == ['Maximum: 30 points.'], 'ten-domain 30-point rubric')
    graduation = parsed[30]
    need([r['fields']['Outcome'] for r in graduation] == ['CORE COMPLETE', 'No-zero rule', 'Performance rule', 'Original-work rule', 'Repertoire rule', 'Repeatability rule'], 'six graduation requirements')
    need(graduation[0]['fields']['Requirement'] == '24/30 or better' and all(name in graduation[1]['fields']['Requirement'] for name in NO_ZERO), 'score/no-zero gate')
    repeatability = graduation[-1]['fields']['Requirement']
    need(repeatability == 'Pass on two separate days OR pass once with an independent listener/reviewer scoring 24+', 'repeatability alternatives')
    need(one_line(lines, '24/30 or better.') and one_line(lines, '- complete final session') and one_line(lines, '- one finished original') and one_line(lines, '- one complete adapted repertoire piece'), 'TXT graduation obligations')
    need([r['fields']['Weak domain'] for r in parsed[31]][-1] == 'Recovery/performance' and len(parsed[32]) == 12 and len(parsed[33]) == 10, 'remediation/completion/specialization extents')
    need('There is no Level 106.' in pages[31] and pages[33][0] == 'FINAL HARD STOP' and any(row.startswith('These are not Levels 106+.') for row in pages[32]), 'PDF no-Level106 hard stop')
    need('The 105-level universal guitar curriculum is complete.' in pages[33], 'PDF final declaration')
    source = {key: {'path': spec[0], 'bytes': spec[1], 'sha256': spec[2]} for key, spec in (('txt', TXT), ('pdf', PDF), ('source_map', MAP))}
    return {'schema': 'fathom.level105.detached-source-task-candidate.1', 'wbs': '2.3.1.3.1', 'level': 105,
            'status': 'non_admitted', 'admitted': False, 'core_complete': None, 'graduated': None,
            'canonical_id': None, 'exercise_id': None, 'existing_representative_item_id_read_only': mapped['representative_item_id'],
            'onset_q': None, 'duration_q': None, 'fixed_bpm': None, 'executable_events': None,
            'sounding_midi_events': None, 'performed_event_count': None, 'rubric_outcome': None,
            'source': source, 'source_map_row': mapped, 'txt_full_lines': lines, 'pdf_full_extracted_pages': pages,
            'foundations': {'domain_tests': parsed[2], 'exam_rules': parsed[3], 'pdf_refs': ['L105-PDF-p2', 'L105-PDF-p3']},
            'modules': modules, 'declared_workload_total': 1872, 'declared_workload_by_module': dict(zip(KEYS, EVENTS)),
            'final_exam': {'schedule': schedule, 'detailed_blocks_1_to_7': detailed, 'block_8_reflection': reflection,
                           'scheduled_minutes': 60, 'minute_windows_are_musical_onsets': False,
                           'actual_duration_minutes': None, 'performed_session': None},
            'graduation': {'rubric': rubric, 'maximum_score': 30, 'required_score': 24,
                           'no_zero_domains': NO_ZERO, 'requirements': graduation,
                           'repeatability_alternatives': ['two separate days', 'one passing session with independent listener/reviewer scoring 24+'],
                           'recorded_scores': None, 'recorded_reviewer': None,
                           'conditional_rules_ref': 'L105-PDF-p30'},
            'remediation': parsed[31], 'core_path_transformations': parsed[32], 'post_core_tracks': parsed[33],
            'hard_stop': {'maximum_core_level': 105, 'level_106_exists': False,
                          'txt_refs': ['L105-TXT-L5-7', 'L105-TXT-L53-61'],
                          'pdf_refs': ['L105-PDF-p1', 'L105-PDF-p3', 'L105-PDF-p30', 'L105-PDF-p32-34'],
                          'post_core_is_specialization': True},
            'source_ambiguities': [
                {'kind': 'PDF_only_exam_expansion', 'status': 'pending_curriculum_review', 'detail': 'TXT summarizes the examination, while PDF pages 2-33 give detailed stations, sub-blocks, scoring, returns and specialization.'},
                {'kind': 'workload_without_printed_note_events', 'status': 'pending_curriculum_review', 'detail': 'The 1872 declared events are not 1872 printed attack pitches/onsets and have no per-task allocation.'},
                {'kind': 'exam_minute_windows_not_event_timing', 'status': 'source_instruction_only', 'detail': 'The 60-minute plan is a flexible session schedule; PDF p20 says minute counts may shift slightly. It does not define musical note timing.'},
                {'kind': 'block7_condensed_core_vs_finished_original', 'status': 'pending_curriculum_review', 'detail': 'PDF p27 allows a complete original or condensed core version in Block 7, while PDF p30 requires one finished original for graduation. A condensed excerpt alone cannot be assumed to satisfy the graduation rule.'},
                {'kind': 'unperformed_prompts_and_reflection', 'status': 'pending_learner_evidence', 'detail': 'PDF p7 fixed top notes, p28 reflection questions and the many timed/station tasks print prompts, not learner answers, audio or reviewer scores.'},
                {'kind': 'representative_scope_is_selected_case_only', 'status': 'pending_whole_workbook_review', 'detail': 'Frozen representative fg:item:000013 is an existing selected final-exam task reference; this whole-source projection does not inherit its identity or establish completion.'},
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
