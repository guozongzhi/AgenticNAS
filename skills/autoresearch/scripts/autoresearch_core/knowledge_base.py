from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any

from .contracts import (
    CONFIDENCE_RANK,
    FAILURE_TYPES,
    KNOWLEDGE_STATUSES,
    PATTERN_DIRECTIONS,
    TRACKS,
)
from .utils import canonical_change_signature, write_text_atomic


SKILL_ROOT = Path(os.path.realpath(__file__)).parents[2]
PRESETS_PATH = SKILL_ROOT / "assets" / "presets.json"
SEED_KNOWLEDGE_BASE_DIR = SKILL_ROOT / "assets" / "knowledge_base"

RECORD_START = "<!-- knowledge_base:record:start -->"
RECORD_END = "<!-- knowledge_base:record:end -->"
EVIDENCE_START = "<!-- knowledge_base:evidence:start -->"
EVIDENCE_END = "<!-- knowledge_base:evidence:end -->"


def load_presets() -> dict[str, Any]:
    if PRESETS_PATH.is_file():
        return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return {}


def _compute_entry_sha256(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "content_sha256"}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _next_revision_label(current: str, draft: bool = True) -> str:
    prefix = current.split("-", 1)[0]
    number = int(prefix[1:]) + 1 if (prefix.startswith("v") and prefix[1:].isdigit()) else 2
    return f"v{number}-draft" if draft else f"v{number}"


def _infer_pattern_direction(gain_pct: float | None, compute_ratio: float | None) -> str:
    gain = gain_pct or 0.0
    ratio = compute_ratio if compute_ratio is not None else 1.0
    if gain > 0 and ratio < 0.99:
        return "gain_up_compute_down"
    if gain > 0 and ratio <= 1.02:
        return "gain_up_compute_neutral"
    if gain > 0:
        return "gain_up_compute_up"
    if abs(gain) <= 1e-6 and ratio < 0.99:
        return "compute_down_tie"
    return "other"


def _infer_failure_type(decision: str, failure_kind: str | None, reason: str | None) -> str:
    if failure_kind == "oom":
        return "compute_budget_exceeded"
    if failure_kind in {"nan_divergence", "timeout"}:
        return "training_crash"
    text = (reason or "").lower()
    if decision == "crash":
        return "training_crash"
    if "compute budget exceeded" in text:
        return "compute_budget_exceeded"
    if "guardrail violated" in text:
        return "guardrail_violated"
    if "delta=" in text:
        return "accuracy_regression"
    return "other"


def _md_cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ").strip() or "-"


def _extract_json_block(markdown: str, start_marker: str, end_marker: str) -> Any:
    start = markdown.find(start_marker)
    end = markdown.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f"Missing structured block ({start_marker}) in Markdown knowledge_base file")
    section = markdown[start + len(start_marker):end]
    fence_start = section.find("```json")
    if fence_start < 0:
        raise ValueError("Missing ```json fenced block inside structured knowledge_base section")
    body = section[fence_start + len("```json"):]
    fence_end = body.find("```")
    if fence_end < 0:
        raise ValueError("Unterminated ```json fenced block inside structured knowledge_base section")
    return json.loads(body[:fence_end].strip())


def _normalize_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(pattern)
    changes = item.get("suggested_changes") or {}
    if not isinstance(changes, dict) or not changes:
        raise ValueError("pattern.suggested_changes must be a non-empty object")
    item["change_signature"] = item.get("change_signature") or canonical_change_signature(changes)
    item["target_fields"] = sorted(set(item.get("target_fields") or list(changes.keys())))
    effect = item.get("effect") if isinstance(item.get("effect"), dict) else {}
    direction = effect.get("direction", "other")
    if direction not in PATTERN_DIRECTIONS:
        raise ValueError(f"Unsupported pattern effect.direction: {direction}")
    item["effect"] = {
        "direction": direction,
        "notes": str(effect.get("notes", "")),
    }
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    gain_pct = stats.get("mean_gain_pct")
    comp_ratio = stats.get("mean_compute_ratio")
    mean_cost = stats.get("mean_cost")
    item["stats"] = {
        "observations": int(stats.get("observations", 1)),
        "wins": int(stats.get("wins", 1)),
        "mean_gain_pct": round(float(gain_pct), 4) if gain_pct is not None else None,
        "mean_compute_ratio": round(float(comp_ratio), 4) if comp_ratio is not None else None,
        "mean_cost": round(float(mean_cost), 4) if mean_cost is not None else None,
    }
    item["confidence"] = item.get("confidence", "medium")
    item["evidence_refs"] = list(dict.fromkeys(item.get("evidence_refs") or []))
    return item


def _normalize_anti_pattern(anti: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(anti)
    changes = item.get("avoid_changes") or {}
    if not isinstance(changes, dict) or not changes:
        raise ValueError("anti_pattern.avoid_changes must be a non-empty object")
    item["change_signature"] = item.get("change_signature") or canonical_change_signature(changes)
    item["target_fields"] = sorted(set(item.get("target_fields") or list(changes.keys())))
    failure_type = item.get("failure_type", "other")
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f"Unsupported anti_pattern.failure_type: {failure_type}")
    item["failure_type"] = failure_type
    item["observed_compute_ratio"] = item.get("observed_compute_ratio")
    item["observed_gain_pct"] = item.get("observed_gain_pct")
    item["observed_failure"] = str(item.get("observed_failure", ""))
    item["occurrences"] = int(item.get("occurrences", 1))
    item["evidence_refs"] = list(dict.fromkeys(item.get("evidence_refs") or []))
    return item


def _weighted_avg(old_val: float | None, old_n: int, new_val: float | None, new_n: int) -> float | None:
    if old_val is None and new_val is None:
        return None
    if old_val is None or old_n <= 0:
        return round(float(new_val), 4)  # type: ignore[arg-type]
    if new_val is None or new_n <= 0:
        return round(float(old_val), 4)
    return round((old_val * old_n + new_val * new_n) / (old_n + new_n), 4)


def render_entry_markdown(doc: dict[str, Any]) -> str:
    scope = doc.get("scope") or {}
    bounds = scope.get("param_bounds") or {}
    lines = [
        f"# {doc['entry_id']} · {doc['title']}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 经验条目编号 | `{doc['entry_id']}` |",
        f"| 修订版本 | `{doc['revision']}`（父版本：`{doc.get('parent_revision') or '-'}`） |",
        f"| 研究轨道 | `{doc['track']}` |",
        f"| 发布状态 | `{doc['status']}` |",
        f"| 适用模型族 | `{_md_cell(scope.get('model_family'))}` |",
        f"| 审核人 | `{_md_cell(doc.get('reviewed_by'))}` |",
        f"| 内容指纹 | `{doc.get('content_sha256', '')[:16]}...` |",
        "",
        "## 摘要",
        "",
        doc["summary"],
        "",
        "## 适用边界与算量红线",
        "",
        f"- **目标算量上限**：`{_md_cell(scope.get('max_compute_value'))}` / 倍率 `<= {_md_cell(scope.get('max_compute_ratio'))}x`",
        f"- **禁用算子**：{', '.join(f'`{op}`' for op in scope.get('forbidden_ops', [])) or '-'}",
        "",
    ]
    if bounds:
        lines.extend([
            "### 参数合法域（`param_bounds`）",
            "",
            "| 字段 | 类型 | 范围 / 枚举 |",
            "| --- | --- | --- |",
        ])
        for field_name, spec in bounds.items():
            constraint = (
                f"enum: `{spec['enum']}`"
                if "enum" in spec
                else f"min=`{spec.get('min', '-')}`, max=`{spec.get('max', '-')}`"
            )
            lines.append(f"| `{field_name}` | `{spec.get('type', 'any')}` | {constraint} |")
        lines.append("")

    lines.extend([
        "## 推荐有效模式（Patterns）",
        "",
        "| ID | 说明 | 声明式变更 | 方向 | 均值增益(%) | 均值算量比 | 观测/胜出 | 置信度 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for pat in doc.get("patterns", []):
        st = pat.get("stats") or {}
        gain_txt = f"{st['mean_gain_pct']:+.2f}%" if st.get("mean_gain_pct") is not None else "-"
        ratio_txt = f"{st['mean_compute_ratio']:.3f}x" if st.get("mean_compute_ratio") is not None else "-"
        lines.append(
            f"| `{pat.get('pattern_id', '-')}` | {_md_cell(pat.get('title'))} | `{pat['change_signature']}` "
            f"| `{pat['effect']['direction']}` | {gain_txt} | {ratio_txt} "
            f"| {st.get('observations', 0)}/{st.get('wins', 0)} | `{pat.get('confidence', 'medium')}` |"
        )
    if not doc.get("patterns"):
        lines.append("| - | 暂无已验证模式 | - | - | - | - | - | - |")

    lines.extend([
        "",
        "## 已知反例与失效边界（Anti-Patterns）",
        "",
        "| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 次数 |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for anti in doc.get("anti_patterns", []):
        ratio_txt = f"{anti['observed_compute_ratio']:.3f}x" if anti.get("observed_compute_ratio") is not None else "-"
        lines.append(
            f"| `{anti.get('pattern_id', '-')}` | {_md_cell(anti.get('title'))} | `{anti['change_signature']}` "
            f"| `{anti['failure_type']}` | {ratio_txt} | {anti.get('occurrences', 1)} |"
        )
    if not doc.get("anti_patterns"):
        lines.append("| - | 暂无记录反例 | - | - | - | - |")

    lines.extend([
        "",
        "---",
        "",
        "<!-- 机器精确解析块：请通过 autoresearch.py configure / knowledge-base distill / knowledge-base publish / knowledge-base prune 维护，勿手改导致 SHA-256 校验失败 -->",
        RECORD_START,
        "```json",
        json.dumps(doc, ensure_ascii=False, indent=2),
        "```",
        RECORD_END,
        "",
    ])
    return "\n".join(lines)


def render_evidence_markdown(entry_id: str, records: list[dict[str, Any]]) -> str:
    lines = [
        f"# {entry_id} · 实证账本（Evidence Ledger）",
        "",
        "| Campaign | 修订 | 胜出 Trial | Holdout 通过 | 增益(%) | 算量比 | 总成本 | 审核人 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rec in records:
        lines.append(
            f"| `{_md_cell(rec.get('campaign_id'))}` | `{_md_cell(rec.get('revision'))}` "
            f"| `{_md_cell(rec.get('incumbent_trial_id'))}` | `{_md_cell(rec.get('holdout_accepted'))}` "
            f"| `{_md_cell(rec.get('gain_pct'))}` | `{_md_cell(rec.get('compute_ratio'))}` "
            f"| `{_md_cell(rec.get('total_cost'))}` | `{_md_cell(rec.get('reviewed_by'))}` |"
        )
    if not records:
        lines.append("| - | - | - | - | - | - | - | - |")
    lines.extend([
        "",
        EVIDENCE_START,
        "```json",
        json.dumps(records, ensure_ascii=False, indent=2),
        "```",
        EVIDENCE_END,
        "",
    ])
    return "\n".join(lines)


def render_index_markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# 模型优化经验知识库总索引（Knowledge Base Index）",
        "",
        "| 条目编号 | 当前版本 | 轨道 | 状态 | 模型族 | 模式 / 反例 / 实证 / 待审草案 | 入口 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        scope = item.get("scope") or {}
        counts = (
            f"{len(item.get('patterns', []))} / {len(item.get('anti_patterns', []))} / "
            f"{len(item.get('evidence', []))} / {len(item.get('draft_revisions', []))}"
        )
        lines.append(
            f"| `{item['entry_id']}` | `{item['revision']}` | `{item['track']}` | `{item['status']}` "
            f"| `{_md_cell(scope.get('model_family'))}` | {counts} | [CURRENT.md](entries/{item['entry_id']}/CURRENT.md) |"
        )
    if not entries:
        lines.append("| - | - | - | - | - | - | - | - |")
    lines.append("")
    return "\n".join(lines)


class KnowledgeBase:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.entries_dir = self.root / "entries"
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.index_md_path = self.root / "INDEX.md"

    @staticmethod
    def _safe_id(identifier: str) -> str:
        clean = identifier.strip()
        if not clean or "/" in clean or "\\" in clean or ".." in clean:
            raise ValueError(f"Invalid knowledge_base entry_id: {identifier!r}")
        return clean

    def _entry_dir(self, entry_id: str) -> Path:
        return self.entries_dir / self._safe_id(entry_id)

    def _current_path(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "CURRENT.md"

    def _revisions_dir(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "revisions"

    def _revision_path(self, entry_id: str, revision: str) -> Path:
        return self._revisions_dir(entry_id) / f"{self._safe_id(revision)}.md"

    def _drafts_dir(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "drafts"

    def _evidence_path(self, entry_id: str) -> Path:
        return self._entry_dir(entry_id) / "EVIDENCE.md"

    @staticmethod
    def validate_doc(raw: dict[str, Any]) -> dict[str, Any]:
        doc = copy.deepcopy(raw)
        if doc.get("schema_version") not in (1, 2):
            raise ValueError("Unsupported knowledge_base schema_version")
        for key in ("entry_id", "revision", "title", "summary"):
            if not isinstance(doc.get(key), str) or not doc[key].strip():
                raise ValueError(f"Knowledge entry {key} is required")
        if doc.get("track") not in TRACKS:
            raise ValueError(f"Unsupported knowledge_base track: {doc.get('track')}")
        if doc.get("status") not in KNOWLEDGE_STATUSES:
            raise ValueError(f"Unsupported knowledge_base status: {doc.get('status')}")
        if not isinstance(doc.get("scope"), dict):
            raise ValueError("Knowledge entry scope must be an object")
        doc["patterns"] = [_normalize_pattern(p) for p in doc.get("patterns", [])]
        doc["anti_patterns"] = [_normalize_anti_pattern(a) for a in doc.get("anti_patterns", [])]
        return doc

    def _read_evidence(self, entry_id: str) -> list[dict[str, Any]]:
        path = self._evidence_path(entry_id)
        if not path.is_file():
            return []
        data = _extract_json_block(path.read_text(encoding="utf-8"), EVIDENCE_START, EVIDENCE_END)
        if not isinstance(data, list):
            raise ValueError(f"Corrupted EVIDENCE.md in {path}")
        return data

    def list_drafts(self, entry_id: str | None = None) -> list[dict[str, Any]]:
        ids = [self._safe_id(entry_id)] if entry_id else sorted(
            p.name for p in self.entries_dir.iterdir() if p.is_dir() and (p / "CURRENT.md").is_file()
        )
        out: list[dict[str, Any]] = []
        for item_id in ids:
            d_dir = self._drafts_dir(item_id)
            if not d_dir.is_dir():
                continue
            for path in sorted(d_dir.glob("*.md")):
                out.append(_extract_json_block(path.read_text(encoding="utf-8"), RECORD_START, RECORD_END))
        return out

    def load(self, entry_id: str, revision: str | None = None) -> dict[str, Any]:
        safe_id = self._safe_id(entry_id)
        cur_path = self._current_path(safe_id)
        if not cur_path.is_file():
            raise ValueError(f"Unknown knowledge_base entry: {entry_id}")
        cur_doc = _extract_json_block(cur_path.read_text(encoding="utf-8"), RECORD_START, RECORD_END)
        target_path = self._revision_path(safe_id, revision) if revision else cur_path
        if not target_path.is_file():
            raise ValueError(f"Unknown revision {revision!r} for knowledge_base entry {entry_id}")
        raw_doc = _extract_json_block(target_path.read_text(encoding="utf-8"), RECORD_START, RECORD_END)
        doc = self.validate_doc(raw_doc)
        expected_sha = doc.get("content_sha256")
        actual_sha = _compute_entry_sha256(doc)
        if expected_sha and expected_sha != actual_sha:
            raise ValueError(
                f"Revision integrity check failed for {safe_id}@{doc['revision']}: "
                "do not hand-edit CURRENT.md; use `configure` (for v1 seed) or "
                "`knowledge-base distill` + `knowledge-base publish`."
            )
        doc["content_sha256"] = actual_sha
        doc["active_revision"] = cur_doc["revision"]
        rev_dir = self._revisions_dir(safe_id)
        doc["revisions"] = [
            _extract_json_block(p.read_text(encoding="utf-8"), RECORD_START, RECORD_END)["revision"]
            for p in sorted(rev_dir.glob("*.md"))
        ] if rev_dir.is_dir() else []
        doc["evidence"] = self._read_evidence(safe_id)
        doc["draft_revisions"] = self.list_drafts(safe_id)
        return doc

    def save(self, entry: dict[str, Any], allow_overwrite_revision: bool = False) -> Path:
        safe_id = self._safe_id(entry["entry_id"])
        revision = self._safe_id(entry["revision"])
        rev_path = self._revision_path(safe_id, revision)
        if rev_path.is_file() and not allow_overwrite_revision:
            raise ValueError(f"Revision {safe_id}@{revision} is immutable and already exists")

        doc = self.validate_doc({
            "schema_version": 2,
            "entry_id": safe_id,
            "revision": revision,
            "parent_revision": entry.get("parent_revision"),
            "track": entry["track"],
            "status": entry["status"],
            "tags": list(entry.get("tags") or []),
            "title": entry["title"],
            "summary": entry["summary"],
            "scope": entry["scope"],
            "patterns": entry.get("patterns", []),
            "anti_patterns": entry.get("anti_patterns", []),
            "reviewed_by": entry.get("reviewed_by", "seed"),
            "published_at": entry.get("published_at", 0),
        })
        doc["content_sha256"] = _compute_entry_sha256(doc)
        markdown = render_entry_markdown(doc)
        write_text_atomic(rev_path, markdown)
        write_text_atomic(self._current_path(safe_id), markdown)
        self._drafts_dir(safe_id).mkdir(parents=True, exist_ok=True)
        if "evidence" in entry and entry["evidence"] is not None:
            write_text_atomic(self._evidence_path(safe_id), render_evidence_markdown(safe_id, list(entry["evidence"])))
        elif not self._evidence_path(safe_id).is_file():
            write_text_atomic(self._evidence_path(safe_id), render_evidence_markdown(safe_id, []))
        self.reindex()
        return rev_path

    def freeze_snapshot(self, entry_id: str, revision: str | None = None) -> dict[str, Any]:
        doc = self.load(entry_id, revision=revision)
        if doc["status"] != "published":
            raise ValueError(f"Knowledge entry {entry_id}@{doc['revision']} is not published")
        return {
            "entry_id": doc["entry_id"],
            "revision": doc["revision"],
            "track": doc["track"],
            "status": doc["status"],
            "title": doc["title"],
            "summary": doc["summary"],
            "scope": copy.deepcopy(doc["scope"]),
            "patterns": copy.deepcopy(doc["patterns"]),
            "anti_patterns": copy.deepcopy(doc["anti_patterns"]),
            "content_sha256": doc["content_sha256"],
        }

    def reindex(self) -> Path:
        entries = self.list_entries()
        write_text_atomic(self.index_md_path, render_index_markdown(entries))
        return self.index_md_path

    def list_entries(self, track: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for entry_dir in sorted(self.entries_dir.iterdir()):
            if not entry_dir.is_dir() or not (entry_dir / "CURRENT.md").is_file():
                continue
            doc = self.load(entry_dir.name)
            if track and doc["track"] != track:
                continue
            if status and doc["status"] != status:
                continue
            out.append(doc)
        return out

    def search(
        self,
        *,
        query: str = "",
        track: str | None = None,
        model_family: str | None = None,
        field_name: str | None = None,
        direction: str | None = None,
        max_compute_ratio: float | None = None,
        min_gain_pct: float | None = None,
        failure_type: str | None = None,
        status: str | None = "published",
    ) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        fam_needle = (model_family or "").strip().lower()
        results: list[dict[str, Any]] = []
        for doc in self.list_entries(track=track, status=status):
            scope = doc.get("scope") or {}
            if fam_needle and fam_needle not in str(scope.get("model_family") or "").lower():
                continue
            patterns = list(doc.get("patterns", []))
            if direction:
                patterns = [p for p in patterns if p["effect"]["direction"] == direction]
            if min_gain_pct is not None:
                patterns = [
                    p for p in patterns
                    if p["stats"].get("mean_gain_pct") is not None and p["stats"]["mean_gain_pct"] >= min_gain_pct
                ]
            if max_compute_ratio is not None:
                patterns = [
                    p for p in patterns
                    if p["stats"].get("mean_compute_ratio") is not None
                    and p["stats"]["mean_compute_ratio"] <= max_compute_ratio
                ]
            if field_name:
                patterns = [p for p in patterns if field_name in p.get("target_fields", [])]

            antis = list(doc.get("anti_patterns", []))
            if failure_type:
                antis = [a for a in antis if a["failure_type"] == failure_type]
            if field_name:
                antis = [a for a in antis if field_name in a.get("target_fields", [])]

            if needle:
                blob = json.dumps(
                    {"title": doc["title"], "summary": doc["summary"], "patterns": patterns, "anti": antis},
                    ensure_ascii=False,
                ).lower()
                if needle not in blob:
                    continue
            if (direction or min_gain_pct is not None or max_compute_ratio is not None) and not patterns:
                continue
            if failure_type and not antis:
                continue

            results.append({
                "entry_id": doc["entry_id"],
                "revision": doc["revision"],
                "track": doc["track"],
                "title": doc["title"],
                "scope": scope,
                "matched_patterns": patterns,
                "matched_anti_patterns": antis,
            })
        return results

    def import_seed_library(self, preset_filter: str | None = None, overwrite: bool = False) -> list[str]:
        presets = load_presets()
        imported: list[str] = []
        for name, preset in presets.items():
            if preset_filter and name != preset_filter:
                continue
            seed_id = preset.get("seed_entry_id")
            if not seed_id:
                continue
            if self._current_path(seed_id).is_file() and not overwrite:
                continue
            self.save({
                "entry_id": seed_id,
                "revision": "v1",
                "parent_revision": None,
                "track": preset["track"],
                "status": "published",
                "tags": [preset.get("model_family", name), preset["track"], "seed-library"],
                "title": preset["title"],
                "summary": preset["summary"],
                "reviewed_by": "seed-library",
                "published_at": 0,
                "scope": {
                    "model_family": preset.get("model_family", name),
                    "forbidden_ops": preset.get("forbidden_ops", []),
                    "max_compute_value": None,
                    "max_compute_ratio": preset.get("max_compute_ratio", 1.10),
                    "param_bounds": preset["param_bounds"],
                },
                "patterns": preset.get("patterns", []),
                "anti_patterns": preset.get("anti_patterns", []),
                "evidence": [],
            }, allow_overwrite_revision=overwrite)
            imported.append(seed_id)
        return imported

    def distill_from_campaign(self, campaign: dict[str, Any], entry_id: str | None = None) -> dict[str, Any]:
        target_id = self._safe_id(entry_id or campaign["plan"]["knowledge_entry_ref"])
        cur = self.load(target_id)
        existing_pattern_sigs = {p["change_signature"] for p in cur.get("patterns", [])}
        holdout = campaign.get("holdout_report")
        holdout_ok = bool(holdout and holdout.get("accepted"))
        confidence = "verified_holdout" if holdout_ok else "dev_only"
        cid = campaign["campaign_id"]

        new_patterns: list[dict[str, Any]] = []
        new_antis: list[dict[str, Any]] = []
        for idx, trial in enumerate(campaign.get("trials", []), start=1):
            if trial.get("is_baseline") or not trial.get("changes"):
                continue
            # Only full-fidelity outcomes update empirical knowledge_base patterns;
            # transient infra_flake crashes NEVER poison anti_patterns!
            if trial.get("fidelity", "full") != "full":
                continue
            if trial.get("failure_kind") == "infra_flake":
                continue

            sig = canonical_change_signature(trial["changes"])
            decision = trial.get("decision")
            if decision == "keep":
                new_patterns.append(_normalize_pattern({
                    "pattern_id": f"P-{cid[-6:].upper()}-{idx:02d}",
                    "title": trial["hypothesis"],
                    "suggested_changes": trial["changes"],
                    "effect": {
                        "direction": _infer_pattern_direction(trial.get("gain_pct"), trial.get("compute_ratio")),
                        "notes": trial.get("decision_reason") or "",
                    },
                    "stats": {
                        "observations": 1,
                        "wins": 1,
                        "mean_gain_pct": trial.get("gain_pct"),
                        "mean_compute_ratio": trial.get("compute_ratio"),
                        "mean_cost": trial.get("cost_value"),
                    },
                    "confidence": confidence,
                    "evidence_refs": [f"{cid}:{trial['trial_id']}"],
                    "change_signature": sig,
                }))
            elif decision in {"discard", "crash"}:
                # If an existing pattern failed when re-tested at full fidelity, record a 0-win observation
                # so its win_rate decays naturally for `knowledge-base prune`.
                if sig in existing_pattern_sigs:
                    new_patterns.append(_normalize_pattern({
                        "pattern_id": f"P-DECAY-{cid[-6:].upper()}-{idx:02d}",
                        "title": trial["hypothesis"],
                        "suggested_changes": trial["changes"],
                        "effect": {"direction": "other", "notes": trial.get("decision_reason") or ""},
                        "stats": {
                            "observations": 1,
                            "wins": 0,
                            "mean_gain_pct": trial.get("gain_pct"),
                            "mean_compute_ratio": trial.get("compute_ratio"),
                            "mean_cost": trial.get("cost_value"),
                        },
                        "confidence": "low",
                        "evidence_refs": [f"{cid}:{trial['trial_id']}"],
                        "change_signature": sig,
                    }))

                ftype = _infer_failure_type(decision, trial.get("failure_kind"), trial.get("decision_reason"))
                if ftype in {"compute_budget_exceeded", "guardrail_violated", "training_crash"} or (
                    trial.get("gain_pct") is not None and trial["gain_pct"] < -1.0
                ):
                    new_antis.append(_normalize_anti_pattern({
                        "pattern_id": f"AP-{cid[-6:].upper()}-{idx:02d}",
                        "title": trial["hypothesis"],
                        "avoid_changes": trial["changes"],
                        "failure_type": ftype,
                        "observed_compute_ratio": trial.get("compute_ratio"),
                        "observed_gain_pct": trial.get("gain_pct"),
                        "observed_failure": trial.get("decision_reason") or decision,
                        "occurrences": 1,
                        "evidence_refs": [f"{cid}:{trial['trial_id']}"],
                        "change_signature": sig,
                    }))

        draft_rev = f"{_next_revision_label(cur['revision'], draft=True)}-{cid[-6:]}"
        draft_doc = {
            "schema_version": 2,
            "entry_id": target_id,
            "revision": draft_rev,
            "parent_revision": cur["revision"],
            "track": cur["track"],
            "status": "draft",
            "tags": cur.get("tags", []),
            "title": cur["title"],
            "summary": cur["summary"],
            "scope": cur["scope"],
            "patterns": new_patterns,
            "anti_patterns": new_antis,
            "source_campaign": {
                "campaign_id": cid,
                "incumbent_trial_id": campaign.get("incumbent_trial_id"),
                "holdout_accepted": holdout_ok if holdout else None,
                "gain_pct": holdout.get("gain_pct") if holdout else None,
                "compute_ratio": holdout.get("compute_ratio") if holdout else None,
                "total_cost": campaign.get("total_cost", 0.0),
            },
            "reviewed_by": None,
            "published_at": round(time.time(), 3),
        }
        draft_doc["content_sha256"] = _compute_entry_sha256(draft_doc)
        draft_path = self._drafts_dir(target_id) / f"{draft_rev}.md"
        write_text_atomic(draft_path, render_entry_markdown(draft_doc))
        self.reindex()
        return {"draft_path": str(draft_path), "draft": draft_doc}

    def publish(self, entry_id: str, draft_revision: str | None = None, reviewer: str = "human") -> dict[str, Any]:
        safe_id = self._safe_id(entry_id)
        cur = self.load(safe_id)
        drafts = self.list_drafts(safe_id)
        if not drafts:
            raise ValueError(f"No pending drafts found for {safe_id}; run `knowledge-base distill` first")
        selected = None
        if draft_revision:
            for item in drafts:
                if item["revision"] == draft_revision:
                    selected = item
                    break
            if selected is None:
                raise ValueError(f"Draft revision {draft_revision!r} not found for {safe_id}")
        else:
            selected = drafts[-1]

        merged_patterns = [_normalize_pattern(p) for p in cur.get("patterns", [])]
        pat_by_sig = {p["change_signature"]: idx for idx, p in enumerate(merged_patterns)}
        for incoming in selected.get("patterns", []):
            cand = _normalize_pattern(incoming)
            sig = cand["change_signature"]
            if sig in pat_by_sig:
                existing = merged_patterns[pat_by_sig[sig]]
                o_s, n_s = existing["stats"], cand["stats"]
                o_n, n_n = o_s["observations"], max(1, n_s["observations"])
                existing["stats"] = {
                    "observations": o_n + n_n,
                    "wins": o_s["wins"] + n_s["wins"],
                    "mean_gain_pct": _weighted_avg(o_s["mean_gain_pct"], o_n, n_s["mean_gain_pct"], n_n),
                    "mean_compute_ratio": _weighted_avg(o_s["mean_compute_ratio"], o_n, n_s["mean_compute_ratio"], n_n),
                    "mean_cost": _weighted_avg(o_s["mean_cost"], o_n, n_s["mean_cost"], n_n),
                }
                if CONFIDENCE_RANK.get(cand["confidence"], 0) > CONFIDENCE_RANK.get(existing["confidence"], 0):
                    existing["confidence"] = cand["confidence"]
                existing["evidence_refs"] = list(dict.fromkeys([*existing["evidence_refs"], *cand["evidence_refs"]]))
                existing["effect"]["direction"] = _infer_pattern_direction(
                    existing["stats"]["mean_gain_pct"], existing["stats"]["mean_compute_ratio"]
                )
            else:
                if cand["stats"]["wins"] > 0:
                    pat_by_sig[sig] = len(merged_patterns)
                    merged_patterns.append(cand)

        merged_antis = [_normalize_anti_pattern(a) for a in cur.get("anti_patterns", [])]
        anti_by_sig = {a["change_signature"]: idx for idx, a in enumerate(merged_antis)}
        for incoming in selected.get("anti_patterns", []):
            cand = _normalize_anti_pattern(incoming)
            sig = cand["change_signature"]
            if sig in anti_by_sig:
                existing = merged_antis[anti_by_sig[sig]]
                existing["occurrences"] += max(1, cand["occurrences"])
                existing["evidence_refs"] = list(dict.fromkeys([*existing["evidence_refs"], *cand["evidence_refs"]]))
                if cand.get("observed_compute_ratio") is not None:
                    existing["observed_compute_ratio"] = cand["observed_compute_ratio"]
            else:
                anti_by_sig[sig] = len(merged_antis)
                merged_antis.append(cand)

        new_rev = _next_revision_label(cur["revision"], draft=False)
        evidence = list(cur.get("evidence", []))
        src_cmp = selected.get("source_campaign") or {}
        if src_cmp.get("campaign_id"):
            evidence.append({
                **src_cmp,
                "revision": new_rev,
                "reviewed_by": reviewer,
                "published_at": round(time.time(), 3),
            })

        self.save({
            "entry_id": safe_id,
            "revision": new_rev,
            "parent_revision": cur["revision"],
            "track": cur["track"],
            "status": "published",
            "tags": cur.get("tags", []),
            "title": cur["title"],
            "summary": cur["summary"],
            "scope": cur["scope"],
            "patterns": merged_patterns,
            "anti_patterns": merged_antis,
            "reviewed_by": reviewer,
            "published_at": round(time.time(), 3),
            "evidence": evidence,
        })
        draft_file = self._drafts_dir(safe_id) / f"{selected['revision']}.md"
        if draft_file.is_file():
            draft_file.unlink()
        self.reindex()
        return self.load(safe_id)

    def prune(
        self,
        entry_id: str,
        *,
        min_win_rate: float = 0.34,
        min_observations: int = 2,
        include_verified: bool = False,
        apply: bool = False,
        reviewer: str = "human",
    ) -> dict[str, Any]:
        """Curate reusable lessons by pruning low-win-rate stale patterns (MLEvolver Skill Deletion).

        Preserves `anti_patterns` safety rails and `verified_holdout` patterns (unless
        `include_verified=True`). Returns a dry-run preview unless `apply=True`.
        """
        safe_id = self._safe_id(entry_id)
        cur = self.load(safe_id)
        kept: list[dict[str, Any]] = []
        pruned: list[dict[str, Any]] = []

        for pat in cur.get("patterns", []):
            obs = int(pat["stats"].get("observations", 1))
            wins = int(pat["stats"].get("wins", 0))
            win_rate = wins / max(1, obs)
            is_verified = pat.get("confidence") == "verified_holdout"
            should_prune = (
                obs >= min_observations
                and win_rate < min_win_rate
                and (include_verified or not is_verified)
            ) or (wins == 0 and (include_verified or not is_verified))
            if should_prune:
                pruned.append({
                    "pattern_id": pat.get("pattern_id"),
                    "change_signature": pat["change_signature"],
                    "observations": obs,
                    "wins": wins,
                    "win_rate": round(win_rate, 3),
                    "confidence": pat.get("confidence"),
                })
            else:
                kept.append(pat)

        if not apply or not pruned:
            return {
                "entry_id": safe_id,
                "applied": False,
                "current_revision": cur["revision"],
                "kept_patterns": len(kept),
                "pruned_candidates": pruned,
            }

        new_rev = _next_revision_label(cur["revision"], draft=False)
        self.save({
            "entry_id": safe_id,
            "revision": new_rev,
            "parent_revision": cur["revision"],
            "track": cur["track"],
            "status": "published",
            "tags": cur.get("tags", []),
            "title": cur["title"],
            "summary": cur["summary"],
            "scope": cur["scope"],
            "patterns": kept,
            "anti_patterns": cur.get("anti_patterns", []),
            "reviewed_by": reviewer,
            "published_at": round(time.time(), 3),
            "evidence": cur.get("evidence", []),
        })
        return {
            "entry_id": safe_id,
            "applied": True,
            "revision": new_rev,
            "kept_patterns": len(kept),
            "pruned_patterns": pruned,
        }
