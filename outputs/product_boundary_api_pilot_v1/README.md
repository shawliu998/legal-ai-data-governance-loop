# Product-boundary API pilot: lightweight evidence

This package contains summaries deterministically generated from **300 retained local Qianfan API run records** across a 12-case subset, five model slots, and five workflows. Of those runs, **271 returned non-empty answer content and 29 returned empty content**. Empty responses are treated as reliability failures, not legal-content judgments.

## Evidence boundary

- Automated judge and claim flags are triage signals, not legal conclusions or a public model ranking.
- The 80-row review set is priority-enriched and includes all 29 empty responses; it is not representative of all runs. All 80 rows have populated final review fields.
- Reviewer-level independent A/B labels are not available in the public evidence schema, so the completed final fields do not support reviewer IAA or formal judge-human agreement.
- Raw answers, detailed reviewer notes, and credentials remain local and are not committed; third parties cannot independently recompute this package without those excluded artifacts.

Run `python scripts/build_api_pilot_evidence.py` to rebuild these files when the retained local raw artifacts are available.
