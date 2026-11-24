# Research upgrade notes (submission prototype)

## What this upgrade changes
- Training workflow now uses stratified 70/10/20 development/validation/test split.
- Candidate models are selected on validation ROC-AUC (with PR-AUC and Brier as tie-breakers), not on the held-out test set.
- The selected model is refit on development data (train + validation), and final test metrics are computed once.
- Metadata stores the split strategy and final test metrics.
- Added `ml/research_audit.py` to inspect missingness and duplicate rows in source CSVs.

## Important limitation
This is a methodological improvement, not evidence of clinical accuracy. Synthetic/demo datasets are not suitable to establish real-world clinical performance. Check dataset provenance, label construction, leakage, and external validation before any clinical claims.

## Run the audit
From the project root: `python ml/research_audit.py` (or add disease keys, e.g. `python ml/research_audit.py kidney`).

## Retrain
From the project root: `python ml/train_models.py kidney` or `python ml/train_models.py` for all available disease models. Retraining can take time and requires dependencies and the original CSVs.
