#!/usr/bin/env bash
set -euo pipefail

readonly uv_version="0.11.28"
readonly script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly repo_root="$(CDPATH= cd -- "$script_dir/../.." && pwd -P)"
readonly profile="${1:-local}"

case "$profile" in
    local|cloud) ;;
    *)
        printf 'ERROR: profile must be local or cloud\n' >&2
        exit 2
        ;;
esac

if [[ "$(uname -s)" != "Linux" ]]; then
    printf 'ERROR: foundation setup requires Linux\n' >&2
    exit 2
fi

case "${repo_root,,}" in
    /mnt/c/pneuma-data|/mnt/c/pneuma-data/*)
        printf 'ERROR: repository resolves inside the protected corpus\n' >&2
        exit 2
        ;;
esac

export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    curl --proto '=https' --tlsv1.2 -LsSf \
        "https://astral.sh/uv/0.11.28/install.sh" | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv_reported="$(uv --version 2>&1)"
if [[ "$uv_reported" != "uv ${uv_version}" && "$uv_reported" != "uv ${uv_version} ("* ]]; then
    printf 'ERROR: uv %s is required\n' "$uv_version" >&2
    exit 2
fi

cd -- "$repo_root"
uv python install 3.12
uv sync --python 3.12 --extra dev --extra foundation --locked
uv run python -m pneuma_lab.foundation doctor --profile "$profile"

printf 'SETUP COMPLETE\n'
printf 'TRAINING HAS NOT STARTED\n'
