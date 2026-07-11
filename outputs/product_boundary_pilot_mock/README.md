# Synthetic fixture boundary

`SYNTHETIC_FIXTURE` — this directory is reserved for deterministic mock-pipeline outputs.

Mock rows are useful for schema, dashboard, routing, and CI checks. They are **not** real model evidence, human annotation evidence, or a basis for portfolio metrics. In particular:

- generated reviewer fields must not be interpreted as work performed by a legal professional;
- mock agreement labels must not be reported as reviewer agreement or judge calibration;
- full generated CSV/XLSX artifacts stay local and are ignored by Git;
- public findings come from the separately identified real API evidence packages.

Regenerate locally with:

```bash
python -m legal_eval_harness.cli all \
  --input dataset_manifest.yaml \
  --config config.yaml \
  --mode mock \
  --output-dir outputs/product_boundary_pilot_mock
```
