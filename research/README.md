# 研究资料入口

`research/` 保存论文索引、阅读笔记和本地 PDF 清单。正式实验及其专属代码统一放在根目录 [`experiments/`](../experiments/README.md)；公司内部实验数据不得放入任一公开目录。

```text
research/
├── papers/
│   ├── INDEX.md       # 阅读队列、状态和主题索引
│   ├── TEMPLATE.md    # 单篇论文笔记模板
│   ├── parsed/
│   │   ├── README.md  # Codex 草稿的核验和保留规则
│   │   └── TEMPLATE.md
│   └── pdfs/
│       └── README.md  # 本地 PDF 文件名、页数和校验值
```

## 使用流程

1. 发现论文时先在 `papers/INDEX.md` 添加一行，状态为 `inbox`；
2. 人工阅读时复制 `TEMPLATE.md`；由 Codex 解析时按 [`parsed/TEMPLATE.md`](papers/parsed/TEMPLATE.md) 生成 `codex_draft`；
3. 人工核对 Codex 草稿中的标题、数字、预算和证据位置，状态改为 `reading`；
4. 完成实验协议、基线、公平性风险和可复现行动项后，状态改为 `retained`；
5. 若已运行代码或重现关键结果，状态改为 `reproduced`，并链接到对应公开脚本、提交或实验 trace；
6. 定期从 `retained` 中提炼 related-work 对比表和下一轮实验假设。

每个正式实验先在根目录 `experiments/` 建立协议，再运行代码；目录名使用 `YYYYMMDD-short-topic`。提交协议、专属代码、聚合结果和结论，不提交 checkpoint、训练数据或未经批准的内部日志。

Git 中只保存引用信息、公开链接、自己的笔记、PDF 清单和获批可公开的结果。`papers/pdfs/*.pdf` 是已忽略的本地缓存；受版权保护的 PDF、公司内部日志、密钥和未审批架构细节不得提交到远端仓库。

建议标签保持小而稳定：`llm-nas`、`evolution`、`pareto`、`hardware-aware`、`zero-cost`、`transformer`、`benchmark`、`hpo`。
