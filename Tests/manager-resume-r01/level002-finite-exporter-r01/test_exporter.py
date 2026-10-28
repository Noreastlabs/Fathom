#!/usr/bin/env python3
"""Bounded finite-export checks; no input mutation, native code, app or audio."""
from pathlib import Path
import argparse
import copy
import datetime
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import resource
import subprocess
import sys
import time
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = 'manager-resume-r01/level002-finite-exporter-r01'
spec = importlib.util.spec_from_file_location('level002_private_exporter', ROOT/'Tools'/BASE/'export_level002.py')
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repeat-output', type=Path, default=ROOT/'Build'/BASE/'export-repeat-r01')
parser.add_argument('--result', type=Path, default=ROOT/'Results'/BASE/'validation-r01.json')
args = parser.parse_args()
repeat_output = args.repeat_output if args.repeat_output.is_absolute() else ROOT/args.repeat_output
result_output = args.result if args.result.is_absolute() else ROOT/args.result
if (ROOT/'Build'/BASE).resolve() not in repeat_output.resolve().parents or (ROOT/'Results'/BASE).resolve() not in result_output.resolve().parents:
    parser.error('Use exclusive output paths inside this private exporter Build/Results root')
if repeat_output.exists() or result_output.exists():
    parser.error('Retain prior evidence; choose fresh repeat/result paths')
checks = []
started = time.monotonic()

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append({'check': name, 'result': 'PASS'})


def refuses(name, expected, call):
    try:
        call()
    except ex.Refusal as error:
        check(name + ' causal refusal', error.code == expected)
        checks[-1]['refusal_code'] = error.code
    else:
        raise AssertionError(name + ' unexpectedly succeeded')

raw = {p: ex.verify_input_bytes(p, ex.read_bounded(ROOT, p)) for p in ex.PINS}
rows = [ex.strict_json(line) for line in raw[ex.PACKET].splitlines()]
review = ex.strict_json(raw[ex.REVIEW])
guidance = ex.strict_json(raw[ex.GUIDANCE])
original_txt = raw[ex.TXT].decode()
records, policy = ex.compile_projection(rows, review, original_txt, guidance)
check('exact108 unique source key coverage', len(records) == len({r['package_key'] for r in records}) == 108)
check('exact4320 contact coverage', sum(len(r['events']) for r in records) == 4320)
check('exact216 variants and8640 memberships', sum(len(r['variants']) for r in records) == 216 and
      sum(len(v['event_ordinals']) for r in records for v in r['variants']) == 8640)
check('review binding preserves ordered108 keys', [(r['package_key'],r['source_identity']) for r in records] ==
      [(r['package_key'],r['source_identity']) for r in review['records']])
all_rationals = [q for r in records for e in r['events'] for q in (e['onset_q'],e['metric_duration_q'])]
all_rationals += [v['end_q'] for r in records for v in r['variants']]
check('all executable rational fields use bounded reduced integer pairs', all(
    len(q)==2 and all(type(x) is int for x in q) and 0<=q[0]<=ex.MAX_INT and 0<q[1]<=ex.MAX_INT and math.gcd(*q)==1 for q in all_rationals))
check('all starts serialize canonical zero', all(r['events'][0]['onset_q']==[0,1] for r in records))
check('formerq2/4 contact nowq1/2', all(r['events'][2]['onset_q']==[1,2] for r in records))
check('exact original relative-time values preserved', all(Fraction(*e['onset_q'])==Fraction(i,4) and Fraction(*e['metric_duration_q'])==Fraction(1,4)
      for r in records for i,e in enumerate(r['events'])))
check('original source contact line/fret/string/pitch retained', all(
    e['fret']==source['fret'] and e['finger']==source['finger'] and e['string_low_to_high']==source['string_low_to_high'] and
    e['written_standard_tuning_midi']==source['midi'] and e['source_token']['txt_line']==source['source_line']
    for r,src in zip(records,rows) for e,source in zip(r['events'],src['implementation']['ordered_contacts'])))
check('every output explicitlyNOT_ADMITTED/no credit', all(r['status']=='NOT_ADMITTED' and not r['runtime_admitted'] and not r['canonical_ids_allocated'] and
      not r['learner_performance_observed'] and not r['credit_awarded'] for r in records))
check('unprinted sounding gates remainnull', all(e['acoustic_gate_q'] is None for r in records for e in r['events']))
check('unknown BPM/meter/capo/performance preserved', all(v is None for v in policy['unspecified'].values()))
check('alternation attributed as authored reviewed interpretation', policy['authored_reviewed_interpretation']['name']=='continuous_alternating_pick.1' and
      'bounded interpretation' in policy['authored_reviewed_interpretation']['basis'])
check('nine source guidance clauses and fullset/twodays retained', len(policy['source_guidance']['clauses'])==9 and
      'two separate clean days' in policy['source_guidance']['progression_unit'] and not policy['source_guidance']['automatic_credit'])
check('unselected rhythm groups not exported', policy['unselected_rhythm_options']==['triplet','quintuplet'])
check('source-local variant labels are not canonical IDs', not policy['source_local_labels_are_canonical_ids'] and
      all(v['source_local_label'] in ('start-D','start-U') for r in records for v in r['variants']) and b'fg:item:' not in ex.canonical(records))
for pair,want in [((2,4),[1,2]),((0,4),[0,1]),((39,4),[39,4]),((ex.MAX_INT,ex.MAX_INT),[1,1])]:
    check('reduced pair '+str(pair),ex.reduced(*pair)==want)
for name,pair,code in [('zero denominator',(1,0),'RATIONAL_SIGN'),('negative denominator',(1,-4),'RATIONAL_SIGN'),
                       ('negative numerator',(-1,4),'RATIONAL_SIGN'),('float pair',(0.5,1),'RATIONAL_INTEGER'),
                       ('boolean pair',(True,4),'RATIONAL_INTEGER'),('numerator overflow',(ex.MAX_INT+1,4),'RATIONAL_OVERFLOW'),
                       ('denominator overflow',(0,ex.MAX_INT+1),'RATIONAL_OVERFLOW')]:
    refuses(name,code,lambda p=pair:ex.reduced(*p))
refuses('nonfinite legacy source','RATIONAL_NONFINITE',lambda:ex.source_quarter(float('inf')))
refuses('legacy decimal overflow','RATIONAL_OVERFLOW',lambda:ex.source_quarter(1e30))
refuses('duplicate JSON key','JSON_DUPLICATE_KEY',lambda:ex.strict_json(b'{"x":1,"x":2}'))
refuses('JSON NaN','JSON_NONFINITE',lambda:ex.strict_json(b'{"x":NaN}'))
for source in (ex.PACKET,ex.TXT,ex.PDF,ex.REVIEW,ex.GUIDANCE):
    refuses('altered pin '+source,'INPUT_SHA',lambda source=source:ex.verify_input_bytes(source,raw[source]+b' '))
refuses('unreviewed input path','UNREVIEWED_INPUT',lambda:ex.verify_input_bytes('unknown.json',b'{}'))

def mutated(name, code, change):
    changed=copy.deepcopy(rows)
    change(changed)
    refuses(name,code,lambda:ex.compile_projection(changed,review,original_txt,guidance))

mutated('missing last record','RECORD_COUNT',lambda r:r.pop())
mutated('duplicate first key','DUPLICATE_OR_MISSING_KEY',lambda r:r.__setitem__(1,copy.deepcopy(r[0])))
mutated('unreviewed key','SOURCE_IDENTITY_ORDER',lambda r:r[1].__setitem__('package_key','unreviewed'))
mutated('wrong source order','SOURCE_IDENTITY_ORDER',lambda r:r.__setitem__(slice(0,2),list(reversed(r[:2]))))
mutated('unsupported record field','UNSUPPORTED_FIELD',lambda r:r[1].__setitem__('runtime_override',True))
mutated('unsupported contact kind','UNSUPPORTED_KIND',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('kind','guessed'))
mutated('changed fret','CONTACT_ORDER_VALUE',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('fret',8))
mutated('wrong written MIDI','CONTACT_PITCH',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('midi',46))
mutated('wrong source coordinate','CONTACT_SOURCE_TOKEN',lambda r:r[1]['implementation']['ordered_contacts'][0].__setitem__('source_line',100))
mutated('wrong note grid','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('onset_q',0.5))
mutated('invented turn gap','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][20].__setitem__('onset_q',6.0))
mutated('zero duration','METRIC_GRID',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('duration_q',0.0))
mutated('unreviewed contact field','UNSUPPORTED_FIELD',lambda r:r[1]['implementation']['ordered_contacts'][1].__setitem__('gate_q',[1,4]))
mutated('variant wrong start','VARIANT_ORDER',lambda r:r[1]['implementation']['relative_variants'][1]['strokes'].__setitem__(0,'D'))
mutated('variant missing event','VARIANT_ORDER',lambda r:r[1]['implementation']['relative_variants'][0]['contact_ordinals'].pop())
mutated('invented fixed BPM','TIMING_AUTHORITY',lambda r:r[1]['timing_authority'].__setitem__('fixed_bpm',120))
mutated('invented credit','NO_CREDIT',lambda r:r[1]['implementation'].__setitem__('mastery_or_credit',True))
mutated('unresolved source conflict','SOURCE_UNRESOLVED',lambda r:r[1].__setitem__('unresolved_reasons',['source conflict']))
mutated('unsupported nonprojected metadata','REVIEW_RECORD_SHA',lambda r:r[1]['provenance'].__setitem__('admission','override'))
bad_guidance=copy.deepcopy(guidance);bad_guidance['obligations'].append({'key':'invented','verbatim':'play120BPM','extracted_char_start':0,'extracted_char_end':1})
refuses('invented source obligation','GUIDANCE_OBLIGATIONS',lambda:ex.compile_projection(rows,review,original_txt,bad_guidance))
bad_guidance=copy.deepcopy(guidance);bad_guidance['applicability']['automatic_mastery_or_credit']=True
refuses('source guidance automatic mastery','NO_CREDIT',lambda:ex.compile_projection(rows,review,original_txt,bad_guidance))
bad_review=copy.deepcopy(review);bad_review['records'][1]['record_sha256_sorted_keys']='0'*64
refuses('wrong per-record independent review','REVIEW_RECORD_SHA',lambda:ex.compile_projection(rows,bad_review,original_txt,guidance))

first=ROOT/'Build'/BASE/'export-r01';repeat=repeat_output
check('first CLI export complete',first.is_dir())
result=ex.export_bundle(ROOT,repeat)
check('deterministic repeat exact file set and bytes',sorted(p.name for p in first.iterdir())==sorted(p.name for p in repeat.iterdir()) and
      all(p.read_bytes()==(repeat/p.name).read_bytes() for p in first.iterdir()))
manifest=ex.strict_json((repeat/'manifest.json').read_bytes())
check('self-excluding output manifest validates every included payload', {x['path'] for x in manifest['files']}=={'records.jsonl','source-policy.json'} and
      all(len((repeat/x['path']).read_bytes())==x['bytes'] and ex.sha((repeat/x['path']).read_bytes())==x['sha256'] for x in manifest['files']))
check('every input pin and exporter source represented',{x['path'] for x in manifest['inputs']}==set(ex.PINS)|{ex.SELF})
refuses('existing output refused','OUTPUT_EXISTS',lambda:ex.export_bundle(ROOT,first))
refuses('outside private output scope','OUTPUT_SCOPE',lambda:ex.export_bundle(ROOT,ROOT/'Build'/'outside-private-level002-export'))
failed=ROOT/'Build'/BASE/'negative-input-must-not-exist'
original_reader=ex.read_bounded
with patch.object(ex,'read_bounded',side_effect=lambda root,path:raw[ex.PACKET]+b' ' if path==ex.PACKET else original_reader(root,path)):
    refuses('corrupt live-read before publication','INPUT_SHA',lambda:ex.export_bundle(ROOT,failed))
check('input refusal published no output',not failed.exists())
output={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'result':'PASS','checks':checks,
        'check_count':len(checks),'causal_refusals':sum('refusal_code' in c for c in checks),
        'elapsed_seconds':round(time.monotonic()-started,4),'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'counts':result['counts'],'deterministic_repeat':True,'exports':result['files'],
        'native_app_audio_broad_qa':'NOT_RUN: outside private exporter release','test_data':'Negative cases are in-memory mutations; sealed source inputs untouched'}
path=result_output
with path.open('x') as stream:json.dump(output,stream,indent=2);stream.write('\n')
print(json.dumps({k:output[k] for k in ('result','check_count','causal_refusals','elapsed_seconds','process_peak_rss_bytes','counts')}))
