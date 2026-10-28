# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import os

import fixture_packet
import evaluate


class PacketTests(unittest.TestCase):
    def test_worker_request_cannot_select_or_replace_packet(self):
        with self.assertRaises(ValueError):
            evaluate.validate_request(dict(hypothesis='candidate', patch='/candidate.patch', packet='/weakened.json'))

    def test_policy_requires_both_packet_path_and_manifest_pin(self):
        policy = dict(repo='/repo', llvm='/llvm', cache='/cache', baseline_revision='a' * 40,
                      type='int64', cpu=min(os.sched_getaffinity(0)), runs=3, repetitions=2,
                      jobs=2, timeout=300, min_gain=.03, max_regression=.02,
                      packet='/packet.json')
        with self.assertRaisesRegex(ValueError, 'together'):
            evaluate.validate_policy(policy)
        policy['packet_sha256'] = 'a' * 64
        evaluate.validate_policy(policy)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        sources = {}
        for name in fixture_packet.SOURCE_NAMES:
            data = ('reviewed ' + name).encode()
            (self.root / name).write_bytes(data)
            sources[name] = hashlib.sha256(data).hexdigest()
        self.manifest = dict(schema=1, name='reviewed_v1', target='avx2-i32x8',
            allowed_paths=['builtins/util.m4'], sources=sources,
            cases=['one', 'two'], discovery_cases=['one'], functional_globs=['*reduce*equal*.ispc'],
            benchmark_header='corpus_ispc.h', oracle_header='oracle_ispc.h')
        self.path = self.root / 'packet.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.manifest))
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_manifest_and_source_tampering_rejected(self):
        pinned = self.save()
        self.manifest['cases'].append('removed-control')
        self.save()
        with self.assertRaisesRegex(ValueError, 'manifest hash'):
            fixture_packet.load(self.path, pinned)
        (self.root / 'oracle.cpp').write_text('weakened oracle')
        with self.assertRaisesRegex(ValueError, 'source hash'):
            fixture_packet.load(self.path)

    def test_packet_cannot_allow_framework_or_escape_source_directory(self):
        self.manifest['allowed_paths'] = ['scripts/builtins_lab/run.py']
        self.save()
        with self.assertRaisesRegex(ValueError, 'builtin source'):
            fixture_packet.load(self.path)
        self.manifest['allowed_paths'] = ['builtins/../scripts/tool.ll']
        self.save()
        with self.assertRaises(ValueError):
            fixture_packet.load(self.path)
        self.manifest['allowed_paths'] = ['builtins/util.m4']
        self.save()
        link = self.root / 'oracle.cpp'
        link.unlink()
        link.symlink_to(self.root / 'contexts.cpp')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            fixture_packet.load(self.path)

    def test_freeze_uses_verified_bytes_even_if_original_changes(self):
        packet = fixture_packet.load(self.path)
        (self.root / 'oracle.cpp').write_text('changed after loading')
        destination = self.root / 'frozen'
        fixture_packet.freeze(packet, destination)
        frozen = fixture_packet.load(destination / 'packet.json', packet['sha256'])
        self.assertEqual(frozen['content'], packet['content'])

    def test_duplicate_and_unfrozen_discovery_cases_rejected(self):
        for field, value in (('cases', ['one', 'one']), ('discovery_cases', ['missing'])):
            with self.subTest(field=field):
                previous = self.manifest[field]
                self.manifest[field] = value
                self.save()
                with self.assertRaises(ValueError):
                    fixture_packet.load(self.path)
                self.manifest[field] = previous


if __name__ == '__main__':
    unittest.main()
