from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SKILL_SRC = Path(__file__).resolve().parents[1]


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)


class SelfContainedAutoResearchSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.temp.name)
        self.isolated_skill = self.sandbox / "standalone_skill" / "autoresearch"
        shutil.copytree(SKILL_SRC, self.isolated_skill)
        self.cli = self.isolated_skill / "scripts" / "autoresearch.py"
        self.install_sh = self.isolated_skill / "scripts" / "install.sh"
        self.project_dir = self.sandbox / "external_model_repo"
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_bundled_prebuilt_knowledge_base_entries_and_install_lifecycle(self) -> None:
        res_list = _run([sys.executable, str(self.cli), "knowledge-base", "list"], cwd=self.project_dir)
        self.assertEqual(res_list.returncode, 0, msg=res_list.stderr)
        entries = json.loads(res_list.stdout)
        entry_ids = {item["entry_id"] for item in entries}
        self.assertEqual(
            entry_ids,
            {"CONV1D-ARCH-001", "EDGE-VIT-ARCH-001", "CNN-CSI-ARCH-001", "FIXED-BACKBONE-HPO-001"},
        )

        res_search = _run([
            sys.executable, str(self.cli), "knowledge-base", "search",
            "--model-family", "conv1d_transformer",
            "--direction", "gain_up_compute_down",
        ], cwd=self.project_dir)
        self.assertEqual(res_search.returncode, 0, msg=res_search.stderr)
        matched = json.loads(res_search.stdout)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["entry_id"], "CONV1D-ARCH-001")

        res_copy = _run(
            ["bash", str(self.install_sh), "--project", str(self.project_dir), "--copy"],
            cwd=self.project_dir,
        )
        self.assertEqual(res_copy.returncode, 0, msg=res_copy.stderr)

        res_check = _run(
            ["bash", str(self.install_sh), "--project", str(self.project_dir), "--check"],
            cwd=self.project_dir,
        )
        self.assertEqual(res_check.returncode, 0, msg=res_check.stderr)
        self.assertIn("OK: autoresearch.py doctor passed", res_check.stdout)

        res_rm = _run(
            ["bash", str(self.install_sh), "--project", str(self.project_dir), "--uninstall"],
            cwd=self.project_dir,
        )
        self.assertEqual(res_rm.returncode, 0, msg=res_rm.stderr)
        self.assertFalse((self.project_dir / ".agents" / "skills" / "autoresearch").exists())

    def test_presets_guards_ratchet_awaiting_holdout_and_hpo_handoff(self) -> None:
        arch_ws = self.project_dir / "csi_arch_ws"
        res_init = _run([
            sys.executable, str(self.cli), "init",
            "--workspace", str(arch_ws),
            "--preset", "cnn_csi",
            "--model-family", "cnn_csi_feedback",
            "--entry-id", "CSI-ARCH-001",
            "--metric", "nmse_db",
            "--direction", "minimize",
            "--min-gain", "0.3",
            "--tie-tolerance", "0.05",
            "--holdout-target", "-18.0",
            "--compute", "macs_m",
            "--max-compute-ratio", "1.10",
            "--cost", "gpu_hours",
            "--max-cost", "1.0",
            "--max-trials", "6",
        ], cwd=self.project_dir)
        self.assertEqual(res_init.returncode, 0, msg=res_init.stderr)

        res_cfg = _run([
            sys.executable, str(self.cli), "configure",
            "--workspace", str(arch_ws),
            "--forbidden-ops", "nn.Linear",
            "--guardrails", json.dumps({"max_metrics": {"latency_ms": 2.5}}),
        ], cwd=self.project_dir)
        self.assertEqual(res_cfg.returncode, 0, msg=res_cfg.stderr)

        mcp_md = arch_ws / "mcp_tools.md"
        mcp_md.write_text(
            mcp_md.read_text(encoding="utf-8")
            .replace("<your_training_mcp_tool>", "mcp_train")
            .replace("<your_evaluation_mcp_tool>", "mcp_eval"),
            encoding="utf-8",
        )
        doc = json.loads(_run([
            sys.executable, str(self.cli), "doctor", "--workspace", str(arch_ws),
        ], cwd=self.project_dir).stdout)
        self.assertTrue(doc["ok"])

        ws_cmd = [sys.executable, str(self.cli), "--workspace", str(arch_ws)]
        created = json.loads(_run([*ws_cmd, "campaign", "create"], cwd=self.project_dir).stdout)
        cid = created["campaign_id"]

        self.assertEqual(_run([*ws_cmd, "campaign", "baseline", cid], cwd=self.project_dir).returncode, 0)
        self.assertEqual(_run([
            *ws_cmd, "campaign", "record", cid,
            "--metrics", json.dumps({"nmse_db": -17.5, "macs_m": 50.0, "latency_ms": 2.0}),
            "--cost", json.dumps({"gpu_hours": 0.30}),
            "--artifacts", json.dumps({"model_ref": "s3://csi/base.pt"}),
        ], cwd=self.project_dir).returncode, 0)

        noop = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "No-op channels=64",
            "--changes", json.dumps({"encoder.channels": 64}),
        ], cwd=self.project_dir)
        self.assertEqual(noop.returncode, 2)
        self.assertIn("No-op proposal", noop.stderr)

        anti = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "Try known bad channels=128",
            "--changes", json.dumps({"encoder.channels": 128}),
        ], cwd=self.project_dir)
        self.assertEqual(anti.returncode, 2)
        self.assertIn("Blocked by knowledge_base anti-pattern", anti.stderr)

        self.assertEqual(_run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "Enable SE and k5 prior",
            "--changes", json.dumps({"encoder.use_se": True, "encoder.kernel_size": 5}),
        ], cwd=self.project_dir).returncode, 0)
        r1 = json.loads(_run([
            *ws_cmd, "campaign", "record", cid,
            "--metrics", json.dumps({"nmse_db": -18.4, "macs_m": 51.2, "latency_ms": 2.1}),
            "--cost", json.dumps({"gpu_hours": 0.35}),
            "--artifacts", json.dumps({"model_ref": "s3://csi/t001.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r1["decision"], "keep")

        self.assertEqual(_run([
            *ws_cmd, "campaign", "propose", cid,
            "--operator", "shrink",
            "--hypothesis", "Slim decoder channels to 48 to cut MACs at tied NMSE",
            "--changes", json.dumps({"decoder.channels": 48}),
        ], cwd=self.project_dir).returncode, 0)
        r2 = json.loads(_run([
            *ws_cmd, "campaign", "record", cid,
            "--metrics", json.dumps({"nmse_db": -18.37, "macs_m": 46.5, "latency_ms": 1.9}),
            "--cost", json.dumps({"gpu_hours": 0.40}),
            "--artifacts", json.dumps({"model_ref": "s3://csi/t002.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r2["decision"], "keep")
        self.assertEqual(r2["campaign_status"], "awaiting_holdout")

        fin = json.loads(_run([
            *ws_cmd, "campaign", "finalize", cid,
            "--metrics", json.dumps({"nmse_db": -18.35, "macs_m": 46.5, "latency_ms": 1.9, "baseline_nmse_db": -17.45}),
            "--cost", json.dumps({"gpu_hours": 0.05}),
            "--artifacts", json.dumps({"model_ref": "s3://csi/t002.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(fin["status"], "succeeded")
        self.assertTrue(Path(fin["report_md_path"]).is_file())
        self.assertIn("Pareto Hypervolume", Path(fin["report_md_path"]).read_text(encoding="utf-8"))

        # HPO handoff
        hpo_ws = self.project_dir / "csi_hpo_ws"
        self.assertEqual(_run([
            sys.executable, str(self.cli), "init",
            "--workspace", str(hpo_ws),
            "--preset", "hpo_recipe",
            "--model-family", "cnn_csi_feedback",
            "--entry-id", "CSI-HPO-001",
            "--track", "hpo",
            "--metric", "nmse_db",
            "--direction", "minimize",
            "--min-gain", "0.1",
            "--compute", "macs_m",
            "--max-compute-ratio", "1.01",
            "--cost", "gpu_hours",
            "--max-cost", "1.5",
        ], cwd=self.project_dir).returncode, 0)
        self.assertEqual(_run([
            sys.executable, str(self.cli), "configure",
            "--workspace", str(hpo_ws),
            "--from-holdout", str(arch_ws),
        ], cwd=self.project_dir).returncode, 0)

    def test_industry_mechanisms_parallel_multifidelity_lineage_folding_collapse_and_prune(self) -> None:
        ws = self.project_dir / "conv1d_ws"
        res_init = _run([
            sys.executable, str(self.cli), "init",
            "--workspace", str(ws),
            "--preset", "conv1d_transformer",
            "--model-family", "conv1d_transformer",
            "--entry-id", "CONV1D-EXP-001",
            "--metric", "val_bpb",
            "--direction", "minimize",
            "--min-gain", "0.02",
            "--tie-tolerance", "0.005",
            "--holdout-target", "0.96",
            "--compute", "macs_m",
            "--max-compute-ratio", "1.10",
            "--cost", "gpu_seconds",
            "--max-cost", "3000",
            "--max-trials", "14",
            "--max-parallel", "2",
        ], cwd=self.project_dir)
        self.assertEqual(res_init.returncode, 0, msg=res_init.stderr)

        ws_cmd = [sys.executable, str(self.cli), "--workspace", str(ws)]
        cid = json.loads(_run([*ws_cmd, "campaign", "create"], cwd=self.project_dir).stdout)["campaign_id"]

        # Baseline trial-000: val_bpb=1.000, macs_m=100.0
        _run([*ws_cmd, "campaign", "baseline", cid], cwd=self.project_dir)
        _run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-000",
            "--metrics", json.dumps({"val_bpb": 1.000, "macs_m": 100.0}),
            "--cost", json.dumps({"gpu_seconds": 120}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t000.pt"}),
        ], cwd=self.project_dir)

        # 1. Multi-fidelity screening (proxy -> full): proxy trial-001 passes screen without replacing incumbent
        p_proxy = json.loads(_run([
            *ws_cmd, "campaign", "propose", cid,
            "--fidelity", "proxy", "--operator", "refine",
            "--hypothesis", "Screen SiLU activation on 1-epoch proxy",
            "--changes", json.dumps({"ffn.activation": "silu"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(p_proxy["trial_id"], "trial-001")
        r_proxy = json.loads(_run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-001",
            "--metrics", json.dumps({"val_bpb": 0.985, "macs_m": 100.2}),
            "--cost", json.dumps({"gpu_seconds": 15}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r_proxy["decision"], "proxy_pass")
        self.assertEqual(r_proxy["incumbent_trial_id"], "trial-000")  # incumbent untouched!

        ctx_after_proxy = json.loads(_run([*ws_cmd, "campaign", "context", cid], cwd=self.project_dir).stdout)
        self.assertEqual(len(ctx_after_proxy["search_diagnostics"]["ready_to_promote_proxies"]), 1)

        # Promote exact same config to --fidelity full (trial-002) -> allowed and wins incumbent!
        p_full = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--fidelity", "full", "--operator", "refine",
            "--expected-primary", "0.975", "--expected-compute-ratio", "1.01",
            "--hypothesis", "Promote SiLU activation to full training",
            "--changes", json.dumps({"ffn.activation": "silu"}),
        ], cwd=self.project_dir)
        self.assertEqual(p_full.returncode, 0, msg=p_full.stderr)
        r_full = json.loads(_run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-002",
            "--metrics", json.dumps({"val_bpb": 0.972, "macs_m": 100.5}),
            "--cost", json.dumps({"gpu_seconds": 120}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t002.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r_full["decision"], "keep")
        self.assertEqual(r_full["incumbent_trial_id"], "trial-002")
        self.assertIsNotNone(r_full["prediction_calibration"])
        self.assertFalse(r_full["prediction_calibration"]["high_surprise"])

        # 2. Infrastructure flake isolation (NOVA / EvoCast): trial-003 crashes with infra_flake,
        # allowing exact same config to be retried in trial-004!
        _run([
            *ws_cmd, "campaign", "propose", cid,
            "--operator", "explore",
            "--hypothesis", "Test 8 attention heads",
            "--changes", json.dumps({"attention.num_heads": 8}),
        ], cwd=self.project_dir)
        _run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-003",
            "--status", "crash", "--failure-kind", "infra_flake",
            "--cost", json.dumps({"gpu_seconds": 5}),
            "--note", "Transient S3 mount timeout",
        ], cwd=self.project_dir)
        retry_after_flake = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--operator", "explore",
            "--hypothesis", "Retry 8 attention heads after S3 recovery",
            "--changes", json.dumps({"attention.num_heads": 8}),
        ], cwd=self.project_dir)
        self.assertEqual(retry_after_flake.returncode, 0, msg=retry_after_flake.stderr)

        # 3. Parallel batch round (max_parallel=2): trial-004 is already active; submit trial-005 concurrently!
        par_second = json.loads(_run([
            *ws_cmd, "campaign", "propose", cid,
            "--parent-trial", "trial-000", "--operator", "shrink",
            "--hypothesis", "Lightweight 4-layer stepping stone from baseline",
            "--changes", json.dumps({"depth": 4}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(par_second["trial_id"], "trial-005")
        self.assertEqual(par_second["open_parallel_slots"], 0)

        # Third parallel proposal while 2 are active must be blocked!
        par_third = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "Exceed parallel cap",
            "--changes", json.dumps({"ffn.kernel_size": 5}),
        ], cwd=self.project_dir)
        self.assertEqual(par_third.returncode, 2)
        self.assertIn("Parallel active trial limit reached", par_third.stderr)

        # Record trial-005 (lightweight stepping stone: val_bpb=0.990 is discarded vs trial-002's 0.972,
        # BUT enters 2D Pareto frontier & lightweight_sub_0.92x MAP-Elites cell at 0.72x MACs!)
        r_t5 = json.loads(_run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-005",
            "--metrics", json.dumps({"val_bpb": 0.990, "macs_m": 72.0}),
            "--cost", json.dumps({"gpu_seconds": 85}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t005.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r_t5["decision"], "discard")

        # Record trial-004 with suspicious 0 cost & missing model_ref -> triggers Sanity Auditor warnings!
        r_t4 = json.loads(_run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-004",
            "--metrics", json.dumps({"val_bpb": 0.980, "macs_m": 102.0}),
            "--cost", json.dumps({"gpu_seconds": 0}),
        ], cwd=self.project_dir).stdout)
        self.assertIn("missing_model_ref_on_full_trial", r_t4["audit_warnings"])
        self.assertIn("zero_cost_reported_on_full_trial", r_t4["audit_warnings"])

        # Verify Pareto frontier & MAP-Elites contain BOTH trial-005 (lightweight) and trial-002 (balanced)!
        ctx_mid = json.loads(_run([*ws_cmd, "campaign", "context", cid, "--recent-window", "2"], cwd=self.project_dir).stdout)
        pf_ids = {item["trial_id"] for item in ctx_mid["pareto_frontier"]}
        self.assertEqual(pf_ids, {"trial-002", "trial-005"})
        self.assertIn("lightweight_sub_0.92x", ctx_mid["compute_elites"])
        self.assertEqual(ctx_mid["compute_elites"]["lightweight_sub_0.92x"]["trial_id"], "trial-005")
        self.assertGreater(len(ctx_mid["folded_history"]), 0)  # Context Folding active!

        # Inspect unfolded trial-005 on demand
        insp = json.loads(_run([*ws_cmd, "campaign", "inspect", cid, "--trial", "trial-005"], cwd=self.project_dir).stdout)
        self.assertEqual(insp["diff_vs_baseline"]["depth"], {"from": 6, "to": 4})

        # Recombine stepping stone trial-005 with inspiration from trial-002 (P-CONV1D-SHALLOW6-R4 loss test first)
        # Let's test seed pattern P-CONV1D-SHALLOW6-R4 (depth=6, ffn.ratio=4; seed has 1/1 wins) and make it lose twice across runs or test recombine winner:
        _run([
            *ws_cmd, "campaign", "propose", cid,
            "--parent-trial", "trial-005",
            "--inspiration-trials", "trial-002",
            "--operator", "recombine",
            "--hypothesis", "Combine lightweight depth=5 + SiLU + ratio=4",
            "--changes", json.dumps({"depth": 5, "ffn.activation": "silu", "ffn.ratio": 4}),
        ], cwd=self.project_dir)
        r_recomb = json.loads(_run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-006",
            "--metrics", json.dumps({"val_bpb": 0.948, "macs_m": 91.0}),
            "--cost", json.dumps({"gpu_seconds": 110}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t006.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(r_recomb["decision"], "keep")
        self.assertEqual(r_recomb["incumbent_trial_id"], "trial-006")

        # Also re-test seed pattern P-CONV1D-SHALLOW6-R4 (`depth=6;ffn.ratio=4` from parent trial-000) and have it discard
        _run([
            *ws_cmd, "campaign", "propose", cid,
            "--parent-trial", "trial-000",
            "--operator", "refine",
            "--hypothesis", "Re-verify seed pattern depth=6;ffn.ratio=4",
            "--changes", json.dumps({"depth": 6, "ffn.ratio": 4}),
        ], cwd=self.project_dir)
        _run([
            *ws_cmd, "campaign", "record", cid, "--trial", "trial-007",
            "--metrics", json.dumps({"val_bpb": 0.995, "macs_m": 108.0}),
            "--cost", json.dumps({"gpu_seconds": 120}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t007.pt"}),
        ], cwd=self.project_dir)

        # Finalize & verify REPORT.md
        fin = json.loads(_run([
            *ws_cmd, "campaign", "finalize", cid,
            "--metrics", json.dumps({"val_bpb": 0.951, "macs_m": 91.0, "baseline_val_bpb": 1.002}),
            "--cost", json.dumps({"gpu_seconds": 20}),
            "--artifacts", json.dumps({"model_ref": "s3://conv1d/t006.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertTrue(fin["holdout_report"]["accepted"])

        # Distill & check that infra_flake (trial-003) did NOT enter anti_patterns!
        distilled = json.loads(_run([*ws_cmd, "knowledge-base", "distill", cid], cwd=self.project_dir).stdout)
        anti_sigs = {a["change_signature"] for a in distilled["draft"]["anti_patterns"]}
        self.assertNotIn("attention.num_heads=8", anti_sigs)

        _run([*ws_cmd, "knowledge-base", "publish", "CONV1D-EXP-001", "--reviewer", "arch-lead"], cwd=self.project_dir)

        # Skill Pruning (MLEvolver): P-CONV1D-SHALLOW6-R4 now has wins=1, observations=2 (win_rate=0.50).
        # With --min-win-rate 0.60, preview detects it without modifying revision, then --apply prunes it cleanly!
        preview_prune = json.loads(_run([
            *ws_cmd, "knowledge-base", "prune", "CONV1D-EXP-001", "--min-win-rate", "0.60",
        ], cwd=self.project_dir).stdout)
        self.assertFalse(preview_prune["applied"])
        self.assertEqual(len(preview_prune["pruned_candidates"]), 1)

        applied_prune = json.loads(_run([
            *ws_cmd, "knowledge-base", "prune", "CONV1D-EXP-001",
            "--min-win-rate", "0.60", "--apply", "--reviewer", "arch-lead",
        ], cwd=self.project_dir).stdout)
        self.assertTrue(applied_prune["applied"])
        self.assertEqual(applied_prune["revision"], "v3")

        # Verify knowledge_base SHA-256 integrity after prune
        doc_final = json.loads(_run([*ws_cmd, "doctor"], cwd=self.project_dir).stdout)
        self.assertTrue(doc_final["ok"])

    def test_principle_collapse_detector_flags_single_axis_tunnel_vision(self) -> None:
        ws = self.project_dir / "collapse_ws"
        _run([
            sys.executable, str(self.cli), "init",
            "--workspace", str(ws),
            "--preset", "conv1d_transformer",
            "--model-family", "conv1d_transformer",
            "--entry-id", "CONV1D-COLLAPSE-001",
            "--metric", "val_bpb",
            "--direction", "minimize",
            "--min-gain", "0.02",
            "--compute", "macs_m",
            "--max-compute-ratio", "1.50",
            "--max-trials", "8",
        ], cwd=self.project_dir)
        ws_cmd = [sys.executable, str(self.cli), "--workspace", str(ws)]
        cid = json.loads(_run([*ws_cmd, "campaign", "create"], cwd=self.project_dir).stdout)["campaign_id"]
        _run([*ws_cmd, "campaign", "baseline", cid], cwd=self.project_dir)
        _run([
            *ws_cmd, "campaign", "record", cid,
            "--metrics", json.dumps({"val_bpb": 1.0, "macs_m": 100.0}),
            "--cost", json.dumps({"gpu_seconds": 60}),
            "--artifacts", json.dumps({"model_ref": "s3://m/0.pt"}),
        ], cwd=self.project_dir)

        # Mutate ONLY `depth` 4 times in a row while 4 other mutable_fields remain untouched
        last_rec = {}
        for idx, depth_val in enumerate((5, 7, 8, 9), start=1):
            _run([
                *ws_cmd, "campaign", "propose", cid,
                "--hypothesis", f"Tunnel vision on depth={depth_val}",
                "--changes", json.dumps({"depth": depth_val}),
            ], cwd=self.project_dir)
            last_rec = json.loads(_run([
                *ws_cmd, "campaign", "record", cid,
                "--metrics", json.dumps({"val_bpb": 0.995, "macs_m": 105.0}),
                "--cost", json.dumps({"gpu_seconds": 60}),
                "--artifacts", json.dumps({"model_ref": f"s3://m/{idx}.pt"}),
            ], cwd=self.project_dir).stdout)

        self.assertTrue(last_rec["principle_collapse_warning"])
        ctx = json.loads(_run([*ws_cmd, "campaign", "context", cid], cwd=self.project_dir).stdout)
        p_div = ctx["search_diagnostics"]["principle_diversity"]
        self.assertEqual(p_div["dominant_family"], "depth")
        self.assertEqual(p_div["dominant_family_share"], 1.0)
        self.assertEqual(p_div["effective_principle_count"], 1.0)
        self.assertIn("ffn.kernel_size", ctx["search_diagnostics"]["untouched_mutable_fields"])


if __name__ == "__main__":
    unittest.main()
