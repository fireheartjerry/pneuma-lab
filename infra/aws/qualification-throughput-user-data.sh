#!/bin/bash
set -uo pipefail

REGION="us-east-1"
BUCKET="pneuma-phase-b-892077329800"
PAYLOAD_PREFIX="runs/step5b/payloads/1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4/objects"
ACTION_PREFIX="runs/qualification/throughput-001"
IMAGE="892077329800.dkr.ecr.us-east-1.amazonaws.com/pneuma-c160-worker@sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2"
SNAPSHOT_SHA256="1358b8a66687d19e2170f57f0051f065c3f0141aee9c7bdf5e903c39fd7032db"
RUNNER_SHA256="b94e081cd22b9f685e1dbb38ceeaa0f53119ab7b522279baa9108f40d7eb09de"
ROOT="/var/lib/pneuma-throughput"
mkdir -p "$ROOT/results" "$ROOT/model"
systemd-run --unit=pneuma-throughput-deadman --on-active=100m /sbin/shutdown -h now

instance_id="$(TOKEN=$(curl --fail --silent --show-error --request PUT --header 'X-aws-ec2-metadata-token-ttl-seconds: 21600' http://169.254.169.254/latest/api/token) && curl --fail --silent --show-error --header "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)"
started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

aws s3 cp "s3://${BUCKET}/${ACTION_PREFIX}/inputs/subject-model-snapshot.json" "$ROOT/subject-model.json" --region "$REGION"
aws s3 cp "s3://${BUCKET}/${ACTION_PREFIX}/inputs/step5b_throughput_runner.py" "$ROOT/runner.py" --region "$REGION"
printf '%s  %s\n' "$SNAPSHOT_SHA256" "$ROOT/subject-model.json" | sha256sum --check
inputs_snapshot_rc=$?
printf '%s  %s\n' "$RUNNER_SHA256" "$ROOT/runner.py" | sha256sum --check
inputs_runner_rc=$?

python3 - "$ROOT" "$BUCKET" "$PAYLOAD_PREFIX" <<'PY' > "$ROOT/results/reconstruction.json"
import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
import sys

root, bucket, prefix = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
snapshot = json.loads(root.joinpath("subject-model.json").read_text())

def one(row):
    target = root / "model" / row["path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".partial")
    subprocess.run([
        "aws", "s3api", "get-object", "--region", "us-east-1", "--bucket", bucket,
        "--key", f"{prefix}/{row['object_id']}", str(temporary),
    ], check=True, stdout=subprocess.DEVNULL)
    digest = hashlib.sha256()
    size = 0
    with temporary.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if size != row["size_bytes"] or digest.hexdigest() != row["payload_sha256"]:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"sealed-byte mismatch: {row['path']}")
    temporary.replace(target)
    return size

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    sizes = list(pool.map(one, snapshot["objects"]))
print(json.dumps({"record_kind": "step5b_subject_reconstruction", "objects": len(sizes), "bytes": sum(sizes)}, sort_keys=True))
PY
reconstruct_rc=$?

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "892077329800.dkr.ecr.us-east-1.amazonaws.com"
docker pull "$IMAGE" > "$ROOT/results/image-pull.txt" 2>&1

run_rung() {
  name="$1"; length="$2"
  timeout 2700 docker run --rm --gpus all --name "pneuma-${name}" \
    --network none --read-only --cap-drop ALL --security-opt no-new-privileges \
    --tmpfs /tmp:rw,exec,nosuid,size=8g --env HOME=/tmp --env TRITON_CACHE_DIR=/tmp/triton \
    -v "$ROOT/model:/model:ro" -v "$ROOT/runner.py:/opt/pneuma/runner.py:ro" \
    --entrypoint python3 "$IMAGE" /opt/pneuma/runner.py --model /model \
    --rung "$name" --max-model-len "$length" \
    > "$ROOT/results/${name}.json" 2> "$ROOT/results/${name}.stderr"
  rc="$?"
  docker rm -f "pneuma-${name}" >/dev/null 2>&1 || true
  echo "$rc" > "$ROOT/results/${name}.rc"
}

if [ "$inputs_snapshot_rc" -eq 0 ] && [ "$inputs_runner_rc" -eq 0 ] && [ "$reconstruct_rc" -eq 0 ]; then
  run_rung l40s-tp1-32768 32768
  run_rung l40s-tp1-65536 65536
fi

finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$ROOT" "$instance_id" "$started" "$finished" "$inputs_snapshot_rc" "$inputs_runner_rc" "$reconstruct_rc" <<'PY'
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
artifacts = []
for path in sorted(root.joinpath("results").iterdir()):
    payload = path.read_bytes()
    artifacts.append({"path": path.name, "size_bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()})
receipt = {
    "record_kind": "step5b_throughput_receipt", "schema_version": "0.1.0",
    "instance_id": sys.argv[2], "instance_type": "g6e.2xlarge",
    "started_timestamp": sys.argv[3], "finished_timestamp": sys.argv[4],
    "input_verification_rc": {"snapshot": int(sys.argv[5]), "runner": int(sys.argv[6])},
    "reconstruction_rc": int(sys.argv[7]), "artifacts": artifacts,
}
root.joinpath("receipt.json").write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
PY

for path in "$ROOT"/results/* "$ROOT/receipt.json"; do
  aws s3 cp "$path" "s3://${BUCKET}/${ACTION_PREFIX}/outputs/$(basename "$path")" --region "$REGION" --sse AES256 || true
done
shutdown -h now
