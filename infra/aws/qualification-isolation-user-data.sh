#!/bin/bash
set -uo pipefail

REGION="us-east-1"
BUCKET="pneuma-phase-b-892077329800"
ACTION_PREFIX="runs/qualification/isolation-001"
ROOT="/var/lib/pneuma-isolation"
mkdir -p "$ROOT/inputs" "$ROOT/outputs"
systemd-run --unit=pneuma-isolation-deadman --on-active=220m /sbin/shutdown -h now

instance_id="$(TOKEN=$(curl --fail --silent --show-error --request PUT --header 'X-aws-ec2-metadata-token-ttl-seconds: 21600' http://169.254.169.254/latest/api/token) && curl --fail --silent --show-error --header "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)"

aws s3 cp "s3://${BUCKET}/${ACTION_PREFIX}/inputs/cases.json" "$ROOT/inputs/cases.json" --region "$REGION"
aws s3 cp "s3://${BUCKET}/${ACTION_PREFIX}/inputs/runner.py" "$ROOT/inputs/runner.py" --region "$REGION"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "892077329800.dkr.ecr.us-east-1.amazonaws.com"

timeout 12600 python3 "$ROOT/inputs/runner.py" \
  --manifest "$ROOT/inputs/cases.json" --instance-id "$instance_id" \
  --output "$ROOT/outputs/isolation-receipt.json" \
  > "$ROOT/outputs/isolation.stdout" 2> "$ROOT/outputs/isolation.stderr"
runner_rc="$?"
echo "$runner_rc" > "$ROOT/outputs/isolation.rc"

for path in "$ROOT"/outputs/*; do
  aws s3 cp "$path" "s3://${BUCKET}/${ACTION_PREFIX}/outputs/$(basename "$path")" --region "$REGION" --sse AES256 || true
done
shutdown -h now
