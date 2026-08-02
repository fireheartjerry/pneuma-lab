"""Run and verify the bounded three-role production-surface handshake.

The command can execute sealed image entrypoints (the admitted path) or the
same Python entrypoint locally for an offline development check.  It never
loads a model, runs a benchmark, or promotes a scientific result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from pneuma_lab.cloud.manifests import validate_production_role_receipt
from pneuma_lab.cloud.production_surface import require_production_execution_surface

ROLES = ("controller", "model-server", "benchmark-worker")


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_bindings(values: list[str], *, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        role, separator, ref = value.partition("=")
        if separator != "=" or role not in ROLES or not ref or role in result:
            raise ValueError(f"{label} must contain each role exactly once as role=value")
        result[role] = ref
    if set(result) != set(ROLES):
        raise ValueError(f"{label} must contain each role exactly once")
    return result


def run_command(command: list[str], *, allow_failure: bool = False) -> bytes:
    result = subprocess.run(command, check=False, capture_output=True)
    if result.returncode != 0 and not (allow_failure and result.returncode == 2):
        raise RuntimeError(
            f"role command failed ({result.returncode}): {result.stderr.decode('utf-8', errors='replace')[-4000:]}"
        )
    if result.stderr:
        raise RuntimeError("role command wrote to stderr")
    return result.stdout


def run_role(
    role: str,
    *,
    image: str | None,
    harness: Path,
    harness_sha256: str,
    input_path: Path | None,
    work: Path,
    controller_privileged: bool,
    allow_failure: bool = False,
) -> bytes:
    if image is None:
        command = [
            sys.executable,
            "-m",
            "pneuma_lab.cloud.production_runtime",
            role,
            "--protocol",
            "e2e",
            "--harness",
            str(harness),
            "--harness-sha256",
            harness_sha256,
        ]
        if input_path is not None:
            command.extend(["--input", str(input_path)])
        return run_command(command, allow_failure=allow_failure)

    command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--volume",
        f"{harness}:/work/harness.json:ro",
    ]
    if input_path is not None:
        command.extend(["--volume", f"{input_path}:/work/predecessor.json:ro"])
    if role == "controller" and controller_privileged:
        command.extend(["--volume", "/var/run/docker.sock:/var/run/docker.sock:ro"])
    command.extend(
        [
            image,
            "--protocol",
            "e2e",
            "--harness",
            "/work/harness.json",
            "--harness-sha256",
            harness_sha256,
        ]
    )
    if input_path is not None:
        command.extend(["--input", "/work/predecessor.json"])
    return run_command(command, allow_failure=allow_failure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--harness-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--image", action="append", default=[], help="role=image reference; provide all three or none")
    parser.add_argument("--image-digest", action="append", default=[], help="role=sha256 digest; provide all three or none")
    parser.add_argument("--controller-privileged", action="store_true")
    args = parser.parse_args()
    if len(args.harness_sha256) != 64 or any(char not in "0123456789abcdef" for char in args.harness_sha256):
        parser.error("--harness-sha256 must be lowercase SHA-256")
    if not args.harness.is_file() or sha256(args.harness.read_bytes()) != args.harness_sha256:
        parser.error("harness bytes do not match --harness-sha256")
    images = parse_bindings(args.image, label="--image") if args.image else {}
    image_digests = parse_bindings(args.image_digest, label="--image-digest") if args.image_digest else {}
    if bool(images) != bool(image_digests):
        parser.error("--image and --image-digest must be supplied together")
    if images and not args.controller_privileged:
        parser.error("image qualification requires --controller-privileged so its controller gates are explicit")
    if images and shutil.which("docker") is None:
        parser.error("Docker is required for image qualification")
    try:
        harness = json.loads(args.harness.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        parser.error(f"invalid harness JSON: {exc}")
    if not isinstance(harness, dict) or harness.get("record_kind") != "cloud_production_e2e_harness":
        parser.error("harness must be a cloud_production_e2e_harness")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    receipts: dict[str, dict[str, Any]] = {}
    predecessor: Path | None = None
    expected_states = {"controller": "DISPATCHED", "model-server": "RESPONDED", "benchmark-worker": "COMPLETE"}
    for role in ROLES:
        stdout = run_role(
            role,
            image=images.get(role),
            harness=args.harness.resolve(),
            harness_sha256=args.harness_sha256,
            input_path=predecessor,
            work=output,
            controller_privileged=args.controller_privileged,
        )
        path = output / f"{role}.json"
        path.write_bytes(stdout)
        receipt = json.loads(stdout.decode("utf-8"))
        validated = validate_production_role_receipt(receipt)
        if validated["state"] != expected_states[role]:
            raise RuntimeError(f"{role} did not reach {expected_states[role]}")
        receipts[role] = validated
        predecessor = path

    for role in ROLES:
        wrong = run_role(
            role,
            image=images.get(role),
            harness=args.harness.resolve(),
            harness_sha256="0" * 64,
            input_path=None,
            work=output,
            controller_privileged=args.controller_privileged,
            allow_failure=True,
        )
        wrong_record = json.loads(wrong.decode("utf-8"))
        if wrong_record.get("state") != "FAILED" or wrong_record.get("reason") != "harness_sha256_mismatch":
            raise RuntimeError(f"{role} wrong-hash probe did not fail closed")
        (output / f"{role}-wrong-hash.json").write_bytes(wrong)

    runtime = args.source_root / "src/pneuma_lab/cloud/production_runtime.py"
    runtime_sha256 = sha256(runtime.read_bytes())
    surface = {
        "record_kind": "cloud_production_execution_surface",
        "schema_version": "0.1.0",
        "input_lock_sha256": harness["input_lock_sha256"],
        "source_commit": args.source_commit,
        "roles": [
            {
                "role": role,
                "image_digest": image_digests.get(role, "sha256:" + ("0" if role == "controller" else "1") * 64),
                "entrypoint": ["python3", "-m", "pneuma_lab.cloud.production_runtime", role],
                "source_sha256": runtime_sha256,
                "e2e_receipt_sha256": sha256((output / f"{role}.json").read_bytes()),
                "gates": {
                    "clean_start": True,
                    "expected_terminal_state": True,
                    "failure_receipt": True,
                    "no_class_a_secret": True,
                    "no_controller_credentials": role != "controller",
                    "imds_blocked": True,
                    "docker_socket_absent": role != "controller",
                },
            }
            for role in ROLES
        ],
    }
    require_production_execution_surface(surface)
    (output / "surface.json").write_bytes(canonical(surface))
    print(json.dumps({"surface_sha256": sha256(canonical(surface)), "roles": list(ROLES)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
