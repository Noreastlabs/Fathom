#!/usr/bin/env python3
"""Build/verify the P68 immutable Level17 pair timing projection repair."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

import parallel65_level017_first_batch as p65

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('Build/parallel-68/level017-source-event-time-repair-r01')
OLD = Path('Build/parallel-65/controlled-open-level017-first-batch-r01')
DIAG = Path('Build/parallel-67/level017-first-source-review-r01/frozen-final-r01/diagnostic-source-event-time-package.json')
PINS = {
    Path('Tools/parallel65_level017_first_batch.py'):'d44c54424092fa06413945e43e9f474d2ddb3c08739f139ea00917e4d81e72f4',
    OLD/'package.json':'119fd781cf094113ea8759ae810043d1adbe205da57ad957267766f390440bf0',
    OLD/'source-provenance.json':'0809946d8dc0af6417d304eebf9c3d72883dcd31cfbef5707593bff7ec125a7e',
    OLD/'expected-profile.json':'7d26a7c19ab71334be6893faa4d243bf31064ab82c1f11745577eb3843772329',
    OLD/'native-report-r01.json':'8a0874d8344859f99acf97d3f59e1517831d9049265108fda80606cb59c717b2',
    OLD/'negative-checks.json':'4cbb0f374eb369544a77f608b74f4419c87e48c8f6ccec555da489447eeb5239',
    Path('Results/parallel-65/controlled-open-level017-first-batch-r01/20260924T090700Z-2.3.1.1.1-level017-first-batch-source-r01-results.md'):'27b203a1232bd7eb7e58e963771d5b56d65fe4058bb3dd830b6e01aa699bb9d5',
    Path('Results/parallel-67/level017-first-source-review-r01/20260924T091600Z-2.3.1.1.1-level017-frozen-source-native-final-r01-results.md'):'479520ecf94477b893d05aa0da986c00c64e6a98f0c4106948746215794e9107',
    DIAG:'bb30d460a3cef81b20ee5f162dfa5c0050effb05ade43dad63623a9c710176a2',
    Path('Notes/music/guitar project/TXT version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.txt'):'e742548015d297941c9972ddb7cfcaeb0a66375b164864698e72d3e0b6bed511',
    Path('Notes/music/guitar project/PDF version/Scale_Exercises_Section_II_Level_17_Major_Scale_Four_Note_Rolling_Sequence_Two_Octave_Six_String_Neck_Ladder.pdf'):'fc60d519a880c3d6a8a4984d99dd07030fcb56d09f1e2ea9ad951da271349d6d',
}
NAMES=('package.json','expected-profile.json','identity-registry.json','source-provenance.json','repair-comparison.json')
PAIR_IDS=('fg:variant:007444','fg:variant:007445')

def require(ok,code):
    if not ok: raise ValueError(code)
def encode(value): return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads((ROOT/path).read_bytes())

def pin_inputs():
    require(ROOT.resolve()==Path(subprocess.check_output(['git','-C',str(ROOT),'rev-parse','--show-toplevel'],text=True).strip()).resolve(),'ROOT_DRIFT')
    for path,expected in PINS.items():
        require(digest((ROOT/path).read_bytes())==expected,'PIN_DRIFT:'+str(path))
    # Rebuild P65 source facts from the pinned original TXT/PDF and P10/P12 maps.
    regenerated=p65.derive()
    require(encode(regenerated['package.json'])==(ROOT/OLD/'package.json').read_bytes(),'P65_SOURCE_REBUILD_DRIFT')
    require(encode(regenerated['source-provenance.json'])==(ROOT/OLD/'source-provenance.json').read_bytes(),'P65_PROVENANCE_REBUILD_DRIFT')

def make():
    pin_inputs()
    original=load(OLD/'package.json')
    package=copy.deepcopy(original)
    require([r['id'] for r in package['records']]==['fg:item:001160','fg:item:001161'],'CASE_DRIFT')
    require([v['id'] for v in package['records'][1]['variants']]==list(PAIR_IDS),'PAIR_ID_DRIFT')
    changed=[]
    for variant in package['records'][1]['variants']:
        before=copy.deepcopy(variant['grouping'])
        require(before['kind']=='even_subdivision' and before['notes_per_beat']==4 and before['beat_unit_q']==[1,1], 'OLD_GROUPING_DRIFT')
        variant['grouping']={
            'kind':'source_event_time', 'notes_per_beat':None, 'beat_unit_q':None,
            'marking_factor':[1,1],
            'source_label':'Original Level17 sixteenth event grid with one-beat intercell pause; retain explicit source event times',
        }
        changed.append({'variant_id':variant['id'],'field':'grouping','before':before,'after':variant['grouping']})
    require(package==load(DIAG),'P67_DIAGNOSTIC_PARITY')
    require(package['records'][0]==original['records'][0],'A_CASE_MUTATION')
    for a,b in zip(package['records'],original['records']):
        require(a['events']==b['events'] and a['source_refs']==b['source_refs'] and a['context']==b['context'],'RECORD_SOURCE_DRIFT')
        require(a['runtime_eligible'] is False and b['runtime_eligible'] is False,'ELIGIBILITY_DRIFT')
        require([(v['id'],v['event_ids'],v['pick_start']) for v in a['variants']]==[(v['id'],v['event_ids'],v['pick_start']) for v in b['variants']],'VARIANT_MEMBERSHIP_DRIFT')
    profile=load(OLD/'expected-profile.json')
    profile['reference_package']=copy.deepcopy(package)
    require(profile['reference_package']==package,'PROFILE_REFERENCE_DRIFT')
    # Registry and sidecar retain exact immutable P65 bytes in a separate P68 Build root.
    registry=(ROOT/OLD/'identity-registry.json').read_bytes()
    provenance=(ROOT/OLD/'source-provenance.json').read_bytes()
    comparison={'status':'pair_grouping_only_repair','base_packet_sha256':PINS[OLD/'package.json'],
                'p67_correct_sha256':PINS[Path('Results/parallel-67/level017-first-source-review-r01/20260924T091600Z-2.3.1.1.1-level017-frozen-source-native-final-r01-results.md')],
                'p67_diagnostic_sha256':PINS[DIAG], 'changed_fields':changed,
                'unchanged_record_event_occurrences':288,'unchanged_source_provenance_sha256':digest(provenance),
                'canonical_identity_allocated':False,'runtime_eligible':False}
    return {'package.json':encode(package),'expected-profile.json':encode(profile),
            'identity-registry.json':registry,'source-provenance.json':provenance,
            'repair-comparison.json':encode(comparison)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('build','verify'))
    parser.add_argument('--out',type=Path,default=OUT);args=parser.parse_args()
    target=(ROOT/args.out).resolve();allowed=(ROOT/OUT).resolve()
    require(target==allowed or allowed in target.parents,'OUTPUT_SCOPE')
    outputs=make()
    if args.command=='build':
        target.mkdir(parents=True,exist_ok=True)
        require(all(not (target/n).exists() for n in NAMES),'OUTPUT_EXISTS')
        for n in NAMES:(target/n).write_bytes(outputs[n])
    else:
        for n in NAMES: require((target/n).read_bytes()==outputs[n],'OUTPUT_DRIFT:'+n)
    print(json.dumps({'status':'P68_PAIR_GROUPING_REPAIRED_NONADMITTED','package_sha256':digest(outputs['package.json']),
                      'profile_sha256':digest(outputs['expected-profile.json']),
                      'provenance_sha256':digest(outputs['source-provenance.json']),
                      'comparison_sha256':digest(outputs['repair-comparison.json'])},sort_keys=True))
if __name__=='__main__':main()
