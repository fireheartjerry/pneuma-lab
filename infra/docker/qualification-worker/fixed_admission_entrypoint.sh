#!/bin/sh
set -eu

: "${QUALIFICATION_CODE:?QUALIFICATION_CODE must be supplied by the signed Terraform admission}"
exec python3 -m pneuma_lab.cloud.fixed_admission_probe --code "$QUALIFICATION_CODE" "$@"
