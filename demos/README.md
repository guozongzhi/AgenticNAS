# 可运行 Demo

`demos/` 保存独立、可运行的 clean-room 示例。每个 Demo 在自己的子目录中集中维护实现、输入样例、测试和已忽略的运行输出。

当前目录：

- `agentic_nas_demo/`：4–10 层 Conv1d Transformer、block/cell/op 搜索空间、LLM Agent 动作契约和 Pareto 搜索闭环。
- `llm_paper_analysis/`：从本地 PDF 检索证据片段，供 Codex 直接生成结构化论文笔记。

从仓库根目录运行：

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/agentic_nas_demo/tests -v
PYTHONPATH=demos python3 -m agentic_nas_demo --iterations 3
PYTHONPATH=demos/llm_paper_analysis python3 -m unittest discover \
  -s demos/llm_paper_analysis/tests -v
```

默认 trace 写入 `demos/agentic_nas_demo/outputs/demo/`。
