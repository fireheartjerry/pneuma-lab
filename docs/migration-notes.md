# Migration Notes

Working notes on _how_ the Pneuma Lab scaffold was derived from the sources. The
formal, structured account is in
[`../migration/MIGRATION_REPORT.md`](../migration/MIGRATION_REPORT.md); this file
holds the reasoning and the gotchas.

## Approach

1. **Read the spec first, code second.** The 9to5 v2 "Psyche" design spec is the
    architecture's source of truth. But per the operator's own methodology lesson
    (spec-header status lines are unreliable), every schema field was cross-checked
    against the _actual_ code in `human_nature/`, not just the spec prose. Where the
    two differ, the code won.
2. **Contracts, not code.** The deliverable is the I/O contract (schemas + docs),
    not a port. Only small, **pure** interface modules were copied, and only as
    read-only reference outside `src/`.
3. **Mirror real shapes.** Field names, enums, and ranges match the live modules so
    a future adapter is a thin mapping, not a reinterpretation:
    - 9 affect axes ← `affect_manifold.AXES`
    - 8 drives ← `drives.CORE`
    - 5 authority tiers ← `authority.TIERS`
    - `InstinctSignal` enums ← `instinct_signal.{MATCH_TYPES,RECOMMENDED_ACTIONS,AUTHORITY_REQUESTS}`
    - run-event vocabulary ← `run_events.EVENT_TYPES`
    - 10 salience terms ← `workspace.SALIENCE_WEIGHTS`
    - 5-cap `min` ← `authority.resolve()` + `operator_authority.*_ceiling()`

## What the lab adds on top of 9to5

Three output frames have **no direct 9to5 module**; they are the lab's reason to
exist as a separate project:

- **`CausalTrace`** — makes the spec's §9 data-flow ("show receipts") an explicit,
    validatable artifact. Without it, Level-4 claims are not auditable.
- **`ConsciousnessEvidenceFrame`** — turns spec §11 (eval stack) + §14 (claims
    policy) into an evidence-graded scoring frame with an explicit ladder.
- **`InterventionFrame`** — formalizes ablation/perturbation as a first-class input.
    9to5 has an `ab_harness.py` but no structured perturbation contract.

## Gotchas / decisions

- **`additionalProperties: true` everywhere.** This is a research contract that will
    grow; over-tight schemas would just cause churn. Required fields are minimal;
    the semantics live in `description`s. Tighten later when shapes stabilize.
- **`x-pneuma-*` vendor keys.** Used for frame-kind and version so tooling can
    partition input/output frames without parsing filenames. JSON Schema ignores
    unknown keywords, so this is safe.
- **Schemas live at repo root, not in the package.** Language-agnostic, easy to diff
    against 9to5, and loadable by non-Python consumers later. `pneuma_lab.schemas`
    locates them via `parents[3]`.
- **manager-data is context, not a dependency.** Its `manager_event_v1` schema and
    13-verb action enum map cleanly onto a _future_ operator-preference stream, but
    nothing here consumes it, and no data/secrets/scripts were copied.
- **Windows + BOM.** A test (`test_schemas_are_utf8_json_on_disk`) guards against a
    UTF-8 BOM sneaking into a schema file from a Windows editor — it would break
    strict JSON consumers.
- **PostToolUse formatter.** pneuma-lab has an active formatter hook (unlike 9to5,
    which is opted out). Harmless here — this is a fresh standalone repo.

## Explicitly deferred (NOT done this pass)

- No runtime / psyche loop.
- No adapters implemented (only the seams + planned signatures).
- No replay harness.
- No evals implemented (only the seam + the five planned suites documented).
- No ML training, no fine-tuning, no manager-data integration.
- No wiring back into 9to5; no dependency in either direction.
- No merge of PR #38; no change to any 9to5 branch or file.
