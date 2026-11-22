# AutoResearcher Harness · 通用模型优化控制面

面向 **Claude Code / Codex / OpenCode** 的模型无关（Model-Agnostic）、MCP 无关（BYO-MCP）自主研究编排底座，聚焦**模型结构优化（主线）**、**增益 + 算量**双核心指标与**纯 Markdown 结构经验库**；HPO 作为锁定胜出结构后的独立收尾轨道。

全部代码仅依赖 Python 3.10+ 标准库，适用于 macOS 或 Linux。

---

## 工程师 1 分钟自助接入（无需改一行代码）

任意模型工程化优化工程师（CV / 无线 CSI / Conv1d / Transformer / 检测 / 回归等）只需一条 `init` 命令，即可为自己的模型生成专属工作区：

```bash
PYTHONPATH=demos python3 -m autoresearcher_harness init \
  --workspace ./my_csi_autoresearch \
  --model-family cnn_csi_feedback \
  --kb-id CSI-ARCH-001 \
  --metric nmse_db --direction minimize --min-gain 0.3 --holdout-target -18.0 \
  --compute macs_m --compute-unit MMACs --max-compute-ratio 1.10 \
  --cost gpu_hours --cost-unit h --max-cost 4.0
```

生成的专属目录结构：
```text
my_csi_autoresearch/
  campaign.json          # 通用计划（external_mcp 模式，支持任意嵌套 base_config 与 dot-path mutable_fields）
  program.md             # 直接投喂 Claude Code / Codex / OpenCode 的定制研究指令
  mcp_tools.md           # 只需填你已搭好的 MCP 工具名与返回字段
  kb/
    INDEX.md             # 纯 Markdown 结构经验库总索引（零数据库，Obsidian / Git 友好）
    entries/CSI-ARCH-001/
      CURRENT.md         # 当前生效版本（Markdown 表格 + 强类型 param_bounds / patterns / anti_patterns）
      revisions/v1.md    # 永久不可变历史修订
      drafts/            # 蒸馏草案物理隔离目录
      EVIDENCE.md        # 追加式实证账本
```

随后工程师只需做 2 步：
1. 在 `campaign.json` 填入模型的 `base_config` / `mutable_fields`（以及 `CURRENT.md` 里的 `param_bounds`）；
2. 在 `mcp_tools.md` 写明自己已搭好的 MCP 工具名，让 Claude Code / Codex / OpenCode 按 `program.md` 开跑即可。

## 作为 Agent Skill 使用（Claude Code / Codex / OpenCode）

本仓库已将上述流程封装为跨工具通用的 Agent Skill：[skills/autoresearch/SKILL.md](../../skills/autoresearch/SKILL.md)，并在项目内配置了 `.claude/skills/autoresearch` 与 `.agents/skills/autoresearch` 软链（克隆本仓库即自动发现）。

如需安装到本机全局供其他模型仓库直接调用：

```bash
bash skills/autoresearch/scripts/install.sh --global
# 或安装到指定模型工程仓库：
bash skills/autoresearch/scripts/install.sh --project /path/to/your-model-repo
```

安装后在 Claude Code / Codex / OpenCode 中直接说“帮我给 XX 模型搭一套 autoresearch 流程”或“按 autoresearch 流程跑 5 轮结构优化”，Agent 即会自动按规范串联结构经验库、Harness 护栏与已有 MCP。

---

## 核心工作流（BYO-MCP 主路径）

当你的训练/仿真/评测 MCP 已经配置在 Claude Code / Codex / OpenCode 中时，Agent 直接调你的 MCP，Harness 负责控制面（经验库、护栏、棘轮、账本与留出隔离）：

```text
① 查纯 Markdown 结构经验库（按 model_family / 增益 / 算量检索先验与反例）
   kb search --model-family cnn_csi --track architecture
        │
        ▼
② 冻结经验与规则创建 Campaign，建立基线
   campaign create --plan campaign.json --kb CNN-CSI-001
   campaign baseline latest
   [Agent 调你已搭好的 MCP 跑基线] → campaign record latest --metrics '{...}' --cost '{...}'
        │
        ▼
③ 多轮棘轮循环
   campaign context latest
   campaign propose latest --hypothesis "..." --changes '{"encoder.use_se": true}'
   → 硬校验白名单 + 嵌套 param_bounds，返回冻结后的完整 candidate_config
   [Agent 调你已搭好的 MCP 跑本轮试验]
   campaign record latest --metrics '{"nmse_db": -18.2, "macs_m": 51.2}' --cost '{"gpu_hours": 0.45}'
   → 自动做方向归一化增益计算 + 算量红线拦截 + keep/discard/crash 棘轮 + 更新 results.tsv
        │
        ▼
④ 独立 Holdout 盲评 + 沉淀回写 Markdown 经验库
   [Agent 对 incumbent.model_ref 调 Holdout 评测 MCP]
   campaign finalize latest --metrics '{...}' --artifacts '{"model_ref": "..."}'
   kb distill latest → 生成隔离 drafts/*.md → 人工审核 kb publish（自动去重聚合统计）
```

---

## 零硬编码的通用指标与裁决口径

- **任意主指标（`acceptance.primary_metric`）**：配置 `name`、`direction`（`maximize` 如 `accuracy / map50 / throughput_mbps`，或 `minimize` 如 `nmse_db / bler / val_bpb`）、`min_gain`、`tie_tolerance`、`holdout_target`。内核统一做方向归一化，**`gain > 0` 恒表示变好**。
- **任意推理/模型算量（`acceptance.compute_metric`）**：可配 `flops_m / gflops / macs_m / latency_ms / params_m`，支持绝对红线 `max_value` 与倍率红线 `max_ratio`；**同增益（在 `tie_tolerance` 内）优先 `keep` 算量更低的候选（`compute win`）**，其次配置更简（`simplicity win`）。
- **任意搜索/训练成本（`budget.cost_metric`）**：可配 `gpu_seconds / gpu_hours / compute_units`，自动累计（含 crash 轮次）并在达到 `max_total` 时自动熔断 `budget_exhausted`，报告输出 `gain_per_cost`。
- **严格分轨（NAS 主线 + HPO 收尾）**：`track="architecture"` 冻结训练配方、`mutable_fields` 禁止触碰超参；锁定最终结构并通过 Holdout 后，另起 `track="hpo"` 独立收尾 Campaign（冻结结构、仅调训练配方）。

---

## 离线演示与配置化 MCP 适配器

无需外部 MCP 也可一键跑通内置离线示例（保留旧版兼容）：

```bash
# 查看多模型纯 Markdown 结构经验库（ARCH-001 / CNN-CSI-001 / HPO-001）
PYTHONPATH=demos python3 -m autoresearcher_harness kb list

# 离线托管模式多轮棘轮示例
PYTHONPATH=demos python3 -m autoresearcher_harness campaign demo
```

如果希望由 Harness 自动编排（`execution_mode="managed"`）对接异构远端 MCP，可参考 [mcp_adapter_example.py](mcp_adapter_example.py) 中的纯 JSON 配置驱动适配器 `ConfigurableMCPAdapter`（通过 `tools / status_map / response_paths` 映射外部工具与字段，无需修改引擎代码）。

---

## 模块清单与验证

| 文件 | 职责 |
| --- | --- |
| `spec_utils.py` | 嵌套 dot-path 配置 patch/diff、通用方向归一化增益与算量/成本规格化 |
| `contracts.py` | 通用 `CampaignPlan`、`Proposal`、`Plan`、分轨隔离与嵌套 `param_bounds` 硬校验 |
| `knowledge_base.py` | 纯 Markdown 分层不可变结构经验库（零数据库）、多维检索、草案隔离与去重聚合 |
| `campaign.py` | `external_mcp`（BYO-MCP）与 `managed` 双模式棘轮编排、动态 `results.tsv` 与 Holdout 验收 |
| `scaffold.py` | 模型工程师 1 秒自助脚手架（`init` 命令） |
| `engine.py` | 托管单运行状态机（提交幂等、对账恢复、停止退避/降级、算量累计） |
| `mcp_adapter_example.py` | 配置驱动 `ConfigurableMCPAdapter` 与异构 MCP 适配示意 |
| `store.py` / `mock_mcp.py` / `__main__.py` | 运行状态持久化、离线模拟与 CLI 入口 |

```bash
PYTHONPATH=demos python3 -m unittest discover -s demos/autoresearcher_harness/tests -v
python3 -m compileall -q demos/autoresearcher_harness
```
