"""Fail-closed AWS provider for one bounded non-scientific surface fixture.

This module is deliberately narrower than the official Batch provider.  It
creates one tagged, private EC2 host, pulls only immutable role images, runs
the inert ``--protocol e2e`` handshake, and tears down every action-owned
resource.  It never accepts a model, benchmark, roster, assignment, packet,
or official run specification.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import base64
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, cast

from .errors import CloudManifestError
from .production_controller import ProductionJobProvider, ProductionSubmission
from .production_run import canonical_bytes


REGION = "us-east-1"
VPC_ID = "vpc-0577decd080525e86"
AVAILABILITY_ZONE = "us-east-1a"
AMI_ID = "ami-0b416d150bdde5ea2"
AMI_OWNER_ID = "591542846629"
AMI_ARCHITECTURE = "x86_64"
AMI_ROOT_DEVICE = "/dev/xvda"
INSTANCE_TYPE = "m7i.large"
SUBNET_CIDR = "10.42.2.0/24"
MAX_DURATION_SECONDS = 900
MAX_USD = Decimal("3.00")
INTERFACE_SERVICES = ("ecr.api", "ecr.dkr", "ssm", "ssmmessages", "ec2messages")
ACTION_TAG = "PneumaSurfaceAction"
MANAGED_TAG = "production-surface-e2e-v2"
ACTION_ID_RE = re.compile(r"^FIXTURE-NONSCI-[0-9]{8}-v2-[a-z0-9]{8}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ID_RE = re.compile(r"^i-[0-9a-f]+$")
INSTANCE_READBACK_TIMEOUT_SECONDS = 60
INSTANCE_READBACK_RETRY_SECONDS = 2
VPC_ENDPOINT_TERMINATION_TIMEOUT_SECONDS = 300
INSTANCE_TERMINATION_CONFIRM_TIMEOUT_SECONDS = 180
INSTANCE_TERMINATION_CONFIRM_RETRY_SECONDS = 3


def _boto3():
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as exc:
        raise CloudManifestError("boto3 is required for the AWS production-surface provider") from exc
    return boto3


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _jsonable(value: object) -> object:
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(nested) for nested in value]
    return value


def _canonical(value: object) -> bytes:
    return canonical_bytes(value)


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha(value: object) -> str:
    return _sha_bytes(_canonical(value))


def _name(value: str, *, max_length: int = 63) -> str:
    safe = re.sub(r"[^A-Za-z0-9+=,.@_-]", "-", value)
    return safe[:max_length].rstrip("-") or "pneuma-surface"


def _absent(exc: Exception, *codes: str) -> bool:
    response = getattr(exc, "response", {})
    error = response.get("Error", {}) if isinstance(response, Mapping) else {}
    return isinstance(error, Mapping) and error.get("Code") in set(codes)


def _network_interface_delete_on_termination(interface: Mapping[str, object]) -> bool:
    """Read EC2's effective ENI deletion flag from its attachment shape."""

    attachment = interface.get("Attachment")
    return isinstance(attachment, Mapping) and attachment.get("DeleteOnTermination") is True


def _security_group_rule_keys(rules: object) -> set[tuple[object, ...]]:
    """Normalize AWS security-group rules for an exact contract comparison."""

    if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes)):
        raise CloudManifestError("security-group rules must be a sequence")
    result: set[tuple[object, ...]] = set()
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise CloudManifestError("security-group rule must be an object")
        pairs = rule.get("UserIdGroupPairs", [])
        ranges = rule.get("IpRanges", [])
        prefixes = rule.get("PrefixListIds", [])
        if not all(isinstance(value, Sequence) and not isinstance(value, (str, bytes)) for value in (pairs, ranges, prefixes)):
            raise CloudManifestError("security-group rule collections are malformed")
        result.add(
            (
                rule.get("IpProtocol"),
                rule.get("FromPort"),
                rule.get("ToPort"),
                tuple(sorted(str(item.get("GroupId")) for item in pairs if isinstance(item, Mapping))),
                tuple(sorted(str(item.get("CidrIp")) for item in ranges if isinstance(item, Mapping))),
                tuple(sorted(str(item.get("PrefixListId")) for item in prefixes if isinstance(item, Mapping))),
            )
        )
    return result


def _validate_surface_security_group_contract(
    groups: Sequence[Mapping[str, object]], *, endpoint_group_id: str, instance_group_id: str
) -> None:
    """Require endpoint-only TCP/443 traffic and no instance ingress."""

    by_id = {str(group.get("GroupId")): group for group in groups}
    if set(by_id) != {endpoint_group_id, instance_group_id}:
        raise CloudManifestError("surface security-group set does not match the action binding")
    endpoint = by_id[endpoint_group_id]
    instance = by_id[instance_group_id]
    endpoint_pair = ("tcp", 443, 443, (instance_group_id,), (), ())
    endpoint_service = ("tcp", 443, 443, (), ("0.0.0.0/0",), ())
    instance_pair = ("tcp", 443, 443, (endpoint_group_id,), (), ())
    if _security_group_rule_keys(endpoint.get("IpPermissions", [])) != {endpoint_pair}:
        raise CloudManifestError("endpoint security group ingress is not the exact instance TCP/443 rule")
    if _security_group_rule_keys(endpoint.get("IpPermissionsEgress", [])) != {endpoint_service}:
        raise CloudManifestError("endpoint security group egress lacks the exact service TCP/443 rule")
    if _security_group_rule_keys(instance.get("IpPermissions", [])):
        raise CloudManifestError("instance security group must have no ingress")
    if _security_group_rule_keys(instance.get("IpPermissionsEgress", [])) != {instance_pair}:
        raise CloudManifestError("instance security group egress is not the exact endpoint TCP/443 rule")


def validate_action_id(action_id: str) -> None:
    if not ACTION_ID_RE.fullmatch(action_id):
        raise CloudManifestError(
            "action_id must use the immutable FIXTURE-NONSCI-YYYYMMDD-v2-xxxxxxxx namespace"
        )


@dataclass(frozen=True, slots=True)
class AwsSurfaceConfig:
    action_id: str
    region: str
    input_lock_sha256: str
    harness_sha256: str
    harness_bytes_b64: str
    image_refs: Mapping[str, str]
    image_digests: Mapping[str, str]
    provider_binding_sha256: str
    source_commit: str
    evidence_dir: Path | None = None
    vpc_id: str = VPC_ID
    availability_zone: str = AVAILABILITY_ZONE
    subnet_cidr: str = SUBNET_CIDR
    ami_id: str = AMI_ID


def _fixed_ssm_document() -> dict[str, object]:
    return {
        "schemaVersion": "2.2",
        "description": "Pneuma FIXTURE-NONSCI v2 fixed status observation; no caller parameters",
        "parameters": {},
        "mainSteps": [
            {
                "action": "aws:runShellScript",
                "name": "readFixedSurfaceStatus",
                "inputs": {
                    "runCommand": [
                        "set -eu",
                        "if test -f /var/lib/pneuma-surface/status.json; then /usr/bin/cat /var/lib/pneuma-surface/status.json; else /usr/bin/printf '%s\\n' '{\"terminal\":false,\"state\":\"WAITING\"}'; fi",
                    ]
                },
            }
        ],
    }


def render_surface_user_data(
    config: AwsSurfaceConfig,
    *,
    endpoint_host_bindings: Mapping[str, str] | None = None,
) -> str:
    """Render bootstrap that cannot install packages or receive science inputs."""

    refs = {role: config.image_refs[role] for role in ("controller", "model-server", "benchmark-worker")}
    encoded_refs = base64.b64encode(_canonical(refs)).decode("ascii")
    registry = next(iter(refs.values())).split("/", 1)[0]
    host_lines = ""
    if endpoint_host_bindings is not None:
        if not endpoint_host_bindings:
            raise CloudManifestError("action endpoint host bindings cannot be empty")
        grouped: dict[str, list[str]] = {}
        for host, address in sorted(endpoint_host_bindings.items()):
            if not re.fullmatch(r"[A-Za-z0-9.*-]+", host) or host.startswith(".") or host.endswith("."):
                raise CloudManifestError("action endpoint host binding contains an invalid hostname")
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as exc:
                raise CloudManifestError("action endpoint host binding contains an invalid address") from exc
            if parsed.version != 4 or not parsed.is_private or parsed.is_loopback or parsed.is_link_local:
                raise CloudManifestError("action endpoint host binding must use a private non-loopback IPv4 address")
            grouped.setdefault(address, []).append(host)
        host_lines = "\n# Action-owned endpoint bindings; no public DNS or general egress is permitted.\n"
        host_lines += "\n".join(f"{address}\t{' '.join(hosts)}" for address, hosts in sorted(grouped.items()))
        host_lines += "\n"
    initial_status = {
        "record_kind": "cloud_production_surface_provider_status",
        "schema_version": "0.2.0",
        "action_id": config.action_id,
        "evidence_class": "production_surface_non_scientific",
        "fixture_mode": "FIXTURE-NONSCI",
        "authority": "none",
        "terminal": False,
        "state": "BOOTSTRAPPING",
        "model_download": False,
        "benchmark_execution": False,
        "official_study": False,
        "canonical_p0_grid": False,
        "roster_ceremony": False,
        "unblind": False,
        "analysis": False,
    }
    initial_json = _json(initial_status)
    return f"""#!/bin/bash
set -euo pipefail
export HOME=/root
ACTION={config.action_id!r}
ROOT=/var/lib/pneuma-surface
REGISTRY={registry!r}
cat >> /etc/hosts <<'HOSTS'
{host_lines}HOSTS
mkdir -p "$ROOT/roles"
chmod 700 "$ROOT"
echo {config.harness_bytes_b64!r} | base64 -d > "$ROOT/harness.json"
chmod 644 "$ROOT/harness.json"
cat > "$ROOT/status.json" <<'JSON'
{initial_json}
JSON

# The bound ECS image must already contain Docker, the AWS CLI, Python, and
# the SSM agent.  Internet package installation is forbidden in this lane.
command -v docker >/dev/null 2>&1
command -v aws >/dev/null 2>&1
command -v python3 >/dev/null 2>&1
systemctl enable --now docker
echo {encoded_refs!r} | base64 -d > "$ROOT/image-refs.json"
aws ecr get-login-password --region {config.region!r} | docker login --username AWS --password-stdin "$REGISTRY"
for role in controller model-server benchmark-worker; do
  image=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$ROOT/image-refs.json" "$role")
  docker pull "$image"
  docker image inspect "$image" --format '{{{{json .RepoDigests}}}}' | grep -F "$image" >/dev/null
done

run_role() {{
  local role="$1"
  local image
  image=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$ROOT/image-refs.json" "$role")
  local input_arg=()
  if [[ "$role" == "model-server" ]]; then input_arg=(--volume "$ROOT/roles/controller.json:/work/predecessor.json:ro"); fi
  if [[ "$role" == "benchmark-worker" ]]; then input_arg=(--volume "$ROOT/roles/model-server.json:/work/predecessor.json:ro"); fi
  local role_input=()
  if [[ "$role" != "controller" ]]; then role_input=(--input /work/predecessor.json); fi
  timeout 300 docker run --rm --network none --read-only --tmpfs /tmp --cap-drop ALL --pids-limit 128 --security-opt no-new-privileges --user 65532:65532 \\
    --volume "$ROOT/harness.json:/work/harness.json:ro" "${{input_arg[@]}}" "$image" \\
    --protocol e2e --harness /work/harness.json --harness-sha256 {config.harness_sha256!r} "${{role_input[@]}}" > "$ROOT/roles/$role.json"
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$ROOT/roles/$role.json"
}}

for role in controller model-server benchmark-worker; do run_role "$role"; done

for role in controller model-server benchmark-worker; do
  image=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$ROOT/image-refs.json" "$role")
  set +e
  timeout 120 docker run --rm --network none --read-only --tmpfs /tmp --cap-drop ALL --pids-limit 128 --security-opt no-new-privileges --user 65532:65532 \\
    --volume "$ROOT/harness.json:/work/harness.json:ro" "$image" \\
    --protocol e2e --harness /work/harness.json --harness-sha256 {'0' * 64} > "$ROOT/roles/$role-wrong-hash.json"
  rc=$?
  set -e
  [[ "$rc" == "2" ]] || exit 31
  python3 -c 'import json,sys; value=json.load(open(sys.argv[1])); assert value.get("state")=="FAILED" and value.get("reason")=="harness_sha256_mismatch"' "$ROOT/roles/$role-wrong-hash.json"
done
rm -f "$ROOT/image-refs.json" /root/.docker/config.json

python3 - "$ROOT/status.json" "$ROOT/roles" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
roles = pathlib.Path(sys.argv[2])
receipts = {{}}
failure_receipts = {{}}
for role in ("controller", "model-server", "benchmark-worker"):
    raw = (roles / f"{{role}}.json").read_bytes()
    receipts[role] = {{"sha256": hashlib.sha256(raw).hexdigest(), "record": json.loads(raw.decode())}}
    wrong = (roles / f"{{role}}-wrong-hash.json").read_bytes()
    failure_receipts[role] = {{"sha256": hashlib.sha256(wrong).hexdigest(), "record": json.loads(wrong.decode())}}
status = {{
    "record_kind": "cloud_production_surface_provider_status",
    "schema_version": "0.2.0",
    "action_id": {json.dumps(config.action_id)},
    "evidence_class": "production_surface_non_scientific",
    "fixture_mode": "FIXTURE-NONSCI",
    "authority": "none",
    "terminal": True,
    "state": "SUCCEEDED",
    "model_download": False,
    "benchmark_execution": False,
    "official_study": False,
    "canonical_p0_grid": False,
    "roster_ceremony": False,
    "unblind": False,
    "analysis": False,
    "network_none": True,
    "credential_free_containers": True,
    "docker_socket_absent": True,
    "receipts": receipts,
    "failure_receipts": failure_receipts,
}}
root.write_bytes((json.dumps(status, sort_keys=True, separators=(",", ":")) + "\\n").encode())
PY
chmod 644 "$ROOT/status.json" "$ROOT"/roles/*.json
"""


class AwsSurfaceProvider(ProductionJobProvider):
    """Concrete one-attempt EC2/SSM v2 provider with explicit cleanup."""

    def __init__(self, config: AwsSurfaceConfig) -> None:
        validate_action_id(config.action_id)
        if (config.region, config.vpc_id, config.availability_zone, config.subnet_cidr, config.ami_id) != (REGION, VPC_ID, AVAILABILITY_ZONE, SUBNET_CIDR, AMI_ID):
            raise CloudManifestError("surface provider binding differs from the registered private action deployment")
        if not re.fullmatch(r"[0-9a-f]{40}", config.source_commit):
            raise CloudManifestError("surface source_commit must be one full lowercase commit")
        if not _DIGEST_RE.fullmatch("sha256:" + config.input_lock_sha256):
            raise CloudManifestError("surface input lock digest is invalid")
        if set(config.image_refs) != {"controller", "model-server", "benchmark-worker"}:
            raise CloudManifestError("surface image refs must cover exactly the three roles")
        if set(config.image_digests) != set(config.image_refs) or any(
            not _DIGEST_RE.fullmatch(str(value)) for value in config.image_digests.values()
        ):
            raise CloudManifestError("surface image bindings must use immutable OCI digests")
        account_ids = set()
        for role, image_ref in config.image_refs.items():
            match = re.fullmatch(r"([0-9]{12})\.dkr\.ecr\.us-east-1\.amazonaws\.com/pneuma-official-production-(controller|model-server|benchmark-worker)@(sha256:[0-9a-f]{64})", image_ref)
            if match is None or match.group(2) != role or match.group(3) != config.image_digests[role]:
                raise CloudManifestError("surface image refs must bind each exact production role to its digest")
            account_ids.add(match.group(1))
        if len(account_ids) != 1:
            raise CloudManifestError("surface images must belong to one exact AWS account")
        self.config = config
        boto3 = _boto3()
        self.ec2 = boto3.client("ec2", region_name=config.region)
        self.iam = boto3.client("iam", region_name=config.region)
        self.ssm = boto3.client("ssm", region_name=config.region)
        self.sts = boto3.client("sts", region_name=config.region)
        self.submission: ProductionSubmission | None = None
        self.instance_id: str | None = None
        self.subnet_id: str | None = None
        self.route_table_id: str | None = None
        self.route_association_id: str | None = None
        self.instance_security_group_id: str | None = None
        self.endpoint_security_group_id: str | None = None
        self.endpoint_ids: dict[str, str] = {}
        self.endpoint_network_interface_ids: list[str] = []
        self.endpoint_host_bindings: dict[str, str] = {}
        self.s3_endpoint_id: str | None = None
        self.instance_volume_ids: list[str] = []
        self.instance_network_interface_ids: list[str] = []
        self.command_id: str | None = None
        self.last_status: Mapping[str, Any] | None = None
        self.last_teardown: Mapping[str, Any] | None = None
        self.provider_responses: list[dict[str, object]] = []
        self.attempt_closed = False
        self.launch_epoch: float | None = None
        self.external_deadline_epoch: float | None = None
        self.ssm_online_seen = False
        self.watchdog: subprocess.Popen[bytes] | None = None
        self.watchdog_pid: int | None = None
        self.watchdog_source_sha256: str | None = None
        self.role_name = _name(f"pneuma-surface-v2-role-{config.action_id}")
        self.profile_name = _name(f"pneuma-surface-v2-profile-{config.action_id}")
        self.profile_arn: str | None = None
        self.policy_name = _name(f"pneuma-surface-v2-ecr-{config.action_id}")
        self.document_name = _name(f"pneuma-surface-v2-status-{config.action_id}")
        self.document_version = "1"
        self.document_sha256: str | None = None
        self.document_provider_hash: str | None = None
        if config.evidence_dir is not None:
            config.evidence_dir.mkdir(parents=True, exist_ok=True)

    def _record(self, operation: str, response: object) -> object:
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operation": operation,
            "response": _jsonable(response),
        }
        raw = _canonical(payload)
        digest = _sha_bytes(raw)
        entry: dict[str, object] = {"operation": operation, "sha256": digest, "recorded_at": payload["recorded_at"]}
        if self.config.evidence_dir is not None:
            index = len(self.provider_responses)
            path = self.config.evidence_dir / "provider-raw" / f"{index:04d}-{_name(operation, max_length=48)}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            descriptor = os.open(path, flags, 0o644)
            try:
                view = memoryview(raw)
                while view:
                    view = view[os.write(descriptor, view):]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            entry["path"] = path.name if path.parent == self.config.evidence_dir else path.relative_to(self.config.evidence_dir).as_posix()
        self.provider_responses.append(entry)
        return response

    def _call(self, operation: str, function: Callable[..., object], **kwargs: object) -> Any:
        try:
            return self._record(operation, function(**kwargs))
        except Exception as exc:
            self._record(operation + ".error", {"type": type(exc).__name__, "message": str(exc), "response": _jsonable(getattr(exc, "response", {}))})
            raise

    def _tags(self, **extra: str) -> list[dict[str, str]]:
        values = {ACTION_TAG: self.config.action_id, "PneumaManaged": MANAGED_TAG, "PneumaEvidenceClass": "non-scientific", **extra}
        return [{"Key": key, "Value": value} for key, value in sorted(values.items())]

    def _resource_tags(self, resource_ids: Sequence[str]) -> None:
        deadline = time.time() + 30
        eventual_codes = (
            "InvalidGroup.NotFound",
            "InvalidInstanceID.NotFound",
            "InvalidNetworkInterfaceID.NotFound",
            "InvalidRouteTableID.NotFound",
            "InvalidSubnetID.NotFound",
            "InvalidVpcEndpoint.NotFound",
            "InvalidVpcEndpointId.NotFound",
        )
        while True:
            try:
                self._call("create_tags", self.ec2.create_tags, Resources=list(resource_ids), Tags=self._tags())
                return
            except Exception as exc:
                if not _absent(exc, *eventual_codes) or time.time() >= deadline:
                    raise
                time.sleep(2)

    def _all_tagged(self, resource_type: str) -> list[dict[str, object]]:
        if resource_type == "instances":
            response = self._call("describe_instances.tagged", self.ec2.describe_instances, Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [self.config.action_id]}])
            return [instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", [])]
        if resource_type == "security_groups":
            return list(self._call("describe_security_groups.tagged", self.ec2.describe_security_groups, Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [self.config.action_id]}]).get("SecurityGroups", []))
        if resource_type == "subnets":
            return list(self._call("describe_subnets.tagged", self.ec2.describe_subnets, Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [self.config.action_id]}]).get("Subnets", []))
        if resource_type == "route_tables":
            return list(self._call("describe_route_tables.tagged", self.ec2.describe_route_tables, Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [self.config.action_id]}]).get("RouteTables", []))
        if resource_type == "endpoints":
            return list(self._call("describe_vpc_endpoints.tagged", self.ec2.describe_vpc_endpoints, Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [self.config.action_id]}, {"Name": "vpc-id", "Values": [self.config.vpc_id]}]).get("VpcEndpoints", []))
        return []

    def _active_instance(self) -> str | None:
        instances = self._all_tagged("instances")
        active = [item for item in instances if item.get("State", {}).get("Name") not in {"terminated", "shutting-down"}]
        if len(active) > 1:
            raise CloudManifestError("multiple active instances share one immutable surface action")
        if active:
            instance_id = active[0].get("InstanceId")
            if not isinstance(instance_id, str):
                raise CloudManifestError("tagged active instance has no ID")
            return instance_id
        if instances and any(item.get("State", {}).get("Name") == "terminated" for item in instances):
            raise CloudManifestError("surface action was already consumed; refusing a second attempt")
        return None

    def _verify_vpc(self) -> None:
        vpcs = self._call("describe_vpcs", self.ec2.describe_vpcs, VpcIds=[self.config.vpc_id]).get("Vpcs", [])
        if len(vpcs) != 1 or vpcs[0].get("State") != "available" or vpcs[0].get("CidrBlock") != "10.42.0.0/16" or vpcs[0].get("IsDefault") is True:
            raise CloudManifestError("provider VPC binding is not the registered private non-default VPC")
        attributes = [self._call("describe_vpc_attribute.dns_support", self.ec2.describe_vpc_attribute, VpcId=self.config.vpc_id, Attribute="enableDnsSupport"), self._call("describe_vpc_attribute.dns_hostnames", self.ec2.describe_vpc_attribute, VpcId=self.config.vpc_id, Attribute="enableDnsHostnames")]
        if not (
            self._vpc_attribute_enabled(attributes[0], "EnableDnsSupport")
            and self._vpc_attribute_enabled(attributes[1], "EnableDnsHostnames")
        ):
            raise CloudManifestError("private action subnet requires VPC DNS support and hostnames")
        igws = self._call("describe_internet_gateways", self.ec2.describe_internet_gateways, Filters=[{"Name": "attachment.vpc-id", "Values": [self.config.vpc_id]}]).get("InternetGateways", [])
        nats = self._call("describe_nat_gateways", self.ec2.describe_nat_gateways, Filter=[{"Name": "vpc-id", "Values": [self.config.vpc_id]}, {"Name": "state", "Values": ["pending", "available", "deleting"]}]).get("NatGateways", [])
        transit = self._call("describe_transit_gateway_attachments", self.ec2.describe_transit_gateway_attachments, Filters=[{"Name": "resource-id", "Values": [self.config.vpc_id]}]).get("TransitGatewayAttachments", [])
        if igws or nats or transit:
            raise CloudManifestError("provider VPC has an internet, NAT, or transit attachment")

    @staticmethod
    def _vpc_attribute_enabled(response: Mapping[str, object], key: str) -> bool:
        value = response.get(key)
        if isinstance(value, Mapping):
            value = value.get("Value")
        return value is True

    def _find_or_create_security_groups(self) -> None:
        self.endpoint_security_group_id = cast(str, self._call("create_security_group.endpoint", self.ec2.create_security_group, GroupName=_name(f"pneuma-surface-v2-endpoints-{self.config.action_id}"), Description="Pneuma FIXTURE-NONSCI v2 endpoint SG", VpcId=self.config.vpc_id)["GroupId"])
        self.instance_security_group_id = cast(str, self._call("create_security_group.instance", self.ec2.create_security_group, GroupName=_name(f"pneuma-surface-v2-instance-{self.config.action_id}"), Description="Pneuma FIXTURE-NONSCI v2 instance SG", VpcId=self.config.vpc_id)["GroupId"])
        self._resource_tags([self.endpoint_security_group_id, self.instance_security_group_id])
        for group_id in (self.endpoint_security_group_id, self.instance_security_group_id):
            rules = self._call("describe_security_groups.rules", self.ec2.describe_security_groups, GroupIds=[group_id])["SecurityGroups"][0].get("IpPermissionsEgress", [])
            if rules:
                self._call("revoke_security_group_egress", self.ec2.revoke_security_group_egress, GroupId=group_id, IpPermissions=rules)
        self._call("authorize_endpoint_ingress", self.ec2.authorize_security_group_ingress, GroupId=self.endpoint_security_group_id, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "UserIdGroupPairs": [{"GroupId": self.instance_security_group_id}]}])
        self._call("authorize_endpoint_service_egress", self.ec2.authorize_security_group_egress, GroupId=self.endpoint_security_group_id, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        self._call("authorize_instance_endpoint_egress", self.ec2.authorize_security_group_egress, GroupId=self.instance_security_group_id, IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "UserIdGroupPairs": [{"GroupId": self.endpoint_security_group_id}]}])
        self._verify_security_group_contract()

    def _verify_security_group_contract(self) -> None:
        if not self.endpoint_security_group_id or not self.instance_security_group_id:
            raise CloudManifestError("surface security-group IDs are missing")
        groups = self._call(
            "verify_security_group_contract",
            self.ec2.describe_security_groups,
            GroupIds=[self.endpoint_security_group_id, self.instance_security_group_id],
        ).get("SecurityGroups", [])
        if not isinstance(groups, Sequence):
            raise CloudManifestError("surface security-group readback is malformed")
        _validate_surface_security_group_contract(
            [group for group in groups if isinstance(group, Mapping)],
            endpoint_group_id=self.endpoint_security_group_id,
            instance_group_id=self.instance_security_group_id,
        )

    def _endpoint_policy(self, service: str) -> dict[str, object]:
        account = self.config.image_refs["controller"].split(".", 1)[0]
        repos = [f"arn:aws:ecr:{REGION}:{account}:repository/pneuma-official-production-{role}" for role in ("controller", "model-server", "benchmark-worker")]
        if service == "s3":
            statement = [{"Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject"], "Resource": "arn:aws:s3:::prod-us-east-1-starport-layer-bucket/*"}]
        elif service in {"ecr.api", "ecr.dkr"}:
            actions = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
            statement: list[dict[str, object]] = [{"Effect": "Allow", "Principal": "*", "Action": actions, "Resource": repos}]
            # AWS recommends the same pull policy on both ECR interface
            # endpoints.  Docker authenticates against the registry endpoint
            # after the CLI obtains its token from the API endpoint; omitting
            # GetAuthorizationToken from ecr.dkr makes that registry handshake
            # fail closed (observed as a client-side TLS timeout).
            if service in {"ecr.api", "ecr.dkr"}:
                statement.append({"Effect": "Allow", "Principal": "*", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"})
        elif service == "ssm":
            statement = [{"Effect": "Allow", "Principal": "*", "Action": ["ssm:UpdateInstanceInformation", "ssm:GetDeployablePatchSnapshotForInstance", "ssm:GetManifest", "ssm:GetParameter", "ssm:GetParameters", "ssm:ListAssociations", "ssm:ListInstanceAssociations", "ssm:PutInventory", "ssm:PutComplianceItems", "ssm:PutConfigurePackageResult", "ssm:UpdateAssociationStatus", "ssm:UpdateInstanceAssociationStatus"], "Resource": "*"}]
        elif service == "ssmmessages":
            statement = [{"Effect": "Allow", "Principal": "*", "Action": ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], "Resource": "*"}]
        else:
            statement = [{"Effect": "Allow", "Principal": "*", "Action": ["ec2messages:AcknowledgeMessage", "ec2messages:DeleteMessage", "ec2messages:FailMessage", "ec2messages:GetEndpoint", "ec2messages:GetMessages", "ec2messages:SendReply"], "Resource": "*"}]
        return {"Version": "2012-10-17", "Statement": statement}

    def _capture_endpoint_bindings(self) -> None:
        endpoint_ids = list(self.endpoint_ids.values())
        response = self._call(
            "describe_action_endpoint_details",
            self.ec2.describe_vpc_endpoints,
            VpcEndpointIds=endpoint_ids,
        )
        endpoints = response.get("VpcEndpoints", [])
        if len(endpoints) != len(endpoint_ids) or any(
            endpoint.get("State") != "available"
            or endpoint.get("VpcId") != self.config.vpc_id
            or endpoint.get("PrivateDnsEnabled") is not True
            for endpoint in endpoints
        ):
            raise CloudManifestError("action interface endpoints did not satisfy the private-DNS-disabled binding")
        network_interface_ids: list[str] = []
        endpoint_service_interfaces: dict[str, list[str]] = {}
        for endpoint in endpoints:
            service_name = str(endpoint.get("ServiceName", ""))
            service = next((name for name in INTERFACE_SERVICES if service_name.endswith("." + name)), None)
            interfaces = [value for value in endpoint.get("NetworkInterfaceIds", []) if isinstance(value, str)]
            groups = {item.get("GroupId") for item in endpoint.get("Groups", []) if isinstance(item, Mapping)}
            try:
                policy = json.loads(str(endpoint.get("PolicyDocument", "")))
            except json.JSONDecodeError as exc:
                raise CloudManifestError("action interface endpoint policy is not JSON") from exc
            if (
                service is None
                or len(interfaces) != 1
                or endpoint.get("SubnetIds") != [self.subnet_id]
                or groups != {self.endpoint_security_group_id}
                or policy != self._endpoint_policy(service)
            ):
                raise CloudManifestError("each action interface endpoint must have exactly one ENI")
            network_interface_ids.extend(interfaces)
            endpoint_service_interfaces[service] = interfaces
        if len(network_interface_ids) != len(endpoint_ids) or set(endpoint_service_interfaces) != set(INTERFACE_SERVICES):
            raise CloudManifestError("action interface endpoint ENI set is incomplete")
        interface_response = self._call(
            "describe_action_endpoint_network_interfaces",
            self.ec2.describe_network_interfaces,
            NetworkInterfaceIds=network_interface_ids,
        )
        interfaces = interface_response.get("NetworkInterfaces", [])
        by_id = {item.get("NetworkInterfaceId"): item for item in interfaces}
        if len(by_id) != len(network_interface_ids):
            raise CloudManifestError("action endpoint ENI readback is incomplete")
        ips: dict[str, str] = {}
        for service, ids in endpoint_service_interfaces.items():
            item = by_id.get(ids[0])
            if not isinstance(item, Mapping) or item.get("VpcId") != self.config.vpc_id or item.get("SubnetId") != self.subnet_id:
                raise CloudManifestError("action endpoint ENI is outside the bound private subnet")
            address = item.get("PrivateIpAddress")
            if not isinstance(address, str):
                raise CloudManifestError("action endpoint ENI has no private IPv4 address")
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as exc:
                raise CloudManifestError("action endpoint ENI private address is malformed") from exc
            if parsed.version != 4 or not parsed.is_private or parsed.is_loopback or parsed.is_link_local or item.get("Association"):
                raise CloudManifestError("action endpoint ENI has a public, non-IPv4, or associated address")
            ips[service] = address
        registry = next(iter(self.config.image_refs.values())).split("/", 1)[0]
        hosts = {
            "ecr.api": ("api.ecr.us-east-1.amazonaws.com", "ecr.us-east-1.api.aws"),
            "ecr.dkr": (registry,),
            "ssm": ("ssm.us-east-1.amazonaws.com", "ssm.us-east-1.api.aws"),
            "ssmmessages": ("ssmmessages.us-east-1.amazonaws.com", "ssmmessages.us-east-1.api.aws"),
            "ec2messages": ("ec2messages.us-east-1.amazonaws.com",),
        }
        self.endpoint_network_interface_ids = network_interface_ids
        self.endpoint_host_bindings = {host: ips[service] for service, names in hosts.items() for host in names}

    def _create_network(self) -> None:
        self._verify_vpc()
        subnet = self._call("create_subnet", self.ec2.create_subnet, VpcId=self.config.vpc_id, CidrBlock=self.config.subnet_cidr, AvailabilityZone=self.config.availability_zone)
        self.subnet_id = cast(str, subnet["Subnet"]["SubnetId"])
        self._resource_tags([self.subnet_id])
        self._call("modify_subnet_no_public_ipv4", self.ec2.modify_subnet_attribute, SubnetId=self.subnet_id, MapPublicIpOnLaunch={"Value": False})
        self.route_table_id = cast(str, self._call("create_route_table", self.ec2.create_route_table, VpcId=self.config.vpc_id)["RouteTable"]["RouteTableId"])
        self._resource_tags([self.route_table_id])
        association = self._call("associate_route_table", self.ec2.associate_route_table, RouteTableId=self.route_table_id, SubnetId=self.subnet_id)
        self.route_association_id = cast(str, association["AssociationId"])
        s3 = self._call("create_s3_gateway_endpoint", self.ec2.create_vpc_endpoint, VpcEndpointType="Gateway", VpcId=self.config.vpc_id, ServiceName=f"com.amazonaws.{REGION}.s3", RouteTableIds=[self.route_table_id], PolicyDocument=_json(self._endpoint_policy("s3")))
        self.s3_endpoint_id = cast(str, s3["VpcEndpoint"]["VpcEndpointId"])
        self._resource_tags([self.s3_endpoint_id])
        self._find_or_create_security_groups()
        for service in INTERFACE_SERVICES:
            response = self._call(f"create_interface_endpoint.{service}", self.ec2.create_vpc_endpoint, VpcEndpointType="Interface", VpcId=self.config.vpc_id, ServiceName=f"com.amazonaws.{REGION}.{service}", SubnetIds=[self.subnet_id], SecurityGroupIds=[self.endpoint_security_group_id], PrivateDnsEnabled=True, PolicyDocument=_json(self._endpoint_policy(service)))
            self.endpoint_ids[service] = cast(str, response["VpcEndpoint"]["VpcEndpointId"])
            self._resource_tags([self.endpoint_ids[service]])
        deadline = time.time() + 180
        while time.time() < deadline:
            states = self._call("describe_action_endpoints", self.ec2.describe_vpc_endpoints, VpcEndpointIds=list(self.endpoint_ids.values())).get("VpcEndpoints", [])
            if len(states) == len(self.endpoint_ids) and all(item.get("State") == "available" for item in states):
                break
            if any(item.get("State") in {"failed", "deleted", "deleting"} for item in states):
                raise CloudManifestError("action interface endpoint failed admission")
            time.sleep(5)
        else:
            raise CloudManifestError("action interface endpoints did not become available")
        self._capture_endpoint_bindings()
        route_tables = self._call("verify_action_route_table", self.ec2.describe_route_tables, RouteTableIds=[self.route_table_id])["RouteTables"]
        routes = route_tables[0].get("Routes", [])
        if any(route.get("GatewayId", "").startswith(("igw-", "nat-", "tgw-")) or route.get("NatGatewayId") or route.get("TransitGatewayId") for route in routes):
            raise CloudManifestError("action route table contains general internet or transit egress")
        if not any(route.get("DestinationPrefixListId") == "pl-63a5400a" and route.get("GatewayId") == self.s3_endpoint_id for route in routes):
            raise CloudManifestError("action route table lacks its exact S3 gateway route")

    def _iam_policy(self) -> dict[str, object]:
        account = self.config.image_refs["controller"].split(".", 1)[0]
        resources = [f"arn:aws:ecr:{REGION}:{account}:repository/pneuma-official-production-{role}" for role in ("controller", "model-server", "benchmark-worker")]
        return {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
                {"Effect": "Allow", "Action": ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"], "Resource": resources},
                {"Effect": "Allow", "Action": ["ssm:DescribeAssociation", "ssm:GetDeployablePatchSnapshotForInstance", "ssm:GetDocument", "ssm:DescribeDocument", "ssm:GetManifest", "ssm:GetParameter", "ssm:GetParameters", "ssm:ListAssociations", "ssm:ListInstanceAssociations", "ssm:PutInventory", "ssm:PutComplianceItems", "ssm:PutConfigurePackageResult", "ssm:UpdateAssociationStatus", "ssm:UpdateInstanceAssociationStatus", "ssm:UpdateInstanceInformation"], "Resource": "*"},
                {"Effect": "Allow", "Action": ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], "Resource": "*"},
                {"Effect": "Allow", "Action": ["ec2messages:AcknowledgeMessage", "ec2messages:DeleteMessage", "ec2messages:FailMessage", "ec2messages:GetEndpoint", "ec2messages:GetMessages", "ec2messages:SendReply"], "Resource": "*"},
            ],
        }

    def _create_iam(self) -> None:
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
        self._call("create_role", self.iam.create_role, RoleName=self.role_name, AssumeRolePolicyDocument=_json(trust), Description="Pneuma FIXTURE-NONSCI v2 role; no scientific inputs")
        self._call("put_role_policy", self.iam.put_role_policy, RoleName=self.role_name, PolicyName=self.policy_name, PolicyDocument=_json(self._iam_policy()))
        created = self._call("create_instance_profile", self.iam.create_instance_profile, InstanceProfileName=self.profile_name)
        created_profile = created.get("InstanceProfile", {})
        profile_arn = created_profile.get("Arn")
        if not isinstance(profile_arn, str) or not profile_arn.endswith(f"instance-profile/{self.profile_name}"):
            raise CloudManifestError("IAM instance profile ARN did not bind the exact action profile")
        self.profile_arn = profile_arn
        self._call("add_role_to_instance_profile", self.iam.add_role_to_instance_profile, InstanceProfileName=self.profile_name, RoleName=self.role_name)
        self._call("tag_role", self.iam.tag_role, RoleName=self.role_name, Tags=self._tags())
        self._call("tag_instance_profile", self.iam.tag_instance_profile, InstanceProfileName=self.profile_name, Tags=self._tags())
        deadline = time.time() + 60
        while time.time() < deadline:
            profile = self._call("get_instance_profile", self.iam.get_instance_profile, InstanceProfileName=self.profile_name)["InstanceProfile"]
            if profile.get("Arn") != self.profile_arn:
                raise CloudManifestError("IAM instance profile readback changed its immutable ARN")
            roles = profile.get("Roles", [])
            if any(item.get("RoleName") == self.role_name for item in roles):
                return
            time.sleep(2)
        raise CloudManifestError("IAM instance profile did not become launchable before the one submit")

    def _create_ssm_document(self) -> None:
        content = _fixed_ssm_document()
        raw = _canonical(content)
        self.document_sha256 = _sha_bytes(raw)
        created = self._call("create_ssm_document", self.ssm.create_document, Content=raw.decode("utf-8"), Name=self.document_name, DocumentType="Command", DocumentFormat="JSON", TargetType="/AWS::EC2::Instance", Tags=self._tags())
        provider_hash = created.get("DocumentDescription", {}).get("Hash")
        if not isinstance(provider_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", provider_hash):
            raise CloudManifestError("custom SSM document provider hash is missing or malformed")
        self.document_provider_hash = provider_hash
        document = self._call("get_ssm_document", self.ssm.get_document, Name=self.document_name, DocumentVersion=self.document_version, DocumentFormat="JSON")
        try:
            returned_content = json.loads(str(document.get("Content", "")))
        except json.JSONDecodeError as exc:
            raise CloudManifestError("custom SSM document content is not JSON") from exc
        if document.get("Status") != "Active" or document.get("DocumentVersion") != self.document_version or returned_content != content:
            raise CloudManifestError("custom SSM document hash/version did not round-trip")
        described = self._call("describe_ssm_document", self.ssm.describe_document, Name=self.document_name, DocumentVersion=self.document_version)
        metadata = described.get("Document", {})
        if metadata.get("Status") != "Active" or metadata.get("DocumentVersion") != self.document_version or metadata.get("Hash") != self.document_provider_hash or metadata.get("HashType") != "Sha256":
            raise CloudManifestError("custom SSM document provider hash/version did not round-trip")

    def _watchdog_path(self) -> Path:
        return Path(__file__).resolve().parents[3] / "scripts/research/fixture_v2_watchdog.py"

    def _start_watchdog(self, *, deadline_epoch: float) -> None:
        path = self._watchdog_path()
        if not path.is_file():
            raise CloudManifestError("durable fixture watchdog source is missing")
        self.watchdog_source_sha256 = _sha_bytes(path.read_bytes())
        command = [os.environ.get("PYTHON", "python3"), str(path), "--region", self.config.region, "--action-id", self.config.action_id, "--deadline-epoch", str(int(deadline_epoch))]
        self.watchdog = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.watchdog_pid = self.watchdog.pid
        time.sleep(0.2)
        if self.watchdog.poll() is not None:
            raise CloudManifestError("external fixture watchdog exited before instance launch")

    def _read_instance(self, instance_id: str, *, require_root_mapping: bool = False) -> Mapping[str, object]:
        deadline = time.time() + INSTANCE_READBACK_TIMEOUT_SECONDS
        while True:
            try:
                response = self._call("describe_instance.effective", self.ec2.describe_instances, InstanceIds=[instance_id])
            except Exception as exc:
                # RunInstances is not replayable.  EC2 can briefly return
                # InvalidInstanceID.NotFound immediately after a successful
                # submit, so only this exact provider condition is retried.
                if not _absent(exc, "InvalidInstanceID.NotFound") or time.time() >= deadline:
                    raise
                time.sleep(INSTANCE_READBACK_RETRY_SECONDS)
                continue
            instances = [instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", [])]
            if len(instances) != 1:
                raise CloudManifestError("effective launch readback did not return exactly one instance")
            instance = cast(Mapping[str, object], instances[0])
            if require_root_mapping:
                mappings = instance.get("BlockDeviceMappings", [])
                root = next((item for item in mappings if isinstance(item, Mapping) and item.get("DeviceName") == AMI_ROOT_DEVICE), None) if isinstance(mappings, Sequence) else None
                ebs = root.get("Ebs") if isinstance(root, Mapping) else None
                if not isinstance(ebs, Mapping) or not isinstance(ebs.get("VolumeId"), str) or not ebs.get("VolumeId"):
                    if time.time() >= deadline:
                        raise CloudManifestError("effective root EBS mapping did not become available")
                    time.sleep(INSTANCE_READBACK_RETRY_SECONDS)
                    continue
            return instance

    def _verify_effective_launch(self, instance_id: str) -> None:
        instance = self._read_instance(instance_id, require_root_mapping=True)
        if instance.get("ImageId") != self.config.ami_id or instance.get("InstanceType") != INSTANCE_TYPE or instance.get("Architecture") != AMI_ARCHITECTURE or instance.get("Placement", {}).get("AvailabilityZone") != self.config.availability_zone or instance.get("ClientToken") is None or instance.get("InstanceLifecycle") not in {None, "normal"}:
            raise CloudManifestError("effective AMI/type/AZ/architecture/client-token binding differs")
        if instance.get("SubnetId") != self.subnet_id or instance.get("VpcId") != self.config.vpc_id or instance.get("PrivateDnsNameOptions", {}).get("HostnameType") not in {None, "ip-name"}:
            raise CloudManifestError("effective private subnet/VPC binding differs")
        if instance.get("PublicIpAddress") is not None or instance.get("Ipv6Address") is not None or instance.get("EnaSupport") is not True:
            raise CloudManifestError("fixture instance has a public or IPv6 address")
        if instance.get("MetadataOptions", {}).get("HttpTokens") != "required" or instance.get("MetadataOptions", {}).get("HttpPutResponseHopLimit") != 1:
            raise CloudManifestError("IMDS hop-limit/token binding differs")
        state = instance.get("State", {}).get("Name")
        if state not in {"pending", "running"}:
            raise CloudManifestError(f"fixture instance entered unexpected state {state!r}")
        profile = instance.get("IamInstanceProfile", {}).get("Arn", "")
        if not str(profile).endswith(f"instance-profile/{self.profile_name}"):
            raise CloudManifestError("effective IAM profile binding differs")
        interfaces = instance.get("NetworkInterfaces", [])
        if len(interfaces) != 1 or interfaces[0].get("Association") or interfaces[0].get("Ipv6Addresses") or not _network_interface_delete_on_termination(interfaces[0]) or interfaces[0].get("Groups", [{}])[0].get("GroupId") != self.instance_security_group_id:
            raise CloudManifestError("effective network interface is not private/action-scoped")
        mappings = instance.get("BlockDeviceMappings", [])
        root = next((item for item in mappings if item.get("DeviceName") == AMI_ROOT_DEVICE), None)
        root_volume_id = self._verify_effective_root_volume(root)
        self.instance_volume_ids = [root_volume_id] + [
            cast(str, item["Ebs"]["VolumeId"])
            for item in mappings
            if item.get("Ebs", {}).get("VolumeId") and item.get("Ebs", {}).get("VolumeId") != root_volume_id
        ]
        self.instance_network_interface_ids = [cast(str, item["NetworkInterfaceId"]) for item in interfaces if item.get("NetworkInterfaceId")]
        self._call("describe_image.effective", self.ec2.describe_images, ImageIds=[self.config.ami_id])

    def _verify_effective_root_volume(self, root: object) -> str:
        if not isinstance(root, Mapping):
            raise CloudManifestError("effective root EBS mapping is missing")
        ebs = root.get("Ebs")
        if not isinstance(ebs, Mapping) or ebs.get("DeleteOnTermination") is not True:
            raise CloudManifestError("effective root EBS deletion binding differs")
        volume_id = ebs.get("VolumeId")
        if not isinstance(volume_id, str) or not volume_id:
            raise CloudManifestError("effective root EBS volume identity is missing")
        response = self._call("describe_volume.effective", self.ec2.describe_volumes, VolumeIds=[volume_id])
        volumes = response.get("Volumes", [])
        if len(volumes) != 1 or volumes[0].get("VolumeId") != volume_id or volumes[0].get("Encrypted") is not True:
            raise CloudManifestError("effective root EBS encryption binding differs")
        return volume_id

    def _probe_run_admission(self, run_kwargs: Mapping[str, object]) -> None:
        deadline = time.time() + 60
        while True:
            try:
                self._call("run_instances.dry_run", self.ec2.run_instances, DryRun=True, **dict(run_kwargs))
            except Exception as exc:
                error = getattr(exc, "response", {}).get("Error", {})
                code = error.get("Code") if isinstance(error, Mapping) else None
                message = error.get("Message", "") if isinstance(error, Mapping) else ""
                if code == "DryRunOperation":
                    return
                if code == "InvalidParameterValue" and "iamInstanceProfile" in str(message) and time.time() < deadline:
                    time.sleep(5)
                    continue
                raise CloudManifestError("fixture RunInstances dry-run admission failed") from exc
            raise CloudManifestError("fixture RunInstances dry-run unexpectedly succeeded")

    def _hydrate(self, instance_id: str) -> None:
        self.instance_id = instance_id
        tagged_subnets = self._all_tagged("subnets")
        tagged_routes = self._all_tagged("route_tables")
        tagged_groups = self._all_tagged("security_groups")
        tagged_endpoints = self._all_tagged("endpoints")
        if len(tagged_subnets) != 1 or len(tagged_routes) != 1 or len(tagged_groups) != 2:
            raise CloudManifestError("restart reconciliation found an incomplete action network")
        self.subnet_id = cast(str, tagged_subnets[0]["SubnetId"])
        self.route_table_id = cast(str, tagged_routes[0]["RouteTableId"])
        self.endpoint_security_group_id = cast(str, next(item["GroupId"] for item in tagged_groups if item.get("Description", "").endswith("endpoint SG")))
        self.instance_security_group_id = cast(str, next(item["GroupId"] for item in tagged_groups if item.get("Description", "").endswith("instance SG")))
        for endpoint in tagged_endpoints:
            if endpoint.get("VpcEndpointType") == "Gateway":
                self.s3_endpoint_id = cast(str, endpoint["VpcEndpointId"])
            else:
                for name in INTERFACE_SERVICES:
                    if str(endpoint.get("ServiceName", "")).endswith("." + name):
                        self.endpoint_ids[name] = cast(str, endpoint["VpcEndpointId"])
        if set(self.endpoint_ids) != set(INTERFACE_SERVICES):
            raise CloudManifestError("restart reconciliation found an incomplete interface endpoint set")
        self._verify_security_group_contract()
        self._capture_endpoint_bindings()
        profile = self._call("get_instance_profile.restart", self.iam.get_instance_profile, InstanceProfileName=self.profile_name).get("InstanceProfile", {})
        profile_arn = profile.get("Arn")
        if not isinstance(profile_arn, str) or not profile_arn.endswith(f"instance-profile/{self.profile_name}"):
            raise CloudManifestError("restart reconciliation found an invalid IAM instance profile ARN")
        self.profile_arn = profile_arn
        self.document_sha256 = _sha_bytes(_canonical(_fixed_ssm_document()))
        described = self._call("describe_ssm_document.restart", self.ssm.describe_document, Name=self.document_name, DocumentVersion=self.document_version)
        metadata = described.get("Document", {})
        provider_hash = metadata.get("Hash")
        if metadata.get("Status") != "Active" or metadata.get("DocumentVersion") != self.document_version or not isinstance(provider_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", provider_hash) or metadata.get("HashType") != "Sha256":
            raise CloudManifestError("restart reconciliation found an invalid custom SSM document binding")
        self.document_provider_hash = provider_hash
        self._verify_effective_launch(instance_id)

    def submit(self, *, client_token: str, allocation: Mapping[str, Sequence[str]]) -> ProductionSubmission:
        if set(allocation) != {"worker-0", "worker-1"}:
            raise CloudManifestError("surface provider requires the canonical two-worker controller allocation shape")
        if len(client_token) > 64 or not re.fullmatch(r"[A-Za-z0-9-]+", client_token):
            raise CloudManifestError("surface client token is not a fixed safe value")
        existing = self._active_instance()
        if existing is not None:
            self._hydrate(existing)
            self.submission = ProductionSubmission(existing, (existing,))
            return self.submission
        self._create_network()
        self._create_iam()
        self._create_ssm_document()
        deadline = time.time() + MAX_DURATION_SECONDS
        self._start_watchdog(deadline_epoch=deadline)
        user_data = render_surface_user_data(self.config, endpoint_host_bindings=self.endpoint_host_bindings)
        tags = self._tags()
        if self.profile_arn is None:
            raise CloudManifestError("verified IAM instance profile ARN is missing before launch")
        run_kwargs: dict[str, object] = {
            "ImageId": self.config.ami_id,
            "InstanceType": INSTANCE_TYPE,
            "MinCount": 1,
            "MaxCount": 1,
            "ClientToken": client_token,
            "IamInstanceProfile": {"Arn": self.profile_arn},
            "NetworkInterfaces": [{"DeviceIndex": 0, "SubnetId": self.subnet_id, "Groups": [self.instance_security_group_id], "AssociatePublicIpAddress": False, "DeleteOnTermination": True}],
            "BlockDeviceMappings": [{"DeviceName": AMI_ROOT_DEVICE, "Ebs": {"VolumeSize": 30, "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
            "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 1},
            "InstanceInitiatedShutdownBehavior": "terminate",
            "UserData": user_data,
            "TagSpecifications": [{"ResourceType": resource_type, "Tags": tags} for resource_type in ("instance", "volume", "network-interface")],
        }
        self._probe_run_admission(run_kwargs)
        # Exactly one RunInstances call. Eventual consistency is handled before
        # this point, never by replaying a potentially successful submission.
        response = self._call("run_instances.once", self.ec2.run_instances, **run_kwargs)
        instances = response.get("Instances", [])
        if len(instances) != 1:
            raise CloudManifestError("RunInstances did not return exactly one fixture instance")
        instance_id = cast(str, instances[0]["InstanceId"])
        self.instance_id = instance_id
        self.launch_epoch = time.time()
        self.external_deadline_epoch = deadline
        self._verify_effective_launch(instance_id)
        self.submission = ProductionSubmission(instance_id, (instance_id,))
        return self.submission

    def _ssm_online(self, instance_id: str) -> bool:
        response = self._call("describe_instance_information", self.ssm.describe_instance_information, Filters=[{"Key": "InstanceIds", "Values": [instance_id]}])
        information = response.get("InstanceInformationList", [])
        online = len(information) == 1 and information[0].get("PingStatus") == "Online"
        self.ssm_online_seen = self.ssm_online_seen or online
        return online

    def observe(self, submission: ProductionSubmission) -> Mapping[str, Any]:
        instance_id = submission.parent_job_id
        self.instance_id = instance_id
        if self.external_deadline_epoch is not None and time.time() >= self.external_deadline_epoch:
            raise CloudManifestError("external fixture deadline expired before observation")
        if not self.ssm_online_seen:
            if not self._ssm_online(instance_id):
                return {"terminal": False, "provider_state": "SSM_OFFLINE"}
        if self.command_id is None:
            command = self._call("send_custom_ssm_command", self.ssm.send_command, InstanceIds=[instance_id], DocumentName=self.document_name, DocumentVersion=self.document_version, Parameters={}, TimeoutSeconds=30, MaxConcurrency="1", MaxErrors="0", Comment="Pneuma FIXTURE-NONSCI v2 fixed status observation")
            self.command_id = cast(str, command["Command"]["CommandId"])
        try:
            invocation = self._call("get_custom_ssm_invocation", self.ssm.get_command_invocation, CommandId=self.command_id, InstanceId=instance_id)
        except Exception as exc:
            if _absent(exc, "InvocationDoesNotExist"):
                return {"terminal": False, "provider_state": "SSM_PENDING"}
            raise
        status_name = invocation.get("Status")
        if status_name not in {"Success", "Failed", "TimedOut", "Cancelled"}:
            return {"terminal": False, "provider_state": status_name or "SSM_UNKNOWN"}
        self.command_id = None
        stdout = str(invocation.get("StandardOutputContent", "")).strip()
        try:
            status = json.loads(stdout) if stdout else {"terminal": False, "state": "NO_STATUS"}
        except json.JSONDecodeError:
            status = {"terminal": False, "state": "INVALID_STATUS"}
        if not isinstance(status, Mapping):
            status = {"terminal": False, "state": "INVALID_STATUS"}
        self.last_status = cast(Mapping[str, Any], status)
        terminal = status_name == "Success" and status.get("terminal") is True
        return {"terminal": terminal, "provider_state": status.get("state", status_name), "status_sha256": _sha(dict(status)), "status": dict(status), "ssm_status": status_name}

    def close_attempt(self) -> None:
        self.attempt_closed = True

    def _wait_absent(self, operation: str, getter: Callable[[], Sequence[Mapping[str, object]]], *, timeout: float = 120) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            values = list(getter())
            if not values:
                return
            time.sleep(3)
        raise CloudManifestError(f"cleanup did not reach terminal absence for {operation}")

    def _volumes_present(self) -> Sequence[Mapping[str, object]]:
        if not self.instance_volume_ids:
            return []
        try:
            response = self._call("describe_action_volumes", self.ec2.describe_volumes, VolumeIds=list(self.instance_volume_ids))
        except Exception as exc:
            if _absent(exc, "InvalidVolume.NotFound", "InvalidVolumeID.NotFound"):
                return []
            raise
        return cast(Sequence[Mapping[str, object]], response.get("Volumes", []))

    def _network_interfaces_present(self) -> Sequence[Mapping[str, object]]:
        network_interface_ids = self.instance_network_interface_ids + self.endpoint_network_interface_ids
        if not network_interface_ids:
            return []
        try:
            response = self._call("describe_action_network_interfaces", self.ec2.describe_network_interfaces, NetworkInterfaceIds=list(dict.fromkeys(network_interface_ids)))
        except Exception as exc:
            if _absent(exc, "InvalidNetworkInterfaceID.NotFound"):
                return []
            raise
        return cast(Sequence[Mapping[str, object]], response.get("NetworkInterfaces", []))

    def _instance_network_interfaces_present(self) -> Sequence[Mapping[str, object]]:
        if not self.instance_network_interface_ids:
            return []
        try:
            response = self._call(
                "describe_instance_network_interfaces",
                self.ec2.describe_network_interfaces,
                NetworkInterfaceIds=list(dict.fromkeys(self.instance_network_interface_ids)),
            )
        except Exception as exc:
            if _absent(exc, "InvalidNetworkInterfaceID.NotFound"):
                return []
            raise
        return cast(Sequence[Mapping[str, object]], response.get("NetworkInterfaces", []))

    def _confirm_instance_terminal(self, instance_id: str) -> bool:
        """Confirm that an instance is absent or in EC2's terminal state.

        The EC2 waiter can observe ``pending`` and then lose the resource while
        the delete propagates.  A second, explicit read is required before
        treating that narrow race as successful cleanup; other observation
        failures remain cleanup failures.
        """

        try:
            response = self._call("confirm_instance_terminated", self.ec2.describe_instances, InstanceIds=[instance_id])
        except Exception as exc:
            if _absent(exc, "InvalidInstanceID.NotFound"):
                return True
            raise
        instances = [instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", [])]
        if not instances:
            return True
        return all(instance.get("State", {}).get("Name") == "terminated" for instance in instances)

    def _wait_instance_terminated(self, instance_id: str) -> None:
        try:
            self._call(
                "wait_instance_terminated",
                self.ec2.get_waiter("instance_terminated").wait,
                InstanceIds=[instance_id],
                WaiterConfig={"Delay": 5, "MaxAttempts": 36},
            )
        except Exception as exc:
            if _absent(exc, "InvalidInstanceID.NotFound"):
                return
            deadline = time.time() + INSTANCE_TERMINATION_CONFIRM_TIMEOUT_SECONDS
            while True:
                if self._confirm_instance_terminal(instance_id):
                    return
                if time.time() >= deadline:
                    raise exc
                time.sleep(INSTANCE_TERMINATION_CONFIRM_RETRY_SECONDS)

    def _stop_watchdog(self) -> None:
        if self.watchdog is None:
            return
        if self.watchdog.poll() is None:
            try:
                os.killpg(self.watchdog.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.watchdog.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.watchdog.pid, signal.SIGKILL)
                self.watchdog.wait(timeout=10)
        self.watchdog = None

    def _delete_action_endpoints(self) -> None:
        tagged = self._all_tagged("endpoints")
        tagged_ids = [value for item in tagged if isinstance((value := item.get("VpcEndpointId")), str)]
        ids = list(dict.fromkeys(list(self.endpoint_ids.values()) + ([self.s3_endpoint_id] if self.s3_endpoint_id else []) + tagged_ids))
        for endpoint in tagged:
            self.endpoint_network_interface_ids.extend(
                value for value in endpoint.get("NetworkInterfaceIds", []) if isinstance(value, str)
            )
        self.endpoint_network_interface_ids = list(dict.fromkeys(self.endpoint_network_interface_ids))
        if ids:
            self._call("delete_vpc_endpoints", self.ec2.delete_vpc_endpoints, VpcEndpointIds=ids)
            cleanup_error: Exception | None = None
            try:
                self._wait_absent("VPC endpoints", lambda: self._all_tagged("endpoints"), timeout=VPC_ENDPOINT_TERMINATION_TIMEOUT_SECONDS)
            except Exception as exc:
                cleanup_error = exc
            try:
                self._wait_absent("VPC endpoint network interfaces", self._network_interfaces_present, timeout=180)
            except Exception as exc:
                cleanup_error = cleanup_error or exc
            if cleanup_error is not None:
                raise cleanup_error

    def _revoke_security_group_pair(self) -> None:
        if not self.endpoint_security_group_id or not self.instance_security_group_id:
            return
        try:
            self._call(
                "revoke_endpoint_ingress",
                self.ec2.revoke_security_group_ingress,
                GroupId=self.endpoint_security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "UserIdGroupPairs": [{"GroupId": self.instance_security_group_id}],
                    }
                ],
            )
        except Exception as exc:
            if not _absent(exc, "InvalidPermission.NotFound"):
                raise
        try:
            self._call(
                "revoke_instance_endpoint_egress",
                self.ec2.revoke_security_group_egress,
                GroupId=self.instance_security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "UserIdGroupPairs": [{"GroupId": self.endpoint_security_group_id}],
                    }
                ],
            )
        except Exception as exc:
            if not _absent(exc, "InvalidPermission.NotFound"):
                raise

    def _revoke_endpoint_service_egress(self) -> None:
        if not self.endpoint_security_group_id:
            return
        try:
            self._call(
                "revoke_endpoint_service_egress",
                self.ec2.revoke_security_group_egress,
                GroupId=self.endpoint_security_group_id,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 443,
                        "ToPort": 443,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    }
                ],
            )
        except Exception as exc:
            if not _absent(exc, "InvalidPermission.NotFound"):
                raise

    def _delete_security_group(self, operation: str, group_id: str) -> None:
        deadline = time.time() + 60
        while True:
            try:
                self._call(operation, self.ec2.delete_security_group, GroupId=group_id)
                return
            except Exception as exc:
                response = getattr(exc, "response", {})
                error = response.get("Error", {}) if isinstance(response, Mapping) else {}
                code = error.get("Code") if isinstance(error, Mapping) else None
                if code != "DependencyViolation" or time.time() >= deadline:
                    raise
                time.sleep(3)

    def _delete_iam(self) -> None:
        for function, kwargs, operation in (
            (self.iam.remove_role_from_instance_profile, {"InstanceProfileName": self.profile_name, "RoleName": self.role_name}, "remove_role_from_instance_profile"),
            (self.iam.delete_instance_profile, {"InstanceProfileName": self.profile_name}, "delete_instance_profile"),
            (self.iam.delete_role_policy, {"RoleName": self.role_name, "PolicyName": self.policy_name}, "delete_role_policy"),
            (self.iam.delete_role, {"RoleName": self.role_name}, "delete_role"),
        ):
            try:
                self._call(operation, function, **kwargs)
            except Exception as exc:
                if not _absent(exc, "NoSuchEntity", "NoSuchEntityException"):
                    raise

    def teardown(self, submission: ProductionSubmission | None) -> Mapping[str, Any] | None:
        if not self.attempt_closed:
            raise CloudManifestError("fixture attempt must be explicitly closed before teardown")
        instance_id = submission.parent_job_id if submission is not None else self.instance_id
        cleanup_error: Exception | None = None
        if instance_id:
            try:
                self._call("describe_instance.before_terminate", self.ec2.describe_instances, InstanceIds=[instance_id])
                self._call("terminate_instances", self.ec2.terminate_instances, InstanceIds=[instance_id])
                self._wait_instance_terminated(instance_id)
            except Exception as exc:
                if not _absent(exc, "InvalidInstanceID.NotFound"):
                    cleanup_error = exc
        self._stop_watchdog()
        try:
            self._wait_absent("EBS volumes", self._volumes_present, timeout=180)
            self._wait_absent("instance network interfaces", self._instance_network_interfaces_present, timeout=180)
        except Exception as exc:
            cleanup_error = cleanup_error or exc
        def cleanup_step(step: Callable[[], None]) -> None:
            nonlocal cleanup_error
            try:
                step()
            except Exception as exc:
                cleanup_error = cleanup_error or exc

        cleanup_step(self._delete_action_endpoints)
        cleanup_step(self._revoke_endpoint_service_egress)
        cleanup_step(self._revoke_security_group_pair)
        for operation, group_id in (
            ("delete_instance_security_group", self.instance_security_group_id),
            ("delete_endpoint_security_group", self.endpoint_security_group_id),
        ):
            if group_id:
                cleanup_step(lambda operation=operation, group_id=group_id: self._delete_security_group(operation, group_id))

        def disassociate_route_table() -> None:
            if not self.route_association_id:
                return
            try:
                self._call("disassociate_route_table", self.ec2.disassociate_route_table, AssociationId=self.route_association_id)
            except Exception as exc:
                if not _absent(exc, "InvalidRouteTableID.NotFound", "InvalidAssociationID.NotFound"):
                    raise

        cleanup_step(disassociate_route_table)
        if self.route_table_id:
            cleanup_step(lambda: self._call("delete_route_table", self.ec2.delete_route_table, RouteTableId=self.route_table_id))
        if self.subnet_id:
            cleanup_step(lambda: self._call("delete_subnet", self.ec2.delete_subnet, SubnetId=self.subnet_id))

        def delete_ssm_document() -> None:
            try:
                self._call("delete_ssm_document", self.ssm.delete_document, Name=self.document_name)
            except Exception as exc:
                if not _absent(exc, "InvalidDocument", "ResourceNotFoundException"):
                    raise

        cleanup_step(delete_ssm_document)
        cleanup_step(self._delete_iam)
        cleanup_step(lambda: self._wait_absent("active action instances", lambda: [item for item in self._all_tagged("instances") if item.get("State", {}).get("Name") not in {"terminated", "shutting-down"}], timeout=60))
        try:
            fresh = self.fresh_absence()
        except Exception as exc:
            cleanup_error = cleanup_error or exc
            fresh = False
        receipt: dict[str, object] = {
            "record_kind": "cloud_production_surface_teardown",
            "schema_version": "0.2.0",
            "action_id": self.config.action_id,
            "evidence_class": "production_surface_non_scientific",
            "authority": "none",
            "fixture_mode": "FIXTURE-NONSCI",
            "status": "COMPLETE" if cleanup_error is None and fresh else "FAILED",
            "instance_id": instance_id,
            "subnet_id": self.subnet_id,
            "route_table_id": self.route_table_id,
            "s3_endpoint_id": self.s3_endpoint_id,
            "interface_endpoint_ids": dict(self.endpoint_ids),
            "security_group_ids": [value for value in (self.instance_security_group_id, self.endpoint_security_group_id) if value],
            "iam_role": self.role_name,
            "instance_profile": self.profile_name,
            "instance_profile_arn": self.profile_arn,
            "ssm_document": {"name": self.document_name, "version": self.document_version, "sha256": self.document_sha256, "provider_hash": self.document_provider_hash},
            "watchdog": {"pid": self.watchdog_pid, "source_sha256": self.watchdog_source_sha256, "deadline_epoch": self.external_deadline_epoch},
            "resource_ids": {"instances": [instance_id] if instance_id else [], "volumes": list(self.instance_volume_ids), "network_interfaces": list(dict.fromkeys(self.instance_network_interface_ids + self.endpoint_network_interface_ids))},
            "provider_response_hashes": list(self.provider_responses),
            "fresh_provider_absence": fresh,
            "retained_ecr_images": True,
            "actual_billing": {"status": "delayed_not_available", "usd": None},
        }
        self.last_teardown = receipt
        if cleanup_error is not None or not fresh:
            raise CloudManifestError(f"fixture teardown failed; fresh_absence={fresh}") from cleanup_error
        return receipt

    def fresh_absence(self) -> bool:
        active = [item for item in self._all_tagged("instances") if item.get("State", {}).get("Name") not in {"terminated", "shutting-down"}]
        groups = self._all_tagged("security_groups")
        subnets = self._all_tagged("subnets")
        routes = self._all_tagged("route_tables")
        endpoints = self._all_tagged("endpoints")
        volumes = self._volumes_present()
        interfaces = self._network_interfaces_present()
        role_absent = profile_absent = document_absent = True
        try:
            self._call("fresh_get_role", self.iam.get_role, RoleName=self.role_name)
            role_absent = False
        except Exception as exc:
            if not _absent(exc, "NoSuchEntity", "NoSuchEntityException"):
                raise
        try:
            self._call("fresh_get_instance_profile", self.iam.get_instance_profile, InstanceProfileName=self.profile_name)
            profile_absent = False
        except Exception as exc:
            if not _absent(exc, "NoSuchEntity", "NoSuchEntityException"):
                raise
        try:
            self._call("fresh_get_ssm_document", self.ssm.get_document, Name=self.document_name, DocumentVersion=self.document_version, DocumentFormat="JSON")
            document_absent = False
        except Exception as exc:
            if not _absent(exc, "InvalidDocument", "ResourceNotFoundException"):
                raise
        return not active and not groups and not subnets and not routes and not endpoints and not volumes and not interfaces and role_absent and profile_absent and document_absent


def _price_document(response: Mapping[str, object]) -> tuple[Decimal, dict[str, object]]:
    values = response.get("PriceList", [])
    if not isinstance(values, list) or not values:
        raise CloudManifestError("fresh m7i.large On-Demand price is unavailable")
    document = json.loads(str(values[0]))
    price: Decimal | None = None
    for term in document.get("terms", {}).get("OnDemand", {}).values():
        for dimension in term.get("priceDimensions", {}).values():
            if dimension.get("unit") == "Hrs":
                price = Decimal(str(dimension["pricePerUnit"]["USD"]))
                break
        if price is not None:
            break
    if price is None:
        raise CloudManifestError("fresh m7i.large hourly price is malformed")
    return price, document


def collect_preflight(*, region: str = REGION, action_id: str | None = None) -> dict[str, Any]:
    """Collect fresh admission data without creating an AWS resource."""

    if region != REGION:
        raise CloudManifestError("fixture provider is registered only in us-east-1")
    boto3 = _boto3()
    ec2 = boto3.client("ec2", region_name=region)
    sts = boto3.client("sts", region_name=region)
    quotas = boto3.client("service-quotas", region_name=region)
    pricing = boto3.client("pricing", region_name=region)
    identity = sts.get_caller_identity()
    account = str(identity["Account"])
    images = ec2.describe_images(ImageIds=[AMI_ID])["Images"]
    if len(images) != 1:
        raise CloudManifestError("registered Docker/SSM AMI is unavailable")
    image = images[0]
    if image.get("OwnerId") != AMI_OWNER_ID or image.get("Architecture") != AMI_ARCHITECTURE or image.get("RootDeviceName") != AMI_ROOT_DEVICE or image.get("RootDeviceType") != "ebs" or image.get("State") != "available":
        raise CloudManifestError("registered AMI owner/architecture/root-device binding failed")
    subnet_conflicts = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [VPC_ID]}, {"Name": "cidr-block", "Values": [SUBNET_CIDR]}]).get("Subnets", [])
    if subnet_conflicts:
        conflict_ids = sorted(str(item.get("SubnetId")) for item in subnet_conflicts if item.get("SubnetId"))
        raise CloudManifestError(f"registered fixture subnet CIDR {SUBNET_CIDR} is already allocated in {VPC_ID}: {conflict_ids}")
    offerings = ec2.describe_instance_type_offerings(LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}])["InstanceTypeOfferings"]
    azs = sorted(item["Location"] for item in offerings if item.get("Location"))
    if AVAILABILITY_ZONE not in azs:
        raise CloudManifestError("fresh m7i.large capacity offering is absent in the registered AZ")
    quota = quotas.get_service_quota(ServiceCode="ec2", QuotaCode="L-1216C47A")
    price_response = pricing.get_products(ServiceCode="AmazonEC2", Filters=[{"Type": "TERM_MATCH", "Field": "instanceType", "Value": INSTANCE_TYPE}, {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"}, {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"}, {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"}, {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"}, {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"}], MaxResults=1)
    price, price_document = _price_document(price_response)
    seconds = Decimal(MAX_DURATION_SECONDS)
    ec2_cost = (price * seconds / Decimal(3600)).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    ebs_cost = (Decimal("30") * Decimal("0.08") * seconds / Decimal("2592000")).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    endpoint_cost = (Decimal(len(INTERFACE_SERVICES)) * Decimal("0.01") * seconds / Decimal(3600)).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    projected = (ec2_cost + ebs_cost + endpoint_cost + Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    if projected > MAX_USD:
        raise CloudManifestError("bounded fixture-v2 projected cost exceeds its admission ceiling")
    active: list[object] = []
    tagged_groups: list[object] = []
    if action_id is not None:
        validate_action_id(action_id)
        active = [item for item in ec2.describe_instances(Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [action_id]}]).get("Reservations", []) for item in item.get("Instances", []) if item.get("State", {}).get("Name") not in {"terminated", "shutting-down"}]
        tagged_groups = ec2.describe_security_groups(Filters=[{"Name": f"tag:{ACTION_TAG}", "Values": [action_id]}]).get("SecurityGroups", [])
    return {
        "record_kind": "cloud_production_surface_preflight",
        "schema_version": "0.2.0",
        "provider": "aws",
        "region": region,
        "account_id": account,
        "caller_arn": identity.get("Arn"),
        "vpc_id": VPC_ID,
        "subnet_cidr": SUBNET_CIDR,
        "availability_zone": AVAILABILITY_ZONE,
        "ami": {"id": AMI_ID, "owner_id": AMI_OWNER_ID, "architecture": AMI_ARCHITECTURE, "root_device_name": AMI_ROOT_DEVICE, "root_device_type": "ebs", "image_response_sha256": _sha(image)},
        "instance_type": INSTANCE_TYPE,
        "capacity_offerings": azs,
        "quota": {"quota_code": "L-1216C47A", "value": quota["Quota"]["Value"], "unit": quota["Quota"]["Unit"]},
        "price": {"hourly_usd": str(price), "currency": "USD", "price_response_sha256": _sha(price_document)},
        "cost": {"max_duration_seconds": MAX_DURATION_SECONDS, "ec2_usd": str(ec2_cost), "ebs_usd": str(ebs_cost), "interface_endpoints": len(INTERFACE_SERVICES), "interface_endpoint_usd": str(endpoint_cost), "other_allowance_usd": "0.50", "projected_max_usd": str(projected), "ceiling_usd": str(MAX_USD), "actual_billing_status": "delayed_not_available"},
        "network_contract": {"public_ipv4": False, "global_ipv6": False, "general_egress": False, "approved_services": ["s3", *INTERFACE_SERVICES], "action_scoped_endpoints": True},
        "fresh_resource_absence_before": not active and not tagged_groups,
    }


__all__ = ["AMI_ID", "AMI_OWNER_ID", "ACTION_ID_RE", "AwsSurfaceConfig", "AwsSurfaceProvider", "INTERFACE_SERVICES", "INSTANCE_TYPE", "MAX_DURATION_SECONDS", "MAX_USD", "collect_preflight", "render_surface_user_data", "validate_action_id"]
