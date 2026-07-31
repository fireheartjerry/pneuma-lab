#!/usr/bin/env bash
# Execute the authority-backed synthetic P0 lineage from a complete shard set
# through registered analysis.  Every stage is the committed CLI route; this
# script adds no scientific choice, seed, key, or override of its own.
set -euo pipefail

ROOT=${ROOT:?set ROOT to the run root}
GRID=${GRID:?set GRID to the manifest-bound power grid ref path}
TOPOLOGY=${TOPOLOGY:?set TOPOLOGY to the manifest-bound screen topology ref path}
AUTHORITY=${AUTHORITY:-power/authority.json}
SCREEN=${SCREEN:-power/screen-gen0.json}
SHARD_PREFIX=${SHARD_PREFIX:-power/shard-gen0-}
SEED_FILE=${SEED_FILE:?set SEED_FILE to the external schedule seed file}
KEY_FILE=${KEY_FILE:?set KEY_FILE to the external assignment key file}
SOURCE_ROOT=${SOURCE_ROOT:?set SOURCE_ROOT to the external analysis source root}
SOURCE=${SOURCE:?set SOURCE to one analysis source name under SOURCE_ROOT}
CONFIG=${CONFIG:?set CONFIG to the external analysis config}
PROJECTION_SCHEMA=${PROJECTION_SCHEMA:?set PROJECTION_SCHEMA to the external projection schema}

cli() { .venv/bin/python -m pneuma_lab.resampling_null --run-root "$ROOT" "$@"; }
power() { cli power "$@" --authority "$AUTHORITY" --grid-ref "$GRID" --screen-topology-ref "$TOPOLOGY"; }

echo "== power select-validation"
power select-validation --screen "$SCREEN" --shard-prefix "$SHARD_PREFIX" --out power/selection-gen0.json

echo "== power validate (registered 99,999-draw multiplier comparison)"
power validate --screen "$SCREEN" --shard-prefix "$SHARD_PREFIX" \
    --selection power/selection-gen0.json --out power/validation-gen0.json

echo "== power finalize"
power finalize --completed-gaussian --selected-screen "$SCREEN" \
    --selected-shard-prefix "$SHARD_PREFIX" --selected-selection power/selection-gen0.json \
    --selected-validation power/validation-gen0.json --out power/final-gen0.json

echo "== schedule seal"
cli schedule seal --study study-manifest.json --power-final power/final-gen0.json \
    --schedule-seed-file "$SEED_FILE" --out schedule/prefix-schedule.json

echo "== synthetic prefixes"
cli synthetic prefixes --study study-manifest.json --schedule schedule/prefix-schedule.json \
    --out prefix/prefix-index.json

echo "== assignment seal"
cli assignment seal --schedule schedule/prefix-schedule.json --prefix-index prefix/prefix-index.json \
    --assignment-key-file "$KEY_FILE" --out assignment/ledger.json

echo "== packets build"
cli packets build --study study-manifest.json --assignment assignment/ledger.json \
    --prefix-index prefix/prefix-index.json --out-candidate packets/candidate.json

echo "== packets audit"
cli packets audit --study study-manifest.json --candidate packets/candidate.json \
    --schedule schedule/prefix-schedule.json --assignment assignment/ledger.json \
    --prefix-index prefix/prefix-index.json --out-index packets/index.json

echo "== analysis freeze (pre-outcome)"
cli analysis freeze --source-root "$SOURCE_ROOT" --source "$SOURCE" --config "$CONFIG" \
    --projection-schema "$PROJECTION_SCHEMA" --packet-index packets/index.json \
    --out analysis/freeze.json

echo "== synthetic branches (isolated opaque slot execution)"
cli synthetic branches --study study-manifest.json --schedule schedule/prefix-schedule.json \
    --assignment assignment/ledger.json --prefix-index prefix/prefix-index.json \
    --packet-index packets/index.json --analysis-freeze analysis/freeze.json \
    --out-prefix task-blocks

echo "== project seal (blinded projection)"
cli project seal --schedule schedule/prefix-schedule.json --analysis-freeze analysis/freeze.json \
    --task-block-prefix task-blocks --out analysis/projection.json

echo "== analyze (gated unblind + registered inference)"
cli analyze --study study-manifest.json --projection analysis/projection.json \
    --assignment assignment/ledger.json --analysis-freeze analysis/freeze.json \
    --packet-index packets/index.json --unblind-receipt analysis/unblind-receipt.json \
    --out analysis/analysis.json --source-root "$SOURCE_ROOT" --source "$SOURCE" \
    --config "$CONFIG" --projection-schema "$PROJECTION_SCHEMA" --assignment-key-file "$KEY_FILE"

echo "== lineage complete"
