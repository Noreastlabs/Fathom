"""Verify actual custody reuse and refusal, without publishing project status."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'Tools/exercise-family-compiler'))
from adopt_reviewed_family import retain_reviewed_inputs


class Custody(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='fathom-custody-')
        self.root = Path(self.tmp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Custody Test',
                        '-c', 'user.email=custody@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        (self.root/'Tools').mkdir(); (self.root/'Results').mkdir()
        shutil.copyfile(PROJECT/'Tools/fathom_evidence.py', self.root/'Tools/fathom_evidence.py')
        self.archive = self.root/'Build/new-archive'; self.archive.mkdir(parents=True)
        self.manifest = self.root/'Results/new-custody.json'
    def tearDown(self): self.tmp.cleanup()
    def ref(self, p):
        raw=p.read_bytes()
        return {'path':str(p.relative_to(self.root)), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}
    def verify(self, pin):
        p=self.root/pin['path']; raw=p.read_bytes()
        if self.ref(p)!=pin: raise ValueError('pin mismatch')
        return raw
    def put(self, path, raw):
        p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        return self.ref(p), raw
    def retain(self, inputs, reuse=(), mode=True):
        return retain_reviewed_inputs(self.root, inputs, self.archive, {'path':'freeze'}, self.verify,
                                      self.ref, self.manifest if mode else None, reuse)
    def test_identical_inputs_have_one_verified_object(self):
        a=self.put('Source/a',b'same independently reviewed input')
        b=self.put('Build/b',a[1])
        index,refs=self.retain([a,b])
        self.assertEqual(refs[0]['archive'],refs[1]['archive'])
        self.assertEqual(len(list((self.root/'Evidence/objects').iterdir())),1)
        self.assertEqual(self.verify(refs[0]['archive']),a[1])
        self.assertEqual(len(json.loads(self.manifest.read_text())['artifacts']),1)
        self.assertEqual(json.loads(index.read_text())['custody']['refs'],2)
    def test_prior_archive_reused_without_new_copy(self):
        a=self.put('Source/current',b'old reviewed input')
        old=self.put('Build/old/reviewed-bytes/Source/current',a[1])[0]
        _,refs=self.retain([a], [({'path':'old-index','sha256':'guarded'}, {'refs':[{'original':a[0],'archive':old}]})])
        self.assertEqual(refs[0]['archive'],old)
        self.assertFalse((self.root/'Evidence').exists())
        self.assertFalse(self.manifest.exists())
    def test_corrupt_prior_bytes_refused(self):
        a=self.put('Source/current',b'reviewed')
        old=self.put('Build/old/file',a[1])[0]
        (self.root/old['path']).write_bytes(b'corrupt!')
        with self.assertRaises(ValueError):
            self.retain([a], [({}, {'refs':[{'original':a[0],'archive':old}]})])
        self.assertFalse((self.archive/'reviewed-bytes.json').exists())
    def test_forged_prior_identity_refused(self):
        a=self.put('Source/current',b'reviewed'); old=self.put('Build/old/file',b'other')[0]
        with self.assertRaises(ValueError):
            self.retain([a], [({}, {'refs':[{'original':a[0],'archive':old}]})])
        self.assertFalse((self.archive/'reviewed-bytes.json').exists())
    def test_historical_invocation_keeps_archive_layout(self):
        a=self.put('Source/a',b'reviewed')
        _,refs=self.retain([a],mode=False)
        self.assertEqual(refs[0]['archive']['path'],'Build/new-archive/reviewed-bytes/Source/a')
        self.assertEqual(self.verify(refs[0]['archive']),a[1])


if __name__=='__main__': unittest.main()
