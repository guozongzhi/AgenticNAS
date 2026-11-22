from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from autoresearcher_harness.campaign import CampaignRunner
from autoresearcher_harness.contracts import CampaignPlan, Proposal


CAMPAIGN_EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'campaign_throughput.json'


class CampaignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plan = json.loads(CAMPAIGN_EXAMPLE.read_text(encoding='utf-8'))
        self.plan['mock']['duration_seconds'] = 0
        self.runner = CampaignRunner(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def finish(self, campaign_id: str, proposer=None) -> dict:
        for _ in range(120):
            # Re-instantiate each step to verify cross-process SQLite checkpoint recovery.
            campaign = CampaignRunner(self.root, proposer=proposer).step(campaign_id)
            if campaign['status'] not in {'running', 'evaluating_holdout'}:
                return campaign
        self.fail('Campaign did not reach a terminal state')

    def test_end_to_end_ratchet_with_restarts_simplicity_crash_and_holdout(self) -> None:
        campaign_id = self.runner.create(self.plan, plan_dir=CAMPAIGN_EXAMPLE.parent)
        campaign = self.finish(campaign_id)
        self.assertEqual(campaign['status'], 'succeeded')
        self.assertIsNotNone(campaign['program_sha256'])
        self.assertEqual(len(campaign['trials']), 6)

        decisions = [trial['decision'] for trial in campaign['trials']]
        self.assertEqual(decisions, ['baseline', 'keep', 'discard', 'crash', 'keep', 'keep'])
        # trial-005 wins by simplicity over trial-004 (same dev score 21/24, lower complexity 1.0 < 2.0).
        self.assertEqual(campaign['incumbent_trial_id'], 'trial-005')
        self.assertEqual(campaign['trials'][4]['complexity_score'], 2.0)
        self.assertEqual(campaign['trials'][5]['complexity_score'], 1.0)
        self.assertIn('simplicity win', campaign['trials'][5]['decision_reason'])

        # Holdout evaluates the exact locked incumbent model_ref without retraining.
        report = campaign['holdout_report']
        self.assertIsNotNone(report)
        self.assertTrue(report['accepted'])
        self.assertEqual(report['evaluation_scope'], 'holdout')
        self.assertEqual(report['evaluator_ref'], self.plan['holdout_evaluator_ref'])
        self.assertEqual(report['model_ref'], campaign['trials'][5]['model_ref'])
        self.assertEqual(report['candidate_correct'], 20)

        holdout_run = self.runner.harness.status(campaign['holdout_run_id'])
        self.assertEqual(holdout_run['attempted_tasks'], 1)
        self.assertEqual(holdout_run['tasks'][0]['remote_status'], 'reused')
        self.assertEqual(holdout_run['tasks'][1]['remote_status'], 'reused')

        export_dir = self.runner.export(campaign_id)
        tsv_lines = (export_dir / 'results.tsv').read_text(encoding='utf-8').strip().splitlines()
        self.assertEqual(len(tsv_lines), 7)  # header + 6 trials
        self.assertTrue(tsv_lines[0].startswith('trial_id\tparent_trial\tstatus\t'))
        self.assertIn('\tbaseline\t', tsv_lines[1])
        self.assertIn('\tcrash\t', tsv_lines[4])

    def test_immutable_field_proposal_is_rejected_without_submission(self) -> None:
        class RogueProposer:
            def propose(self, context: dict) -> Proposal:
                return Proposal(
                    hypothesis='Attempt to change frozen architecture',
                    changes={'architecture': 'forbidden-large-model'},
                )

        self.plan['proposals'] = []
        campaign_id = self.runner.create(self.plan)
        campaign = self.finish(campaign_id, proposer=RogueProposer())
        self.assertEqual(campaign['status'], 'paused')
        self.assertIn('immutable fields: architecture', campaign['error'])
        # Only baseline trial should exist; rogue proposal must not create a second trial.
        self.assertEqual(len(campaign['trials']), 1)
        events = self.runner.events(campaign_id)
        self.assertTrue(any(event['kind'] == 'proposal_rejected' for event in events))

    def test_guardrail_violation_discards_higher_score_candidate(self) -> None:
        self.plan['budget']['max_trials'] = 2
        self.plan['proposals'] = [
            {
                'hypothesis': 'High overall accuracy but breaks mixed_error_rate guardrail',
                'changes': {'mixed_ratio': 0.05},
                'reuse_simulation': True,
                'mock_overrides': {
                    'eval_fixture': {
                        'baseline_correct': 16,
                        'candidate_correct': 23,
                        'total_cases': 24,
                        'metrics': {'mixed_error_rate': 0.35},
                    }
                },
            }
        ]
        campaign_id = self.runner.create(self.plan)
        campaign = self.finish(campaign_id)
        self.assertEqual(campaign['status'], 'succeeded')
        self.assertEqual(campaign['trials'][1]['decision'], 'discard')
        self.assertIn('guardrail violated', campaign['trials'][1]['decision_reason'])
        self.assertEqual(campaign['incumbent_trial_id'], 'trial-000')

    def test_per_trial_wall_budget_isolates_timeout_as_crash_and_continues(self) -> None:
        self.plan['budget']['max_trials'] = 3
        self.plan['budget']['per_trial_wall_seconds'] = 5.0
        self.plan['proposals'] = [
            {
                'hypothesis': 'Slow job exceeding per-trial time cap',
                'changes': {'epochs': 8},
                'reuse_simulation': True,
                'mock_overrides': {'duration_seconds': 100.0},
            },
            {
                'hypothesis': 'Fast valid candidate after timeout crash',
                'changes': {'mixed_ratio': 0.30},
                'reuse_simulation': True,
                'mock_overrides': {
                    'duration_seconds': 0,
                    'eval_fixture': {
                        'baseline_correct': 16,
                        'candidate_correct': 20,
                        'total_cases': 24,
                        'metrics': {'mixed_error_rate': 0.14},
                    },
                },
            },
        ]
        campaign_id = self.runner.create(self.plan)
        for _ in range(30):
            state = self.runner.step(campaign_id)
            if state['active_trial_id'] == 'trial-001':
                break
        self.assertEqual(self.runner.status(campaign_id)['active_trial_id'], 'trial-001')
        # Submit slow trial-001 training task, then simulate per-trial wall-clock expiry in engine.
        self.runner.step(campaign_id)
        trial_run_id = self.runner.status(campaign_id)['trials'][1]['run_id']
        trial_created = self.runner.harness.status(trial_run_id)['created_at']
        with patch('autoresearcher_harness.engine.time.time', return_value=trial_created + 10.0):
            for _ in range(20):
                state = self.runner.step(campaign_id)
                if state['active_trial_id'] != 'trial-001':
                    break
        campaign = self.finish(campaign_id)
        self.assertEqual(campaign['status'], 'succeeded')
        self.assertEqual([t['decision'] for t in campaign['trials']], ['baseline', 'crash', 'keep'])
        self.assertEqual(campaign['incumbent_trial_id'], 'trial-002')

    def test_campaign_plan_rejects_shared_dev_and_holdout_evaluator(self) -> None:
        bad = json.loads(json.dumps(self.plan))
        bad['holdout_evaluator_ref'] = bad['dev_evaluator_ref']
        with self.assertRaises(ValueError):
            CampaignPlan.from_dict(bad)

    def test_campaign_cancel_stops_active_trial_and_skips_holdout(self) -> None:
        self.plan['mock']['duration_seconds'] = 100
        campaign_id = self.runner.create(self.plan)
        self.runner.step(campaign_id)  # create baseline trial
        self.runner.step(campaign_id)  # submit baseline simulation
        self.runner.request_stop(campaign_id)
        campaign = self.finish(campaign_id)
        self.assertEqual(campaign['status'], 'cancelled')
        self.assertIsNone(campaign['holdout_run_id'])
        self.assertIsNone(campaign['holdout_report'])
        self.assertEqual(campaign['trials'][0]['decision'], 'cancelled')

    def test_proposer_receives_results_tsv_memory_and_stops_early(self) -> None:
        seen_tsvs: list[str] = []

        class MemoryAwareProposer:
            def propose(self, context: dict) -> Proposal | None:
                seen_tsvs.append(context['results_tsv'])
                if len(seen_tsvs) == 1:
                    return Proposal(
                        hypothesis='Single targeted edit after inspecting baseline',
                        changes={'mixed_ratio': 0.30},
                        reuse_simulation=True,
                        mock_overrides={
                            'eval_fixture': {
                                'baseline_correct': 16,
                                'candidate_correct': 20,
                                'total_cases': 24,
                                'metrics': {'mixed_error_rate': 0.14},
                            }
                        },
                    )
                return None

        self.plan['proposals'] = []
        campaign_id = self.runner.create(self.plan)
        campaign = self.finish(campaign_id, proposer=MemoryAwareProposer())
        self.assertEqual(campaign['status'], 'succeeded')
        self.assertEqual(len(seen_tsvs), 2)
        self.assertIn('trial-000', seen_tsvs[0])
        self.assertIn('trial-001', seen_tsvs[1])
        self.assertIn('\tkeep\t', seen_tsvs[1])
        self.assertEqual(campaign['incumbent_trial_id'], 'trial-001')

    def test_baseline_crash_fails_campaign_without_holdout(self) -> None:
        self.plan['mock']['fail_stage'] = 'training'
        campaign_id = self.runner.create(self.plan)
        campaign = self.finish(campaign_id)
        self.assertEqual(campaign['status'], 'failed')
        self.assertEqual(campaign['trials'][0]['decision'], 'crash')
        self.assertIsNone(campaign['holdout_run_id'])


if __name__ == '__main__':
    unittest.main()
