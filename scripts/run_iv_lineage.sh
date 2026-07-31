#!/usr/bin/env bash
# Step 4A: the miniature production-path lineage.
#
# This drives the SAME real authority, scheduling, opaque-branch, task-block,
# analysis-freeze, blinded-projection, gated-unblind, and registered-analysis
# machinery as the canonical study, using the separately governed
# implementation-verification power authority and its miniature frozen grid.
#
# Its outcome is IMPLEMENTATION VERIFICATION ONLY.  It is not a P0 result and
# not scientific evidence; its records are deliberately inadmissible under a P0
# power authority.
set -euo pipefail

ROOT=${ROOT:?set ROOT to a fresh run root}
SEED_FILE=${SEED_FILE:?set SEED_FILE to the external schedule seed file}
KEY_FILE=${KEY_FILE:?set KEY_FILE to the external assignment key file}
SOURCE_ROOT=${SOURCE_ROOT:?set SOURCE_ROOT to the external analysis source root}
SOURCE=${SOURCE:?set SOURCE to one analysis source name under SOURCE_ROOT}
CONFIG=${CONFIG:?set CONFIG to the external analysis config}
PROJECTION_SCHEMA=${PROJECTION_SCHEMA:?set PROJECTION_SCHEMA to the external projection schema}

cli() { .venv/bin/python -m pneuma_lab.resampling_null --run-root "$ROOT" "$@"; }

GRID=$(cd "$ROOT" && ls sources/power-grid/*.json)
TOPOLOGY=$(cd "$ROOT" && ls sources/power-screen-topology/*.json)
power() { cli power "$@" --authority power/authority.json --grid-ref "$GRID" --screen-topology-ref "$TOPOLOGY"; }

echo "== gaussian screen"
power screen --phase gaussian_approximation --generation 0 --shard-count 4 --out power/screen-gen0.json
for index in 0 1 2 3; do
    echo "== gaussian shard $index"
    power simulate --screen power/screen-gen0.json --shard-index "$index" --out "power/shard-gen0-0$index.json"
done
echo "== worst-five selection"
power select-validation --screen power/screen-gen0.json --shard-prefix power/shard-gen0-0 --out power/selection-gen0.json
echo "== gaussian-versus-multiplier validation"
power validate --screen power/screen-gen0.json --shard-prefix power/shard-gen0-0 \
    --selection power/selection-gen0.json --out power/validation-gen0.json

echo "== full-multiplier fallback screen (registered response to a failed approximation)"
power screen --phase full_multiplier_fallback --generation 0 --shard-count 4 \
    --fallback-trigger power/validation-gen0.json --out power/screen-fb0.json
for index in 0 1 2 3; do
    echo "== fallback shard $index"
    power simulate --screen power/screen-fb0.json --shard-index "$index" --out "power/shard-fb0-0$index.json"
done
echo "== full-grid fallback validation"
power validate-fallback --screen power/screen-fb0.json --shard-prefix power/shard-fb0-0 --out power/validation-fb0.json
echo "== final"
power finalize --completed-implementation-verification-fallback --selected-screen power/screen-fb0.json \
    --selected-shard-prefix power/shard-fb0-0 --fallback-validation power/validation-fb0.json --out power/final.json

echo "== schedule seal"
cli schedule seal --study study-manifest.json --power-final power/final.json \
    --schedule-seed-file "$SEED_FILE" --out prefix-schedule.json
echo "== synthetic prefixes"
cli synthetic prefixes --study study-manifest.json --schedule prefix-schedule.json --out prefix/prefix-index.json
echo "== assignment seal"
cli assignment seal --schedule prefix-schedule.json --prefix-index prefix/prefix-index.json \
    --assignment-key-file "$KEY_FILE" --out assignment/ledger.json
echo "== packets build"
cli packets build --study study-manifest.json --assignment assignment/ledger.json \
    --prefix-index prefix/prefix-index.json --out-candidate packets/candidate.json
echo "== packets audit"
cli packets audit --study study-manifest.json --candidate packets/candidate.json \
    --schedule prefix-schedule.json --assignment assignment/ledger.json \
    --prefix-index prefix/prefix-index.json --out-index packets/index.json
echo "== analysis freeze"
cli analysis freeze --source-root "$SOURCE_ROOT" --source "$SOURCE" --config "$CONFIG" \
    --projection-schema "$PROJECTION_SCHEMA" --packet-index packets/index.json --out analysis/freeze.json
echo "== opaque branch execution"
cli synthetic branches --study study-manifest.json --schedule prefix-schedule.json \
    --assignment assignment/ledger.json --prefix-index prefix/prefix-index.json \
    --packet-index packets/index.json --analysis-freeze analysis/freeze.json --out-prefix task-blocks
echo "== blinded projection"
cli project seal --schedule prefix-schedule.json --analysis-freeze analysis/freeze.json \
    --task-block-prefix task-blocks --out analysis/projection.json
echo "== gated unblind and registered analysis"
cli analyze --study study-manifest.json --projection analysis/projection.json \
    --assignment assignment/ledger.json --analysis-freeze analysis/freeze.json \
    --packet-index packets/index.json --unblind-receipt analysis/unblind-receipt.json \
    --out analysis/analysis.json --source-root "$SOURCE_ROOT" --source "$SOURCE" \
    --config "$CONFIG" --projection-schema "$PROJECTION_SCHEMA" --assignment-key-file "$KEY_FILE"
echo "== implementation-verification lineage complete"
