from pathlib import Path
import datetime, hashlib, json, resource, sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Tools/fullscope-private-c-r01'))
from rhythm_vocabulary_contract_r21 import RhythmVocabularySession
checks = 0


def ck(v, label):
    global checks
    checks += 1
    if not v:
        raise AssertionError(label)


def refuse(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


packet = ROOT / 'Build/fullscope-private-c-r01/level076-r21/rhythm-vocabulary-overlays.jsonl'
rows = [json.loads(s) for s in packet.read_text().splitlines()]
catalogue_path = ROOT / 'Build/fullscope-private-c-r01/level076-r21/rhythm-vocabulary-source.json'
cat = json.loads(catalogue_path.read_text())
names = [cell['name'] for cell in cat['cells']]
ck(len(rows) == len(names) == len(set(names)) == len({r['package_key'] for r in rows}) == 16, 'sixteen exact child/cell identities')
for i, r in enumerate(rows):
    c = r['implementation']['task']['contract']
    cell = c['source_cell']
    ck(cell == cat['cells'][i], 'per-child exact ordered cell')
    for ref in [c['source_catalogue_ref'], c['state_engine_ref'], *r['source_refs']]:
        ck(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest() == ref['sha256'], 'source/catalogue/engine pin')
    txtref = next(x for x in r['source_refs'] if x['path'].endswith('.txt'))
    txtline = (ROOT/txtref['path']).read_text().splitlines()[cell['original_txt_line']-1]
    ck(txtline == cell['name']+': '+cell['rhythm_string'], 'original exact TXT cell')
    ck(''.join(v['character'] for v in cell['literal_characters']) == cell['rhythm_string'], 'spaces/ties/literal order exact')
    s = RhythmVocabularySession(c, cat)
    ck(s.learner_view()['source_cell'] == cell, 'initial study source visible')
    ck(refuse(s.hide_for_memory), 'basic practice before memory')
    ck(refuse(lambda: s.submit_memory('synthetic')), 'reference hidden before memory response')
    ck(refuse(lambda: s.report_basic_step('speak_grid', 'synthetic')), 'clap before speak')
    for step in s.basic_order:
        s.report_basic_step(step, 'Synthetic manual '+step)
    ck(refuse(lambda: s.report_basic_step('play_one_muted_string', 'synthetic')), 'cannot overwrite practice reports')
    s.hide_for_memory()
    ck(s.learner_view()['source_cell'] is None, 'source actually hidden during memory response')
    ck(refuse(s.reveal_memory_comparison), 'own written answer before comparison')
    s.submit_memory('Synthetic uncertain memory grid')
    ck(s.learner_view()['source_cell'] is None, 'answer submission does not auto-show reference')
    ck(s.reveal_memory_comparison()['source_cell'] == cell, 'comparison reveals exact original')
    ck(refuse(lambda: s.begin_variation([names[i]], 'synthetic', 'synthetic')), 'two selections required')
    ck(refuse(lambda: s.begin_variation([names[i], 'foreign'], 'synthetic', 'synthetic')), 'original catalogue only')
    pair_names = [names[i], names[(i+1)%16]]
    s.begin_variation(pair_names, 'Synthetic external player', 'Synthetic manual realization; no app audio')
    pair_names[0] = 'mutation'
    view = s.source_player_variation_view()
    ck([x['name'] for x in view['ordered_cell_segments']] == [names[i], names[(i+1)%16]] and view['repeat_complete_pair_count'] == 4, 'ordered cell segments and four complete-pair repeats')
    view['ordered_cell_segments'][0]['rhythm_string'] = 'mutation'
    ck(s.source_player_variation_view()['ordered_cell_segments'][0]['rhythm_string'] == cell['rhythm_string'], 'source view detached')
    ck(s.learner_view()['variation_reference_segments'] is None, 'learner chosen-source pair hidden initially')
    ck(refuse(lambda: s.report_variation_repeat(True, 'synthetic')), 'repeat bool refused')
    ck(refuse(lambda: s.report_variation_repeat(2, 'synthetic')), 'repeat order')
    for n in range(1, 5):
        ck(refuse(lambda: s.submit_variation_layer('attacks', 'synthetic')), 'all four renditions before transcription')
        s.report_variation_repeat(n, 'Synthetic complete-pair rendition')
    ck(refuse(lambda: s.report_variation_repeat(5, 'synthetic')), 'no invented fifth required repeat')
    ck(refuse(lambda: s.submit_variation_layer('rests_ties', 'synthetic')), 'attacks first')
    s.submit_variation_layer('attacks', 'Synthetic contacts including uncertainty')
    ck(refuse(lambda: s.submit_variation_layer('accents', 'synthetic')), 'rests/ties before accents')
    s.submit_variation_layer('rests_ties', 'Synthetic rest/tie report')
    ck(refuse(s.reveal_variation_reference), 'complete layered transcription before pair disclosure')
    s.submit_variation_layer('accents', 'uncertain; source accents not established')
    ck([x['name'] for x in s.reveal_variation_reference()['variation_reference_segments']] == [names[i], names[(i+1)%16]], 'full chosen pair reference after all three responses')
    ck(refuse(lambda: s.begin_variation([names[0], names[1]], 'other', 'other')), 'no silent source pair replacement')
    before = s.snapshot()
    s.cancel()
    ck(refuse(s.learner_view) and refuse(lambda: s.restart_variation('synthetic')), 'cancel guards')
    s.reopen()
    ck(s.snapshot() == before, 'cancel/reopen retains responses/script/history')
    s.restart_basic('Synthetic deliberate memory revision')
    ck(s.snapshot()['history'][-1]['prior_memory_answer'] == before['memory_answer'] and s.learner_view()['prior_memory_comparison_disclosure'], 'memory history and prior reference retained')
    s.restart_variation('Synthetic new pair pass')
    ck(s.snapshot()['history'][-1]['ordered_pair'] == before['ordered_pair'] and s.learner_view()['prior_variation_reference_disclosure'], 'variation history/disclosure retained')
    ck(s.learner_view()['variation_reference_segments'] is None and not s.snapshot()['repeat_reports'], 'new pass does not reuse old performance reports')
    ck(not any(s.snapshot()[k] for k in ['performance_observed', 'app_audio_supplied', 'Attempt_credit', 'mastery_awarded']), 'no acoustic/audio/credit claims')

special = RhythmVocabularySession(rows[0]['implementation']['task']['contract'], cat)
special.begin_variation(['5/4 3+2', '7/8 2+2+3'], 'Synthetic mixed-meter source player', 'Synthetic source-realized meter changes, not converted native timing')
ck([x['rhythm_string'] for x in special.source_player_variation_view()['ordered_cell_segments']] == ['P--P--P-P-', 'P-P-P--'] and not special.source_player_variation_view()['timing_conversion_performed'], 'mixed-meter source boundary preserved without one-grid normalization')
dest = ROOT / 'Results/fullscope-private-c-r01/level076-r21/integrity.json'
ck(not dest.exists(), 'immutable result')
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'result': 'PASS', 'checks': checks,
          'complete_manual_contracts': 16, 'new_category_promotions': 16,
          'packet_sha256': hashlib.sha256(packet.read_bytes()).hexdigest(),
          'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
          'all_responses_performances_and_variations_synthetic': True, 'native_app_gui': 'NOT_RUN'}
dest.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
