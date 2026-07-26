# 解析后的论文

本目录保存 Codex 基于本地 PDF 证据生成、并可继续人工修订的结构化论文笔记。文件命名使用 `YYYY-venue-short-title.md`，例如 `2023-arxiv-evoprompting.md`。

## 状态要求

- 新生成笔记必须标记为 `codex_draft`；
- 每个关键结果必须附带页码、章节、表格或图编号；
- 没有证据时写“论文未报告”，不得根据常识补全；
- 不保留大段论文原文，只记录必要的短语和自己的归纳；
- 完成人工核验后填写模板末尾的检查项，并在 `INDEX.md` 中链接笔记；
- 未经人工核验的内容不能直接用于论文 related work 或实验结论。

Codex 证据包工具与使用方法见 [`demos/llm_paper_analysis/`](../../../demos/llm_paper_analysis/README.md)。
