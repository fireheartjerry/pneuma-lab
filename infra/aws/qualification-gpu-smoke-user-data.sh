#!/bin/bash
set -euo pipefail

REGION="us-east-1"
IMAGE="892077329800.dkr.ecr.us-east-1.amazonaws.com/pneuma-c160-worker@sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2"
BUCKET="pneuma-phase-b-892077329800"
PREFIX="runs/qualification/gpu-smoke-001"

# The EC2 launch sets instance-initiated shutdown behavior to terminate. This
# deadman remains independent of the interactive controller and caps runtime.
systemd-run --unit=pneuma-qualification-deadman --on-active=110m /sbin/shutdown -h now
mkdir -p /var/lib/pneuma

instance_id="$(curl --fail --silent --show-error --request PUT \
  --header 'X-aws-ec2-metadata-token-ttl-seconds: 21600' \
  http://169.254.169.254/latest/api/token | xargs -I{} curl --fail --silent --show-error \
  --header 'X-aws-ec2-metadata-token: {}' \
  http://169.254.169.254/latest/meta-data/instance-id)"

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "892077329800.dkr.ecr.us-east-1.amazonaws.com"
docker pull "$IMAGE"
nvidia-smi --query-gpu=name,uuid,memory.total,driver_version --format=csv,noheader \
  | tee /var/lib/pneuma/nvidia-smi.csv
docker run --rm --gpus all "$IMAGE" inspect \
  | tee /var/lib/pneuma/worker-inspect.json

python3 - "$instance_id" <<'PY'
import hashlib
import json
import pathlib
import sys
from datetime import datetime, timezone

root = pathlib.Path("/var/lib/pneuma")
inspect = root.joinpath("worker-inspect.json").read_bytes()
nvidia = root.joinpath("nvidia-smi.csv").read_bytes()
receipt = {
    "record_kind": "step5b_gpu_smoke_receipt",
    "schema_version": "0.1.0",
    "frozen_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "instance_id": sys.argv[1],
    "instance_type": "g6e.2xlarge",
    "ami_id": "ami-011db5ae81cc0f370",
    "image": "892077329800.dkr.ecr.us-east-1.amazonaws.com/pneuma-c160-worker@sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2",
    "nvidia_smi_sha256": hashlib.sha256(nvidia).hexdigest(),
    "worker_inspect_sha256": hashlib.sha256(inspect).hexdigest(),
    "worker_inspect": json.loads(inspect),
}
root.joinpath("receipt.json").write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
PY

aws s3 cp /var/lib/pneuma/nvidia-smi.csv "s3://${BUCKET}/${PREFIX}/nvidia-smi.csv" --region "$REGION" --sse AES256
aws s3 cp /var/lib/pneuma/worker-inspect.json "s3://${BUCKET}/${PREFIX}/worker-inspect.json" --region "$REGION" --sse AES256
aws s3 cp /var/lib/pneuma/receipt.json "s3://${BUCKET}/${PREFIX}/receipt.json" --region "$REGION" --sse AES256
shutdown -h now
