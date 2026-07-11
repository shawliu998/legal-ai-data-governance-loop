# Controlled RAG corpus: provenance boundary

This corpus is a **controlled evaluation fixture**, not a production legal knowledge base.

- Rows with `source_url=self_authored` are synthetic, self-authored contract, policy, order, or evidence excerpts.
- Rows pointing to an official portal currently contain evaluator-authored rule summaries and a portal-level URL, not a verified verbatim primary-law excerpt.
- Those summaries are marked `summary_requires_primary_source_verification` and `publishable_as_authoritative_source=false`.
- Blank `document_identifier` and `retrieved_at` values are intentional evidence gaps; they must be populated before a source can be promoted into a production retrieval corpus.
- `content_sha256` identifies the exact fixture text used in this pilot; it does not prove legal authority or freshness.

The corpus is suitable for testing retrieval boundaries, citation mechanics, and release-gate behavior. It must not be presented as proof that a legal answer is substantively correct or current.

Run `python scripts/enrich_source_provenance.py` after editing the fixture text.
