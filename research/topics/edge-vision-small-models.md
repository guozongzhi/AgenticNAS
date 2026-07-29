# 技术点一：边缘视觉小模型（工业单任务场景）

> 状态：活跃研究线 · 负责人关注度高 · 与 Agentic NAS 的接口：硬件感知搜索目标
>
> 背景：本仓库作者过往工作为工业界边缘算力上的**视觉/图像类单任务小模型**（非 LLM），模型规模小、任务固定、部署导向。本文档是该技术点的独立研究档案。

## 1. 问题定义与约束

- **场景**：工业质检/检测类单一任务，模型在边缘设备（Jetson 级、NPU 盒子、嵌入式板卡）上长期固定运行；
- **硬约束**：延迟（实时检测通常要求 sub-100ms，部分产线 sub-30ms）、功耗（整机 30W 量级）、内存（数百 MB 级）、NPU 算子支持集；
- **数据特征**：单一任务、样本量小（与互联网规模视觉数据完全不同量级）——这决定了架构选型和方法有效性都与大模型时代的主流叙事不同。

## 2. 架构选型（2026 工业部署基准）

来源：[Algorithmine: Vision Transformers in Industrial QC — Real Deployment Benchmarks 2026](https://algorithmine.com/research/vision-transformers-industrial-qc-2026)

- **混合 MS-ViT-CNN 是当前主流部署形态**，Jetson NX 级硬件可实时推理，ViT 成分使误报率降约 23%；
- **关键警示（小数据）**：风机叶片缺陷等小样本工业数据集上，轻量 CNN 达 98.2% 准确率，纯 ViT 仅 50.6%。**数据规模决定架构选型，小数据场景 CNN 或 CNN 主导的混合架构仍是正解**；
- 工业 QC 边缘视觉市场：2026 年约 $0.5B，预计 2034 年 $5.66B。

**对本仓库的含义**：NAS 搜索空间应以 CNN / CNN-混合块为主体，纯 attention 块在小数据工业场景的收益需要先验证再纳入。

## 3. 效率优化三板斧

### 3.1 知识蒸馏

- [Towards Optimal Trade-offs in KD for CNNs and ViTs at the Edge (arXiv 2407.12808)](https://arxiv.org/html/2407.12808v1)：ViT/DeiT/Swin 做 teacher、小 CNN 做 student 的系统权衡研究；
- [Hybrid KD for Edge 3D CNNs (MDPI 2026)](https://www.mdpi.com/2073-431X/15/6/371)：Lite-R21D，8.33M 参数，UCF101 92.07%；
- DeViT（蒸馏+分解）：精度损失 ≤1.7%，可部署到 4× Jetson Nano（见 [EdgeViTs 综述](https://www.emergentmind.com/topics/edgevits)）。

### 3.2 量化

- FP32→INT8 + QAT：2–4× 加速，精度损失很小，总延迟可压至 sub-30ms（[Oxmaint 钢铁厂实时检测案例](https://oxmaint.com/industries/steel-plant/vision-ai-latency-optimization-for-real-time-inspection)）；
- 部署侧惯例：AWQ→GPU/NPU，GGUF→CPU；必须在真实硬件上验证高分位延迟和 NPU 利用率，不看纸面 TOPS（[Robustel 边缘 AI 网关选型指南 2026](https://robustel.com/edge-ai-gateway-buying-guide-2026-what-to-check-before-industrial-deployment/)）。

### 3.3 剪枝与结构自适应

- NuWa 自适应剪枝：提速 2.8×，子任务精度反升 11.8%；
- ED-ViT 模型切分：树莓派集群上提速 28.9×、内存降 34.1×；
- EdgeViTs-XXS：ImageNet top-1 74.4%，Snapdragon 888 上 32.8ms。

## 4. 部署形态新趋势（2026）

- **多模型共存**：[Innodisk @ Computex 2026](https://thetechrevolutionist.com/2026/06/computex-2026-innodisk-demonstrates-how-edge-ai-is-moving-from-concept-to-deployment.html)——CNN 缺陷检测 + 轻量 VLM（PPE 识别）同时运行，平均延迟 4.4ms、30W 功耗包络。传统专小模型未被 VLM 取代，而是形成「专模型干活 + 轻量 VLM 补长尾」的组合；
- 专用边缘运行时（如 [Neuro-R](https://www.neuro-cle.com/en/product/neuro-r)）把量化模型下沉到 NPU/嵌入式板卡，软硬协同成为交付标准。

## 5. 与 Agentic NAS 的接口（本仓库切入点）

工业边缘视觉是 hardware-aware NAS 需求最刚性的场景：硬件杂（Jetson/瑞芯微/地平线/各类 NPU）、单任务、数据少、延迟功耗卡死，**每换一款芯片/产线就要重新调模型**。

可迁移的方法组合：

1. **硬件感知搜索目标**：`latency_proxy_ms` 应替换为目标 NPU 的实测延迟或经校准的延迟模型，与精度组成 Pareto 前沿；
2. **蒸馏感知搜索**：搜索 student 架构时以「蒸馏后精度」而非「直接训练精度」为适应度——student 的蒸馏友好性（与 teacher 的特征对齐能力）是可搜索属性；
3. **量化感知搜索**：把 INT8 量化后的精度掉点和 NPU 算子支持纳入 validator 约束（非法算子直接拒绝，等价于现有的非法动作拒绝机制）；
4. **搜索空间**：以 CNN/混合块为主体（见 §2 的小数据警示），深度/宽度/卷积核/激活为 cell/op 级动作。

## 6. 待办与开放问题

- [ ] 收集 2–3 个目标 NPU 平台的算子支持集与延迟实测数据，作为 hardware-aware 评估器的校准基础；
- [ ] 调研「蒸馏友好性作为搜索适应度」的已有工作（KD-aware NAS），登记到 `papers/INDEX.md`；
- [ ] 验证小数据场景下混合搜索空间中 attention 块的真实收益（对照 §2 的 50.6% vs 98.2% 案例）；
- [ ] 开放问题：轻量 VLM 进入边缘盒子后，单任务小模型的搜索目标是否会从「单模型精度/延迟」变为「系统级覆盖率/误报率」？

## 7. 主要参考

- [Vision Transformers in Industrial Quality Control: Real Deployment Benchmarks for 2026](https://algorithmine.com/research/vision-transformers-industrial-qc-2026)
- [EdgeViTs: Efficient Vision Transformers for the Edge (Emergent Mind)](https://www.emergentmind.com/topics/edgevits)
- [Towards Optimal Trade-offs in KD for CNNs and ViTs at the Edge (arXiv 2407.12808)](https://arxiv.org/html/2407.12808v1)
- [Vision AI Latency Optimization for Real-Time Inspection (Oxmaint)](https://oxmaint.com/industries/steel-plant/vision-ai-latency-optimization-for-real-time-inspection)
- [Edge AI Gateway Buying Guide 2026 (Robustel)](https://robustel.com/edge-ai-gateway-buying-guide-2026-what-to-check-before-industrial-deployment/)
- [Real-Time Edge AI Vision at Computex 2026 / Innodisk](https://thetechrevolutionist.com/2026/06/computex-2026-innodisk-demonstrates-how-edge-ai-is-moving-from-concept-to-deployment.html)

> 注意：部分来源为行业博客/厂商资料（Algorithmine、Oxmaint、Robustel），数字未经同行评议核验；引用到正式 related-work 前需按仓库流程找到原始论文或实测复核。
