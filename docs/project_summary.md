# Project Summary

## Project Name

Legal AI Data Governance Eval Harness

## One-Line Summary

Built a leakage-safe legal AI evaluation and data-loop governance harness that turns legal model failures into structured data actions: eval, SFT, preference, badcase, and human review.

中文一句话：

构建法律 AI 数据闭环治理评测工作流，覆盖 gold label 防泄漏、多任务 rubric 评测、normalized run log、错误标签标准化、人审队列和 badcase-to-data routing。

## Implementation Highlights

- Built a leakage-safe Legal AI Data Governance Eval Harness with 85 diagnostic samples, 380 rubric items, and 546 normalized model runs across consultation, case analysis, and document drafting tasks.
- Designed strict `Eval_Input` / `Gold_Labels` / `Rubric_Items` separation so tested agents cannot access gold labels while Judge and Human Review can use full annotation context.
- Implemented task-specific rubric-based LLM judges, standardized error taxonomy, human review queueing, and error-to-data routing across eval, SFT, preference, badcase, and human-review workflows.
- Generated an executive dashboard for dataset coverage, error patterns, badcase cards, routing mix, and recommended data actions, positioning the project as data governance rather than model ranking.

## Project Scope

This repository is not a legal consultation product and does not claim final legal correctness. It focuses on evaluation data design, leakage control, task-specific judging, error taxonomy, and routing failed outputs into reusable data assets.

The default mock run is deterministic and designed for workflow verification. API mode can connect to OpenAI-compatible providers for real model outputs while preserving the same data-governance pipeline.
