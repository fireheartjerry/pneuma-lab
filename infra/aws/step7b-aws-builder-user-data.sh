#!/bin/bash
# Exact Step 7B AWS builder bootstrap template.  The controller substitutes only
# the five uppercase tokens below, records the resulting SHA-256 in its plan,
# and launches it once after preparation admission has verified.
set -euo pipefail

readonly SOURCE_ARCHIVE_URL='__SOURCE_ARCHIVE_URL__'
readonly SOURCE_ARCHIVE_SHA256='__SOURCE_ARCHIVE_SHA256__'
readonly PLAN_URL='__PLAN_URL__'
readonly PLAN_SHA256='__PLAN_SHA256__'
readonly SYFT_URL='__SYFT_URL__'
readonly SYFT_SHA256='__SYFT_SHA256__'
readonly OUTPUT_PREFIX='__OUTPUT_PREFIX__'

mkdir -p /opt/pneuma-step7b/{source,output,tools}
exec > >(tee /opt/pneuma-step7b/output/bootstrap.log) 2>&1

fail() {
    local message="$1"
    printf '{"state":"FAILED","reason":"%s"}\n' "$message" > /opt/pneuma-step7b/output/bootstrap-status.json
    aws s3 cp /opt/pneuma-step7b/output "${OUTPUT_PREFIX}" --recursive --only-show-errors || true
    shutdown -h now
    exit 1
}

trap 'fail bootstrap_error' ERR
dnf install -y docker tar gzip curl
systemctl enable --now docker
curl --fail --silent --show-error --location "$SOURCE_ARCHIVE_URL" --output /opt/pneuma-step7b/source.tar
printf '%s  %s\n' "$SOURCE_ARCHIVE_SHA256" /opt/pneuma-step7b/source.tar | sha256sum --check --status || fail source_archive_digest_mismatch
curl --fail --silent --show-error --location "$PLAN_URL" --output /opt/pneuma-step7b/plan.json
printf '%s  %s\n' "$PLAN_SHA256" /opt/pneuma-step7b/plan.json | sha256sum --check --status || fail plan_digest_mismatch
curl --fail --silent --show-error --location "$SYFT_URL" --output /opt/pneuma-step7b/syft.tar.gz
printf '%s  %s\n' "$SYFT_SHA256" /opt/pneuma-step7b/syft.tar.gz | sha256sum --check --status || fail syft_digest_mismatch
tar -xzf /opt/pneuma-step7b/syft.tar.gz -C /opt/pneuma-step7b/tools syft
install -m 0755 /opt/pneuma-step7b/tools/syft /usr/local/bin/syft
tar -xf /opt/pneuma-step7b/source.tar -C /opt/pneuma-step7b/source
timeout --preserve-status 6h python3 /opt/pneuma-step7b/source/scripts/research/run_step7b_builds.py \
    --plan /opt/pneuma-step7b/plan.json \
    --source-root /opt/pneuma-step7b/source \
    --output-dir /opt/pneuma-step7b/output
rpm -qa --qf '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | LC_ALL=C sort > /opt/pneuma-step7b/output/rpm-manifest.txt
docker version --format '{{json .}}' > /opt/pneuma-step7b/output/docker-version.json
syft version --output json > /opt/pneuma-step7b/output/syft-version.json
sha256sum /opt/pneuma-step7b/output/* > /opt/pneuma-step7b/output/sha256sums.txt
printf '{"state":"COMPLETE","action":"step7b-aws-builder-001"}\n' > /opt/pneuma-step7b/output/bootstrap-status.json
aws s3 cp /opt/pneuma-step7b/output "${OUTPUT_PREFIX}" --recursive --only-show-errors
shutdown -h now
