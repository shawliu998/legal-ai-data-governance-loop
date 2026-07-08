# GitHub Upload Guide

这份文档说明如何把当前项目上传到 GitHub。

当前本地状态：

- 当前分支：`codex/legal-data-governance-eval`
- 当前仓库还没有 commit
- 当前仓库还没有 remote
- 发布所需文件已经 staged
- 完整输出 CSV 和旧 20 条 workbook 已通过 `.gitignore` 排除

## 1. 提交前检查

查看当前暂存文件：

```bash
git status --short
git diff --cached --name-only | sort
```

应该提交的核心内容：

- `README.md`
- `docs/`
- `src/`
- `tests/`
- `prompts/`
- `config.yaml`
- `dataset_manifest.yaml`
- `data/eval_input.csv`
- `data/gold_labels.csv`
- `data/rubric_items.csv`
- `data/sample_metadata.csv`
- `data/Legal_AI_Data_Governance_Eval_Harness_40_Core.xlsx`
- `outputs/executive_dashboard.xlsx`

不建议提交：

- `outputs/model_run_log.csv`
- `outputs/judge_scores.csv`
- `outputs/data_routing.csv`
- `data/Legal_Agent_Eval_Harness_20_Samples.xlsx`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `build/`
- `*.egg-info/`

确认忽略规则：

```bash
git check-ignore -v \
  data/Legal_Agent_Eval_Harness_20_Samples.xlsx \
  outputs/model_run_log.csv \
  outputs/judge_scores.csv \
  outputs/data_routing.csv
```

## 2. 本地 Commit

运行测试和数据校验：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m legal_eval_harness.cli validate \
  --input dataset_manifest.yaml \
  --config config.yaml
```

创建 commit：

```bash
git commit -m "Build legal AI data governance eval harness"
```

## 3. 在 GitHub 创建空仓库

在 GitHub 网页新建 repository，建议：

- Repository name: `legal-ai-data-governance-eval-harness`
- Visibility: public 或 private 均可
- 不要勾选 `Add a README file`
- 不要勾选 `.gitignore`
- 不要选择 license

因为本地项目已经有 README 和 `.gitignore`，远端仓库保持空仓库最简单。

## 4. 添加 Remote

把下面的 URL 换成你的 GitHub 仓库地址：

```bash
git remote add origin https://github.com/<your-username>/legal-ai-data-governance-eval-harness.git
git remote -v
```

如果你使用 SSH：

```bash
git remote add origin git@github.com:<your-username>/legal-ai-data-governance-eval-harness.git
git remote -v
```

## 5. Push 到 GitHub

如果这是最终发布仓库，建议把当前分支改名为 `main` 后推送：

```bash
git branch -M main
git push -u origin main
```

如果你想保留当前 Codex 工作分支，也可以直接推送当前分支：

```bash
git push -u origin codex/legal-data-governance-eval
```

对外共享仓库时，最简单的方式是使用 `main` 分支。

## 6. 上传后检查

打开 GitHub 仓库，优先检查：

- README 首屏是否能说明项目不是法律问答系统、不是模型排行榜
- `docs/case_study.md` 是否能打开
- `outputs/executive_dashboard.xlsx` 是否存在
- `data/*.csv` 是否存在
- `outputs/*.csv` 是否没有被提交
- `data/Legal_Agent_Eval_Harness_20_Samples.xlsx` 是否没有被提交

可以在 GitHub README 中优先打开：

1. `docs/case_study.md`
2. `outputs/executive_dashboard.xlsx`
3. `docs/runbook.md`
4. `data/eval_input.csv`, `data/gold_labels.csv`, `data/rubric_items.csv`

## 7. Repository Summary

中文：

```text
项目：Legal AI Data Governance Eval Harness
链接：https://github.com/<your-username>/legal-ai-data-governance-eval-harness
说明：构建法律 AI 数据闭环治理评测工作流，覆盖 gold label 防泄漏、多任务 rubric 评测、normalized run log、错误标签标准化、人审队列和 badcase-to-data routing。
```

英文：

```text
Legal AI Data Governance Eval Harness
Built a leakage-safe legal AI evaluation and data-loop governance harness with 85 samples, 380 rubric items, 546 normalized model runs, task-specific LLM judges, standardized error taxonomy, human review queueing, and error-to-data routing.
```

## 8. 常见问题

如果 `git push` 要求登录：

- HTTPS 方式通常需要 GitHub personal access token
- SSH 方式需要先配置 SSH key

如果提示 remote 已存在：

```bash
git remote -v
git remote set-url origin https://github.com/<your-username>/legal-ai-data-governance-eval-harness.git
```

如果误提交了不该提交的文件，但还没 push：

```bash
git rm --cached outputs/model_run_log.csv outputs/judge_scores.csv outputs/data_routing.csv
git commit --amend
```

如果已经 push 了，优先新提交一个清理 commit；不要随意改历史，除非确定仓库还没有被别人拉取。
