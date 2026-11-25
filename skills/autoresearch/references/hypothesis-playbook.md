# 假设生成与防坍缩实战手册（Hypothesis Playbook）

本手册指导 Agent 在多轮棘轮循环中高效利用每次训练预算，避免无归因乱改、重复探索、算量爆表或局部坍缩。

---

## 1. 通用实验纪律（NAS 与 HPO 共用）

1. **单轴可归因原则（One-Axis Attribution）**
   - 除直接验证经验知识库（`knowledge_base`）中已登记的组合模式（`untried_knowledge_priors`）外，每轮提案相对当前 `incumbent` **只修改 1 个字段**。
   - 同时修改 3 个以上不相关字段既无法判断收益与副作用来源，也会推高 `complexity_score`（相对 `base_config` 的变更字段数），导致平局时丧失 `simplicity win` 优势。
2. **先预检再立项（`--dry-run`）**
   - 不确定嵌套路径、边界或是否与历史配置同构时，先运行 `campaign propose latest --dry-run ...`，确认 `valid: true` 且 `config_id` 唯一后再正式开单。
3. **读取 `search_diagnostics` 主动早停**
   - 当 `context.search_diagnostics.plateau_warning == true`（连续 ≥3 轮 `discard/crash`），必须切换搜索维度（例如从“扩深度”切到“改局部卷积核/算子类型”或“压算量换 `compute win`”）；若所有正交维度均已尝试且无增益，立即执行 `campaign stop latest` 进入 `awaiting_holdout`，不空耗剩余预算。

---

## 2. 结构优化主线策略（`track=architecture`）

固定 `base_training_recipe` 不变，围绕**主指标增益**与**推理算量（FLOPs / MACs / Latency / Params）**做三阶段推进：

### 阶段一：高性价比先验与低开销感受野探索（前 30% 预算）
- 优先消费 `context.search_diagnostics.untried_knowledge_priors` 中方向为 `gain_up_compute_down` 或 `gain_up_compute_neutral` 的模式。
- 若无现成先验，优先测试**算量增幅小但表征变化明显**的算子级/局部结构变更：
  - 卷积核尺寸 / 窗口大小（如 `ffn.kernel_size: 1 -> 3`、`window_size`）；
  - 轻量化通道/门控注意力（如开启 `use_se`、激活函数 `gelu <-> silu`）；
  - 注意力头数或分组配置（保持总通道不变，调整 `num_heads`）。

### 阶段二：容量分配与算量红线博弈（中段 50% 预算）
- **若主指标仍低于目标且算量余量充足（`compute_ratio < 0.9 * max_ratio`）**：
  - 尝试适度加深 `depth`（每次 `+1` 或 `+2`）或提高瓶颈扩展比 `ffn_ratio / mlp_ratio`。
  - 谨慎倍增全局宽度 `channels / embed_dim`（宽度翻倍通常令算量呈平方级 $\approx 4\times$ 增长，极易触发 `compute_budget_exceeded`）。
- **若候选增益达标但因 `compute budget exceeded` 被 `discard`**：
  - 下一轮将重算子替换为轻量化算子（如 `block_type: standard -> depthwise_separable / inverted_bottleneck`），或裁剪次要模块通道（如 `decoder.channels`、`head.hidden_dim`），把算量拉回红线内。

### 阶段三：同精度减算量收官（末段 20% 预算）
- 当主指标已达预期、且 `tie_tolerance > 0` 时，针对当前 `incumbent` 尝试**减法提案**（如砍掉 1 层冗余深度、收缩头部维度）：只要主指标退化不超过 `tie_tolerance` 且算量下降，棘轮即会判定 `compute win` 并晋升更轻量的 `incumbent`。

---

## 3. 独立收尾 HPO 策略（`track=hpo`）

仅在结构已完成 Holdout 验收并用 `configure --from-holdout` 锁定 `base_architecture` 后执行：

1. **按敏感度分层单步调节**：
   - **第一优先级（学习率与预热）**：在当前 `lr` 附近按对数步长（如 `0.5x`、`1.5x`、`2.0x`）探索，必要时联动 `warmup_ratio`（大 `lr` 配稍长 warmup 防早期发散）。
   - **第二优先级（正则化）**：观察开发集过拟合/欠拟合趋势，单向微调 `weight_decay` 或 `dropout`（欠拟合降正则，过拟合升正则）。
   - **第三优先级（训练轮数 `epochs`）**：仅当验证集预算契约允许可变 `epochs` 且单轮成本仍在 `max_cost` 范围内时微调；若对比协议要求固定训练 token/sample 预算，切勿把 `epochs` 放入 `mutable_fields`。
2. **OOM / NaN 发散快速止损**：
   - 若某轮因 `lr` 过高触发 NaN `crash`，记入 `--status crash` 后立即回到 `incumbent` 向更小 `lr` 或更高 `warmup_ratio` 探索，绝不在崩溃点同方向继续试探。
3. **结论隔离**：
   - 收尾 HPO 带来的增益必须单独归因于 `track=hpo` 经验知识库条目，不得回写进 `track=architecture` 条目冒充结构收益。
