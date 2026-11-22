from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from autoresearcher_harness.campaign import CampaignRunner
from autoresearcher_harness.contracts import Proposal
from autoresearcher_harness.engine import Harness
from autoresearcher_harness.knowledge_base import KnowledgeBase
from autoresearcher_harness.mcp_adapter_example import ConfigurableMCPAdapter, DEFAULT_MCP_MAPPING, StubRawMCPTransport
from autoresearcher_harness.scaffold import init_workspace


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / 'examples'
BYO_PLAN = EXAMPLES_DIR / 'campaign_byo_mcp_nmse.json'
KB_SOURCE = EXAMPLES_DIR / 'kb'
SINGLE_PLAN = EXAMPLES_DIR / 'throughput.json'


class GenericBYOMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'outputs'
        self.kb_dir = Path(self.temp.name) / 'kb'
        shutil.copytree(KB_SOURCE, self.kb_dir)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_byo_mcp_minimize_nmse_nested_dotpath_compute_win_and_kb_distill(self) -> None:
        plan = json.loads(BYO_PLAN.read_text(encoding='utf-8'))
        runner = CampaignRunner(self.root)
        cid = runner.create(plan, plan_dir=EXAMPLES_DIR, kb_root=self.kb_dir, kb_id='CNN-CSI-001')

        # 1. Baseline ticket + record (minimize nmse_db, macs_m compute, gpu_hours cost)
        base_ticket = runner.run_baseline(cid)
        self.assertEqual(base_ticket['run_status'], 'awaiting_result')
        self.assertEqual(base_ticket['candidate_config']['encoder']['num_blocks'], 4)
        base_done = runner.record_trial(
            cid,
            status='succeeded',
            metrics={'nmse_db': -16.5, 'macs_m': 50.0, 'latency_ms': 1.8},
            cost={'gpu_hours': 0.4},
            artifacts={'model_ref': 'uri://models/csi-base'},
            external_jobs=[{'tool': 'csi_train', 'job_id': 'j-0'}],
        )
        self.assertEqual(base_done['decision'], 'baseline')
        self.assertEqual(base_done['primary_value'], -16.5)

        # 2. Nested param_bounds check blocks out-of-range dot-path change
        with self.assertRaises(ValueError) as ctx:
            runner.submit_proposal(
                cid,
                Proposal(hypothesis='Too many encoder blocks', changes={'encoder.num_blocks': 20}),
            )
        self.assertIn('param_bounds', str(ctx.exception))

        # 3. Trial-001: nested dot-path gain win (-18.2 dB is +1.7 dB better than -16.5 dB under minimize)
        t1 = runner.submit_proposal(
            cid,
            Proposal(
                hypothesis='Enable SE attention and k=5 in encoder',
                changes={'encoder.use_se': True, 'encoder.kernel_size': 5},
            ),
        )
        self.assertTrue(t1['candidate_config']['encoder']['use_se'])
        self.assertEqual(t1['candidate_config']['encoder']['kernel_size'], 5)
        t1_done = runner.record_trial(
            cid,
            status='succeeded',
            metrics={'nmse_db': -18.2, 'macs_m': 51.2, 'latency_ms': 1.9},
            cost={'gpu_hours': 0.45},
            artifacts={'model_ref': 'uri://models/csi-t1'},
        )
        self.assertEqual(t1_done['decision'], 'keep')
        self.assertAlmostEqual(t1_done['gain'], 1.7, places=3)
        self.assertAlmostEqual(t1_done['compute_ratio'], 1.024, places=3)

        # 4. Trial-002: better NMSE but exceeds macs_m compute budget -> discarded!
        runner.submit_proposal(
            cid,
            Proposal(hypothesis='Double encoder channels', changes={'encoder.channels': 128}),
        )
        t2_done = runner.record_trial(
            cid,
            status='succeeded',
            metrics={'nmse_db': -19.0, 'macs_m': 92.0, 'latency_ms': 2.1},
            cost={'gpu_hours': 0.8},
            artifacts={'model_ref': 'uri://models/csi-t2'},
        )
        self.assertEqual(t2_done['decision'], 'discard')
        self.assertIn('compute budget exceeded', t2_done['decision_reason'])

        # 5. Trial-003: remote MCP crash isolated with cost still accounted
        runner.submit_proposal(
            cid,
            Proposal(hypothesis='Deep refine blocks trigger OOM', changes={'decoder.refine_blocks': 4}),
        )
        t3_done = runner.record_trial(
            cid,
            status='crash',
            cost={'gpu_hours': 0.15},
            note='Remote GPU OOM',
        )
        self.assertEqual(t3_done['decision'], 'crash')
        self.assertEqual(runner.status(cid)['incumbent_trial_id'], 'trial-001')

        # 6. Trial-004: tied NMSE within tie_tolerance=0.05 but lower MACs -> compute win!
        runner.submit_proposal(
            cid,
            Proposal(hypothesis='Prune decoder refine blocks to cut MACs', changes={'decoder.refine_blocks': 1}),
        )
        t4_done = runner.record_trial(
            cid,
            status='succeeded',
            metrics={'nmse_db': -18.22, 'macs_m': 44.5, 'latency_ms': 1.5},
            cost={'gpu_hours': 0.35},
            artifacts={'model_ref': 'uri://models/csi-t4'},
        )
        self.assertEqual(t4_done['decision'], 'keep')
        self.assertIn('compute win', t4_done['decision_reason'])
        self.assertEqual(runner.status(cid)['incumbent_trial_id'], 'trial-004')

        # 7. Holdout rejects mismatched model_ref, accepts matching incumbent model_ref
        with self.assertRaises(ValueError):
            runner.finalize_external_holdout(
                cid,
                metrics={'nmse_db': -18.3, 'macs_m': 44.5, 'latency_ms': 1.5},
                artifacts={'model_ref': 'uri://models/wrong-model'},
            )
        final = runner.finalize_external_holdout(
            cid,
            metrics={'nmse_db': -18.1, 'macs_m': 44.5, 'latency_ms': 1.5},
            cost={'gpu_hours': 0.05},
            artifacts={'model_ref': 'uri://models/csi-t4'},
        )
        self.assertEqual(final['status'], 'succeeded')
        report = final['holdout_report']
        self.assertTrue(report['accepted'])
        self.assertEqual(report['primary_metric_name'], 'nmse_db')
        self.assertAlmostEqual(report['gain'], 1.6, places=3)
        self.assertLess(report['compute_ratio'], 1.0)
        self.assertAlmostEqual(report['campaign_compute_usage']['total_cost'], 2.2, places=3)

        # 8. Export results.tsv with dynamic metric headers + distill & publish to Markdown KB
        export_dir = runner.export(cid)
        tsv = (export_dir / 'results.tsv').read_text(encoding='utf-8')
        self.assertIn('primary(nmse_db)\tgain\tcompute(macs_m)\tcompute_ratio\tcost(gpu_hours)', tsv)

        kb = KnowledgeBase(self.kb_dir)
        draft = kb.distill_from_campaign(final)
        self.assertEqual(draft['kb_id'], 'CNN-CSI-001')
        published = kb.publish('CNN-CSI-001', reviewer='csi-lead')
        self.assertEqual(published['revision'], 'v2')
        self.assertEqual(len(kb.search(model_family='cnn_csi')), 1)

    def test_cost_metric_budget_stops_external_mcp_campaign(self) -> None:
        plan = json.loads(BYO_PLAN.read_text(encoding='utf-8'))
        plan['budget']['cost_metric']['max_total'] = 0.5
        runner = CampaignRunner(self.root)
        cid = runner.create(plan, plan_dir=EXAMPLES_DIR, kb_root=self.kb_dir, kb_id='CNN-CSI-001')
        runner.run_baseline(cid)
        runner.record_trial(
            cid,
            status='succeeded',
            metrics={'nmse_db': -16.5, 'macs_m': 50.0, 'latency_ms': 1.8},
            cost={'gpu_hours': 0.6},
            artifacts={'model_ref': 'uri://models/base'},
        )
        self.assertEqual(runner.status(cid)['status'], 'budget_exhausted')

    def test_configurable_mcp_adapter_drives_harness_via_json_mapping(self) -> None:
        plan = json.loads(SINGLE_PLAN.read_text(encoding='utf-8'))
        plan.pop('mock')
        plan['architecture'] = {'num_layers': 6, 'conv_type': 'depthwise_separable'}
        adapter = ConfigurableMCPAdapter(StubRawMCPTransport(), mapping=DEFAULT_MCP_MAPPING)
        harness = Harness(self.root / 'cfg_adapter', client=adapter)
        run_id = harness.create(plan)
        for _ in range(20):
            run = harness.step(run_id)
            if run['status'] != 'running':
                break
        self.assertEqual(run['status'], 'succeeded')
        self.assertEqual(run['report']['mode'], 'configurable_mcp')
        self.assertTrue(run['report']['accepted'])
        self.assertEqual(run['report']['gain_correct'], 5)

    def test_engineer_init_scaffold_runs_full_loop_without_code_changes(self) -> None:
        ws = Path(self.temp.name) / 'vit_edge_workspace'
        created = init_workspace(
            workspace=ws,
            model_family='vit_edge_detector',
            kb_id='VIT-ARCH-001',
            primary_metric='map50',
            direction='maximize',
            min_gain=0.5,
            holdout_target=72.0,
            compute_metric='latency_ms',
            compute_unit='ms',
            max_compute_value=8.0,
            max_compute_ratio=1.05,
            cost_metric='gpu_seconds',
            cost_unit='s',
            max_cost=1800.0,
            max_trials=5,
            track='architecture',
            stages=['training', 'evaluation'],
        )
        self.assertTrue(Path(created['campaign_plan']).is_file())
        self.assertTrue(Path(created['program_md']).is_file())
        self.assertTrue(Path(created['mcp_tools_md']).is_file())
        self.assertTrue(Path(created['kb_index']).is_file())

        # Immediately execute a full BYO-MCP cycle using the scaffolded artifacts as-is.
        runner = CampaignRunner(ws / 'outputs')
        plan = json.loads(Path(created['campaign_plan']).read_text(encoding='utf-8'))
        cid = runner.create(plan, plan_dir=ws, kb_root=ws / 'kb', kb_id='VIT-ARCH-001')
        runner.run_baseline(cid)
        runner.record_trial(
            cid,
            metrics={'map50': 70.0, 'latency_ms': 7.5},
            cost={'gpu_seconds': 200},
            artifacts={'model_ref': 'uri://vit/base'},
        )
        runner.submit_proposal(
            cid,
            Proposal(
                hypothesis='Switch to inverted_bottleneck and widen head',
                changes={'backbone.block_type': 'inverted_bottleneck', 'head.hidden_dim': 192},
            ),
        )
        t1 = runner.record_trial(
            cid,
            metrics={'map50': 73.2, 'latency_ms': 7.1},
            cost={'gpu_seconds': 210},
            artifacts={'model_ref': 'uri://vit/t1'},
        )
        self.assertEqual(t1['decision'], 'keep')
        final = runner.finalize_external_holdout(
            cid,
            metrics={'map50': 72.8, 'latency_ms': 7.1},
            cost={'gpu_seconds': 30},
            artifacts={'model_ref': 'uri://vit/t1'},
        )
        self.assertTrue(final['holdout_report']['accepted'])
        kb = KnowledgeBase(ws / 'kb')
        kb.distill_from_campaign(final)
        pub = kb.publish('VIT-ARCH-001', reviewer='vit-eng')
        self.assertEqual(pub['revision'], 'v2')


if __name__ == '__main__':
    unittest.main()
