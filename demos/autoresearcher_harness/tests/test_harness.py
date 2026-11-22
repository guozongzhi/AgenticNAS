from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from autoresearcher_harness.engine import Harness
from autoresearcher_harness.contracts import Plan
from autoresearcher_harness.mock_mcp import MockMCP
from autoresearcher_harness.store import WorkerBusy


EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'throughput.json'


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plan = json.loads(EXAMPLE.read_text())
        self.plan['mock']['duration_seconds'] = 0
        self.harness = Harness(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def finish(self, run_id: str) -> dict:
        for _ in range(25):
            run = Harness(self.root).step(run_id)
            if run['status'] != 'running':
                return run
        self.fail('Run did not reach a terminal state')

    def test_end_to_end_restarts_preserve_artifact_lineage_and_trace(self) -> None:
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'succeeded')
        self.assertTrue(run['report']['accepted'])
        self.assertEqual(len(run['tasks']), 3)
        for task in run['tasks']:
            self.assertTrue((self.root / task['log_path']).is_file())
        events = self.harness.events(run_id)
        training = next(event for event in events if event['kind'] == 'tool_call' and event['data']['name'] == 'submit_training')
        self.assertEqual(training['data']['arguments']['dataset_ref'], run['tasks'][0]['result']['dataset_ref'])
        evaluation = next(event for event in events if event['kind'] == 'tool_call' and event['data']['name'] == 'submit_evaluation')
        self.assertEqual(evaluation['data']['arguments']['model_ref'], run['tasks'][1]['result']['model_ref'])
        self.harness.export(run_id)
        self.assertTrue((self.root / run_id / 'report.json').is_file())
        self.assertTrue((self.root / run_id / 'trace.jsonl').is_file())
        self.assertEqual(len(list(self.harness.mcp_jobs())), 3)

    def test_lost_submit_response_reconciles_without_duplicate_job(self) -> None:
        self.plan['mock']['lose_submit_reply_stage'] = 'simulation'
        run_id = self.harness.create(self.plan)
        paused = self.harness.step(run_id)
        self.assertEqual(paused['status'], 'paused')
        self.assertEqual(paused['tasks'][0]['status'], 'reconciling')
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')
        self.assertEqual(len(list(self.harness.mcp_jobs())), 3)

    def test_cancel_during_submission_unknown_state_stops_reconciled_job(self) -> None:
        self.plan['mock'].update(duration_seconds=100, lose_submit_reply_stage='simulation')
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        self.harness.request_stop(run_id)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'cancelled')
        self.assertEqual(run['tasks'][0]['remote_status'], 'cancelled')
        self.assertEqual(len(list(self.harness.mcp_jobs())), 1)

    def test_cancel_prevents_downstream_even_if_remote_already_finished(self) -> None:
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        self.harness.request_stop(run_id)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'cancelled')
        self.assertEqual(run['tasks'][1]['status'], 'pending')
        self.assertEqual(len(list(self.harness.mcp_jobs())), 1)

    def test_failed_training_collects_logs_and_prevents_evaluation(self) -> None:
        self.plan['mock']['fail_stage'] = 'training'
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'failed')
        self.assertEqual(run['tasks'][2]['status'], 'pending')
        self.assertTrue((self.root / run['tasks'][1]['log_path']).is_file())

    def test_attempt_budget_counts_submissions_and_blocks_next_stage(self) -> None:
        self.plan['budget']['max_tasks'] = 1
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'budget_exhausted')
        self.assertEqual(run['attempted_tasks'], 1)
        self.assertEqual(len(list(self.harness.mcp_jobs())), 1)

    def test_wall_budget_stops_active_job(self) -> None:
        self.plan['budget']['wall_seconds'] = 1
        self.plan['mock']['duration_seconds'] = 10000
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        with patch('autoresearcher_harness.engine.time.time', return_value=time.time() + 2):
            run = self.finish(run_id)
        self.assertEqual(run['status'], 'budget_exhausted')
        self.assertEqual(run['tasks'][0]['remote_status'], 'cancelled')
        self.assertEqual(len(list(self.harness.mcp_jobs())), 1)

    def test_knowledge_snapshot_is_frozen(self) -> None:
        run_id = self.harness.create(self.plan)
        self.plan['knowledge']['text'] = 'changed later'
        stored = self.harness.status(run_id)
        self.assertNotEqual(stored['plan']['knowledge']['text'], 'changed later')
        self.assertEqual(len(stored['knowledge_sha256']), 64)

    def test_plan_rejects_unpublished_knowledge_and_invalid_budgets(self) -> None:
        self.plan['knowledge']['status'] = 'draft'
        with self.assertRaises(ValueError):
            Plan.from_dict(self.plan)
        self.plan['knowledge']['status'] = 'published'
        for budget in [0, -1, True, 1.5]:
            self.plan['budget']['max_tasks'] = budget
            with self.assertRaises(ValueError):
                Plan.from_dict(self.plan)

    def test_plan_rejects_unknown_schema_and_missing_training_permission(self) -> None:
        self.plan['schema_version'] = 9
        with self.assertRaises(ValueError):
            Plan.from_dict(self.plan)
        self.plan['schema_version'] = 1
        self.plan['knowledge']['approved_uses'] = ['retrieval']
        with self.assertRaises(ValueError):
            Plan.from_dict(self.plan)

    def test_terminal_resume_is_idempotent(self) -> None:
        run_id = self.harness.create(self.plan)
        original = self.finish(run_id)
        self.assertEqual(self.harness.step(run_id), original)
        self.assertEqual(len(list(self.harness.mcp_jobs())), 3)

    def test_process_exit_after_remote_acceptance_recovers_from_intent(self) -> None:
        mock = MockMCP(self.root, self.plan['mock'])
        original = mock.call_tool

        def crash(name: str, arguments: dict) -> dict:
            result = original(name, arguments)
            if name == 'submit_simulation':
                raise SystemExit('Fixture abrupt process exit')
            return result

        run_id = self.harness.create(self.plan)
        with patch.object(mock, 'call_tool', side_effect=crash):
            with self.assertRaises(SystemExit):
                Harness(self.root, mock).step(run_id)
        self.assertEqual(self.harness.status(run_id)['tasks'][0]['status'], 'reconciling')
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')
        self.assertEqual(len(self.harness.mcp_jobs()), 3)

    def test_concurrent_worker_cannot_submit_second_job(self) -> None:
        run_id = self.harness.create(self.plan)
        with self.harness.store.worker_lock(run_id):
            with self.assertRaises(WorkerBusy):
                Harness(self.root).step(run_id)
        self.assertEqual(len(self.harness.mcp_jobs()), 0)
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')

    def test_unknown_remote_status_pauses_without_advancing(self) -> None:
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        mock = MockMCP(self.root, self.plan['mock'])
        with patch.object(mock, 'call_tool', return_value={'status': 'UNRECOGNIZED'}):
            paused = Harness(self.root, mock).step(run_id)
        self.assertEqual(paused['status'], 'paused')
        self.assertEqual(paused['tasks'][1]['status'], 'pending')
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')

    def test_missing_artifact_blocks_downstream(self) -> None:
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        mock = MockMCP(self.root, self.plan['mock'])
        original = mock.call_tool

        def missing(name: str, arguments: dict) -> dict:
            if name == 'get_job':
                return {'status': 'succeeded', 'result': {}}
            return original(name, arguments)

        with patch.object(mock, 'call_tool', side_effect=missing):
            Harness(self.root, mock).step(run_id)
            run = Harness(self.root, mock).step(run_id)
        self.assertEqual(run['status'], 'paused')
        self.assertIn('Missing dataset_ref', run['error'])
        self.assertEqual(len(self.harness.mcp_jobs()), 1)
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')

    def test_failed_log_download_retries_collection_without_resubmission(self) -> None:
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        self.harness.step(run_id)
        mock = MockMCP(self.root, self.plan['mock'])
        with patch.object(mock, 'call_tool', side_effect=TimeoutError('log download interrupted')):
            run = Harness(self.root, mock).step(run_id)
        self.assertEqual(run['status'], 'paused')
        self.assertEqual(run['tasks'][0]['status'], 'collecting')
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')
        self.assertEqual(len(self.harness.mcp_jobs()), 3)

    def test_uneventful_execution_can_fail_acceptance(self) -> None:
        self.plan['acceptance']['min_correct'] = 21
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'succeeded')
        self.assertFalse(run['report']['accepted'])

    def test_mismatched_evaluation_is_rejected(self) -> None:
        self.plan['acceptance']['total_cases'] = 25
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'paused')
        self.assertIsNone(run['report'])

    def test_mismatched_model_reference_can_recover_after_result_correction(self) -> None:
        run_id = self.harness.create(self.plan)
        for _ in range(7):
            self.harness.step(run_id)
        mock = MockMCP(self.root, self.plan['mock'])
        original = mock.call_tool

        def mismatched(name: str, arguments: dict) -> dict:
            result = original(name, arguments)
            if name == 'get_job':
                result['result']['model_ref'] = 'mock://wrong-model'
            return result

        with patch.object(mock, 'call_tool', side_effect=mismatched):
            Harness(self.root, mock).step(run_id)
            run = Harness(self.root, mock).step(run_id)
        self.assertEqual(run['status'], 'paused')
        self.assertIn('mismatched model_ref', run['error'])
        self.assertEqual(run['tasks'][2]['status'], 'collecting')
        self.assertEqual(self.finish(run_id)['status'], 'succeeded')

    def test_plan_rejects_malformed_case_counts_and_mock_settings(self) -> None:
        cases = [
            ('acceptance', 'min_correct', 25),
            ('acceptance', 'total_cases', True),
            ('mock', 'duration_seconds', -1),
            ('mock', 'fail_stage', 'arbitrary-code'),
            ('knowledge', 'approved_uses', 'training'),
            ('budget', 'wall_seconds', float('inf')),
        ]
        for section, key, value in cases:
            with self.subTest(section=section, key=key, value=value):
                plan = json.loads(json.dumps(self.plan))
                plan[section][key] = value
                with self.assertRaises(ValueError):
                    Plan.from_dict(plan)

    def test_stop_job_is_throttled_and_degrades_when_unsupported(self) -> None:
        self.plan['mock'].update(duration_seconds=100, stop_unsupported=True)
        run_id = self.harness.create(self.plan)
        self.harness.step(run_id)
        self.harness.request_stop(run_id)
        first = self.harness.step(run_id)
        second = self.harness.step(run_id)
        self.assertEqual(first['status'], 'running')
        self.assertEqual(second['status'], 'running')
        stop_calls = [
            e for e in self.harness.events(run_id)
            if e['kind'] == 'tool_call' and e['data']['name'] == 'stop_job'
        ]
        self.assertEqual(len(stop_calls), 1)
        self.assertTrue(second['tasks'][0]['stop_unsupported'])

    def test_stop_job_backoff_prevents_repeated_calls_per_poll(self) -> None:
        class SlowCancelClient:
            mode = 'mock'

            def __init__(self) -> None:
                self.stops = 0

            def call_tool(self, name: str, arguments: dict) -> dict:
                if name == 'submit_simulation':
                    return {'job_id': 'job-1'}
                if name == 'stop_job':
                    self.stops += 1
                    return {'status': 'cancelling'}
                if name == 'get_job':
                    return {'status': 'running', 'result': {}}
                raise AssertionError(f'Unexpected tool: {name}')

        client = SlowCancelClient()
        harness = Harness(self.root, client=client, stop_retry_seconds=60.0)
        run_id = harness.create(self.plan)
        harness.step(run_id)
        harness.request_stop(run_id)
        harness.step(run_id)
        harness.step(run_id)
        self.assertEqual(client.stops, 1)

    def test_wall_budget_during_final_eval_collection_preserves_report(self) -> None:
        run_id = self.harness.create(self.plan)
        # Advance through simulation, training, and evaluation submit + get_job -> collecting.
        for _ in range(8):
            run = self.harness.step(run_id)
        self.assertEqual(run['tasks'][2]['status'], 'collecting')
        with patch('autoresearcher_harness.engine.time.time', return_value=run['created_at'] + 9999):
            final = self.harness.step(run_id)
        self.assertEqual(final['status'], 'succeeded')
        self.assertIsNotNone(final['report'])
        self.assertTrue(final['report']['accepted'])

    def test_plan_allows_optional_mock_with_live_client_mode(self) -> None:
        class LiveClient:
            def call_tool(self, name: str, arguments: dict) -> dict:
                if name.startswith('submit_'):
                    return {'job_id': 'live-' + name}
                if name == 'get_job':
                    job_id = arguments['job_id']
                    if job_id.endswith('simulation'):
                        return {'status': 'succeeded', 'result': {'dataset_ref': 's3://ds/1'}}
                    if job_id.endswith('training'):
                        return {'status': 'succeeded', 'result': {'model_ref': 's3://model/1'}}
                    return {
                        'status': 'succeeded',
                        'result': {
                            'baseline_correct': 16,
                            'candidate_correct': 20,
                            'total_cases': 24,
                            'model_ref': 's3://model/1',
                            'baseline_model_ref': 'mock://models/baseline-v1',
                            'evaluator_ref': 'mock://evaluators/throughput-holdout-v1',
                        },
                    }
                if name == 'download_logs':
                    return {'text': 'live-log\n'}
                raise AssertionError(f'Unexpected tool: {name}')

        plan = json.loads(json.dumps(self.plan))
        plan.pop('mock')
        harness = Harness(self.root, client=LiveClient())
        run_id = harness.create(plan)
        for _ in range(15):
            run = harness.step(run_id)
            if run['status'] != 'running':
                break
        self.assertEqual(run['status'], 'succeeded')
        self.assertEqual(run['report']['mode'], 'live')

    def test_reuse_model_ref_runs_evaluation_only(self) -> None:
        self.plan['reuse_dataset_ref'] = 'mock://datasets/reused-1'
        self.plan['reuse_model_ref'] = 'mock://models/reused-1'
        self.plan['budget']['max_tasks'] = 1
        run_id = self.harness.create(self.plan)
        run = self.finish(run_id)
        self.assertEqual(run['status'], 'succeeded')
        self.assertEqual(run['attempted_tasks'], 1)
        self.assertEqual(run['report']['model_ref'], 'mock://models/reused-1')
        self.assertEqual(len(self.harness.mcp_jobs()), 1)


if __name__ == '__main__':
    unittest.main()
