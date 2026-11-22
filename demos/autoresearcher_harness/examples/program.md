# Research Program · 给 Claude Code / Codex / OpenCode 的通用自主研究指令

本文件仿照 `karpathy/autoresearch` 的 `program.md`，供外部 Coding Agent（Claude Code / Codex / OpenCode）直接驱动 `autoresearcher_harness`。

支持两种运行方式：
- **推荐主路径（`external_mcp` / BYO-MCP）**：你已经搭好了训练/仿真/评测 MCP，Agent 直接调用你的 MCP 工具，Harness 作为零硬编码的控制面负责**纯 Markdown 结构经验库、嵌套白名单与 `param_bounds` 硬门禁、通用增益（`maximize/minimize`）与算量/成本棘轮、`results.tsv` 账本及 Holdout 验收**。
- **离线托管模式（`managed`）**：无外部 MCP 时使用内置模拟或配置化适配器（`ConfigurableMCPAdapter`）跑通演示与测试。

---

## 0. 模型工程师 1 秒自助搭建新模型流程

任意模型工程化优化工程师只需一条命令即可生成自己的专属目录（`campaign.json` + `program.md` + `mcp_tools.md` + 纯 Markdown `kb/`），**无需修改一行 Harness 代码**：

```bash
PYTHONPATH=demos python3 -m autoresearcher_harness init \
  --workspace ./my_csi_autoresearch \
  --model-family cnn_csi_feedback \
  --kb-id CSI-ARCH-001 \
  --metric nmse_db --direction minimize --min-gain 0.3 --holdout-target -18.0 \
  --compute macs_m --compute-unit MMACs --max-compute-ratio 1.10 \
  --cost gpu_hours --cost-unit h --max-cost 4.0
```

随后只需在生成的 `campaign.json` 填入模型的 `base_config` / `mutable_fields`，在 `mcp_tools.md` 填好自己已搭好的 MCP 工具名即可开跑。

---

## 1. 核心目标（增益 + 算量双优先，结构主线 + HPO 独立收尾）

- **结构轨道（`track=architecture`，优先）**：冻结训练配方，演化声明式模型配置（支持嵌套 dot-path 如 `encoder.num_blocks`），在推理算量红线内最大化主指标增益；同增益下优先保留推理算量更低的结构。
- **收尾 HPO 轨道（`track=hpo`）**：锁定胜出结构并完成独立 Holdout 验收后，另起独立 HPO Campaign（冻结结构、仅调训练配方）。**严禁混搜结构与 HPO。**

---

## 2. Agent 标准循环（BYO-MCP 主路径）

### Step 1：检索纯 Markdown 结构经验库（按模型族、增益方向、算量比）
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness kb list --track architecture --status published
PYTHONPATH=demos python3 -m autoresearcher_harness kb search --model-family cnn_csi --track architecture
PYTHONPATH=demos python3 -m autoresearcher_harness kb show CNN-CSI-001
```

### Step 2：创建 Campaign 并建立基线（Baseline-first）
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness campaign create \
  --plan demos/autoresearcher_harness/examples/campaign_byo_mcp_nmse.json \
  --kb CNN-CSI-001
PYTHONPATH=demos python3 -m autoresearcher_harness campaign baseline latest
# Agent 调用你已搭好的 MCP 跑完基线训练与 Dev 评测后回填：
PYTHONPATH=demos python3 -m autoresearcher_harness campaign record latest --status succeeded \
  --metrics '{"nmse_db": -16.5, "macs_m": 50.0, "latency_ms": 1.8}' \
  --cost '{"gpu_hours": 0.4}' \
  --artifacts '{"model_ref": "uri://models/csi-base-ckpt"}'
```

### Step 3：多轮棘轮循环（Context → Propose → 调你的 MCP → Record）
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness campaign context latest
PYTHONPATH=demos python3 -m autoresearcher_harness campaign propose latest \
  --hypothesis "在编码器引入 SE 注意力并扩大卷积核至 5，提升 CSI 重建精度同时控制 MACs <= 1.10x" \
  --changes '{"encoder.use_se": true, "encoder.kernel_size": 5}'
# 读取返回的 candidate_config，直接调用你已搭好的 MCP 执行训练与 Dev 评测，随后回填：
PYTHONPATH=demos python3 -m autoresearcher_harness campaign record latest --status succeeded \
  --metrics '{"nmse_db": -18.2, "macs_m": 51.2, "latency_ms": 1.9}' \
  --cost '{"gpu_hours": 0.45}' \
  --artifacts '{"model_ref": "uri://models/csi-trial-001"}'
```
若某轮远端训练 OOM/失败/超时，记录 crash（不中断后续探索）：
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness campaign record latest --status crash \
  --cost '{"gpu_hours": 0.15}' --note "OOM at batch_size=128"
```

### Step 4：锁定最终 Incumbent，调用 Holdout 评测 MCP 并验收
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness campaign finalize latest \
  --metrics '{"nmse_db": -18.1, "macs_m": 51.2, "latency_ms": 1.9}' \
  --cost '{"gpu_hours": 0.05}' \
  --artifacts '{"model_ref": "uri://models/csi-trial-001"}'
```

### Step 5：将实测增益、算量与反例蒸馏回写为隔离 Markdown 草案
```bash
PYTHONPATH=demos python3 -m autoresearcher_harness kb distill latest
PYTHONPATH=demos python3 -m autoresearcher_harness kb drafts CNN-CSI-001
# 人工审核通过后发布不可变新修订并自动去重聚合：
# PYTHONPATH=demos python3 -m autoresearcher_harness kb publish CNN-CSI-001 --reviewer <name>
```
