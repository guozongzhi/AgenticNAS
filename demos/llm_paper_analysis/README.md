# Codex 论文检索与解析

该工具从本地 PDF 提取文本，按研究问题检索相关片段，并生成带页码的 Codex 证据包。Codex 直接读取证据包并填写 [`research/papers/parsed/TEMPLATE.md`](../../research/papers/parsed/TEMPLATE.md)，不需要额外 LLM API、API key 或模型配置。

PDF 提取依次尝试 `pypdf`、PyMuPDF 和 Poppler 的 `pdftotext`，三者具备其一即可。第一版使用可复现的关键词排序，不引入向量数据库。

## 生成 Codex 证据包

```bash
PYTHONPATH=demos/llm_paper_analysis python3 \
  demos/llm_paper_analysis/paper_parser.py \
  --pdf research/papers/pdfs/2302.14838-evoprompting.pdf \
  --query "LLM NAS mutation crossover Pareto budget ablation" \
  --force
```

证据包默认写入已忽略的 `demos/llm_paper_analysis/outputs/`。在 Codex 中要求“解析这篇论文”时，Codex负责运行工具、阅读证据、填写模板并把结果保存到 `research/papers/parsed/`。

## 结果约束

- Codex 输出标记为 `codex_draft`；
- 关键主张必须附带 PDF 页码、章节、表格或图编号；
- 没有证据时写“论文未报告”；
- 人工核对关键数字后，才能在论文索引中改为 `retained`。

## 验证

```bash
PYTHONPATH=demos/llm_paper_analysis python3 -m unittest discover \
  -s demos/llm_paper_analysis/tests -v
```
