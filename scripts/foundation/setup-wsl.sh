#!/usr/bin/env bash
set -euo pipefail

if [[ ! -r /proc/version ]] || ! grep -qi microsoft /proc/version; then
    printf 'ERROR: this wrapper requires WSL2\n' >&2
    exit 2
fi

readonly script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly repo_root="$(CDPATH= cd -- "$script_dir/../.." && pwd -P)"
exec "$repo_root/scripts/foundation/setup-linux.sh" local
