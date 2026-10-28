#!/usr/bin/env python3
# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import copy
import hashlib
import json
import subprocess
import tempfile
import sys
from pathlib import Path
import unittest

import research


class ResearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / 'source.ll').write_text('baseline instruction\n')
        subprocess.run(['git', '-C', str(self.root), 'add', 'source.ll'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.com', 'commit', '-qm', 'baseline'], check=True)
        sha = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD']).decode().strip()
        evidence = self.root / 'probe.s'
        evidence.write_text('observed assembly')
        candidate = dict(id='a', family='shuffle', locations=[dict(path='source.ll', line=1)],
                         evidence_level='codegen_verified', relevance_level='representative',
                         evidence=[dict(path=str(evidence), sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(),
                                        command=['compiler', 'probe.ispc'], observation='assembly observation')])
        for key in ('mechanism', 'expected_codegen_change', 'caller_relevance', 'risks',
                    'disproof', 'next_probe', 'ranking_reason'):
            candidate[key] = 'specific explanation'
        self.report = dict(baseline_revision=sha, selected='a', selection_reason='evidence comparison',
                           candidates=[copy.deepcopy(candidate) for _ in range(3)])
        for item, identifier, family in zip(self.report['candidates'], 'abc', ('shuffle', 'reduce', 'packed')):
            item.update(id=identifier, family=family)

    def test_ready_and_abstention_are_distinct(self):
        self.assertEqual(research.validate(self.report, self.root)['status'], 'ready_for_patch_design')
        self.report['selected'] = None
        self.assertEqual(research.validate(self.report, self.root)['status'], 'needs_more_evidence')

    def test_source_suspicion_and_unmeasured_relevance_cannot_select(self):
        for key, value in (('evidence_level', 'source_only'), ('relevance_level', 'unmeasured')):
            report = copy.deepcopy(self.report)
            report['candidates'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                research.validate(report, self.root)

    def test_modified_artifact_and_invalid_source_reference_rejected(self):
        for key, value in (('sha256', '0' * 64), ('path', '/missing-evidence')):
            report = copy.deepcopy(self.report)
            report['candidates'][0]['evidence'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                research.validate(report, self.root)
        self.report['candidates'][0]['locations'][0]['line'] = 2
        with self.assertRaises(ValueError):
            research.validate(self.report, self.root)

    def test_single_family_search_rejected(self):
        for item in self.report['candidates']:
            item['family'] = 'shuffle'
        with self.assertRaises(ValueError):
            research.validate(self.report, self.root)

    def test_profile_claim_cannot_use_assembly_as_runtime_evidence(self):
        self.report['candidates'][0]['evidence_level'] = 'profiled'
        with self.assertRaisesRegex(ValueError, 'profile report'):
            research.validate(self.report, self.root)

    def test_design_handoff_refuses_abstention_and_freezes_selected_report(self):
        report = self.root / 'report.json'
        output = self.root / 'design'
        self.report['selected'] = None
        report.write_text(json.dumps(self.report))
        command = [sys.executable, research.__file__, 'design', str(report),
                   '--repo', str(self.root), '--output', str(output)]
        rejected = subprocess.run(command, capture_output=True)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse(output.exists())
        self.report['selected'] = 'a'
        report.write_text(json.dumps(self.report))
        subprocess.run(command, capture_output=True, check=True)
        self.assertEqual(json.loads((output / 'research-report.json').read_text()), self.report)
        self.assertIn('Selected hypothesis: a', (output / 'agent-task.txt').read_text())


if __name__ == '__main__':
    unittest.main()
