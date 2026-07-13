# Legal flywheel v0.2 面试展示说明

这份说明只使用仓库中的公开、脱敏证据。完整 prompt、模型输出、专家提交、source snapshot
和逐事件 lineage 属于 restricted evidence，不应在公开演示中展示。

## 一句话结论

这个项目的重点不是把五条回归做出高分，而是建立一个可审计的数据治理闭环：训练资产和
独立测试资产来源互斥，每次修订重新绑定审核与 QA，真实失败不可覆盖，最终只发布脱敏证据。

## 三分钟演示路径

### 1. 先讲问题

v0.1 的五条 regression 与 SFT 复用源案例，只能称为同源 bug reproduction，不能作为独立
test split。旧版状态机还存在跨 revision 复用审核证据、候选构建丢失 `provided_context`、
强制回归覆盖历史等风险。

### 2. 再讲治理改造

- train/test 同时检查 source case、source snapshot、normalized prompt hash 和 counterfactual
  family ID；
- review、adjudication、QA 和专家决定绑定当前 correction revision、answer hash 与 source
  snapshot；
- grounded case 从候选构建到回归 prompt 保留限定来源内容；
- 每次 regression 写入独立 attempt 目录，并追加不可变事件账本；
- preference 的完整可发布 payload 接受 PII 检查；
- 公开包只包含脱敏样例、汇总指标、回归 gate 结果和文件哈希。

### 3. 最后讲真实结果

v0.2 包含 15 个 accepted 资产：5 SFT、5 preference 和 5 个来源互斥的 independent
regression test。正式 V5/W4 attempt 1 的同一批不可变模型输出，在登记限定语义别名后按
scoring-v3 透明重评分为 2/5；006 和 010 通过，007、008、009 仍缺 required topics。

这 2/5 是严格产品 gate 的五条 pilot 诊断结果，不是法律正确率，也不是模型排行榜。保留
失败本身就是治理闭环的一部分。

## 十分钟追问路径

### 如何证明没有 train/test 污染？

发布构建跨 asset type 和 split 检查四类标识，并将结果写入 restricted contamination audit。
公开指标报告只披露检查结论，不公开受限 prompt 或 hash。标准候选构建和自动测试还阻止同一
案例同时进入 train 与 test。

### 为什么不能复用上一 revision 的审核？

修订后的文本、hash 和 source snapshot 已经变化，旧审核不再评价当前对象。状态转换只读取
与 latest correction 完全匹配的 review、adjudication、QA 和专家事件；不匹配就不能 accepted。

### 0/5 为什么后来变成 2/5？

模型没有重跑。exact-topic revision 2 对部分等义表达产生字面匹配假阴性，revision 3 只登记
限定别名，再对原始不可变输出做确定性重评分。账本同时保留原评分、attempt hash 和重评分
事件；三条真实 required-topic 失败仍然保留。

### 为什么专家审核时间不能解读为真实工时？

当前字段是 reviewer 自填的 `self_reported_review_entry_seconds`，没有 start、pause、submit
计时能力。因此公开报告明确将其标为录入值，不称为 active review time。真实计时属于后续
版本的产品能力。

### 为什么暂时不扩到 100 条？

在小样本中先验证 lineage、污染检查、不可变 attempt、人工终审和公开脱敏边界，能先消除
规模化后更难修正的系统性错误。扩量应发生在这些门禁稳定之后。

## 建议现场打开的证据

1. [`release/legal_flywheel_v0.2.0/metrics_report.md`](../release/legal_flywheel_v0.2.0/metrics_report.md)
   —— 15 个资产、2/5 回归结果及指标边界；
2. [`release/legal_flywheel_v0.2.0/public_manifest.yaml`](../release/legal_flywheel_v0.2.0/public_manifest.yaml)
   —— 公开文件哈希以及 deliberately excluded evidence；
3. [`docs/flywheel_v0.2_independent_regression.md`](flywheel_v0.2_independent_regression.md)
   —— 修订、终审和不可变回归的完整过程；
4. [`tests/test_asset_flywheel.py`](../tests/test_asset_flywheel.py)
   —— revision binding、污染门禁、context 保留和 attempt 历史的自动测试。

## 不应声称的内容

- 不声称 40% 是法律正确率或模型整体能力；
- 不声称五条测试具有统计代表性；
- 不声称 reviewer 自填秒数是真实 active review time；
- 不把 restricted evidence 上传到公开仓库；
- 不修改 v0.2 标签或为了提高分数反复抽样。

## 下一版边界

v0.3 应在不改写 v0.2 的前提下诊断 007、008、009，分离模型、prompt/context 与 assertion
原因；任何训练改进只能使用 train 案例，正式评估必须使用新的来源互斥 holdout。路线与验收
门槛记录在 GitHub Issue #6。
