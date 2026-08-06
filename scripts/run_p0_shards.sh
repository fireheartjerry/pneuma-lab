#!/usr/bin/env bash
# Execute the frozen P0 grid shards for one admitted screen generation.
#
# Shards are independent immutable artifacts with distinct attempt identities,
# so they may run concurrently.  Concurrency is an execution convenience only:
# the registered timing projection already charged the complete workload with
# no parallelism discount before this screen was admitted.
set -uo pipefail

ROOT=${ROOT:?set ROOT to the run root}
SCREEN=${SCREEN:?set SCREEN to the admitted screen ref path}
GRID=${GRID:?set GRID to the manifest-bound power grid ref path}
TOPOLOGY=${TOPOLOGY:?set TOPOLOGY to the manifest-bound screen topology ref path}
AUTHORITY=${AUTHORITY:-power/authority.json}
SHARDS=${SHARDS:-64}
WORKERS=${WORKERS:-6}
TIER=${TIER:-}
LOG=${LOG:-build/step4/shards.log}

mkdir -p "$(dirname "$LOG")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

run_shard() {
    local index=$1
    local out
    out=$(printf 'power/shard-gen0-%02d.json' "$index")
    if [ -f "$ROOT/$out" ]; then
        echo "skip $index (already present)" >> "$LOG"
        return 0
    fi
    local started
    started=$SECONDS
    local tier_args=()
    if [ -n "$TIER" ]; then
        tier_args=(--tier "$TIER")
    fi
    if .venv/bin/python -m pneuma_lab.resampling_null --run-root "$ROOT" power simulate \
        --authority "$AUTHORITY" --grid-ref "$GRID" --screen-topology-ref "$TOPOLOGY" \
        "${tier_args[@]}" --screen "$SCREEN" --shard-index "$index" --out "$out" >> "$LOG" 2>&1; then
        echo "ok $index in $((SECONDS - started))s" >> "$LOG"
    else
        echo "FAIL $index in $((SECONDS - started))s" >> "$LOG"
    fi
}

pids=()
for index in $(seq 0 $((SHARDS - 1))); do
    run_shard "$index" &
    pids+=($!)
    while [ "$(jobs -rp | wc -l)" -ge "$WORKERS" ]; do
        sleep 2
    done
done
wait
grep -c '^ok ' "$LOG" || true
grep '^FAIL' "$LOG" || true
