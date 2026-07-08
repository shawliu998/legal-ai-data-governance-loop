# Case Study: Legal AI Product Eval & Data Governance System

## 30 秒项目摘要

这个项目不是法律问答系统，也不是模型排行榜，而是一个法律 AI 数据闭环治理评测工作流。它把法律任务拆成可评测的数据结构，把被测 Agent 可见的输入和 Judge/Human Review 可见的 gold label 严格隔离，再用 rubric-based judge、标准化错误标签和 data routing，把模型输出转化为 eval、SFT、preference、badcase 和 human_review 等数据生产动作。

当前版本覆盖 85 条样本、3 类法律任务、380 条 rubric item、546 条 normalized model run。最终 dashboard 的重点不是证明哪个模型最好，而是回答一个数据产品问题：哪些失败应该进入人审，哪些可以沉淀成训练样本，哪些应该保留为回归评测集。

## 设计说明

项目边界是数据治理与评测流程，不是 RAG、Web UI、数据库或自动法条检索。这样设计的原因是，法律 AI 数据治理更关心任务拆解、标注规范、评测隔离、错误归因和数据回流，而不是堆一个问答演示。

核心设计有三层：

1. 数据层：`Eval_Input` 只包含 Agent 可见字段，`Gold_Labels` 和 `Rubric_Items` 只给 Judge 和 Human Review 使用，避免 gold label 泄漏。
2. 实验层：统一 normalized run log，一行代表一次 run，支持多模型、多 prompt version、多任务类型，避免宽表难以扩展。
3. 治理层：Judge 输出标准化评分和错误标签，Router 根据错误类型、风险等级和 judge confidence 决定数据去向，Dashboard 服务数据生产决策。

## 当前结果

从 `outputs/executive_dashboard.xlsx` 读取到的摘要：

- `total_samples`: 85
- `total_runs`: 546
- `avg_v0_score`: 0.264
- `avg_v3_score`: 0.836
- `avg_score_delta`: 0.571
- `high_risk_rate`: 0.555
- `human_review_queue_size`: 303
- `top_3_error_tags`: needs_human_review, missing_evidence_warning, overclaim
- `recommended_data_actions`: build preference pairs for overclaim control; add evidence-risk warning exemplars; calibrate high-risk review queue

这些数字的解读不是“V3 一定更好”，而是 workflow prompt 在 mock 诊断里显著改善了结构化风险控制，但仍然暴露出证据风险提示、人审校准和 overclaim 控制这三类数据生产需求。

## 5 个案例卡

以下案例来自 `outputs/executive_dashboard.xlsx` 的 `Badcase_Cards` sheet，做了去重和说明口径整理。

### 案例 1: L-004 调岗降薪咨询进入 Human Review

样本问题：公司突然通知我调岗降薪，我不同意，可以要求赔偿吗？

Badcase 信号：

- task_category: consultation
- version: V0
- main_error_type: needs_human_review
- risk_level: high
- judge_confidence: low
- data_route: human_review
- score_rate: 0.143

解读：

这个案例看起来是普通劳动咨询，但真实风险点在于不能直接建议“拒绝到岗”或“必然可以赔偿”。gold label 里要求先补齐合同岗位、薪资结构、调岗理由、书面通知、是否协商、新岗位差异等事实。V0 输出只给了泛化建议，缺少旷工风险、证据固定和协商路径，因此 router 把它放进 human_review。

这个例子说明：法律 AI 的高风险不是只看领域，还要看回答是否诱导用户采取可能损害自身权益的行动。这个样本适合做人审校准和风险等级标注，不应该直接拿去做 SFT。

### 案例 2: L-032 违约金调整案例分析进入 Human Review

样本问题：合同约定日违约金较高，实际损失较低，法院如何处理？

Badcase 信号：

- task_category: case_analysis
- version: V0
- main_error_type: needs_human_review
- risk_level: high
- judge_confidence: low
- data_route: human_review
- score_rate: 0.179

解读：

这是 case_analysis 任务，不应该只泛泛说“协商、投诉、起诉”。合格回答要围绕违约金条款、实际损失、违约时间、是否请求调整、履行情况和过错因素做事实到规则的连接。V0 的问题不是表达不流畅，而是没有做案例分析所需的事实组织和裁量因素拆解。

这个例子说明 task-specific judge 的价值：咨询任务可以重点看追问和风险边界，但案例分析要看结论、关键事实、推理链和法律依据。相同的模型输出，在不同任务类型下应该被不同 rubric 评价。

### 案例 3: L-040 违约金答辩状要点进入 Badcase

样本问题：对方起诉要求高额违约金，被告认为明显过高，请起草答辩状要点。

Badcase 信号：

- task_category: document_drafting
- version: V1
- main_error_type: overclaim
- risk_level: medium
- judge_confidence: medium
- data_route: badcase
- score_rate: 0.643

解读：

这个案例体现文书起草任务的特殊性。文书不是普通咨询，不能只写“整理材料、保留证据、协商诉讼”。答辩状要点至少要包括对诉请的答辩意见、违约金过高抗辩、实际损失和履行情况、证据目录、待补信息和程序风险。V1 虽然结构化了，但仍然偏咨询模板，容易给出过强或过泛的建议。

Router 把它路由到 badcase，而不是 human_review，表示它适合进入回归 badcase 集：后续每次改 prompt 或换模型，都要检查文书任务是否还会退化成通用咨询话术。

### 案例 4: L-008 定金/订金争议进入 Preference

样本问题：我交了定金，现在不想买了，对方不退，我能要回来吗？

Badcase 信号：

- task_category: consultation
- version: V1
- main_error_type: overclaim
- risk_level: medium
- judge_confidence: medium
- data_route: preference
- score_rate: 0.679

解读：

这个案例的核心不是回答“能不能退”，而是先识别付款凭证到底写的是定金还是订金、合同是否成立、谁违约、解除原因、商家是否存在违约。V1 的结构还可以，但 overclaim 控制不够，容易把“定金一般不退”或“都能退”说得过满。

它适合做成 preference pair：差答案是直接下结论，好答案是先区分术语和违约方，再给条件化路径。这个例子说明 badcase 可以被继续转成偏好训练数据。

### 案例 5: L-018 餐厅摔倒责任进入 Risk-Control SFT

样本问题：我在餐厅包间门口台阶摔倒受伤，餐厅说有提示牌不赔，可以要求赔偿吗？

Badcase 信号：

- task_category: consultation
- version: V3
- main_error_type: missing_evidence_warning
- risk_level: low
- judge_confidence: medium
- data_route: sft
- score_rate: 0.750

解读：

这个例子说明不是所有问题都要进人审。V3 已经能做 intake、clarification 和条件化分析，但对现场照片、监控、台阶设计、照明、提示位置、伤情证明这些证据风险的提示还可以更稳定。因此 router 把它放进 SFT，具体是 risk-control SFT。

这个样本适合训练模型形成稳定模式：先确认安全保障义务和自身注意义务，再提示证据固定、责任比例和损失证明，而不是简单说“餐厅有提示牌就不赔”或“一定可以赔”。

## Project Summary

Legal AI Product Eval & Data Governance System: built a leakage-safe evaluation workflow for legal AI data-loop governance. The system separates agent-visible inputs from gold labels, supports multi-task legal evaluation, runs normalized multi-model experiments, applies task-specific rubric-based judging, standardizes error taxonomy, routes failures into eval/SFT/preference/badcase/human-review queues, and generates an executive dashboard for data production decisions rather than model ranking.

## Implementation Highlights

- Built a leakage-safe Legal AI Product Eval & Data Governance System with 85 diagnostic legal samples, 380 rubric items, and 546 normalized model runs across consultation, case analysis, and document drafting tasks.
- Designed strict `Eval_Input` / `Gold_Labels` / `Rubric_Items` separation so tested agents cannot access gold labels while Judge and Human Review can use full annotation context.
- Implemented multi-version prompt evaluation including direct answer, structured answer protocol, blind review agent, and workflow agent, with V2 restricted from gold label access.
- Created task-specific rubric-based judge prompts and unified scoring dimensions covering missing facts, clarification quality, legal grounding, fact-rule application, risk coverage, overclaim control, hallucination control, and data tag usability.
- Standardized legal AI error taxonomy and built an error-to-data router that maps failures into fixed data routes: eval, SFT, preference, badcase, and human_review.
- Generated an executive dashboard with dataset coverage, task-category summary, badcase cards, routing summary, and data actions to support legal AI data production decisions rather than model ranking.

## GitHub 提交建议

建议提交：

- `README.md`, `docs/*.md`, `prompts/*.txt`, `src/`, `tests/`, `config.yaml`, `dataset_manifest.yaml`
- `data/eval_input.csv`, `data/gold_labels.csv`, `data/rubric_items.csv`, `data/sample_metadata.csv`
- `outputs/executive_dashboard.xlsx`

可以不提交，或只提交 sample：

- `outputs/model_run_log.csv`
- `outputs/judge_scores.csv`
- `outputs/data_routing.csv`

原因是这三个 CSV 是 pipeline 生成物，完整文件会让仓库显得杂，也容易让读者误以为项目重点是静态结果。更好的做法是 README 里保留复现命令，GitHub 提交 dashboard 作为可直接打开的结果证据，CSV 输出可由运行命令重新生成。

如果确实想展示 CSV 格式，可以放小样本，例如 `outputs/samples/model_run_log_sample.csv`、`outputs/samples/judge_scores_sample.csv`、`outputs/samples/data_routing_sample.csv`，每个保留 5 到 20 行。

## 这些文件在仓库中的作用

`data/eval_input.csv` 是被测 Agent 唯一可见的数据层。它证明项目做了 gold label 防泄漏，也是 prompt 渲染和 run plan 的输入。

`data/gold_labels.csv` 是 Judge 和 Human Review 使用的标准答案层。它不追求“唯一法律答案”，而是记录关键缺失事实、预期追问、预期答案点、风险点和人审备注。

`data/rubric_items.csv` 是可评分的细粒度 rubric。它让评测从主观印象变成可拆分、可聚合、可追踪的维度评分。

`data/sample_metadata.csv` 存放 difficulty、risk_level、deep_badcase_flag 等管理字段。它用于数据运营和抽样决策，但不进入 Agent prompt。

`outputs/model_run_log.csv` 是 normalized run log，一行一个模型运行。它解决宽表难扩展的问题，让多模型、多版本、多 run 的实验可追踪。

`outputs/judge_scores.csv` 是 Judge 的结构化评分结果。它连接模型输出和错误标签，是 dashboard、router 和 badcase 分析的核心中间层。

`outputs/data_routing.csv` 是数据闭环的决策结果。它把错误类型、风险等级和 judge confidence 转成 eval、SFT、preference、badcase、human_review 等固定数据用途。

`outputs/executive_dashboard.xlsx` 是建议随仓库保留的可视化成果。它让评审者不用跑代码，也能看到数据覆盖、任务分布、错误模式、badcase 卡片和推荐数据动作。

## 项目边界和诚实表述

这个项目不证明模型法律能力优劣，不提供法律咨询，不自动验证法条，不替代律师审查。mock mode 的输出和评分用于展示数据闭环流程，API mode 才用于接入真实 OpenAI-compatible provider。

对外说明时建议表述为：一个可复现的法律 AI 评测与数据治理工作流，重点展示法律数据产品能力、评测设计能力和 badcase-to-data 的闭环思维。
