"""Month-1 learned estimators (Phase 4, doc 08): E1 risk + E2 stage-1.

Pure-stdlib, deterministic, leakage-masked feature extraction and calibrated
logistic regression over engineered, named features. No sklearn/numpy, no
wall-clock, no randomness. Outcome/oracle/reference-supervision fields are
structurally deleted before featurization (scrub-invariance is unit-tested).
Scores are advisory pressure signals, never interiority claims.
"""
