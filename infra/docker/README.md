# Static image recipes (Step 7A)

The three Dockerfiles are deliberately non-buildable fixture recipes: every
base uses `registry.invalid` and a syntactically immutable placeholder digest.
They verify ordering and pin discipline without retrieving any bytes.

Step 7B, under its own hash-bound authorization, must replace each fixture with
a retrieved base receipt, generate real dependency locks/SBOMs, build each image
twice with `SOURCE_DATE_EPOCH`, `PYTHONHASHSEED`, UTC, and deterministic package
resolution, then record image digests or a blocking reproducibility deviation.

Build arguments are `SOURCE_DATE_EPOCH` and role-specific immutable input refs;
the build order is base receipt → dependency lock → source copy → image build →
SBOM → second identical build → digest comparison. No Step 7A recipe authorizes
a pull, build, push, or execution.
