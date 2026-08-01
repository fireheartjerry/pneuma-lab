#!/bin/bash
# Exact Step 7B AWS builder bootstrap template.  The controller substitutes only
# the uppercase tokens below, records the resulting SHA-256 in its plan,
# and launches it once after preparation admission has verified.
set -euo pipefail

readonly SOURCE_ARCHIVE_S3_URI='__SOURCE_ARCHIVE_S3_URI__'
readonly SOURCE_ARCHIVE_SHA256='__SOURCE_ARCHIVE_SHA256__'
readonly PLAN_S3_URI='__PLAN_S3_URI__'
readonly ACTION_ID='__ACTION_ID__'
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
aws --version
aws sts get-caller-identity --output json > /opt/pneuma-step7b/output/instance-identity.json
docker info > /opt/pneuma-step7b/output/docker-info-before-build.json
aws s3 cp "$SOURCE_ARCHIVE_S3_URI" /opt/pneuma-step7b/source.tar --only-show-errors
printf '%s  %s\n' "$SOURCE_ARCHIVE_SHA256" /opt/pneuma-step7b/source.tar | sha256sum --check --status || fail source_archive_digest_mismatch
aws s3 cp "$PLAN_S3_URI" /opt/pneuma-step7b/plan.json --only-show-errors
curl --fail --silent --show-error --location "$SYFT_URL" --output /opt/pneuma-step7b/syft.tar.gz
printf '%s  %s\n' "$SYFT_SHA256" /opt/pneuma-step7b/syft.tar.gz | sha256sum --check --status || fail syft_digest_mismatch
tar -tzf /opt/pneuma-step7b/syft.tar.gz | grep -Fx 'syft' >/dev/null || fail syft_member_missing
tar -xzf /opt/pneuma-step7b/syft.tar.gz -C /opt/pneuma-step7b/tools syft
install -m 0755 /opt/pneuma-step7b/tools/syft /usr/local/bin/syft
command -v syft
tar -xf /opt/pneuma-step7b/source.tar -C /opt/pneuma-step7b/source
timeout --preserve-status 6h python3 /opt/pneuma-step7b/source/scripts/research/run_step7b_builds.py \
    --plan /opt/pneuma-step7b/plan.json \
    --source-root /opt/pneuma-step7b/source \
    --output-dir /opt/pneuma-step7b/output
rpm -qa --qf '%{NAME} %{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' | LC_ALL=C sort > /opt/pneuma-step7b/output/rpm-manifest.txt
docker version --format '{{json .}}' > /opt/pneuma-step7b/output/docker-version.json
syft version --output json > /opt/pneuma-step7b/output/syft-version.json
find /opt/pneuma-step7b/output -type f -printf '%p\n' | LC_ALL=C sort | xargs sha256sum > /opt/pneuma-step7b/output/sha256sums.txt
printf '{"state":"COMPLETE","action_id":"%s"}\n' "$ACTION_ID" > /opt/pneuma-step7b/output/bootstrap-status.json
aws s3 cp /opt/pneuma-step7b/output "${OUTPUT_PREFIX}" --recursive --only-show-errors
shutdown -h now
