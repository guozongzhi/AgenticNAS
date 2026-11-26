# 五算子假设生成与防坍缩实战手册（Hypothesis Playbook）

本手册吸收 `MLEvolver`、`AlphaEvolve`、`Heuresis` 与《Principle-Level Local Optima》的实证规律，指导 Agent 用**五类显式演化算子**高效分配预算。

---

## 1. 五大显式提案算子（`--operator`）

每次调用 `campaign propose` 时，必须根据 `context.search_diagnostics` 明确声明本轮使用的算子：

| 算子 | 适用时机 | 标准用法 |
| --- | --- | --- |
| `refine` | 默认局部精调：沿已知有效方向微调单个参数，或消费 `untried_knowledge_priors` | 基于当前 `incumbent` 修改 1 个字段 |
| `explore` | 当 `principle_collapse_warning == true`、`plateau_warning == true` 或存在 `untouched_mutable_fields` 时强制切换原理轴 | 挑选 `untouched_mutable_fields` 中的正交维度，或指定 `--parent-trial` 从 `compute_elites` 跳板重新出发 |
| `recombine` | 当 `pareto_frontier` 或并行批次中出现两条互补有效分支（例如 `trial-001` 提精度、`trial-002` 降算量） | `--parent-trial trial-001 --inspiration-trials trial-002 --operator recombine` 合成优势特征 |
| `ablate` | 当某个胜出 `incumbent` 同时改了 $\ge 2$ 个字段（`complexity_score` 较高）时验证最小充分性 | 逐个还原次要字段回基线值，若精度在 `tie_tolerance` 内持平即可赢得 `simplicity win` |
| `shrink` | 主指标已达预期、冲刺更低推理 FLOPs / MACs / 时延时 | 在 `tie_tolerance` 容差内缩窄次要通道、减少层数或切换轻量算子争取 `compute win` |

---

## 2. 防止“原理级局部坍缩”与自校准纪律

1. **盯紧有效原理数 $N_{\text{eff}}$ 与未探索轴**：
   - 切勿连续 4 轮只改同一个字段（如反复试 `depth=5,6,7,8`）。一旦 `principle_diversity.principle_collapse_warning == true`，下一轮**必须**切换至 `untouched_mutable_fields` 中的未测维度。
2. **先预测再验证（Predict-Then-Verify）**：
   - 提交提案时传入 `--expected-primary <val> --expected-compute-ratio <val>`。
   - 回填后检查 `prediction_calibration`：若出现 `high_surprise == true`（例如本以为算量不变，实测算量暴涨 1.4x），在下一轮假设中显式修正对该模块算量耦合关系的认知。
3. **昂贵训练优先走两级多保真漏斗（`proxy -> full`）**：
   - 当全量训练单次耗时较长时，先用 `--fidelity proxy`（如短周期/子集训练 MCP）低成本验证候选是否 OOM、算量是否超标及早期趋势是否正向；
   - 从 `search_diagnostics.ready_to_promote_proxies` 中挑出最优候选，用相同修改提交 `--fidelity full` 正式冲击 `incumbent`。

---

## 3. 分轨专项策略

### 3.1 结构优化主线（`track=architecture`）
- **前期（低开销表征改善）**：优先验证 `gain_up_compute_down / neutral` 先验，测试局部感受野（卷积核/窗口尺寸）、轻量化门控注意力（SE / 激活函数）与注意力头配置。
- **中期（容量与算量红线博弈）**：结合 `compute_elites` 中的 `lightweight_sub_0.92x` 跳板，用 `recombine` 将轻量化骨干与高表征模块组合，突破算量上限瓶颈。
- **收官（消融减重）**：对胜出模型执行 `ablate` 与 `shrink`，剥离无实质贡献的冗余结构改动。

### 3.2 独立收尾 HPO（`track=hpo`）
- 仅在 `configure --from-holdout <arch_ws>` 冻结胜出结构后启动。
- 按“学习率与预热联动（`lr + warmup_ratio`）→ 正则化（`weight_decay / dropout`）→ 调度周期”分层探索；遇到梯度爆炸立即标 `--failure-kind nan_divergence` 并向低学习率/长预热侧回撤。
