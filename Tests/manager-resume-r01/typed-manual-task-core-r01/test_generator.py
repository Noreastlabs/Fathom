#!/usr/bin/env python3
"""Focused causal tests. Mutations are in memory, never in pinned source artifacts."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
BASE='manager-resume-r01/typed-manual-task-core-r01'
spec=importlib.util.spec_from_file_location('adapter',ROOT/'Tools'/BASE/'generate_representative.py')
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
checks=[]
def check(value,label):
    assert value,label
    checks.append(label)
def refused(code,fn):
    try:
        fn()
    except g.Refusal as exc:
        check(exc.code==code,code)
    else:
        raise AssertionError('Expected '+code)

def run(label):
    start=time.monotonic()
    work=ROOT/'Build'/BASE/label
    work.mkdir(parents=True)
    raw=g.read_pinned(ROOT)
    d=g.definition(raw,g.KEY)
    check(len(d['actions'])==4,'four actions')
    check([len(a['contacts']) for a in d['actions']]==[3,1,1,1],'3+1+1+1 memberships')
    check([a['authored_cue_onset_q'] for a in d['actions']]==[[0,1],[1,1],[2,1],[3,1]],'authored cue sequence')
    check(d['initial_mode']=='unselected' and d['initial_bpm'] is None,'no automatic numeric mode')
    check(d['audio_contract'] is None and d['runtime_admitted'] is False,'no audio or admission')
    check('one progression' in d['setup'][0] and 'relax the hand fully' in d['setup'][0],'full corrected source context')
    check(any('randomize' in c for c in d['context']),'workout context retained')
    check(any('suggestions' in c for c in d['context']),'fingering adaptation context')
    check(d['provenance']['policy_source_facts']['source_meter'] is None,'source unknowns retained')
    check(d['provenance']['source_discrepancy'][0]['class']=='pdf_only_or_no_exact_standalone_txt_boundary','source-boundary disclosure')
    refused('REPRESENTATIVE_SCOPE',lambda:g.definition(raw,'another-cell'))
    refused('DUPLICATE_JSON_KEY',lambda:g.strict_json('{"a":1,"a":2}'))
    refused('NONFINITE_JSON',lambda:g.strict_json('{"a":NaN}'))
    refused('NONFINITE_JSON',lambda:g.strict_json('{"a":Infinity}'))
    def mutation(path,fn,code):
        changed=dict(raw)
        if path in [g.BINDINGS,g.PACKET]:
            obj=[g.strict_json(x) for x in raw[path].splitlines()]
            fn(obj)
            changed[path]=b'\n'.join(g.canonical(x) for x in obj)+b'\n'
        else:
            obj=g.strict_json(raw[path]);fn(obj);changed[path]=g.canonical(obj)
        refused(code,lambda:g.definition(changed,g.KEY))
    mutation(g.BINDINGS,lambda x:x.pop(),'BINDING_SCOPE')
    mutation(g.BINDINGS,lambda x:x.__setitem__(1,copy.deepcopy(x[0])),'BINDING_SCOPE')
    mutation(g.PACKET,lambda x:x.reverse(),'RECORD_CONTENT')
    mutation(g.PACKET,lambda x:x[0]['implementation']['events'][0]['members'].reverse(),'RECORD_CONTENT')
    mutation(g.PACKET,lambda x:x[0]['implementation']['events'][1].update(onset_q=1),'RECORD_CONTENT')
    mutation(g.PACKET,lambda x:x[0]['source_payload'].update(label='changed nonprojected label'),'RECORD_CONTENT')
    mutation(g.REP,lambda x:x['binding'].update(txt_line=64),'REPRESENTATIVE_BINDING')
    mutation(g.REP,lambda x:x.update(policy_sha256='0'*64),'POLICY_BINDING')
    mutation(g.POLICY,lambda x:x['authored_projection'].update(onsets_q=[[0,1],[1,2],[2,1],[3,1]]),'CUE_COORDINATES')
    mutation(g.POLICY,lambda x:x['authored_projection'].update(acoustic_gate_q=[1,1]),'ACOUSTIC_OR_SOURCE_CLAIM')
    mutation(g.POLICY,lambda x:x['authored_projection'].update(source_rhythm_claim=True),'ACOUSTIC_OR_SOURCE_CLAIM')
    mutation(g.POLICY,lambda x:x['manual_boundaries'].update(automatic_repeat=True),'AUTOMATIC_SELECTION')
    mutation(g.POLICY,lambda x:x['tempo_and_audio'].update(default_bpm=80),'AUTOMATIC_SELECTION')
    mutation(g.POLICY,lambda x:x['source_facts']['source_setup'].__setitem__(0,'Choose one string set.'),'SOURCE_CONTEXT')
    original_read=Path.read_bytes
    # Every pinned input is independently perturbed through the read seam.
    for name in g.PINS:
        def changed_read(path, target=ROOT/name):
            data=original_read(path)
            return data+b'\n' if path==target else data
        with patch.object(Path,'read_bytes',changed_read):
            refused('INPUT_HASH',lambda:g.read_pinned(ROOT))
    first=g.generate(ROOT,work/'first')
    second=g.generate(ROOT,work/'second')
    check(first==second,'deterministic manifest')
    for name in ['task-definition.json','GeneratedRepresentative.hpp','manifest.json']:
        check((work/'first'/name).read_bytes()==(work/'second'/name).read_bytes(),'byte identical '+name)
    for item in first['payloads']:
        data=(work/'first'/item['path']).read_bytes()
        check(g.sha(data)==item['sha256'] and len(data)==item['bytes'],'payload readback '+item['path'])
    refused('OUTPUT_EXISTS',lambda:g.generate(ROOT,work/'first'))
    refused('OUTPUT_SCOPE',lambda:g.generate(ROOT,ROOT/'Build'/'outside-task-core'))
    (work/'linked').symlink_to(work/'first',target_is_directory=True)
    refused('SYMLINK',lambda:g.generate(ROOT,work/'linked'/'nested'))
    with patch.object(Path,'is_symlink',lambda p: p==ROOT/g.TXT):
        refused('SYMLINK',lambda:g.read_pinned(ROOT))
    for mode in ['payload','manifest']:
        destination=work/('failed-'+mode)
        writer=g.write_exclusive
        def failing_write(path,data):
            if mode=='payload' and path.name=='task-definition.json':
                raise OSError('injected payload write failure')
            writer(path,data)
        try:
            if mode=='payload':
                with patch.object(g,'write_exclusive',failing_write):g.generate(ROOT,destination)
            else:
                with patch.object(g.os,'link',side_effect=OSError('injected publication failure')):g.generate(ROOT,destination)
        except OSError:
            check(destination.exists() and not (destination/'manifest.json').exists(),'failed '+mode+' lacks success manifest')
        else: raise AssertionError('Expected injected I/O failure')
    return {'status':'PASS','checks':len(checks),'check_labels':checks,'seconds':round(time.monotonic()-start,4),
            'scope':'generator and synthetic causal checks only; native/UI/installed NOT_RUN'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-label',required=True);args=parser.parse_args()
    assert args.run_label.replace('-','').isalnum()
    print(json.dumps(run(args.run_label),indent=2))
