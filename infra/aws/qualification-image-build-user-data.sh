#!/bin/bash
set -Eeuo pipefail

# Action-specific values are rendered into this content-addressed template
# immediately before the one-use EC2 launch. The template itself is sealed in
# the source commit and its hash is bound by the preparation plan.
readonly ACTION_ID="__ACTION_ID__"
readonly SOURCE_ARCHIVE_URI="__SOURCE_ARCHIVE_URI__"
readonly SOURCE_ARCHIVE_SHA256="__SOURCE_ARCHIVE_SHA256__"
readonly SOURCE_COMMIT="__SOURCE_COMMIT__"
readonly DOCKERFILE_SHA256="__DOCKERFILE_SHA256__"
readonly BASE_DIGEST="__BASE_DIGEST__"
readonly REPOSITORY_URI="__REPOSITORY_URI__"
readonly IMAGE_TAG="__IMAGE_TAG__"
readonly OUTPUT_URI="__OUTPUT_URI__"
readonly ROOT="/opt/pneuma-qualification-build"
readonly OUTPUT_DIR="$ROOT/output"
readonly SOURCE_ROOT="$ROOT/source"
readonly IMAGE_REF="$REPOSITORY_URI:$IMAGE_TAG"

fail() {
    local reason="$1"
    printf '{"action_id":"%s","reason":"%s","state":"FAILED"}\n' \
        "$ACTION_ID" "$reason" > "$OUTPUT_DIR/bootstrap-status.json"
    aws s3 cp "$OUTPUT_DIR" "$OUTPUT_URI" --recursive --only-show-errors || true
    shutdown -h now || true
    exit 1
}

trap 'fail bootstrap_error' ERR

run_negative_entrypoint_check() {
    local image_ref="$1"
    local output_dir="$2"
    local stdout_path="$output_dir/entrypoint-negative.stdout"
    local stderr_path="$output_dir/entrypoint-negative.stderr"
    local receipt_path="$output_dir/entrypoint-negative.json"
    local negative_status

    # An expected nonzero result is the condition being tested. Keeping the
    # command in an if condition suppresses ERR-trap handling for this branch
    # only; the trap remains active for every unexpected failure.
    if docker run --rm --network none --read-only --tmpfs /tmp "$image_ref" \
        > "$stdout_path" 2> "$stderr_path"; then
        fail entrypoint_negative_check_succeeded
    else
        negative_status=$?
    fi
    grep -Fq 'QUALIFICATION_CODE' "$stderr_path" || fail entrypoint_negative_check_missing_code_error
    printf '{"command":"docker run --rm --network none --read-only --tmpfs /tmp %s","returncode":%s,"qualification_code_required":true}\n' \
        "$image_ref" "$negative_status" > "$receipt_path"
}

run_image_fixture_check() {
    local image_ref="$1"
    local output_dir="$2"
    local fixture_script="$3"
    local output_name="$4"
    docker run --rm --network none --read-only --tmpfs /tmp \
        --entrypoint python3 \
        --volume "$fixture_script:/work/qualification_image_fixture_check.py:ro" \
        "$image_ref" /work/qualification_image_fixture_check.py \
        > "$output_dir/$output_name"
}

run_pre_push_checks() {
    local image_ref="$1"
    local output_dir="$2"
    run_negative_entrypoint_check "$image_ref" "$output_dir"
    docker run --rm --network none --read-only --tmpfs /tmp \
        --entrypoint /usr/local/bin/aws "$image_ref" --version \
        > "$output_dir/image-aws-version.txt"
    grep -Eq '^aws-cli/2\.' "$output_dir/image-aws-version.txt" \
        || fail image_aws_cli_v2_check_failed
    if [[ "${3:-}" != "" ]]; then
        run_image_fixture_check "$image_ref" "$output_dir" "$3" "fixture-runtime.json"
    fi
    printf '{"stage":"post-negative-check","reached":true}\n' \
        > "$output_dir/post-negative-check-sentinel.json"
}

main() {
    mkdir -p "$OUTPUT_DIR" "$SOURCE_ROOT"
    exec > >(tee "$OUTPUT_DIR/bootstrap.log") 2>&1

    STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    aws sts get-caller-identity --output json --no-cli-pager > "$OUTPUT_DIR/builder-identity.json"
    dnf install -y docker tar gzip
    systemctl enable --now docker
    docker version --format '{{json .}}' > "$OUTPUT_DIR/docker-version.json"
    aws s3 cp "$SOURCE_ARCHIVE_URI" "$ROOT/source.tar" --only-show-errors
    printf '%s  %s\n' "$SOURCE_ARCHIVE_SHA256" "$ROOT/source.tar" | sha256sum --check --status || fail source_archive_digest_mismatch
    tar -xf "$ROOT/source.tar" -C "$SOURCE_ROOT"
    readonly DOCKERFILE="$SOURCE_ROOT/infra/docker/qualification-worker/Dockerfile"
    printf '%s  %s\n' "$DOCKERFILE_SHA256" "$DOCKERFILE" | sha256sum --check --status || fail dockerfile_digest_mismatch
    grep -Fqx 'ENTRYPOINT ["/opt/pneuma/fixed_admission_entrypoint.sh"]' "$DOCKERFILE" || fail entrypoint_source_mismatch
    grep -Fqx "      org.opencontainers.image.base.digest=\"$BASE_DIGEST\"" "$DOCKERFILE" || fail base_label_source_mismatch
    timeout --foreground 6600 docker build \
        --pull=false \
        --platform linux/amd64 \
        --build-arg "SOURCE_COMMIT=$SOURCE_COMMIT" \
        --file "$DOCKERFILE" \
        --tag "$IMAGE_REF" \
        "$SOURCE_ROOT"
    docker image inspect "$IMAGE_REF" > "$OUTPUT_DIR/image-inspect.json"
    python3 - "$OUTPUT_DIR/image-inspect.json" "$SOURCE_COMMIT" "$BASE_DIGEST" <<'PY'
import json
import sys

rows = json.load(open(sys.argv[1], encoding="utf-8"))
if len(rows) != 1:
    raise SystemExit("image inspect did not return one image")
config = rows[0].get("Config") or {}
if config.get("Entrypoint") != ["/opt/pneuma/fixed_admission_entrypoint.sh"]:
    raise SystemExit("image entrypoint is not the fixed qualification entrypoint")
labels = config.get("Labels") or {}
if labels.get("org.opencontainers.image.revision") != sys.argv[2]:
    raise SystemExit("image source revision label is not the sealed commit")
if labels.get("org.opencontainers.image.base.digest") != sys.argv[3]:
    raise SystemExit("image base digest label is not the sealed digest")
PY
    docker run --rm --network none --read-only --tmpfs /tmp --entrypoint /bin/sh "$IMAGE_REF" \
        -c 'test -d /opt/pneuma/pneuma_lab'
    run_pre_push_checks "$IMAGE_REF" "$OUTPUT_DIR" \
        "$SOURCE_ROOT/scripts/research/qualification_image_fixture_check.py"
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$REPOSITORY_URI" \
        > "$OUTPUT_DIR/ecr-login.txt"
    docker push "$IMAGE_REF" > "$OUTPUT_DIR/docker-push.log"
    aws ecr describe-images --region us-east-1 --repository-name pneuma-c160-worker \
        --image-ids imageTag="$IMAGE_TAG" --output json --no-cli-pager \
        > "$OUTPUT_DIR/ecr-image-metadata.json"
    IMAGE_DIGEST="$(python3 - "$OUTPUT_DIR/ecr-image-metadata.json" <<'PY'
import json
import re
import sys

rows = json.load(open(sys.argv[1], encoding="utf-8")).get("imageDetails") or []
if len(rows) != 1:
    raise SystemExit("fresh ECR metadata did not contain exactly one image")
digest = rows[0].get("imageDigest")
if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
    raise SystemExit("fresh ECR metadata lacks an immutable image digest")
print(digest)
PY
)"
    readonly IMMUTABLE_IMAGE_REF="$REPOSITORY_URI@$IMAGE_DIGEST"
    docker pull "$IMMUTABLE_IMAGE_REF" > "$OUTPUT_DIR/ecr-image-pull.log"
    docker image inspect "$IMMUTABLE_IMAGE_REF" > "$OUTPUT_DIR/ecr-image-inspect.json"
    python3 - "$OUTPUT_DIR/ecr-image-inspect.json" "$SOURCE_COMMIT" "$BASE_DIGEST" <<'PY'
import json
import sys

rows = json.load(open(sys.argv[1], encoding="utf-8"))
if len(rows) != 1:
    raise SystemExit("fresh ECR image inspect did not return one image")
config = rows[0].get("Config") or {}
if config.get("Entrypoint") != ["/opt/pneuma/fixed_admission_entrypoint.sh"]:
    raise SystemExit("fresh ECR image entrypoint is not fixed")
if config.get("Cmd") not in (None, []):
    raise SystemExit("fresh ECR image has a command override")
labels = config.get("Labels") or {}
if labels.get("org.opencontainers.image.revision") != sys.argv[2]:
    raise SystemExit("fresh ECR image source revision label differs")
if labels.get("org.opencontainers.image.base.digest") != sys.argv[3]:
    raise SystemExit("fresh ECR image base digest label differs")
PY
    run_image_fixture_check \
        "$IMMUTABLE_IMAGE_REF" "$OUTPUT_DIR" \
        "$SOURCE_ROOT/scripts/research/qualification_image_fixture_check.py" \
        "ecr-fixture-runtime.json"
    docker run --rm --network none --read-only --tmpfs /tmp \
        --entrypoint python3 \
        --volume "$OUTPUT_DIR:/work/qualification-output:ro" \
        "$IMMUTABLE_IMAGE_REF" - \
        /work/qualification-output/ecr-image-inspect.json \
        /work/qualification-output/ecr-fixture-runtime.json "$IMAGE_DIGEST" \
        > "$OUTPUT_DIR/ecr-image-config-receipt.json" <<'PY'
import hashlib
import json
import sys

from pneuma_lab.cloud.authorization_keys import canonical_bytes

inspect_path, fixture_path, image_digest = sys.argv[1:]
inspect_sha256 = hashlib.sha256(open(inspect_path, "rb").read()).hexdigest()
fixture_bytes = open(fixture_path, "rb").read()
fixture = json.loads(fixture_bytes.decode("utf-8"))
if fixture.get("status") != "pass" or fixture.get("worker_indices") != [0, 1]:
    raise SystemExit("fresh ECR fixture did not pass the two-worker contract")
config = {
    "status": "pass",
    "image_digest": image_digest,
    "inspect_sha256": inspect_sha256,
}
config["receipt_sha256"] = hashlib.sha256(canonical_bytes(config)).hexdigest()
runtime = {
    "status": "pass",
    "worker_indices": [0, 1],
    "runtime_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
}
runtime["receipt_sha256"] = hashlib.sha256(canonical_bytes(runtime)).hexdigest()
sidecar = {
    "fresh_ecr_image_config": config,
    "fresh_ecr_fixture_runtime": runtime,
}
sidecar["fresh_ecr_sidecar_sha256"] = hashlib.sha256(canonical_bytes(sidecar)).hexdigest()
print(json.dumps(sidecar, sort_keys=True, separators=(",", ":")))
PY
    ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '{"action_id":"%s","ended_at":"%s","image":"%s","source_commit":"%s","started_at":"%s","state":"COMPLETE"}\n' \
        "$ACTION_ID" "$ENDED_AT" "$IMAGE_REF" "$SOURCE_COMMIT" "$STARTED_AT" \
        > "$OUTPUT_DIR/bootstrap-status.json"
    find "$OUTPUT_DIR" -maxdepth 1 -type f -printf '%f\n' | LC_ALL=C sort > "$OUTPUT_DIR/output-files.txt"
    sha256sum "$OUTPUT_DIR"/* > "$OUTPUT_DIR/output-sha256sums.txt"
    aws s3 cp "$OUTPUT_DIR" "$OUTPUT_URI" --recursive --only-show-errors
    shutdown -h now
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
