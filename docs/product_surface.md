# Product Surface

This repository focuses on the data and evaluation layer behind legal AI products. The same harness can support several product surfaces, but it does not implement the surfaces themselves.

## Legal Consultation Assistant

The harness helps judge whether a consultation-style answer can respond directly, needs more facts, should cite grounded sources, or should route to human review. Failures can become eval, preference, badcase, regression, or human review data.

## Legal Document Drafting Assistant

For drafting tasks, the harness checks whether the model respects the requested document type, identifies missing facts, avoids unsupported legal claims, and triggers a release gate when the output is not safe to ship as a draft candidate.

## Enterprise Legal Knowledge Assistant

For internal legal knowledge QA, the harness focuses on source-boundary and citation behavior: whether the answer stays within the allowed corpus, whether material claims are supported, and whether unsupported rows should enter review or regression data.

## Legal Intake Assistant

For intake flows, the harness checks whether the system asks the right follow-up questions before answering, recognizes escalation signals, and routes incomplete or high-risk traces to human review or blocker-level data assets.

## What Is Not Built

This repository does not include a Web UI, production case management system, lawyer workbench, or live legal retrieval service. The focus is the offline data and evaluation layer: scenario design, rubric scoring, human review inputs, release-gate checks, and data asset routing.
