# 业界 AutoResearch 核心范式与本技能工程映射

本手册总结业界主流自主机器学习研究系统（`karpathy/autoresearch`、`AlphaEvolve`/`OpenEvolve`、`AIDE`/`MLEvolve`、`MLEvolver`、`Heuresis`、`NOVA`/`EvoCast`、`LinkedIn AutoResearch` 等）的实证结论，并说明本技能如何在**严守 Clean-Room 分轨与声明式动作红线**的前提下将其落地为具体命令与控制面机制。

---

## 1. 机制对照表

| 业界系统 / 文献来源 | 解决的核心痛点 | 本技能落地机制与 CLI 入口 | 本技能增强的 Clean-Room 护栏 |
| --- | --- | --- | --- |
| **`karpathy/autoresearch`** | 无人值守闭环需要只读协议、基线先行、简洁偏置与无逗号污染账本 | `program.md` + `campaign baseline` + `simplicity win` + `results.tsv` + `campaign report`（自动生成 `REPORT.md` 晨报） | 原版允许自由改 `train.py` 且混搜深度与学习率；本技能强制**声明式 JSON 补丁**与 **`architecture` / `hpo` 严格分轨** |
| **`MLEvolver`**（Context Folding & Skill Deletion） | 长周期（30~100+ 轮）下，截断最近 $K$ 条会遗忘早期实验，滚动摘要会丢失个体细节；未修剪的经验库会拉低检索质量 | 1. **Context Folding**：`campaign context --recent-window 6` 折叠旧试验为单行结构化摘要 + `campaign inspect --trial <id>` 按需无损展开<br>2. **Skill Pruning**：`knowledge-base prune <id> --apply` 淘汰低胜率失效经验 | 永久保留 `verified_holdout` 经验与 `anti_patterns` 安全红线，未获用户确认默认仅输出预览 |
| **`AlphaEvolve` / `OpenEvolve` / `AIDE` / `MLEvolve`** | 单一线性棘轮极易陷入贪心局部最优，错失“算量大幅下降但精度微降”的高潜力跳板（Stepping Stones） | 1. **跳板谱系与重组**：`propose --parent-trial <id> --inspiration-trials <t1,t2> --operator <refine\|explore\|recombine\|ablate\|shrink>`<br>2. **2D Pareto + MAP-Elites 分档精英**：实时维护 `pareto_frontier`、`compute_elites`（轻量化/均衡/扩展三档）与二维 `pareto_hypervolume` | 所有父节点与跨分支重组产物仍须通过 `mutable_fields`、`param_bounds` 与 `forbidden_ops` 硬校验 |
| **`LinkedIn AutoResearch` / `NOVA`** | 多 GPU 集群串行单跑吞吐低；把兄弟分支代码盲目自动合并会破坏归因 | **同步并行批次**：`init/configure --max-parallel <K>`，支持同轮提交最多 $K$ 个正交提案并发调 MCP，按 `--trial <id>` 独立回填裁决，绝不盲目自动合并兄弟配置 | 任一在途试验未 `record` 前禁止进入 `finalize`，杜绝并发竞态污染留出集 |
| **`SkyPilot × autoresearch` / `ArchPilot`** | 全量训练昂贵，直接跑满全周期试错成本过高 | **多保真预筛漏斗**：`propose --fidelity <smoke\|proxy\|full>`；`proxy` 通过标记 `proxy_pass` 并列入 `ready_to_promote_proxies`，允许同 `config_id` 晋升 `--fidelity full` | 低保真分数**绝不覆盖全保真 `incumbent`**，也不直接写入经验知识库发布模式 |
| **`NOVA` / `EvoCast`** | 集群掉卡、网络超时等基础设施抖动若记为模型失败，会污染反例库并锁死有效配置 | **故障分类隔离**：`record --status crash --failure-kind <oom\|nan_divergence\|timeout\|infra_flake>` | `infra_flake` 计入实际开销账本，但**不阻塞重提该配置、不计入连续停滞、不污染 `anti_patterns`** |
| **Principle-Level Local Optima** | 候选表面数值不同（如 `depth=7,8,9`），但搜索实际坍缩在单一结构轴上空耗预算 | **原理级多样性审计**：自动计算 `mutation_family` 的 Inverse Simpson 有效原理数 $N_{\text{eff}}$、主导占比与 `untouched_mutable_fields`，超阈值触发 `principle_collapse_warning` | 在线实时告警而非事后统计，直接驱动 Agent 切换算子为 `--operator explore` |
| **`Heuresis`**（Curiosity & HackerJudge） | 1. Agent 缺乏对模型/硬件响应的定量自校准<br>2. 开放代码 Agent 存在篡改评测或伪造零成本分数的作弊风险 | 1. **Predict-Then-Verify**：`propose --expected-primary ... --expected-compute-ratio ...` 自动统计预测误差与 `high_surprise_trials`<br>2. **反作弊审计器**：自动标记缺 `model_ref`、全量训练零成本、单步 >50% 异常跳变等 `audit_warnings`，并在 `finalize` 硬校验 `model_ref` 一致性 | 评测器 URI（`dev_evaluator_ref` / `holdout_evaluator_ref`）在创建时冻结且物理隔离 |

---

## 2. 实战组合范式建议

1. **单卡串行精细调优（`max_parallel=1`）**：
   - 先用 `--fidelity proxy` 快速筛掉 OOM 与明显负向假设 → 对 `ready_to_promote_proxies` 执行 `--fidelity full` → 对多字段胜出者执行一次 `--operator ablate` 剔除冗余改动 → `finalize` + `report`。
2. **多卡集群宽幅探索（`max_parallel=4`）**：
   - 每轮围绕当前 `incumbent`（或 `compute_elites` 中的轻量化跳板）沿 4 个互不重叠的 `mutable_fields` 并行提交提案 → 全部 `record` 后检查 `pareto_frontier` 与 `incumbent` → 下一轮对两个互补分支用 `--operator recombine --inspiration-trials ...` 组合验证。
