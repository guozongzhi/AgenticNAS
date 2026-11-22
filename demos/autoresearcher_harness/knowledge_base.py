from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any

from .contracts import TRACKS
from .store import write_text


KB_STATUSES = {'draft', 'published', 'deprecated'}
PATTERN_DIRECTIONS = {
    'gain_up_compute_down',
    'gain_up_compute_neutral',
    'gain_up_compute_up',
    'compute_down_tie',
    'other',
}
FAILURE_TYPES = {
    'compute_budget_exceeded',
    'guardrail_violated',
    'accuracy_regression',
    'training_crash',
    'other',
}
CONFIDENCE_RANK = {'low': 1, 'medium': 2, 'dev_only': 2, 'verified_holdout': 3}

RECORD_START = '<!-- kb:record:start -->'
RECORD_END = '<!-- kb:record:end -->'
EVIDENCE_START = '<!-- kb:evidence:start -->'
EVIDENCE_END = '<!-- kb:evidence:end -->'


def canonical_change_signature(changes: dict[str, Any]) -> str:
    if not changes:
        return '-'
    return ';'.join(
        f'{key}={json.dumps(changes[key], sort_keys=True, ensure_ascii=False)}'
        for key in sorted(changes)
    )


def _compute_content_sha256(payload: dict[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != 'content_sha256'}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _next_revision_label(current: str, draft: bool = True) -> str:
    prefix = current.split('-', 1)[0]
    if prefix.startswith('v') and prefix[1:].isdigit():
        number = int(prefix[1:]) + 1
    else:
        number = 2
    return f'v{number}-draft' if draft else f'v{number}'


def _infer_direction(gain_pp: float | None, flops_ratio: float | None) -> str:
    gain = gain_pp or 0.0
    ratio = flops_ratio if flops_ratio is not None else 1.0
    if gain > 0 and ratio < 0.99:
        return 'gain_up_compute_down'
    if gain > 0 and ratio <= 1.02:
        return 'gain_up_compute_neutral'
    if gain > 0:
        return 'gain_up_compute_up'
    if abs(gain) <= 1e-6 and ratio < 0.99:
        return 'compute_down_tie'
    return 'other'


def _infer_failure_type(decision: str, reason: str | None) -> str:
    text = (reason or '').lower()
    if decision == 'crash':
        return 'training_crash'
    if 'compute budget exceeded' in text or 'flops' in text:
        return 'compute_budget_exceeded'
    if 'guardrail violated' in text:
        return 'guardrail_violated'
    if 'delta=' in text:
        return 'accuracy_regression'
    return 'other'


def _md_cell(value: Any) -> str:
    if value is None or value == '':
        return '-'
    return str(value).replace('|', '\\|').replace('\n', ' ').strip() or '-'


def _extract_json_block(markdown: str, start_marker: str, end_marker: str) -> Any:
    start = markdown.find(start_marker)
    end = markdown.find(end_marker)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(f'Missing structured block ({start_marker}) in Markdown KB document')
    section = markdown[start + len(start_marker):end]
    fence_start = section.find('```json')
    if fence_start < 0:
        raise ValueError('Missing ```json fenced block inside structured KB section')
    body = section[fence_start + len('```json'):]
    fence_end = body.find('```')
    if fence_end < 0:
        raise ValueError('Unterminated ```json fenced block inside structured KB section')
    return json.loads(body[:fence_end].strip())


def _normalize_pattern(pattern: dict[str, Any]) -> dict[str, Any]:
    item = json.loads(json.dumps(pattern))
    changes = item.get('suggested_changes') or {}
    if not isinstance(changes, dict):
        raise ValueError('pattern.suggested_changes must be an object')
    item['change_signature'] = item.get('change_signature') or canonical_change_signature(changes)
    item['target_fields'] = sorted(set(item.get('target_fields') or list(changes.keys())))
    effect = item.get('effect') if isinstance(item.get('effect'), dict) else {}
    direction = effect.get('direction', 'other')
    if direction not in PATTERN_DIRECTIONS:
        raise ValueError(f'Unsupported pattern effect.direction: {direction}')
    item['effect'] = {
        'expected_gain_pp_range': effect.get('expected_gain_pp_range'),
        'expected_flops_ratio_range': effect.get('expected_flops_ratio_range'),
        'direction': direction,
        'notes': effect.get('notes', ''),
    }
    stats = item.get('stats') if isinstance(item.get('stats'), dict) else {}
    item['stats'] = {
        'observations': int(stats.get('observations', 0)),
        'wins': int(stats.get('wins', 0)),
        'mean_gain_pp': float(stats['mean_gain_pp']) if stats.get('mean_gain_pp') is not None else None,
        'mean_flops_ratio': float(stats['mean_flops_ratio']) if stats.get('mean_flops_ratio') is not None else None,
        'mean_gpu_seconds': float(stats['mean_gpu_seconds']) if stats.get('mean_gpu_seconds') is not None else None,
    }
    item['confidence'] = item.get('confidence', 'medium')
    item['evidence_refs'] = list(dict.fromkeys(item.get('evidence_refs') or []))
    return item


def _normalize_anti_pattern(anti: dict[str, Any]) -> dict[str, Any]:
    item = json.loads(json.dumps(anti))
    changes = item.get('avoid_changes') or {}
    if not isinstance(changes, dict):
        raise ValueError('anti_pattern.avoid_changes must be an object')
    item['change_signature'] = item.get('change_signature') or canonical_change_signature(changes)
    item['target_fields'] = sorted(set(item.get('target_fields') or list(changes.keys())))
    failure_type = item.get('failure_type', 'other')
    if failure_type not in FAILURE_TYPES:
        raise ValueError(f'Unsupported anti_pattern.failure_type: {failure_type}')
    item['failure_type'] = failure_type
    item['occurrences'] = int(item.get('occurrences', 1))
    item['evidence_refs'] = list(dict.fromkeys(item.get('evidence_refs') or []))
    return item


def _weighted_avg(old_val: float | None, old_n: int, new_val: float | None, new_n: int) -> float | None:
    if old_val is None and new_val is None:
        return None
    if old_val is None or old_n <= 0:
        return round(float(new_val), 4)
    if new_val is None or new_n <= 0:
        return round(float(old_val), 4)
    return round((old_val * old_n + new_val * new_n) / (old_n + new_n), 4)


def merge_patterns(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    merged: list[dict[str, Any]] = [_normalize_pattern(p) for p in existing]
    by_sig = {p['change_signature']: idx for idx, p in enumerate(merged)}
    added_count = 0
    merged_count = 0
    for raw in incoming:
        cand = _normalize_pattern(raw)
        sig = cand['change_signature']
        if sig in by_sig:
            cur = merged[by_sig[sig]]
            old_s, new_s = cur['stats'], cand['stats']
            old_n, new_n = old_s['observations'], max(1, new_s['observations'])
            cur['stats'] = {
                'observations': old_n + new_n,
                'wins': old_s['wins'] + new_s['wins'],
                'mean_gain_pp': _weighted_avg(old_s['mean_gain_pp'], old_n, new_s['mean_gain_pp'], new_n),
                'mean_flops_ratio': _weighted_avg(old_s['mean_flops_ratio'], old_n, new_s['mean_flops_ratio'], new_n),
                'mean_gpu_seconds': _weighted_avg(old_s['mean_gpu_seconds'], old_n, new_s['mean_gpu_seconds'], new_n),
            }
            if CONFIDENCE_RANK.get(cand['confidence'], 0) > CONFIDENCE_RANK.get(cur['confidence'], 0):
                cur['confidence'] = cand['confidence']
            cur['evidence_refs'] = list(dict.fromkeys([*cur['evidence_refs'], *cand['evidence_refs']]))
            cur['effect']['direction'] = _infer_direction(cur['stats']['mean_gain_pp'], cur['stats']['mean_flops_ratio'])
            merged_count += 1
        else:
            by_sig[sig] = len(merged)
            merged.append(cand)
            added_count += 1
    return merged, {'added': added_count, 'merged': merged_count}


def merge_anti_patterns(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    merged: list[dict[str, Any]] = [_normalize_anti_pattern(a) for a in existing]
    by_sig = {a['change_signature']: idx for idx, a in enumerate(merged)}
    added_count = 0
    merged_count = 0
    for raw in incoming:
        cand = _normalize_anti_pattern(raw)
        sig = cand['change_signature']
        if sig in by_sig:
            cur = merged[by_sig[sig]]
            cur['occurrences'] += max(1, cand['occurrences'])
            cur['evidence_refs'] = list(dict.fromkeys([*cur['evidence_refs'], *cand['evidence_refs']]))
            if cand.get('observed_flops_ratio') is not None:
                cur['observed_flops_ratio'] = cand['observed_flops_ratio']
            if cand.get('observed_gain_pp') is not None:
                cur['observed_gain_pp'] = cand['observed_gain_pp']
            merged_count += 1
        else:
            by_sig[sig] = len(merged)
            merged.append(cand)
            added_count += 1
    return merged, {'added': added_count, 'merged': merged_count}


def render_revision_markdown(doc: dict[str, Any]) -> str:
    scope = doc.get('scope') or {}
    bounds = scope.get('param_bounds') or {}
    lines = [
        f"# {doc['kb_id']} · {doc['title']}",
        '',
        '| 字段 | 值 |',
        '| --- | --- |',
        f"| 经验编号 | `{doc['kb_id']}` |",
        f"| 修订版本 | `{doc['revision']}`（父版本：`{doc.get('parent_revision') or '-'}`） |",
        f"| 轨道 | `{doc['track']}` |",
        f"| 状态 | `{doc['status']}` |",
        f"| 允许用途 | {', '.join(f'`{u}`' for u in doc.get('approved_uses', []))} |",
        f"| 标签 | {', '.join(f'`{t}`' for t in doc.get('tags', [])) or '-'} |",
        f"| 审核人 | `{doc.get('reviewed_by') or '-'}` |",
        f"| 内容指纹 | `{doc.get('content_sha256', '')[:16]}...` |",
        '',
        '## 摘要',
        '',
        doc['summary'],
        '',
        '## 适用范围与算量约束',
        '',
        f"- **模型族**：`{scope.get('model_family') or '-'}`",
        f"- **基线推理算量**：`{scope.get('baseline_flops_m')}` MFLOPs",
        f"- **目标算量红线**：`<= {scope.get('target_flops_budget_m')}` MFLOPs / `<= {scope.get('max_flops_ratio')}x`",
        f"- **禁用算子**：{', '.join(f'`{op}`' for op in scope.get('forbidden_ops', [])) or '-'}",
        '',
    ]
    if bounds:
        lines.extend([
            '### 参数合法域（`param_bounds`）',
            '',
            '| 字段 | 类型 | 范围 / 枚举 |',
            '| --- | --- | --- |',
        ])
        for field_name, spec in bounds.items():
            if 'enum' in spec:
                constraint = f"enum: `{spec['enum']}`"
            else:
                constraint = f"min=`{spec.get('min', '-')}`, max=`{spec.get('max', '-')}`"
            lines.append(f"| `{field_name}` | `{spec.get('type', '-')}` | {constraint} |")
        lines.append('')

    lines.extend([
        '## 推荐结构模式（Patterns）',
        '',
        '| ID | 模式说明 | 声明式变更 | 方向 | 均值增益(pp) | 均值算量比 | 观测/胜出 | 置信度 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ])
    for p in doc.get('patterns', []):
        st = p['stats']
        gain_str = f"{st['mean_gain_pp']:+.2f}" if st.get('mean_gain_pp') is not None else '-'
        flops_str = f"{st['mean_flops_ratio']:.2f}x" if st.get('mean_flops_ratio') is not None else '-'
        lines.append(
            f"| `{p['pattern_id']}` | {_md_cell(p['title'])} | `{_md_cell(p['change_signature'])}` "
            f"| `{p['effect']['direction']}` | {gain_str} | {flops_str} | {st['observations']}/{st['wins']} | `{p['confidence']}` |"
        )
    if not doc.get('patterns'):
        lines.append('| - | 暂无 | - | - | - | - | - | - |')

    lines.extend([
        '',
        '## 已知反例与失效边界（Anti-Patterns）',
        '',
        '| ID | 反例说明 | 避坑变更 | 失败类型 | 实测算量比 | 实测增益(pp) | 次数 |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ])
    for a in doc.get('anti_patterns', []):
        flops_str = f"{a['observed_flops_ratio']:.2f}x" if a.get('observed_flops_ratio') is not None else '-'
        gain_str = f"{a['observed_gain_pp']:+.2f}" if a.get('observed_gain_pp') is not None else '-'
        lines.append(
            f"| `{a['pattern_id']}` | {_md_cell(a['title'])} | `{_md_cell(a['change_signature'])}` "
            f"| `{a['failure_type']}` | {flops_str} | {gain_str} | {a['occurrences']} |"
        )
    if not doc.get('anti_patterns'):
        lines.append('| - | 暂无 | - | - | - | - | - |')

    lines.extend([
        '',
        '---',
        '',
        '<!-- 以下为机器精确解析用结构化块，请通过 kb CLI 或保持合法 JSON 维护 -->',
        RECORD_START,
        '```json',
        json.dumps(doc, ensure_ascii=False, indent=2),
        '```',
        RECORD_END,
        '',
    ])
    return '\n'.join(lines)


def render_draft_markdown(draft: dict[str, Any]) -> str:
    ev = draft['evidence']
    preview = draft.get('merge_preview') or {}
    lines = [
        f"# [DRAFT] {draft['kb_id']} · {draft['revision']}",
        '',
        f"- **来源 Campaign**：`{draft['source_campaign_id']}`",
        f"- **基于父修订**：`{draft['parent_revision']}`",
        f"- **合并预览**：Patterns 新增 `{preview.get('patterns', {}).get('added', 0)}` / 聚合 `{preview.get('patterns', {}).get('merged', 0)}`；"
        f"Anti-Patterns 新增 `{preview.get('anti_patterns', {}).get('added', 0)}` / 聚合 `{preview.get('anti_patterns', {}).get('merged', 0)}`",
        f"- **Holdout 结论**：accepted=`{ev.get('holdout_accepted')}`, gain=`{ev.get('holdout_gain_pp')}pp`, "
        f"flops_ratio=`{ev.get('flops_ratio')}x`, total_gpu_s=`{ev.get('total_gpu_seconds')}`",
        '',
        f"人工审核通过后执行：`PYTHONPATH=demos python3 -m autoresearcher_harness kb publish {draft['kb_id']} --reviewer <name>`",
        '',
        RECORD_START,
        '```json',
        json.dumps(draft, ensure_ascii=False, indent=2),
        '```',
        RECORD_END,
        '',
    ]
    return '\n'.join(lines)


def render_evidence_markdown(kb_id: str, records: list[dict[str, Any]]) -> str:
    lines = [
        f'# {kb_id} · 实证账本（Evidence Log）',
        '',
        '| 证据 ID | 修订 | Campaign | Holdout 验收 | 增益(pp) | 推理算量比 | 搜索 GPU(s) | 单位算量增益 | 胜出变更 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for ev in records:
        ev_id = ev.get('evidence_id') or ev.get('source') or ev.get('campaign_id') or '-'
        accepted = ev.get('holdout_accepted') if 'holdout_accepted' in ev else ev.get('accepted')
        gain = f"{ev['holdout_gain_pp']:+.2f}" if ev.get('holdout_gain_pp') is not None else '-'
        flops = f"{ev['flops_ratio']:.2f}x" if ev.get('flops_ratio') is not None else '-'
        gpu_s = f"{ev.get('total_gpu_seconds', ev.get('gpu_seconds', 0.0)):.1f}"
        gph = f"{ev['gain_per_gpu_hour']:.1f}" if ev.get('gain_per_gpu_hour') is not None else '-'
        changes = canonical_change_signature(ev.get('incumbent_changes') or {})
        lines.append(
            f"| `{_md_cell(ev_id)}` | `{_md_cell(ev.get('revision'))}` | `{_md_cell(ev.get('campaign_id'))}` "
            f"| `{accepted}` | {gain} | {flops} | {gpu_s} | {gph} | `{_md_cell(changes)}` |"
        )
    if not records:
        lines.append('| - | - | - | - | - | - | - | - | - |')
    lines.extend([
        '',
        EVIDENCE_START,
        '```json',
        json.dumps(records, ensure_ascii=False, indent=2),
        '```',
        EVIDENCE_END,
        '',
    ])
    return '\n'.join(lines)


def render_index_markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        '# 结构经验库总索引（INDEX）',
        '',
        '本目录全部采用纯 Markdown 文档存储，无数据库依赖，支持人工/Obsidian 阅读、Git 评审与 Coding Agent 直接检索。',
        '',
        '| 编号 | 活跃修订 | 轨道 | 状态 | 模型族 | 算量红线(MFLOPs) | 模式 / 反例 / 证据 / 草案 | 文档入口 |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for item in entries:
        scope = item.get('scope') or {}
        counts = (
            f"{len(item.get('patterns', []))} / {len(item.get('anti_patterns', []))} / "
            f"{len(item.get('evidence', []))} / {len(item.get('draft_revisions', []))}"
        )
        lines.append(
            f"| `{item['kb_id']}` | `{item['revision']}` | `{item['track']}` | `{item['status']}` "
            f"| `{_md_cell(scope.get('model_family'))}` | `{_md_cell(scope.get('target_flops_budget_m'))}` "
            f"| {counts} | [CURRENT.md](entries/{item['kb_id']}/CURRENT.md) |"
        )
    if not entries:
        lines.append('| - | - | - | - | - | - | - | - |')
    lines.append('')
    return '\n'.join(lines)


class KnowledgeBase:
    """Pure-Markdown layered immutable structured knowledge base (zero database dependency).

    Directory layout:
      <root>/INDEX.md                                 (auto-maintained Markdown catalog)
      <root>/entries/<kb_id>/CURRENT.md               (active revision snapshot)
      <root>/entries/<kb_id>/revisions/<rev>.md       (immutable historical snapshots)
      <root>/entries/<kb_id>/drafts/<draft>.md        (isolated review drafts)
      <root>/entries/<kb_id>/EVIDENCE.md              (append-only empirical evidence log)
    """

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.entries_dir = self.root / 'entries'
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self.index_md_path = self.root / 'INDEX.md'

    def _safe_id(self, kb_id: str) -> str:
        safe = kb_id.strip()
        if not safe or '/' in safe or '\\' in safe or '..' in safe:
            raise ValueError(f'Invalid kb_id: {kb_id}')
        return safe

    def _entry_dir(self, kb_id: str) -> Path:
        return self.entries_dir / self._safe_id(kb_id)

    def _current_path(self, kb_id: str) -> Path:
        return self._entry_dir(kb_id) / 'CURRENT.md'

    def _revisions_dir(self, kb_id: str) -> Path:
        return self._entry_dir(kb_id) / 'revisions'

    def _revision_path(self, kb_id: str, revision: str) -> Path:
        return self._revisions_dir(kb_id) / f'{self._safe_id(revision)}.md'

    def _drafts_dir(self, kb_id: str) -> Path:
        return self._entry_dir(kb_id) / 'drafts'

    def _evidence_path(self, kb_id: str) -> Path:
        return self._entry_dir(kb_id) / 'EVIDENCE.md'

    @staticmethod
    def validate_revision_doc(doc: dict[str, Any]) -> dict[str, Any]:
        if doc.get('schema_version') not in (1, 2):
            raise ValueError('Unsupported KB schema_version')
        for field in ('kb_id', 'revision', 'title', 'summary'):
            if not isinstance(doc.get(field), str) or not doc[field].strip():
                raise ValueError(f'KB {field} is required')
        if doc.get('track') not in TRACKS:
            raise ValueError(f"Unsupported KB track: {doc.get('track')}")
        if doc.get('status') not in KB_STATUSES:
            raise ValueError(f"Unsupported KB status: {doc.get('status')}")
        if not isinstance(doc.get('approved_uses'), list):
            raise ValueError('KB approved_uses must be a list')
        if not isinstance(doc.get('scope'), dict):
            raise ValueError('KB scope must be an object')
        if not isinstance(doc.get('patterns', []), list):
            raise ValueError('KB patterns must be a list')
        if not isinstance(doc.get('anti_patterns', []), list):
            raise ValueError('KB anti_patterns must be a list')
        doc['patterns'] = [_normalize_pattern(p) for p in doc.get('patterns', [])]
        doc['anti_patterns'] = [_normalize_anti_pattern(a) for a in doc.get('anti_patterns', [])]
        return doc

    def _read_evidence(self, kb_id: str) -> list[dict[str, Any]]:
        path = self._evidence_path(kb_id)
        if not path.is_file():
            return []
        data = _extract_json_block(path.read_text(encoding='utf-8'), EVIDENCE_START, EVIDENCE_END)
        if not isinstance(data, list):
            raise ValueError(f'Invalid evidence block in {path}')
        return data

    def _write_evidence(self, kb_id: str, records: list[dict[str, Any]]) -> None:
        write_text(self._evidence_path(kb_id), render_evidence_markdown(kb_id, records))

    def _list_revisions(self, kb_id: str) -> list[dict[str, Any]]:
        rev_dir = self._revisions_dir(kb_id)
        if not rev_dir.is_dir():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(rev_dir.glob('*.md')):
            doc = _extract_json_block(path.read_text(encoding='utf-8'), RECORD_START, RECORD_END)
            items.append({
                'revision': doc['revision'],
                'parent_revision': doc.get('parent_revision'),
                'status': doc['status'],
                'reviewed_by': doc.get('reviewed_by'),
                'published_at': doc.get('published_at'),
                'content_sha256': doc.get('content_sha256'),
            })
        return items

    def list_drafts(self, kb_id: str | None = None) -> list[dict[str, Any]]:
        kb_ids = [self._safe_id(kb_id)] if kb_id else sorted(
            p.name for p in self.entries_dir.iterdir() if p.is_dir() and (p / 'CURRENT.md').is_file()
        )
        drafts: list[dict[str, Any]] = []
        for item_id in kb_ids:
            d_dir = self._drafts_dir(item_id)
            if not d_dir.is_dir():
                continue
            for path in sorted(d_dir.glob('*.md')):
                drafts.append(_extract_json_block(path.read_text(encoding='utf-8'), RECORD_START, RECORD_END))
        return drafts

    def load(self, kb_id: str, revision: str | None = None) -> dict[str, Any]:
        safe_id = self._safe_id(kb_id)
        current_path = self._current_path(safe_id)
        if not current_path.is_file():
            raise ValueError(f'Unknown KB entry: {kb_id}')
        current_doc = _extract_json_block(current_path.read_text(encoding='utf-8'), RECORD_START, RECORD_END)
        active_revision = current_doc['revision']
        target_path = self._revision_path(safe_id, revision) if revision else current_path
        if not target_path.is_file():
            raise ValueError(f'Unknown revision {revision} for KB entry {kb_id}')
        raw_doc = _extract_json_block(target_path.read_text(encoding='utf-8'), RECORD_START, RECORD_END)
        doc = self.validate_revision_doc(raw_doc)
        expected_sha = doc.get('content_sha256')
        actual_sha = _compute_content_sha256(doc)
        if expected_sha and expected_sha != actual_sha:
            raise ValueError(f'Revision integrity check failed for {safe_id}@{doc["revision"]}')
        doc['content_sha256'] = actual_sha
        doc['active_revision'] = active_revision
        doc['revisions'] = self._list_revisions(safe_id)
        doc['evidence'] = self._read_evidence(safe_id)
        doc['draft_revisions'] = self.list_drafts(safe_id)
        return doc

    def save(self, entry: dict[str, Any], allow_overwrite_revision: bool = False) -> Path:
        """Persist an immutable revision .md file, update CURRENT.md / EVIDENCE.md, and refresh INDEX.md."""
        safe_id = self._safe_id(entry['kb_id'])
        revision = self._safe_id(entry['revision'])
        rev_path = self._revision_path(safe_id, revision)
        if rev_path.is_file() and not allow_overwrite_revision:
            raise ValueError(f'Revision {safe_id}@{revision} is immutable and already exists')

        rev_doc = self.validate_revision_doc({
            'schema_version': 2,
            'kb_id': safe_id,
            'revision': revision,
            'parent_revision': entry.get('parent_revision'),
            'track': entry['track'],
            'status': entry['status'],
            'approved_uses': list(entry['approved_uses']),
            'tags': list(entry.get('tags') or []),
            'title': entry['title'],
            'summary': entry['summary'],
            'scope': entry['scope'],
            'patterns': entry.get('patterns', []),
            'anti_patterns': entry.get('anti_patterns', []),
            'text': entry.get('text') or self._render_text(entry),
            'reviewed_by': entry.get('reviewed_by', 'seed'),
            'published_at': entry.get('published_at', time.time()),
        })
        rev_doc['content_sha256'] = _compute_content_sha256(rev_doc)
        md_text = render_revision_markdown(rev_doc)
        write_text(rev_path, md_text)
        write_text(self._current_path(safe_id), md_text)
        self._drafts_dir(safe_id).mkdir(parents=True, exist_ok=True)
        if 'evidence' in entry and entry['evidence'] is not None:
            self._write_evidence(safe_id, list(entry['evidence']))
        elif not self._evidence_path(safe_id).is_file():
            self._write_evidence(safe_id, [])
        self.reindex()
        return rev_path

    def reindex(self) -> Path:
        """Rebuild INDEX.md directly from all Markdown entries under entries/."""
        entries = self.list_entries()
        write_text(self.index_md_path, render_index_markdown(entries))
        return self.index_md_path

    def list_entries(self, track: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for entry_dir in sorted(self.entries_dir.iterdir()):
            if not entry_dir.is_dir() or not (entry_dir / 'CURRENT.md').is_file():
                continue
            doc = self.load(entry_dir.name)
            if track and doc['track'] != track:
                continue
            if status and doc['status'] != status:
                continue
            entries.append(doc)
        return entries

    def search(
        self,
        query: str | None = None,
        track: str | None = None,
        model_family: str | None = None,
        max_flops_m: float | None = None,
        max_flops_ratio: float | None = None,
        min_gain_pp: float | None = None,
        field: str | None = None,
        direction: str | None = None,
        failure_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Multi-dimensional structured search directly over Markdown KB documents."""
        needle = (query or '').strip().lower()
        family_needle = (model_family or '').strip().lower()
        results: list[dict[str, Any]] = []
        for entry in self.list_entries(track=track, status=status):
            scope = entry.get('scope') or {}
            if family_needle:
                fam = str(scope.get('model_family') or '').lower()
                if family_needle not in fam:
                    continue
            if max_flops_m is not None:
                budget = scope.get('target_flops_budget_m')
                if isinstance(budget, (int, float)) and budget > max_flops_m:
                    continue

            matched_patterns = list(entry.get('patterns', []))
            if direction:
                matched_patterns = [p for p in matched_patterns if p['effect']['direction'] == direction]
            if min_gain_pp is not None:
                matched_patterns = [
                    p for p in matched_patterns
                    if p['stats'].get('mean_gain_pp') is not None and p['stats']['mean_gain_pp'] >= min_gain_pp
                ]
            if max_flops_ratio is not None:
                matched_patterns = [
                    p for p in matched_patterns
                    if p['stats'].get('mean_flops_ratio') is not None and p['stats']['mean_flops_ratio'] <= max_flops_ratio
                ]
            if field:
                matched_patterns = [p for p in matched_patterns if field in p.get('target_fields', [])]
            matched_patterns.sort(key=lambda p: p['stats'].get('mean_gain_pp') or -1e9, reverse=True)

            matched_anti = list(entry.get('anti_patterns', []))
            if failure_type:
                matched_anti = [a for a in matched_anti if a['failure_type'] == failure_type]
            if field:
                matched_anti = [a for a in matched_anti if field in a.get('target_fields', [])]
            matched_anti.sort(key=lambda a: a.get('occurrences', 0), reverse=True)

            has_pattern_filter = any(x is not None for x in (direction, min_gain_pp, max_flops_ratio))
            if has_pattern_filter and not matched_patterns:
                continue
            if failure_type and not matched_anti:
                continue
            if field and not matched_patterns and not matched_anti:
                continue
            if needle and needle not in json.dumps(entry, ensure_ascii=False).lower():
                continue

            entry['matched_patterns'] = matched_patterns
            entry['matched_anti_patterns'] = matched_anti
            results.append(entry)
        return results

    def freeze_snapshot(self, kb_id: str, revision: str | None = None) -> dict[str, Any]:
        entry = self.load(kb_id, revision=revision)
        if entry['status'] != 'published':
            raise ValueError(f"KB entry {kb_id} must be published (got status={entry['status']})")
        if 'training' not in entry['approved_uses']:
            raise ValueError(f'KB entry {kb_id} must allow training use')
        snapshot = {
            'id': entry['kb_id'],
            'revision': entry['revision'],
            'track': entry['track'],
            'status': entry['status'],
            'approved_uses': list(entry['approved_uses']),
            'title': entry['title'],
            'scope': entry['scope'],
            'patterns': entry['patterns'],
            'anti_patterns': entry['anti_patterns'],
            'evidence_count': len(entry['evidence']),
            'text': entry.get('text') or self._render_text(entry),
        }
        snapshot['sha256'] = hashlib.sha256(
            json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).hexdigest()
        return snapshot

    @staticmethod
    def _render_text(entry: dict[str, Any]) -> str:
        patterns = '; '.join(p.get('title', '') for p in entry.get('patterns', []))
        anti = '; '.join(a.get('title', '') for a in entry.get('anti_patterns', []))
        return (
            f"{entry['title']}。{entry['summary']}"
            + (f' 推荐结构模式：{patterns}。' if patterns else '')
            + (f' 已知反例：{anti}。' if anti else '')
        )

    def distill_from_campaign(self, campaign: dict[str, Any], kb_id: str | None = None) -> dict[str, Any]:
        """Write an isolated draft .md file under entries/<kb_id>/drafts/ without mutating published files."""
        plan = campaign['plan']
        resolved_id = self._safe_id(kb_id or plan.get('kb_ref') or plan['knowledge']['id'])
        if not self._current_path(resolved_id).is_file():
            self.save({
                'schema_version': 2,
                'kb_id': resolved_id,
                'revision': plan['knowledge'].get('revision', 'v1'),
                'track': plan.get('track', 'architecture'),
                'status': 'draft',
                'approved_uses': list(plan['knowledge'].get('approved_uses', ['training', 'evaluation'])),
                'title': plan['knowledge'].get('title') or f'{resolved_id} 结构经验条目',
                'summary': plan['base_hypothesis'],
                'scope': plan['knowledge'].get('scope') or {},
                'patterns': list(plan['knowledge'].get('patterns') or []),
                'anti_patterns': list(plan['knowledge'].get('anti_patterns') or []),
                'text': plan['knowledge']['text'],
            })
        entry = self.load(resolved_id)
        incumbent = next(
            (t for t in campaign['trials'] if t['trial_id'] == campaign.get('incumbent_trial_id')),
            None,
        )
        holdout = campaign.get('holdout_report') or {}
        incoming_patterns: list[dict[str, Any]] = []
        incoming_anti: list[dict[str, Any]] = []
        for trial in campaign['trials']:
            if trial['is_baseline'] or not trial.get('changes'):
                continue
            sig = canonical_change_signature(trial['changes'])
            gain_metric = trial.get('gain_pct') if trial.get('gain_pct') is not None else trial.get('gain_pp')
            compute_ratio = trial.get('compute_ratio') if trial.get('compute_ratio') is not None else trial.get('flops_ratio')
            cost_val = trial.get('cost_value') if trial.get('cost_value') else trial.get('gpu_seconds')
            if trial['decision'] == 'keep':
                incoming_patterns.append({
                    'pattern_id': f"P-{campaign['campaign_id'][-6:].upper()}-{trial['trial_id']}",
                    'change_signature': sig,
                    'title': trial['hypothesis'],
                    'suggested_changes': trial['changes'],
                    'target_fields': sorted(trial['changes'].keys()),
                    'effect': {
                        'expected_gain_pp_range': [gain_metric, gain_metric] if gain_metric is not None else None,
                        'expected_flops_ratio_range': [compute_ratio, compute_ratio] if compute_ratio is not None else None,
                        'direction': _infer_direction(gain_metric, compute_ratio),
                        'notes': trial.get('decision_reason') or '',
                    },
                    'stats': {
                        'observations': 1,
                        'wins': 1,
                        'mean_gain_pp': gain_metric,
                        'mean_flops_ratio': compute_ratio,
                        'mean_gpu_seconds': cost_val,
                    },
                    'confidence': 'verified_holdout' if holdout.get('accepted') else 'dev_only',
                    'evidence_refs': [campaign['campaign_id']],
                })
            elif trial['decision'] in {'discard', 'crash'}:
                incoming_anti.append({
                    'pattern_id': f"AP-{campaign['campaign_id'][-6:].upper()}-{trial['trial_id']}",
                    'change_signature': sig,
                    'title': trial['hypothesis'],
                    'avoid_changes': trial['changes'],
                    'target_fields': sorted(trial['changes'].keys()),
                    'failure_type': _infer_failure_type(trial['decision'], trial.get('decision_reason')),
                    'observed_flops_ratio': compute_ratio,
                    'observed_gain_pp': gain_metric,
                    'observed_failure': trial.get('decision_reason') or trial['decision'],
                    'occurrences': 1,
                    'evidence_refs': [campaign['campaign_id']],
                })

        _, p_preview = merge_patterns(entry['patterns'], incoming_patterns)
        _, a_preview = merge_anti_patterns(entry['anti_patterns'], incoming_anti)
        draft_revision = _next_revision_label(entry['revision'], draft=True)
        holdout_gain_pct = holdout.get('gain_pct') if holdout.get('gain_pct') is not None else holdout.get('gain_pp')
        holdout_compute_ratio = holdout.get('compute_ratio') if holdout.get('compute_ratio') is not None else holdout.get('flops_ratio')
        total_cost_val = campaign.get('total_cost') or campaign.get('total_gpu_seconds', 0.0)
        evidence_item = {
            'evidence_id': f"ev-{campaign['campaign_id']}",
            'campaign_id': campaign['campaign_id'],
            'parent_revision': entry['revision'],
            'recorded_at': time.time(),
            'track': plan.get('track', 'architecture'),
            'model_family': plan.get('model_family') or (plan['knowledge'].get('scope') or {}).get('model_family'),
            'incumbent_trial_id': campaign.get('incumbent_trial_id'),
            'incumbent_changes': incumbent['changes'] if incumbent else {},
            'incumbent_config': (incumbent.get('candidate_config') or incumbent.get('architecture')) if incumbent else None,
            'holdout_accepted': holdout.get('accepted'),
            'primary_metric': holdout.get('primary_metric_name', 'correct'),
            'holdout_primary_value': holdout.get('candidate_primary_value', holdout.get('candidate_correct')),
            'holdout_gain': holdout.get('gain', holdout.get('gain_correct')),
            'holdout_gain_pp': holdout_gain_pct,
            'compute_metric': holdout.get('compute_metric_name', 'inference_flops_m'),
            'candidate_compute_value': holdout.get('candidate_compute_value', holdout.get('candidate_inference_flops_m')),
            'flops_ratio': holdout_compute_ratio,
            'cost_metric': holdout.get('cost_metric_name', 'gpu_seconds'),
            'total_gpu_seconds': round(float(total_cost_val), 3),
            'total_train_tflops': round(campaign.get('total_train_tflops', 0.0), 3),
            'gain_per_gpu_hour': holdout.get('gain_per_cost', holdout.get('gain_per_gpu_hour')),
        }
        draft_payload = {
            'schema_version': 2,
            'kb_id': resolved_id,
            'revision': draft_revision,
            'parent_revision': entry['revision'],
            'status': 'draft',
            'created_at': time.time(),
            'source_campaign_id': campaign['campaign_id'],
            'merge_preview': {'patterns': p_preview, 'anti_patterns': a_preview},
            'added_patterns': incoming_patterns,
            'added_anti_patterns': incoming_anti,
            'evidence': evidence_item,
        }
        draft_path = self._drafts_dir(resolved_id) / f"{draft_revision}-{campaign['campaign_id'][-8:]}.md"
        write_text(draft_path, render_draft_markdown(draft_payload))
        self.reindex()
        return draft_payload

    def publish(self, kb_id: str, draft_revision: str | None = None, reviewer: str = 'human') -> dict[str, Any]:
        """Merge a reviewed draft .md into a new immutable revision .md, append EVIDENCE.md, and refresh INDEX.md."""
        safe_id = self._safe_id(kb_id)
        entry = self.load(safe_id)
        draft_dir = self._drafts_dir(safe_id)
        draft_files = sorted(draft_dir.glob('*.md')) if draft_dir.is_dir() else []
        if not draft_files:
            if entry['status'] == 'draft':
                entry['status'] = 'published'
                entry['reviewed_by'] = reviewer
                self.save(entry, allow_overwrite_revision=True)
                return self.load(safe_id)
            raise ValueError(f'No pending draft revisions for {kb_id}')

        selected_path = None
        selected = None
        for path in draft_files:
            payload = _extract_json_block(path.read_text(encoding='utf-8'), RECORD_START, RECORD_END)
            if draft_revision is None or payload['revision'] == draft_revision or path.stem == draft_revision:
                selected_path = path
                selected = payload
        if selected is None or selected_path is None:
            raise ValueError(f'Unknown draft revision {draft_revision} for {kb_id}')

        new_revision = _next_revision_label(entry['revision'], draft=False)
        merged_patterns, _ = merge_patterns(entry['patterns'], selected.get('added_patterns', []))
        merged_anti, _ = merge_anti_patterns(entry['anti_patterns'], selected.get('added_anti_patterns', []))

        new_doc = {
            'schema_version': 2,
            'kb_id': safe_id,
            'revision': new_revision,
            'parent_revision': entry['revision'],
            'track': entry['track'],
            'status': 'published',
            'approved_uses': entry['approved_uses'],
            'tags': entry.get('tags', []),
            'title': entry['title'],
            'summary': entry['summary'],
            'scope': entry['scope'],
            'patterns': merged_patterns,
            'anti_patterns': merged_anti,
            'reviewed_by': reviewer,
            'published_at': time.time(),
        }
        new_doc['text'] = self._render_text(new_doc)
        evidence_records = [*self._read_evidence(safe_id), {**selected['evidence'], 'revision': new_revision}]
        self._write_evidence(safe_id, evidence_records)
        selected_path.unlink()
        self.save(new_doc, allow_overwrite_revision=False)
        return self.load(safe_id)
