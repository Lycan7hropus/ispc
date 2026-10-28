# Copyright (c) 2026, Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""Lifecycle boundary tests for T1 preparation; no real builds or timings."""
import contextlib
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

import evaluate
import prepare_t1
import run as runner


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.trial = prepare_t1.Preparation.__new__(prepare_t1.Preparation)
        t = self.trial
        t.home, t.out = self.root/'home', self.root/'out'
        t.source, t.build = t.home/'source', t.home/'build'
        for path in [t.home, t.out, t.source/'builtins', t.build/'bin']:
            path.mkdir(parents=True, exist_ok=True)
        t.started, t.deadline = time.monotonic(), time.monotonic()+900
        t.policy = dict(baseline_revision='a'*40, timeout=1800, jobs=2)
        t.request = dict(hypothesis='Reviewed mixed candidate')
        t.report = dict(status='failed', accepted=False, commands=[], steps=[])
        t.paths = ['builtins/util.m4']
        t.originals = {}
        self.original = b'original builtin\n'
        (t.source/t.paths[0]).write_bytes(self.original)
        for path in [t.home/'worker.json', t.home/'baseline.json', t.home/'baseline-ispc',
                     t.build/'CMakeCache.txt', t.build/'build.ninja']:
            path.write_text('cached')
        metadata = dict(ispc_sha256=runner.sha256(t.home/'baseline-ispc'),
                        cmake_cache_sha256=runner.sha256(t.build/'CMakeCache.txt'))
        (t.home/'baseline.json').write_text(json.dumps(metadata))
        self.contents = {'oracle.ispc':b'oracle source', 'oracle.cpp':b'oracle host',
                         'contexts.ispc':b'caller source', 'contexts.cpp':b'caller host',
                         'config.h':b'config'}
        import hashlib
        t.packet = dict(sha256='b'*64, manifest=dict(
            sources={n:hashlib.sha256(b).hexdigest() for n,b in self.contents.items()},
            functional_globs=['reduce-equal*.ispc'], cases=['case'], discovery_cases=['case']))
        t.input_hashes = {'cache':'fixed'}
        t.input_identities = mock.Mock(return_value=dict(t.input_hashes))
        t.git = mock.Mock(side_effect=self.git)
        t.prepare = mock.Mock(side_effect=self.prepare)
        t.fixtures = mock.Mock(side_effect=self.fixture)
        t.compile_candidate = mock.Mock(side_effect=self.compile)
        t.emit_job = mock.Mock(side_effect=self.emit)
        self.events = []

    def git(self, *args):
        if args[:2] == ('rev-parse','HEAD'):
            return self.trial.policy['baseline_revision']
        if args[0] == 'status':
            return '' if (self.trial.source/self.trial.paths[0]).read_bytes()==self.original else ' M builtins/util.m4'
        raise AssertionError(args)

    def prepare(self):
        self.events.append('cache-prepare')
        self.trial.originals = {self.trial.paths[0]:self.original}
        self.trial.report['baseline'] = json.loads((self.trial.home/'baseline.json').read_text())

    def compile(self):
        self.events.append('candidate-compile')
        (self.trial.source/self.trial.paths[0]).write_bytes(b'candidate builtin')
        (self.trial.out/'candidate-ispc').write_bytes(b'candidate compiler')

    def fixture(self, label, compiler):
        self.events.append(label+'-fixture')
        t = self.trial
        validation, contexts = t.out/f'{label}-validation', t.out/f'{label}-contexts'
        validation.mkdir(); contexts.mkdir()
        for name, data in self.contents.items():
            directory = validation if name.startswith('oracle.') else contexts
            (directory/name).write_bytes(data)
        (contexts/'contexts.s').write_text('assembly '+label)
        (contexts/'builtin-contexts').write_text('benchmark '+label)
        (validation/'validate-builtin').write_text('oracle '+label)
        artifacts = {str(p):runner.sha256(p) for d in [validation,contexts] for p in d.iterdir()}
        (validation/'fixture.json').write_text(json.dumps(dict(status='verified',runtime_verified=True,
            packet_sha256=t.packet['sha256'],artifacts_sha256=artifacts)))

    def emit(self):
        self.events.append('emit')
        self.assertEqual((self.trial.source/self.trial.paths[0]).read_bytes(),self.original)
        path = self.trial.out/'focus-job.json'
        path.write_text('prepared job')
        self.trial.report['focus_job'] = dict(path=str(path),sha256=runner.sha256(path))

    def run_preparation(self):
        with mock.patch.object(prepare_t1,'bounded_worker',return_value=contextlib.nullcontext()), \
             mock.patch.object(runner,'host_access',return_value=contextlib.nullcontext()), \
             mock.patch.object(evaluate.Evaluation,'build_candidate',side_effect=AssertionError('T2 forbidden')), \
             mock.patch.object(evaluate.Evaluation,'measure',side_effect=AssertionError('timing forbidden')), \
             mock.patch.object(runner,'execute',side_effect=AssertionError('external commands forbidden in mocks')):
            return self.trial.prepare_t1()

    def test_cache_miss_blocks_parent_preparation_and_cold_build(self):
        (self.trial.home/'baseline.json').unlink()
        with self.assertRaisesRegex(ValueError,'cache miss'):
            self.run_preparation()
        self.trial.prepare.assert_not_called()
        self.trial.compile_candidate.assert_not_called()
        self.assertFalse((self.trial.out/'focus-job.json').exists())

    def test_constructor_cache_miss_does_not_invoke_parent_cold_prepare(self):
        home = self.root/'missing-worker'; home.mkdir()
        build = home/'build'; build.mkdir()
        tools = self.root/'tools'; tools.mkdir()
        def initialize(t,*args):
            t.home, t.build, t.tools, t.packet = home,build,tools,{'reviewed':True}
            t.report['evaluator_sha256'] = {}
        with mock.patch.object(evaluate.Evaluation,'initialize',new=initialize), \
             mock.patch.object(evaluate.Evaluation,'prepare',side_effect=AssertionError('cold prepare forbidden')) as cold, \
             mock.patch.object(runner,'host_access',return_value=contextlib.nullcontext()):
            output = self.root/'new-output'
            with self.assertRaisesRegex(ValueError,'cache miss'):
                prepare_t1.Preparation({}, {}, 'worker', output)
        cold.assert_not_called()
        self.assertEqual(json.loads((output/'evaluation.json').read_text())['status'],'failed')

    def test_success_uses_compiler_only_and_restores_before_job(self):
        report = self.run_preparation()
        self.assertEqual(self.events,['cache-prepare','baseline-fixture','candidate-compile','candidate-fixture','emit'])
        self.assertEqual(report['status'],'prepared_for_T1_not_accepted')
        self.assertFalse(report['accepted'])
        self.assertTrue(report['postconditions']['worker_source_restored'])
        self.assertTrue(report['postconditions']['clean'])
        self.assertTrue((self.trial.out/'focus-job.json').exists())

    def test_identical_compiler_skips_candidate_fixture_and_job_after_restoration(self):
        def compile_identical():
            self.events.append('candidate-compile-identical')
            (self.trial.source/self.trial.paths[0]).write_bytes(b'patch outside selected compiler input')
            (self.trial.out/'candidate-ispc').write_bytes((self.trial.home/'baseline-ispc').read_bytes())
        self.trial.compile_candidate.side_effect = compile_identical
        self.trial.source_parity = mock.Mock(side_effect=AssertionError('no candidate fixture exists'))
        report = self.run_preparation()
        self.assertEqual(self.events,['cache-prepare','baseline-fixture','candidate-compile-identical'])
        self.assertEqual(report['status'],'no_compiler_change_not_accepted')
        self.assertFalse(report['accepted'])
        self.assertEqual(report['candidate_ispc_sha256'],report['baseline']['ispc_sha256'])
        self.trial.fixtures.assert_called_once_with('baseline',self.trial.home/'baseline-ispc')
        self.trial.source_parity.assert_not_called()
        self.trial.emit_job.assert_not_called()
        self.assertFalse((self.trial.out/'candidate-contexts').exists())
        self.assertFalse((self.trial.out/'focus-job.json').exists())
        self.assertNotIn('focus_job',report)
        self.assertTrue(report['postconditions']['worker_source_restored'])
        self.assertTrue(report['postconditions']['clean'])
        self.assertEqual((self.trial.source/self.trial.paths[0]).read_bytes(),self.original)

    def test_build_failure_restores_source_and_never_emits_job(self):
        def fail():
            self.compile()
            raise RuntimeError('build failed')
        self.trial.compile_candidate.side_effect = fail
        with self.assertRaisesRegex(RuntimeError,'build failed'):
            self.run_preparation()
        self.assertEqual((self.trial.source/self.trial.paths[0]).read_bytes(),self.original)
        self.trial.emit_job.assert_not_called()
        self.assertTrue(self.trial.report['source_restored'])
        self.assertFalse((self.trial.out/'focus-job.json').exists())

    def test_candidate_oracle_failure_restores_and_never_emits(self):
        def fixture(label,compiler):
            self.fixture(label,compiler)
            if label=='candidate': raise ValueError('oracle failure')
        self.trial.fixtures.side_effect = fixture
        with self.assertRaisesRegex(ValueError,'oracle failure'):
            self.run_preparation()
        self.assertEqual((self.trial.source/self.trial.paths[0]).read_bytes(),self.original)
        self.trial.emit_job.assert_not_called()
        self.assertFalse((self.trial.out/'focus-job.json').exists())

    def test_cleanup_failure_prevents_job_and_cleans_stale_job(self):
        (self.trial.out/'focus-job.json').write_text('must be removed')
        self.trial.report['focus_job'] = {'stale':True}
        self.trial.restore = mock.Mock(side_effect=ValueError('restoration failed'))
        with self.assertRaisesRegex(ValueError,'restoration failed'):
            self.run_preparation()
        self.trial.emit_job.assert_not_called()
        self.assertFalse((self.trial.out/'focus-job.json').exists())
        self.assertNotIn('focus_job',self.trial.report)
        self.assertEqual(self.trial.report['status'],'failed')

    def test_source_parity_and_artifact_hash_changes_are_rejected(self):
        for label in ['baseline','candidate']: self.fixture(label,Path('/unused'))
        self.trial.source_parity()
        source = self.trial.out/'candidate-contexts/contexts.ispc'
        source.write_text('different source')
        with self.assertRaisesRegex(ValueError,'source differs'):
            self.trial.source_parity()
        source.write_bytes(self.contents['contexts.ispc'])
        assembly = self.trial.out/'candidate-contexts/contexts.s'
        assembly.write_text('mutated assembly')
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            self.trial.source_parity()

    def test_unverified_or_different_packet_manifest_is_rejected(self):
        for label in ['baseline','candidate']: self.fixture(label,Path('/unused'))
        path=self.trial.out/'candidate-validation/fixture.json'
        original=json.loads(path.read_text())
        for change,message in [({'runtime_verified':False},'not verified'),
                               ({'packet_sha256':'different'},'packet changed')]:
            current=dict(original);current.update(change);path.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError,message):self.trial.source_parity()

    def test_preparation_identity_mutation_blocks_patch_application(self):
        self.trial.input_identities.return_value={'cache':'mutated'}
        with self.assertRaisesRegex(ValueError,'inputs changed'):
            self.run_preparation()
        self.trial.prepare.assert_not_called()
        self.trial.compile_candidate.assert_not_called()
        self.trial.emit_job.assert_not_called()

    def test_source_parity_failure_after_build_restores_no_job(self):
        def fixture(label,compiler):
            self.fixture(label,compiler)
            if label=='candidate':
                (self.trial.out/'candidate-contexts/config.h').write_text('tampered')
        self.trial.fixtures.side_effect=fixture
        with self.assertRaisesRegex(ValueError,'source differs'):
            self.run_preparation()
        self.assertEqual((self.trial.source/self.trial.paths[0]).read_bytes(),self.original)
        self.trial.emit_job.assert_not_called()

    def test_marker_loss_during_patch_check_cannot_fall_through_to_cold_build(self):
        t = self.trial
        t.identity = {'compiler':'pinned'}
        (t.home/'worker.json').write_text(json.dumps(t.identity))
        t.patch = self.root/'candidate.patch'
        t.patch.write_text('patch bytes')
        t.require_cache()
        called = []
        def parent(trial,label,argv,**kwargs):
            called.append(label)
            trial.report['commands'].append({'label':label})
            if label == 'patch-check':
                (trial.home/'baseline.json').unlink()
        with mock.patch.object(evaluate.Evaluation,'stage',autospec=True,side_effect=parent), \
             mock.patch.object(runner,'execute',side_effect=AssertionError('no real process')):
            with self.assertRaisesRegex(ValueError,'cold preparation is forbidden'):
                evaluate.Evaluation.prepare(t)
        self.assertEqual(called,['patch-check'])
        self.assertEqual(t.originals,{t.paths[0]:self.original})
        self.assertFalse((t.out/'focus-job.json').exists())

    def test_t1_stage_never_launches_cold_cache_build_commands(self):
        for label in ['worktree','submodules','configure','baseline-build','baseline-lit']:
            with self.subTest(label=label), \
                 mock.patch.object(evaluate.Evaluation,'stage') as parent:
                with self.assertRaises(ValueError):
                    self.trial.stage(label,['forbidden cold preparation'])
                parent.assert_not_called()

    def test_stage_clamps_policy_timeout_to_process_cap_and_remaining(self):
        for now,deadline,requested,expected in [(0,1000,None,300),(10,17,99,7),(0,1000,12,12)]:
            self.trial.deadline=deadline
            def parent(t,label,argv,**kwargs):
                t.report['commands'].append({'label':label})
            with self.subTest(expected=expected), \
                 mock.patch.object(prepare_t1.time,'monotonic',return_value=now), \
                 mock.patch.object(evaluate.Evaluation,'stage',autospec=True,side_effect=parent) as stage:
                self.trial.stage('probe',['command'],timeout=requested)
            self.assertEqual(stage.call_args.kwargs['timeout'],expected)

    def test_expired_deadline_prevents_launch_and_late_stage_fails(self):
        self.trial.deadline=1
        with mock.patch.object(prepare_t1.time,'monotonic',return_value=2), \
             mock.patch.object(evaluate.Evaluation,'stage') as stage:
            with self.assertRaises(TimeoutError):self.trial.stage('probe',['command'])
        stage.assert_not_called()
        self.trial.deadline=5
        with mock.patch.object(prepare_t1.time,'monotonic',side_effect=[0,0,6]), \
             mock.patch.object(evaluate.Evaluation,'stage'):
            with self.assertRaises(TimeoutError):self.trial.stage('late',['command'])

    def test_full_evaluator_build_order_retains_all_t2_gates(self):
        t=self.trial
        tests=t.source/'tests/func-tests';tests.mkdir(parents=True)
        (tests/'reduce-equal-example.ispc').write_text('functional test')
        for label in ['baseline','candidate']:
            directory=t.out/f'{label}-contexts';directory.mkdir()
            for name in ['contexts.ispc','contexts.cpp']: (directory/name).write_text(name)
        t.llvm=self.root/'llvm'
        t.compile_candidate=mock.Mock(side_effect=lambda:self.events.append('compile'))
        t.fixtures=mock.Mock(side_effect=lambda *args:self.events.append('fixtures'))
        t.packet_command=mock.Mock(return_value=['compile-only-command'])
        t.stage=mock.Mock(side_effect=lambda label,*a,**kw:self.events.append(label))
        evaluate.Evaluation.build_candidate(t)
        self.assertEqual(self.events,['compile','fixtures','candidate-vnni-compile','candidate-lit','candidate-functional'])
        self.assertTrue(t.packet_command.call_args.args[-1])
        functional=t.stage.call_args
        self.assertIn(str(t.source/'scripts/run_tests.py'),[str(v) for v in functional.args[1]])
        self.assertTrue(t.report['functional_test_sha256'])


if __name__=='__main__':
    unittest.main()
