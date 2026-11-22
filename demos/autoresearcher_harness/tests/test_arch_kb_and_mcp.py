from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from autoresearcher_harness.campaign import CampaignRunner
from autoresearcher_harness.contracts import CampaignPlan, Proposal
from autoresearcher_harness.engine import Harness
from autoresearcher_harness.knowledge_base import KnowledgeBase, canonical_change_signature
from autoresearcher_harness.mcp_adapter_example import ExampleMCPAdapter, StubRawMCPTransport


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / 'examples'
ARCH_CAMPAIGN = EXAMPLES_DIR / 'campaign_arch.json'
KB_SOURCE = EXAMPLES_DIR / 'kb'
SINGLE_PLAN = EXAMPLES_DIR / 'throughput.json'


class ArchKBAndMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'outputs'
        self.kb_dir = Path(self.temp.name) / 'kb'
        shutil.copytree(KB_SOURCE, self.kb_dir)
        self.arch_plan = json.loads(ARCH_CAMPAIGN.read_text(encoding='utf-8'))
        self.arch_plan['mock']['duration_seconds'] = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _finish_campaign(self, runner: CampaignRunner, campaign_id: str) -> dict:
        for _ in range(140):
            state = runner.step(campaign_id)
            if state['status'] not in {'running', 'evaluating_holdout'}:
                return state
        self.fail('Campaign did not finish')

    def test_architecture_campaign_gain_compute_ratchet_and_layered_kb_lifecycle(self) -> None:
        runner = CampaignRunner(self.root)
        campaign_id = runner.create(
            self.arch_plan,
            plan_dir=EXAMPLES_DIR,
            kb_root=self.kb_dir,
            kb_id='ARCH-001',
        )
        campaign = self._finish_campaign(runner, campaign_id)
        self.assertEqual(campaign['status'], 'succeeded')
        self.assertEqual(campaign['plan']['track'], 'architecture')
        self.assertEqual(len(campaign['trials']), 6)

        decisions = [t['decision'] for t in campaign['trials']]
        self.assertEqual(decisions, ['baseline', 'keep', 'discard', 'keep', 'crash', 'keep'])
        self.assertIn('compute budget exceeded', campaign['trials'][2]['decision_reason'])
        self.assertIn('compute win', campaign['trials'][5]['decision_reason'])
        self.assertLess(
            campaign['trials'][5]['candidate_inference_flops_m'],
            campaign['trials'][3]['candidate_inference_flops_m'],
        )
        self.assertEqual(campaign['incumbent_trial_id'], 'trial-005')

        report = campaign['holdout_report']
        self.assertIsNotNone(report)
        self.assertTrue(report['accepted'])
        self.assertGreater(report['gain_correct'], 0)
        self.assertGreater(report['gain_pp'], 0)
        self.assertLess(report['flops_ratio'], 1.0)
        self.assertGreater(report['campaign_compute_usage']['total_gpu_seconds'], 0)
        self.assertIsNotNone(report['gain_per_gpu_hour'])

        # Distill writes an isolated .md file under entries/ARCH-001/drafts/ without modifying revisions/v1.md or CURRENT.md.
        kb = KnowledgeBase(self.kb_dir)
        v1_path = self.kb_dir / 'entries' / 'ARCH-001' / 'revisions' / 'v1.md'
        current_path = self.kb_dir / 'entries' / 'ARCH-001' / 'CURRENT.md'
        v1_before = v1_path.read_text(encoding='utf-8')
        current_before = current_path.read_text(encoding='utf-8')
        before = kb.load('ARCH-001')

        draft = kb.distill_from_campaign(campaign)
        self.assertEqual(draft['status'], 'draft')
        self.assertEqual(draft['revision'], 'v2-draft')
        # P-DWCONV (conv_type=depthwise_separable;kernel_size=7) and P-PRUNE-FFN (ffn_ratio=1.75) match seed signatures -> merged!
        self.assertGreaterEqual(draft['merge_preview']['patterns']['merged'], 2)
        self.assertEqual(v1_path.read_text(encoding='utf-8'), v1_before)
        self.assertEqual(current_path.read_text(encoding='utf-8'), current_before)
        self.assertEqual(len(kb.list_drafts('ARCH-001')), 1)

        # Human review publishes immutable v2.md, updates CURRENT.md & EVIDENCE.md, and keeps v1.md untouched.
        published = kb.publish('ARCH-001', reviewer='arch-lead')
        self.assertEqual(published['revision'], 'v2')
        self.assertEqual(published['parent_revision'], 'v1')
        self.assertEqual(len(published['revisions']), 2)
        self.assertEqual(len(kb.list_drafts('ARCH-001')), 0)
        self.assertEqual(v1_path.read_text(encoding='utf-8'), v1_before)
        self.assertTrue((self.kb_dir / 'entries' / 'ARCH-001' / 'revisions' / 'v2.md').is_file())

        # Historical v1 snapshot remains intact and queryable by revision.
        v1_loaded = kb.load('ARCH-001', revision='v1')
        self.assertEqual(v1_loaded['revision'], 'v1')
        self.assertEqual(len(v1_loaded['patterns']), len(before['patterns']))

        # Deduplication & aggregation: P-DWCONV was merged instead of duplicated, and observations incremented.
        dw_sig = canonical_change_signature({'conv_type': 'depthwise_separable', 'kernel_size': 7})
        dw_matches = [p for p in published['patterns'] if p['change_signature'] == dw_sig]
        self.assertEqual(len(dw_matches), 1)
        self.assertGreater(dw_matches[0]['stats']['observations'], 0)
        self.assertEqual(dw_matches[0]['confidence'], 'verified_holdout')
        self.assertEqual(len(published['evidence']), len(before['evidence']) + 1)

        # Confirm zero database files created inside the Markdown KB directory.
        self.assertEqual(list(self.kb_dir.rglob('*.sqlite*')), [])

    def test_kb_markdown_multidimensional_search_and_reindex(self) -> None:
        kb = KnowledgeBase(self.kb_dir)
        index_md = kb.reindex()
        self.assertTrue(index_md.is_file())
        self.assertIn('ARCH-001', index_md.read_text(encoding='utf-8'))

        hits = kb.search(
            track='architecture',
            field='conv_type',
            direction='gain_up_compute_down',
            max_flops_ratio=0.95,
            min_gain_pp=10.0,
        )
        self.assertEqual([e['kb_id'] for e in hits], ['ARCH-001'])
        self.assertTrue(any(p['pattern_id'] == 'P-DWCONV' for p in hits[0]['matched_patterns']))

        anti_hits = kb.search(track='architecture', model_family='conv1d', failure_type='compute_budget_exceeded')
        self.assertEqual([e['kb_id'] for e in anti_hits], ['ARCH-001'])
        self.assertTrue(any(a['pattern_id'] == 'AP-OVERDEEP-WIDE' for a in anti_hits[0]['matched_anti_patterns']))

        hpo_entries = kb.list_entries(track='hpo')
        self.assertEqual([e['kb_id'] for e in hpo_entries], ['HPO-001'])
        self.assertEqual(list(self.kb_dir.rglob('*.sqlite*')), [])

    def test_kb_immutability_and_draft_guard(self) -> None:
        kb = KnowledgeBase(self.kb_dir)
        existing = kb.load('ARCH-001')
        with self.assertRaises(ValueError):
            kb.save(existing)  # cannot overwrite existing immutable v1 without explicit opt-in

        draft_entry = json.loads(json.dumps(existing))
        draft_entry['kb_id'] = 'ARCH-DRAFT'
        draft_entry['status'] = 'draft'
        kb.save(draft_entry)
        with self.assertRaises(ValueError):
            kb.freeze_snapshot('ARCH-DRAFT')

    def test_param_bounds_from_kb_blocks_illegal_architecture_proposal(self) -> None:
        plan = json.loads(json.dumps(self.arch_plan))
        plan['proposals'] = []
        runner = CampaignRunner(self.root)
        campaign_id = runner.create(plan, plan_dir=EXAMPLES_DIR, kb_root=self.kb_dir, kb_id='ARCH-001')
        runner.run_baseline(campaign_id, poll_seconds=0.01)

        # num_layers=12 violates ARCH-001 scope.param_bounds (4..10).
        with self.assertRaises(ValueError) as ctx:
            runner.submit_proposal(
                campaign_id,
                Proposal(hypothesis='Exceed 10-layer Conv1d boundary', changes={'num_layers': 12}),
            )
        self.assertIn('param_bounds', str(ctx.exception))

        # Unknown conv_type violates enum constraint.
        with self.assertRaises(ValueError) as ctx2:
            runner.submit_proposal(
                campaign_id,
                Proposal(hypothesis='Invalid conv op', changes={'conv_type': 'linear_mlp'}),
            )
        self.assertIn('param_bounds', str(ctx2.exception))
        self.assertEqual(len(runner.status(campaign_id)['trials']), 1)

    def test_track_isolation_blocks_mixing_architecture_and_hpo_fields(self) -> None:
        mixed = json.loads(json.dumps(self.arch_plan))
        mixed['mutable_fields'] = ['kernel_size', 'lr']
        with self.assertRaises(ValueError) as ctx:
            CampaignPlan.from_dict(mixed)
        self.assertIn('training recipe fields: lr', str(ctx.exception))

        hpo_mixed = json.loads(json.dumps(self.arch_plan))
        hpo_mixed['track'] = 'hpo'
        hpo_mixed['knowledge']['track'] = 'hpo'
        hpo_mixed['mutable_fields'] = ['lr', 'num_layers']
        with self.assertRaises(ValueError) as ctx2:
            CampaignPlan.from_dict(hpo_mixed)
        self.assertIn('architecture fields: num_layers', str(ctx2.exception))

    def test_interactive_agent_cli_workflow_context_propose_finalize(self) -> None:
        plan = json.loads(json.dumps(self.arch_plan))
        plan['proposals'] = []
        runner = CampaignRunner(self.root)
        campaign_id = runner.create(plan, plan_dir=EXAMPLES_DIR, kb_root=self.kb_dir, kb_id='ARCH-001')

        baseline = runner.run_baseline(campaign_id, poll_seconds=0.01)
        self.assertEqual(baseline['decision'], 'baseline')
        self.assertEqual(baseline['candidate_inference_flops_m'], 120.0)

        ctx = runner.get_context(campaign_id)
        self.assertEqual(ctx['track'], 'architecture')
        self.assertIn('num_layers', ctx['param_bounds'])
        self.assertEqual(len(ctx['knowledge']['patterns']), 3)
        self.assertEqual(len(ctx['knowledge']['anti_patterns']), 2)
        self.assertIn('trial-000', ctx['results_tsv'])

        runner.submit_proposal(
            campaign_id,
            Proposal(
                hypothesis='Depthwise separable conv + dilation=2 + k=7 for higher gain and lower FLOPs',
                changes={'conv_type': 'depthwise_separable', 'kernel_size': 7, 'dilation': 2},
                reuse_simulation=True,
            ),
        )
        trial = runner.run_active_trial(campaign_id, poll_seconds=0.01)
        self.assertEqual(trial['decision'], 'keep')
        self.assertGreater(trial['gain_vs_baseline'], 0)
        self.assertLess(trial['flops_ratio'], 1.0)

        final = runner.finalize_holdout(campaign_id, poll_seconds=0.01)
        self.assertEqual(final['status'], 'succeeded')
        self.assertTrue(final['holdout_report']['accepted'])
        self.assertEqual(final['holdout_report']['incumbent_trial_id'], 'trial-001')

    def test_gpu_seconds_budget_exhausts_campaign(self) -> None:
        plan = json.loads(json.dumps(self.arch_plan))
        plan['budget']['max_gpu_seconds'] = 80.0
        runner = CampaignRunner(self.root)
        campaign_id = runner.create(plan, plan_dir=EXAMPLES_DIR, kb_root=self.kb_dir, kb_id='ARCH-001')
        campaign = self._finish_campaign(runner, campaign_id)
        self.assertEqual(campaign['status'], 'budget_exhausted')
        self.assertGreaterEqual(campaign['total_gpu_seconds'], 80.0)
        self.assertLess(len(campaign['trials']), plan['budget']['max_trials'])

    def test_example_mcp_adapter_drives_harness_and_campaign(self) -> None:
        plan = json.loads(SINGLE_PLAN.read_text(encoding='utf-8'))
        plan.pop('mock')
        plan['architecture'] = {'num_layers': 6, 'conv_type': 'depthwise_separable'}
        plan['acceptance']['max_flops_ratio'] = 1.0
        adapter = ExampleMCPAdapter(StubRawMCPTransport())
        harness = Harness(self.root / 'adapter_single', client=adapter)
        run_id = harness.create(plan)
        for _ in range(20):
            run = harness.step(run_id)
            if run['status'] != 'running':
                break
        self.assertEqual(run['status'], 'succeeded')
        self.assertEqual(run['report']['mode'], 'mcp_example')
        self.assertTrue(run['report']['accepted'])
        self.assertEqual(run['report']['gain_correct'], 5)
        self.assertLess(run['report']['flops_ratio'], 1.0)
        self.assertGreater(run['report']['compute_usage']['gpu_seconds'], 0)

        unsafe_adapter = ExampleMCPAdapter(StubRawMCPTransport(support_idempotent_lookup=False))
        lookup = unsafe_adapter.call_tool('find_job', {'request_id': 'req-unknown'})
        self.assertFalse(lookup['found'])
        self.assertFalse(lookup['conclusive'])

        nocancel_adapter = ExampleMCPAdapter(StubRawMCPTransport(support_cancel=False))
        submitted = nocancel_adapter.call_tool('submit_simulation', {
            'request_id': 'r1', 'knowledge_sha256': 'abc', 'dataset_ref': 'ds', 'hypothesis': 'h',
        })
        stop_reply = nocancel_adapter.call_tool('stop_job', {'job_id': submitted['job_id']})
        self.assertFalse(stop_reply['supported'])


if __name__ == '__main__':
    unittest.main()
