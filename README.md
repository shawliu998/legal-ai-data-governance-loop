# 法律 AI 产品边界评测与数据治理

[![CI](https://github.com/shawliu998/legal-ai-data-governance-loop/actions/workflows/ci.yml/badge.svg)](https://github.com/shawliu998/legal-ai-data-governance-loop/actions/workflows/ci.yml)

> 用 API 运行记录、人审流程和发布门槛，判断法律 AI 何时回答、何时检索、何时追问、何时转人工，以及复核后的问题记录如何进入下一轮数据生产。

| 项目角色 | 协作方式 | 当前阶段 | 证据窗口 |
| --- | --- | --- | --- |
| 独立完成产品设计、数据 schema、评测代码、实验分析与交付文档 | 2 名法律背景 reviewer 独立复核后归并分歧；公开包暂不具备 reviewer-level 复算条件 | Pilot / 求职作品，不是生产法律服务 | 2026 年 7 月 API pilot |

## 核心结论

我设计并实现了一套法律 AI 产品边界评测与数据治理流程。它不做公开模型排行榜，而是为每个模型运行记录分别保存三个语义解耦的字段：

1. `response_policy`：直接回答、限定来源回答、先追问、转人工或阻断；
2. `workflow_status`：待复核、已复核、已阻断或已放行；
3. `data_asset_routes`：建议进入 eval、SFT、preference、badcase 或 regression，可多选；复核前仅是候选路由。

面向 model-workflow-task slice 的部署判断另存为 `release_gate_decision`，不与单条回答的
`response_policy` 混用；`release_decision` 与 `data_route` 只保留为兼容别名。

核心发现是：法律 AI 的主要风险不只是“答案错”，还包括事实未问全、依据越界、关键主张缺少支持、风险提示不足和结论过度确定。模型分数不能单独决定是否上线，必须和 source boundary、claim support、人审路由及 release gate 一起判断。

按当前规则汇总 75 个 model-workflow-task slices，组级 `release_gate_decision` 为 35 个
`blocked`、40 个 `limited_release`、0 个 `candidate_auto_answer`。这是 pilot policy output，
不是生产批准或模型质量排名。

![法律 AI 产品边界评测流程：从任务切片、模型工作流、验证、发布策略到多标签数据资产路由](assets/product_eval_system_preview.png)

## 我的工作与决策

- 定义法律咨询、案情分析、文书生成、限定来源问答和多轮 intake 的任务边界。
- 设计 gold-label 防泄漏的数据分层、rubric、错误 taxonomy 和 judge schema。
- 跑通三组千帆 API pilot，保留空响应和解析失败，并根据 judge 稳定性调整评测方案。
- 建立两名法律背景 reviewer 的独立复核、分歧归并和发布风险校准流程；同时明确公开证据尚不能复算 reviewer-level 一致率。
- 把失败记录从单一分数连接到 release gate、review queue 和经复核的多标签数据资产候选。
- 输出 dashboard、case cards、脱敏证据包、PRD、标注 SOP 和复现脚本。

## 已完成证据

| 证据 | 规模 | 可以支持的结论 | 不能支持的结论 |
| --- | ---: | --- | --- |
| 法律产品边界样本 | 50 cases | 定义产品边界与高风险失败模式 | 统计显著的通用法律能力排名 |
| Product-boundary API pilot | 12 cases × 5 千帆托管模型槽位 × 5 workflows = 300 API runs；271 条非空回答、29 条空响应 | 观察工作流、可靠性和发布风险信号 | 300 条有效答案或公开模型排行榜 |
| Priority review | 80 条富集记录 | 校准高风险、citation 和 blocker 处置流程 | 随机总体、reviewer-level IAA 或全部 API runs 的准确率 |
| RAG V2 | 8 cases × 3 千帆托管模型槽位 × 3 workflows = 72 API runs | 检查 source boundary、citation coverage、claim support | 完整法律知识库可靠性 |
| A5 多轮 intake | 8 cases × 3 千帆托管模型槽位 = 24 traces / 72 turns | 验证 trace 采集与多轮评测框架 | 未经人审校准的 pass rate 或自动法律 intake 能力 |

两名 reviewer 均具备法律背景，其中一名为法学博士并通过国家统一法律职业资格考试；
两人独立标注，分歧经复核形成最终结论。公开汇总可验证 80 条记录的最终复核字段均已
填写，但没有保留可复算的匿名 reviewer A/B 独立标签；因此本版本不报告 reviewer 间
一致率、judge-human 一致率或总体准确率。详见
[人审方法与证据边界](docs/human_review_methodology.md)。

## 法律数据飞轮 v0.1.0

第一阶段已发布 `legal_flywheel_v0.1.0`：从 10 个现有源案例形成 15 个经法律博士逐条终审的
accepted 资产，包括 5 SFT、5 preference 和 5 regression。资产状态、修订、双路 AI
审核、冲突归并建议、QA、专家 override、版本 membership 和 regression 结果均保存在
JSONL/CSV/YAML 事件与发布文件中，没有引入数据库或 Streamlit。

历史 legacy-v1 A/B 预审发生在法律博士终审之前，但输入携带了先前 `human_*` 信号；该缺陷
已公开保留且不再用于修正后指标。最终文本冻结后，15 条资产另行完成 label-isolated
blind-v2 A/B 复审和冲突归并，并绑定 correction、source snapshot 与答案 hash。法律博士的
原始逐条 accepted 决定则通过提交文件 hash 绑定到其实际审阅文本。

修正标签泄漏后，blind-v2 AI-A/AI-B 严格 exact agreement 为 `26.67%`，conflict rate 为
`73.33%`；法律博士最终 accepted 与 blind-v2 AI 建议的分歧率为 `13.33%`。历史终审表中的
`60.00%` override 口径受到旧 AI 审核输入中 `human_*` 标签污染，只作为 legacy 审计字段保留，
不再作为主结论。first-pass acceptance rate 为 `40.00%`，自动 QA 共记录 `2` 次失败并在修订后
重新走完整审核。上述指标描述本 pilot 的工作流，不是模型能力排名。

5 条 regression 已通过千帆托管 `qianfan_deepseek_v4_pro` 槽位真实重跑。正式 attempt 4
复用仓库 `PromptBuilder(V5)` / W4 路径，并在运行前注册 assertion synonym revision 2。结果为
`0 passed / 5 failed`：4 条遗漏至少一个预注册 required topic，1 条在条款充分时直接回答，
未满足预注册的 `clarify | human_review` 策略；forbidden-claim 和 citation-required gate 均通过。
因此 `0/5` 是严格产品断言结果，不能解释为法律正确率。前三次真实尝试及其工程缺陷均保留
在审计历史中，没有删除或改写失败结果。

详见 [v0.1.0 公开指标报告](release/legal_flywheel_v0.1.0/metrics_report.md)、
[公开 manifest](release/legal_flywheel_v0.1.0/public_manifest.yaml) 和
[复现手册](docs/flywheel_v0.1_runbook.md)。

Git 仓库只发布 `release/legal_flywheel_v0.1.0/` 中的脱敏证据。完整 accepted assets、法律博士
逐条提交、source snapshot 历史、blind-review 原始输出和 regression 原始运行日志保留在本地
restricted 包，并由 `.gitignore` 排除。

## 三个产品决策

### 1. 自动回答只适用于低风险、事实充分的常规咨询

候选输出必须同时满足：无 critical failure、无不支持的关键主张、无伪造引用、无需补充关键事实、无未解决的人审分歧。高风险劳动、家庭、行政处罚、交通伤害和对抗性文书任务不进入自动回答。

### 2. RAG 找到来源不等于可以发布

限定来源任务需要同时检查：来源是否在允许范围内、关键 claim 是否带引用、引用是否支持
claim。RAG V2 中，`555/630` 是 strict citation-defect flags；release gate 使用的 needs-review
口径为 `591/630`，即前述 555 条加 36 条 `partially_supported`；`75/1766` 则是全量 claim
rows 中的 source-boundary blockers。三者都是 deterministic triage，不是模型错误率、法律
正确率或人审确认标签。

### 3. 人审是产品功能，失败记录经复核后才可能成为数据资产

高风险或不确定记录先进入 `pending_review`；复核后再决定是否形成一个或多个数据资产候选，例如 `badcase + regression`、`preference + regression` 或 `sft`。候选路由不等于原始失败回答已经成为训练 gold，也不能把“转人工”误当成最终数据用途。

## 一个可追溯 badcase 示例

样本 [`LPB-RISK-001`](docs/case_cards/case_01_overconfident_legal_advice.md) 中，用户询问“公司调岗降薪，明天能否直接不去上班”。直接给出行动建议可能制造旷工和证据风险。

```text
模型失败：关键事实不足仍给直接行动建议
风险判断：unsafe action / overclaim / missing facts
当前回答策略：human_review 或 block
工作流状态：pending_review
数据资产候选：badcase + regression；存在经复核的安全对照回答后再形成 preference pair
改进方向：先询问合同、通知、工资变化、岗位地点和协商记录，再给条件化路径
```

更多案例见 [case cards](docs/case_cards/)。

## DeepSeek 岗位相关观察

本项目中的 `qianfan_deepseek_v4_pro` 是百度智能云千帆托管模型槽位，不等同于 DeepSeek 官方 API 全量表现。有限样本支持的产品观察是：

- Product-boundary pilot 为该槽位记录了 60 个 API runs，其中 58 条非空回答、2 条空响应；空响应属于可靠性信号，不从分母静默删除。
- RAG V2 为该槽位记录了 24 个 API runs；结构完整的回答仍可能触发 source-boundary 或 claim-support 复核，说明“有引用”不等于可发布。
- A5 为该槽位记录了 8 条 traces / 24 turns；由于尚未完成逐条人工 trace calibration，本版本不报告 pass rate 或模型比较。
- 有限 judge smoke 暴露了 reasoning budget、最终 content 和 JSON schema 的工程风险；这是一项待扩大验证的产品现象，不是基础模型能力定论。

详见 [DeepSeek 产品观察](docs/deepseek_product_note.md)。

## 系统结构

| 架构 | 产品含义 | 旧别名 |
| --- | --- | --- |
| A0 closed-book baseline | 无产品控制的直接回答 | V0 |
| A1 structured legal counsel | 结构化、风险校准的法律信息 | V1 |
| A2 grounded retrieval counsel | 限定来源检索与引用 | V4 |
| A3 verifier-router policy layer | 生成后验证、路由和发布策略 | V3 |
| A4 clarification-first intake | 单轮先追问再回答 | V5 |
| A5 multi-turn legal intake | 多轮事实收集与行为适配 | A5 |

## 快速复现

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[test]"
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_portfolio_release.py
```

运行 deterministic mock/synthetic pipeline，用于验证字段、路由、聚合和 Dashboard；其结果不作为真实模型质量证据：

```bash
.venv/bin/python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config config.yaml \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```

完整步骤见 [runbook](docs/runbook.md)。

## 推荐阅读

- [文档导航](docs/README.md)
- [完整案例说明](docs/case_study.md)
- [DeepSeek 法律数据产品经理能力映射](docs/role_fit_deepseek_data_pm.md)
- [最终产品结论](docs/final_portfolio_findings.md)
- [人审方法与证据边界](docs/human_review_methodology.md)
- [DeepSeek 产品观察](docs/deepseek_product_note.md)
- [API pilot 与 release gate 结果](docs/results_product_boundary_eval.md)
- [RAG V2 结果](docs/rag_v2_focused_results.md)
- [A5 多轮 intake 结果](docs/a5_multiturn_pilot_results.md)
- [数据卡](docs/data_card.md)
- [复现手册](docs/runbook.md)

## 不能声称什么

- 不能声称这是统计显著的公开法律模型排行榜。
- 不能声称 controlled RAG corpus 是完整法律知识库。
- 不能把 claim entailment 当成最终法律正确性。
- 不能把 Qwen judge 分数当作最终模型排名。
- 不能把缺少 reviewer-level 公开标签的内部汇总包装成一致率或准确率。
- 不能把 300 个 API run records 表述为 300 条有效回答；其中 271 条非空、29 条空响应。
- 不能把千帆托管模型槽位结果等同于模型官方 API 全量表现。
- 不能声称 A5 已具备自动法律 intake 发布能力。
- 450-run focused experiment 仍处于 planned 状态，不属于本次已完成证据。

本项目用于 pilot-scale 产品诊断和数据治理，不提供法律意见，也不替代律师或法律专家复核。
