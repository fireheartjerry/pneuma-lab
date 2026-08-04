"""Content-addressed runtime for the three production image roles.

The default ``verify`` protocol is the small Step 7B image probe.  The
``e2e`` protocol is retained as an explicitly qualification-only harness.
The ``production`` protocol consumes the immutable run specification and
sends the registered task surface through the real model and benchmark
adapters.  It is a runtime path, not authorization to launch it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .production_evidence import ProductionWorkerExecutor, launch_model_server, write_worker_result
from .production_controller import ProductionOrchestrator, ProductionStateStore
from .production_run import ProductionRunSpec, canonical_digest, task_rows, work_ids_for_worker

_ROLES = frozenset({"controller", "model-server", "benchmark-worker"})
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_E2E_KIND = "cloud_production_e2e_harness"


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _canonical_bytes(value: object) -> bytes:
    return (_canonical(value) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _failure(role: str, reason: str) -> int:
    print(_canonical({"role": role, "state": "FAILED", "reason": reason}))
    return 2


def _read_harness(path: Path, expected: str) -> tuple[bytes, str] | None:
    payload = path.read_bytes()
    observed = _sha256(payload)
    if observed != expected:
        return None
    return payload, observed


def _require_e2e_harness(payload: bytes) -> dict[str, Any] | None:
    try:
        harness = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(harness, dict) or _canonical_bytes(harness) != payload:
        return None
    if harness.get("record_kind") != _E2E_KIND or harness.get("schema_version") != "0.1.0":
        return None
    if not isinstance(harness.get("action_id"), str) or not harness["action_id"]:
        return None
    if not isinstance(harness.get("input_lock_sha256"), str) or not _DIGEST.fullmatch(harness["input_lock_sha256"]):
        return None
    request = harness.get("request")
    if not isinstance(request, dict):
        return None
    if not isinstance(request.get("request_id"), str) or not request["request_id"]:
        return None
    if not isinstance(request.get("prompt"), str) or not request["prompt"]:
        return None
    if type(request.get("max_tokens")) is not int or not 1 <= request["max_tokens"] <= 16:
        return None
    if type(request.get("temperature")) is not float or request["temperature"] != 0.0:
        return None
    return harness


def _common(harness: dict[str, Any], role: str, state: str, harness_sha256: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = harness["request"]
    request_bytes = _canonical_bytes(request)
    return {
        "record_kind": "cloud_production_role_receipt",
        "schema_version": "0.1.0",
        "role": role,
        "state": state,
        "action_id": harness["action_id"],
        "input_lock_sha256": harness["input_lock_sha256"],
        "harness_sha256": harness_sha256,
        "harness_bytes": len(_canonical_bytes(harness)),
        "request_id": request["request_id"],
        "request_sha256": _sha256(request_bytes),
        "payload": payload,
    }


def _load_input(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _e2e(role: str, harness: dict[str, Any], harness_sha256: str, input_path: Path | None) -> int:
    request = harness["request"]
    request_sha256 = _sha256(_canonical_bytes(request))
    if role == "controller":
        if input_path is not None:
            return _failure(role, "controller_input_forbidden")
        receipt = _common(
            harness,
            role,
            "DISPATCHED",
            harness_sha256,
            {"next_role": "model-server", "request": request},
        )
        print(_canonical(receipt))
        return 0

    if input_path is None:
        return _failure(role, "role_input_required")
    predecessor = _load_input(input_path)
    if predecessor is None:
        return _failure(role, "predecessor_receipt_invalid")
    if predecessor.get("record_kind") != "cloud_production_role_receipt":
        return _failure(role, "predecessor_kind_mismatch")
    if predecessor.get("harness_sha256") != harness_sha256:
        return _failure(role, "predecessor_harness_mismatch")
    if predecessor.get("action_id") != harness["action_id"] or predecessor.get("input_lock_sha256") != harness["input_lock_sha256"]:
        return _failure(role, "predecessor_authority_mismatch")
    if predecessor.get("request_sha256") != request_sha256:
        return _failure(role, "predecessor_request_mismatch")

    if role == "model-server":
        if predecessor.get("role") != "controller" or predecessor.get("state") != "DISPATCHED":
            return _failure(role, "controller_dispatch_required")
        digest = _sha256(request["prompt"].encode("utf-8"))
        token_count = min(request["max_tokens"], 4)
        response = {
            "adapter": "content-addressed-qualification-v1",
            "text": f"qualification:{digest[:16]}",
            "token_ids": [int(digest[index : index + 2], 16) for index in range(0, token_count * 2, 2)],
        }
        response_sha256 = _sha256(_canonical_bytes(response))
        receipt = _common(
            harness,
            role,
            "RESPONDED",
            harness_sha256,
            {"response": response, "response_sha256": response_sha256, "next_role": "benchmark-worker"},
        )
        print(_canonical(receipt))
        return 0

    if predecessor.get("role") != "model-server" or predecessor.get("state") != "RESPONDED":
        return _failure(role, "model_response_required")
    predecessor_payload = predecessor.get("payload")
    if not isinstance(predecessor_payload, dict):
        return _failure(role, "model_payload_invalid")
    response = predecessor_payload.get("response")
    response_sha256 = predecessor_payload.get("response_sha256")
    if not isinstance(response, dict) or not isinstance(response_sha256, str) or _sha256(_canonical_bytes(response)) != response_sha256:
        return _failure(role, "model_response_digest_mismatch")
    token_ids = response.get("token_ids")
    if not isinstance(token_ids, list) or not token_ids or any(type(token) is not int or not 0 <= token <= 255 for token in token_ids):
        return _failure(role, "model_response_tokens_invalid")
    receipt = _common(
        harness,
        role,
        "COMPLETE",
        harness_sha256,
        {
            "response_sha256": response_sha256,
            "accepted": True,
            "generated_tokens": len(token_ids),
            "evaluation": "protocol_round_trip",
        },
    )
    print(_canonical(receipt))
    return 0


def _production(
    role: str,
    spec_path: Path | None,
    spec_sha256: str | None,
    *,
    worker_id: str | None,
    output_path: Path | None,
    raw_output_path: Path | None,
    run_root: Path,
) -> int:
    """Run one production role without ever falling back to the fixture path."""

    if spec_path is None or spec_sha256 is None:
        return _failure(role, "production_run_spec_required")
    try:
        spec = ProductionRunSpec.load(spec_path, expected_sha256=spec_sha256)
        if spec.run_mode == "official":
            # A real official job must carry its own cryptographically verified
            # authority.  Merely selecting ``--protocol production`` cannot
            # turn a qualification action or local mock into official evidence.
            spec.verify_official_authorization(run_root=run_root)
        if role == "controller":
            rows = task_rows(spec, run_root=run_root)
            allocation = {
                worker: list(
                    work_ids_for_worker(spec, worker_id=worker, run_root=run_root)
                )
                for worker in spec.worker_ids
            }
            state_ref = spec.value["output"]["controller_state_path"]
            state_path = run_root / str(state_ref)
            store = ProductionStateStore(
                state_path,
                action_id=str(spec.value["action_id"]),
                run_spec_sha256=spec.digest,
                binding={"action_id": spec.value["action_id"], "run_spec_sha256": spec.digest},
            )
            orchestrator = ProductionOrchestrator(
                store,
                action_id=str(spec.value["action_id"]),
                run_spec_sha256=spec.digest,
                allocation=allocation,
            )
            orchestrator.prepare()
            print(
                _canonical(
                    {
                        "record_kind": "cloud_production_dispatch_plan",
                        "schema_version": "0.1.0",
                        "run_spec_sha256": spec.digest,
                        "task_count": len(rows),
                        "allocation": allocation,
                        "execution_class": (
                            "official_candidate"
                            if spec.run_mode == "official"
                            else "local_mock_non_scientific"
                        ),
                    }
                )
            )
            return 0
        if role == "model-server":
            launch_model_server(spec, run_root=run_root)
            return 0
        if worker_id is None or output_path is None or raw_output_path is None:
            return _failure(role, "production_worker_outputs_required")
        result = ProductionWorkerExecutor(spec, run_root=run_root).execute(worker_id)
        evidence = write_worker_result(
            result,
            evidence_path=output_path,
            raw_path=raw_output_path,
            run_root=run_root,
        )
        print(
            _canonical(
                {
                    "record_kind": "cloud_production_worker_terminal",
                    "schema_version": "0.1.0",
                    "run_spec_sha256": spec.digest,
                    "worker_id": worker_id,
                    "evidence_sha256": canonical_digest(evidence),
                    "state": evidence["state"],
                }
            )
        )
        return 0
    except Exception as exc:
        return _failure(role, type(exc).__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(_ROLES))
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--harness-sha256")
    parser.add_argument("--protocol", choices=("verify", "e2e", "production"), default="verify")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-spec", type=Path)
    parser.add_argument("--run-spec-sha256")
    parser.add_argument("--worker-id")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--run-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    if args.protocol == "production":
        if args.run_spec_sha256 is not None and not _DIGEST.fullmatch(args.run_spec_sha256):
            parser.error("--run-spec-sha256 must be lowercase SHA-256")
        return _production(
            args.role,
            args.run_spec,
            args.run_spec_sha256,
            worker_id=args.worker_id,
            output_path=args.output,
            raw_output_path=args.raw_output,
            run_root=args.run_root,
        )
    if args.harness is None or args.harness_sha256 is None:
        parser.error("--harness and --harness-sha256 are required for qualification protocols")
    if not _DIGEST.fullmatch(args.harness_sha256):
        parser.error("--harness-sha256 must be lowercase SHA-256")
    read = _read_harness(args.harness, args.harness_sha256)
    if read is None:
        return _failure(args.role, "harness_sha256_mismatch")
    payload, observed = read
    if args.protocol == "verify":
        print(_canonical({"role": args.role, "state": "READY", "harness_sha256": observed, "harness_bytes": len(payload)}))
        return 0
    harness = _require_e2e_harness(payload)
    if harness is None:
        return _failure(args.role, "e2e_harness_invalid")
    return _e2e(args.role, harness, observed, args.input)


if __name__ == "__main__":
    raise SystemExit(main())
