"""Execute one frozen 33-pair Linux container-isolation qualification action."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SPLITS = {"swe": ("c", "cpp", "cs", "go", "java", "js", "rust", "ts"), "tau2": ("airline", "telecom", "banking")}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def run(*args: str, capture: bool = True) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return result.stdout.strip() if capture else ""


def inspect(name: str) -> dict:
    return json.loads(run("docker", "inspect", name))[0]


def create(name: str, image: str) -> str:
    return run(
        "docker", "create", "--name", name, "--network", "none", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true", "--pids-limit", "256",
        "--entrypoint", "/bin/sh", image, "-c", "trap 'exit 0' TERM INT; while :; do sleep 60; done",
    )


def clean(name: str) -> None:
    subprocess.run(("docker", "rm", "-f", name), check=False, capture_output=True)


def qualify(case: dict, index: int) -> dict:
    image = case["image_reference"]
    run("docker", "pull", image, capture=False)
    image_info = inspect(image)
    suffix = hashlib.sha256(case["pair_id"].encode()).hexdigest()[:12]
    a, b = f"pneuma-iso-a-{suffix}", f"pneuma-iso-b-{suffix}"
    clean(a)
    clean(b)
    try:
        a_id, b_id = create(a, image), create(b, image)
        run("docker", "start", a, b)
        a_info, b_info = inspect(a), inspect(b)
        fresh = run("docker", "exec", a, "/bin/sh", "-c", "test ! -e /tmp/pneuma-a -a ! -e /tmp/pneuma-b; echo $?") == "0"
        fresh = fresh and run("docker", "exec", b, "/bin/sh", "-c", "test ! -e /tmp/pneuma-a -a ! -e /tmp/pneuma-b; echo $?") == "0"
        run("docker", "exec", a, "/bin/sh", "-c", "printf '%s' a > /tmp/pneuma-a")
        a_absent_b = run("docker", "exec", b, "/bin/sh", "-c", "test ! -e /tmp/pneuma-a; echo $?") == "0"
        run("docker", "exec", b, "/bin/sh", "-c", "printf '%s' b > /tmp/pneuma-b")
        b_absent_a = run("docker", "exec", a, "/bin/sh", "-c", "test ! -e /tmp/pneuma-b; echo $?") == "0"
        clean(a)
        create(a, image)
        run("docker", "start", a)
        recreated = run("docker", "exec", a, "/bin/sh", "-c", "test ! -e /tmp/pneuma-a -a ! -e /tmp/pneuma-b; echo $?") == "0"
        def security(info: dict) -> dict:
            return info["HostConfig"]
        repo_digests = image_info.get("RepoDigests") or []
        assertions = {
            "immutable_image_digest": "@sha256:" in image and any(
                digest.endswith("@" + image.rsplit("@", 1)[1]) for digest in repo_digests
            ),
            "linux_amd64": image_info.get("Os") == "linux" and image_info.get("Architecture") == "amd64",
            "network_none": all(security(info).get("NetworkMode") == "none" for info in (a_info, b_info)),
            "capabilities_dropped": all("ALL" in (security(info).get("CapDrop") or []) for info in (a_info, b_info)),
            "no_new_privileges": all("no-new-privileges:true" in (security(info).get("SecurityOpt") or []) for info in (a_info, b_info)),
            "fresh_pair_clean": fresh,
            "a_marker_absent_from_b": a_absent_b,
            "b_marker_absent_from_a": b_absent_a,
            "recreated_a_clean": recreated,
        }
        if not all(assertions.values()):
            raise RuntimeError(f"isolation assertions failed for {case['pair_id']}: {assertions}")
        return {
            "pair_id": case["pair_id"], "family": case["family"], "split": case["split"],
            "unit_id": case["unit_id"], "image_reference": image,
            "image_digest": image.rsplit("@", 1)[1], "container_a_id": a_id, "container_b_id": b_id,
            "assertions": assertions,
        }
    finally:
        clean(a)
        clean(b)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    body = dict(manifest)
    claimed = body.pop("manifest_sha256")
    if hashlib.sha256(canonical_bytes(body)).hexdigest() != claimed:
        raise ValueError("case manifest digest mismatch")
    cases = manifest["cases"]
    expected = {(family, split): 3 for family, splits in SPLITS.items() for split in splits}
    observed = {(family, split): sum(c["family"] == family and c["split"] == split for c in cases) for family, split in expected}
    if len(cases) != 33 or observed != expected or len({c["unit_id"] for c in cases}) != 33:
        raise ValueError("case manifest must contain exactly three distinct units per registered split")
    pairs = [qualify(case, index) for index, case in enumerate(cases)]
    receipt = {
        "record_kind": "cloud_isolation_qualification_receipt", "schema_version": "0.1.0",
        "frozen_timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tier": "C120", "input_lock_sha256": manifest["input_lock_sha256"],
        "case_manifest": {"sha256": claimed, "input_lock_sha256": manifest["input_lock_sha256"]},
        "host": {"os": "linux", "architecture": platform.machine(),
                 "docker_version": run("docker", "version", "--format", "{{.Server.Version}}"),
                 "instance_id": args.instance_id},
        "pairs": pairs, "qualification_only": True,
    }
    args.output.write_bytes(canonical_bytes(receipt) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
