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
        # Out-of-the-box query against bundled assets/knowledge_base without any workspace!
        res_list = _run([sys.executable, str(self.cli), "knowledge-base", "list"], cwd=self.project_dir)
        self.assertEqual(res_list.returncode, 0, msg=res_list.stderr)
        entries = json.loads(res_list.stdout)
        entry_ids = {item["entry_id"] for item in entries}
        self.assertEqual(
            entry_ids,
            {"CONV1D-ARCH-001", "EDGE-VIT-ARCH-001", "CNN-CSI-ARCH-001", "FIXED-BACKBONE-HPO-001"},
        )

        # Search bundled priors for Conv1d Transformer
        res_search = _run([
            sys.executable, str(self.cli), "knowledge-base", "search",
            "--model-family", "conv1d_transformer",
            "--direction", "gain_up_compute_down",
        ], cwd=self.project_dir)
        self.assertEqual(res_search.returncode, 0, msg=res_search.stderr)
        matched = json.loads(res_search.stdout)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["entry_id"], "CONV1D-ARCH-001")
        self.assertEqual(len(matched[0]["matched_patterns"]), 1)

        # Standalone copy installation, check, and uninstall
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
        self.assertIn("bundled_seed_knowledge_base_verified", doc["checks"])
        self.assertIn("knowledge_base_sha256_integrity_verified", doc["checks"])
        self.assertIn("mcp_tools_customized", doc["checks"])

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

        # Guard 1: No-op proposal -> rejected
        noop = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "No-op channels=64",
            "--changes", json.dumps({"encoder.channels": 64}),
        ], cwd=self.project_dir)
        self.assertEqual(noop.returncode, 2)
        self.assertIn("No-op proposal", noop.stderr)

        # Guard 2: Known anti-pattern in knowledge_base -> blocked
        anti = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "Try known bad channels=128",
            "--changes", json.dumps({"encoder.channels": 128}),
        ], cwd=self.project_dir)
        self.assertEqual(anti.returncode, 2)
        self.assertIn("Blocked by knowledge_base anti-pattern", anti.stderr)

        # Guard 3: Dry-run valid proposal does not open active trial
        dry = json.loads(_run([
            *ws_cmd, "campaign", "propose", cid, "--dry-run",
            "--hypothesis", "Preview SE + k5",
            "--changes", json.dumps({"encoder.use_se": True, "encoder.kernel_size": 5}),
        ], cwd=self.project_dir).stdout)
        self.assertTrue(dry["dry_run"])
        self.assertIsNone(json.loads(_run([*ws_cmd, "campaign", "status", cid], cwd=self.project_dir).stdout)["active_trial_id"])

        # Trial-001: Gain win
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

        # Guard 4: Duplicate configuration -> blocked
        dup = _run([
            *ws_cmd, "campaign", "propose", cid,
            "--hypothesis", "Revert back to baseline config",
            "--changes", json.dumps({"encoder.use_se": False, "encoder.kernel_size": 3}),
        ], cwd=self.project_dir)
        self.assertEqual(dup.returncode, 2)
        self.assertIn("Duplicate configuration", dup.stderr)

        # Trial-002: Compute win within tie_tolerance=0.05 (cost hits max_cost -> awaiting_holdout)
        self.assertEqual(_run([
            *ws_cmd, "campaign", "propose", cid,
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
        self.assertIn("compute win", r2["reason"])
        self.assertEqual(r2["campaign_status"], "awaiting_holdout")

        fin = json.loads(_run([
            *ws_cmd, "campaign", "finalize", cid,
            "--metrics", json.dumps({"nmse_db": -18.35, "macs_m": 46.5, "latency_ms": 1.9, "baseline_nmse_db": -17.45}),
            "--cost", json.dumps({"gpu_hours": 0.05}),
            "--artifacts", json.dumps({"model_ref": "s3://csi/t002.pt"}),
        ], cwd=self.project_dir).stdout)
        self.assertEqual(fin["status"], "succeeded")
        self.assertTrue(fin["holdout_report"]["accepted"])

        # Distill & publish v2 into Markdown knowledge_base
        self.assertEqual(_run([*ws_cmd, "knowledge-base", "distill", cid], cwd=self.project_dir).returncode, 0)
        pub = json.loads(_run([
            *ws_cmd, "knowledge-base", "publish", "CSI-ARCH-001", "--reviewer", "lead-eng",
        ], cwd=self.project_dir).stdout)
        self.assertEqual(pub["revision"], "v2")
        self.assertEqual(pub["patterns"], 3)

        # Hand-editing CURRENT.md must fail SHA-256 integrity check
        cur_md = arch_ws / "knowledge_base" / "entries" / "CSI-ARCH-001" / "CURRENT.md"
        original_md = cur_md.read_text(encoding="utf-8")
        cur_md.write_text(original_md.replace('"max_compute_ratio": 1.1', '"max_compute_ratio": 9.9'), encoding="utf-8")
        tampered = _run([*ws_cmd, "knowledge-base", "show", "CSI-ARCH-001"], cwd=self.project_dir)
        self.assertEqual(tampered.returncode, 2)
        self.assertIn("Revision integrity check failed", tampered.stderr)
        cur_md.write_text(original_md, encoding="utf-8")

        # Post-architecture HPO handoff via configure --from-holdout <arch_ws>
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

        hpo_cfg = _run([
            sys.executable, str(self.cli), "configure",
            "--workspace", str(hpo_ws),
            "--from-holdout", str(arch_ws),
        ], cwd=self.project_dir)
        self.assertEqual(hpo_cfg.returncode, 0, msg=hpo_cfg.stderr)
        hpo_plan = json.loads((hpo_ws / "campaign.json").read_text(encoding="utf-8"))
        self.assertEqual(
            hpo_plan["base_architecture"],
            {
                "encoder": {"num_blocks": 4, "channels": 64, "kernel_size": 5, "use_se": True},
                "decoder": {"refine_blocks": 2, "channels": 48},
            },
        )
        self.assertEqual(hpo_plan["baseline_model_ref"], "s3://csi/t002.pt")

        illegal_mix = _run([
            sys.executable, str(self.cli), "configure",
            "--workspace", str(hpo_ws),
            "--mutable-fields", "lr,encoder.channels",
        ], cwd=self.project_dir)
        self.assertEqual(illegal_mix.returncode, 2)


if __name__ == "__main__":
    unittest.main()
