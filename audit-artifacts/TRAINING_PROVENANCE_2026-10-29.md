# Was the current model trained on only 2,000 records?

**No. The 2,000 cap belongs to historical V2, not current V3.**

| Artifact | Verified meaning |
|---|---|
| `models/rf_v2_23class_prototype_manifest.json` | 2,000 DDXPlus rows per class cap, 41,061 total training rows; 400 synthetic COVID rows and 400 synthetic allergic-rhinitis rows. Not live. |
| `models/v3_partial_evidence.json` | 443,075 source training records, 21 respiratory classes, 34 selected evidence features; no 2,000-row sampling cap. |

This is more than a metadata assertion. The official DDXPlus v15 files were
downloaded from [Figshare](https://doi.org/10.6084/m9.figshare.20043374.v15), under
CC BY 4.0, and checked against publisher byte sizes and MD5 checksums. The full
respiratory source inputs were reconstructed locally with the frozen 198-feature
source schema. Restored counts: train **443,075**, validation **55,808**, test
**56,817**. Raw data and processed cohorts remain ignored, not committed.

The existing V3 fitting function was run in memory on **all 443,075** reconstructed
training rows using the saved settings. Its class counts match the artifact and
the maximum absolute differences from the saved parameters were:

| Parameter | Maximum absolute difference |
|---|---:|
| Group priors | **0.0** |
| Group evidence likelihoods | **0.0** |
| Conditional pain-location likelihoods | **0.0** |
| Background evidence likelihoods | **0.0** |

No model file was overwritten or promoted. This reproduces the current model's
parameters from the full selected respiratory training split, rather than
assuming the old conversation describes the live model.

## What “full” does not mean

- It is the full **selected respiratory training subset**, not every DDXPlus
  condition, every source feature, real Kenyan patients, or all of medicine.
- V3 deliberately consumes 34 selected features; the 198-feature source profile
  is also used to prevent duplicate-profile overlap between evaluation folds.
- Generic weakness is now preserved as context, not invented as a trained
  respiratory feature. Duration and severity remain advice-only context.
- Adding COVID, malaria, anaemia or multi-disease predictions needs suitable
  labels, justified scope and independent evaluation—not another alias or more
  copies of existing simulated rows.

Official `release_conditions.json` uses French keys with English label fields;
the restore script re-keys those fields **in memory for scope verification only**.
It does not rename patient labels or modify the downloaded source metadata.

Reproduction utility: `python scripts/restore_ddxplus.py` in the ML project.
The original missing-data test failures are now resolved without deleting or
skipping those tests. Source-check provenance is in ignored
`data/raw/download_manifest.json`; aggregate evaluation is separately reported in
`reports/gap_validation/` and is not Kenyan clinical validation.
