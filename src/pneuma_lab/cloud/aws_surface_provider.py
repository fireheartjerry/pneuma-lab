"""Concrete AWS provider for the bounded production-surface E2E.

The provider deliberately provisions a small CPU-only EC2 host for the role
handshake.  It never receives a run specification, model credentials, task
payloads, or benchmark inputs, and the user-data contract rejects all
scientific actions.  The official two-L40S Batch deployment remains a separate
provider action gated by the signed official run specification.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import base64
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import re
import time
from typing import Any, cast

from .errors import CloudManifestError
from .production_controller import ProductionJobProvider, ProductionSubmission
from .production_run import canonical_bytes


AMI_ID = "ami-08bc385c9fc5afc94"
INSTANCE_TYPE = "m7i.large"
MAX_DURATION_SECONDS = 900
MAX_USD = Decimal("3.00")
_TAG_KEY = "PneumaSurfaceAction"


def _boto3():
    try:
        import boto3  # type: ignore[import-not-found]
    except ImportError as exc:
        raise CloudManifestError("boto3 is required for the AWS production-surface provider") from exc
    return boto3


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_iam_profile_propagation_error(exc: Exception) -> bool:
    """Recognize the transient EC2/IAM eventual-consistency failure."""

    response = getattr(exc, "response", {})
    if not isinstance(response, Mapping):
        return False
    error = response.get("Error", {})
    if not isinstance(error, Mapping):
        return False
    return error.get("Code") == "InvalidParameterValue" and "iamInstanceProfile" in str(error.get("Message", ""))


def _name(value: str, *, max_length: int = 63) -> str:
    safe = re.sub(r"[^A-Za-z0-9+=,.@_-]", "-", value)
    return safe[:max_length].rstrip("-") or "pneuma-surface"


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


def render_surface_user_data(config: AwsSurfaceConfig) -> str:
    """Render a no-model/no-benchmark role handshake for Amazon Linux 2023."""

    refs = {role: config.image_refs[role] for role in ("controller", "model-server", "benchmark-worker")}
    encoded_refs = base64.b64encode(canonical_bytes(refs)).decode("ascii")
    registry = next(iter(refs.values())).split("/", 1)[0]
    return f"""#!/bin/bash
set -euo pipefail
export HOME=/root
ACTION={config.action_id!r}
ROOT=/var/lib/pneuma-surface
REGISTRY={registry!r}
mkdir -p "$ROOT/roles"
chmod 700 "$ROOT"
echo {config.harness_bytes_b64!r} | base64 -d > "$ROOT/harness.json"
chmod 644 "$ROOT/harness.json"
cat > "$ROOT/status.json" <<'JSON'
{{"record_kind":"cloud_production_surface_provider_status","schema_version":"0.1.0","action_id":{json.dumps(config.action_id)},"terminal":false,"state":"BOOTSTRAPPING","model_download":false,"benchmark_execution":false,"official_study":false,"canonical_p0_grid":false,"roster_ceremony":false,"unblind":false,"analysis":false}}
JSON

dnf install -y docker
command -v aws >/dev/null 2>&1 || {{ echo 'Amazon Linux AWS CLI is unavailable' >&2; exit 21; }}
systemctl enable --now docker
echo {encoded_refs!r} | base64 -d > "$ROOT/image-refs.json"
aws ecr get-login-password --region {config.region!r} | docker login --username AWS --password-stdin "$REGISTRY"
for role in controller model-server benchmark-worker; do
  image=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$ROOT/image-refs.json" "$role")
  docker pull "$image"
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
  timeout 300 docker run --rm --network none --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \\
    --volume "$ROOT/harness.json:/work/harness.json:ro" "${{input_arg[@]}}" "$image" \\
    --protocol e2e --harness /work/harness.json --harness-sha256 {config.harness_sha256!r} "${{role_input[@]}}" > "$ROOT/roles/$role.json"
  python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$ROOT/roles/$role.json"
}}

for role in controller model-server benchmark-worker; do run_role "$role"; done

for role in controller model-server benchmark-worker; do
  image=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' "$ROOT/image-refs.json" "$role")
  set +e
  timeout 120 docker run --rm --network none --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \\
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
    "schema_version": "0.1.0",
    "action_id": {json.dumps(config.action_id)},
    "terminal": True,
    "state": "SUCCEEDED",
    "model_download": False,
    "benchmark_execution": False,
    "official_study": False,
    "canonical_p0_grid": False,
    "roster_ceremony": False,
    "unblind": False,
    "analysis": False,
    "receipts": receipts,
    "failure_receipts": failure_receipts,
}}
root.write_bytes((json.dumps(status, sort_keys=True, separators=(",", ":")) + "\\n").encode())
PY
chmod 644 "$ROOT/status.json" "$ROOT"/roles/*.json
"""


class AwsSurfaceProvider(ProductionJobProvider):
    """Idempotent EC2/SSM implementation of the durable provider protocol."""

    def __init__(self, config: AwsSurfaceConfig) -> None:
        if config.region != "us-east-1":
            raise CloudManifestError("AWS surface provider is registered only in us-east-1")
        self.config = config
        boto3 = _boto3()
        self.ec2 = boto3.client("ec2", region_name=config.region)
        self.iam = boto3.client("iam", region_name=config.region)
        self.ssm = boto3.client("ssm", region_name=config.region)
        self.ecr = boto3.client("ecr", region_name=config.region)
        self.submission: ProductionSubmission | None = None
        self.instance_id: str | None = None
        self.security_group_id: str | None = None
        self.role_name = _name(f"pneuma-surface-role-{config.action_id}")
        self.profile_name = _name(f"pneuma-surface-profile-{config.action_id}")
        self.policy_name = _name(f"pneuma-surface-ecr-{config.action_id}")
        self.command_id: str | None = None
        self.last_status: Mapping[str, Any] | None = None
        self.last_teardown: Mapping[str, Any] | None = None

    def _find_existing(self) -> str | None:
        response = self.ec2.describe_instances(
            Filters=[
                {"Name": f"tag:{_TAG_KEY}", "Values": [self.config.action_id]},
                {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
            ]
        )
        instances = [instance for reservation in response.get("Reservations", []) for instance in reservation.get("Instances", [])]
        if len(instances) > 1:
            raise CloudManifestError("multiple active surface instances share one action tag")
        return instances[0]["InstanceId"] if instances else None

    def _default_network(self) -> tuple[str, str]:
        vpcs = self.ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
        if not vpcs:
            raise CloudManifestError("no default VPC is available for bounded surface E2E")
        vpc_id = vpcs[0]["VpcId"]
        subnets = self.ec2.describe_subnets(
            Filters=[{"Name": "vpc-id", "Values": [vpc_id]}, {"Name": "state", "Values": ["available"]}]
        )["Subnets"]
        if not subnets:
            raise CloudManifestError("no available subnet is present in the default VPC")
        return vpc_id, sorted(subnets, key=lambda item: item["SubnetId"])[0]["SubnetId"]

    def _security_group(self, vpc_id: str) -> str:
        group = self.ec2.create_security_group(
            GroupName=_name(f"pneuma-surface-{self.config.action_id}"),
            Description="Pneuma bounded production surface; no inbound traffic",
            VpcId=vpc_id,
        )
        group_id = cast(str, group["GroupId"])
        self.ec2.create_tags(Resources=[group_id], Tags=[{"Key": _TAG_KEY, "Value": self.config.action_id}, {"Key": "PneumaManaged", "Value": "production-surface-e2e"}])
        try:
            self.ec2.revoke_security_group_egress(
                GroupId=group_id,
                IpPermissions=[{"IpProtocol": "-1", "FromPort": 0, "ToPort": 0, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
            )
        except self.ec2.exceptions.ClientError:
            pass
        self.ec2.authorize_security_group_egress(
            GroupId=group_id,
            IpPermissions=[{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
        )
        return group_id

    def _iam(self) -> str:
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
        self.iam.create_role(RoleName=self.role_name, AssumeRolePolicyDocument=_json(trust), Description="Pneuma non-scientific production surface E2E")
        account = self.ecr.get_authorization_token()["authorizationData"][0]["proxyEndpoint"].split("//", 1)[-1].split(".", 1)[0]
        resources = [f"arn:aws:ecr:us-east-1:{account}:repository/pneuma-official-production-{role}" for role in ("controller", "model-server", "benchmark-worker")]
        policy = {"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Action": ["ecr:GetAuthorizationToken"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"], "Resource": resources},
        ]}
        self.iam.put_role_policy(RoleName=self.role_name, PolicyName=self.policy_name, PolicyDocument=_json(policy))
        self.iam.attach_role_policy(RoleName=self.role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore")
        self.iam.create_instance_profile(InstanceProfileName=self.profile_name)
        self.iam.add_role_to_instance_profile(InstanceProfileName=self.profile_name, RoleName=self.role_name)
        return self.profile_name

    def submit(self, *, client_token: str, allocation: Mapping[str, Sequence[str]]) -> ProductionSubmission:
        if set(allocation) != {"worker-0", "worker-1"}:
            raise CloudManifestError("surface provider requires the canonical two-worker allocation shape")
        existing = self._find_existing()
        if existing is not None:
            self.instance_id = existing
            self.submission = ProductionSubmission(existing, (existing,))
            return self.submission
        vpc_id, subnet_id = self._default_network()
        self.security_group_id = self._security_group(vpc_id)
        profile = self._iam()
        user_data = render_surface_user_data(self.config)
        tags = [
            {"Key": _TAG_KEY, "Value": self.config.action_id},
            {"Key": "PneumaManaged", "Value": "production-surface-e2e"},
            {"Key": "PneumaEvidenceClass", "Value": "non-scientific"},
        ]
        run_kwargs = {
            "ImageId": AMI_ID,
            "InstanceType": INSTANCE_TYPE,
            "MinCount": 1,
            "MaxCount": 1,
            "ClientToken": client_token[:64],
            "IamInstanceProfile": {"Name": profile},
            "NetworkInterfaces": [{"DeviceIndex": 0, "SubnetId": subnet_id, "Groups": [self.security_group_id], "AssociatePublicIpAddress": True, "DeleteOnTermination": True}],
            "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {"VolumeSize": 80, "VolumeType": "gp3", "Encrypted": True, "DeleteOnTermination": True}}],
            "MetadataOptions": {"HttpTokens": "required", "HttpEndpoint": "enabled", "HttpPutResponseHopLimit": 1},
            "UserData": user_data,
            "TagSpecifications": [{"ResourceType": "instance", "Tags": tags}, {"ResourceType": "volume", "Tags": tags}],
        }
        response = None
        for attempt in range(4):
            try:
                response = self.ec2.run_instances(**run_kwargs)
                break
            except self.ec2.exceptions.ClientError as exc:
                if not _is_iam_profile_propagation_error(exc) or attempt == 3:
                    raise
                time.sleep(2**attempt)
        if response is None:
            raise CloudManifestError("AWS instance submission produced no response")
        instance_id = cast(str, response["Instances"][0]["InstanceId"])
        self.instance_id = instance_id
        self.submission = ProductionSubmission(instance_id, (instance_id,))
        return self.submission

    def observe(self, submission: ProductionSubmission) -> Mapping[str, Any]:
        instance_id = submission.parent_job_id
        self.instance_id = instance_id
        if self.command_id is None:
            try:
                command = self.ssm.send_command(
                    InstanceIds=[instance_id],
                    DocumentName="AWS-RunShellScript",
                    Parameters={"commands": ["if test -f /var/lib/pneuma-surface/status.json; then cat /var/lib/pneuma-surface/status.json; else echo '{\"terminal\":false,\"state\":\"WAITING\"}'; fi"]},
                    TimeoutSeconds=30,
                    Comment="Pneuma bounded production-surface status read",
                )
            except self.ssm.exceptions.InvalidInstanceId:
                return {"terminal": False, "provider_state": "SSM_INSTANCE_PENDING"}
            self.command_id = cast(str, command["Command"]["CommandId"])
        try:
            invocation = self.ssm.get_command_invocation(CommandId=self.command_id, InstanceId=instance_id)
        except self.ssm.exceptions.InvocationDoesNotExist:
            return {"terminal": False, "provider_state": "SSM_PENDING"}
        if invocation.get("Status") not in {"Success", "Failed", "TimedOut", "Cancelled"}:
            return {"terminal": False, "provider_state": invocation.get("Status", "SSM_UNKNOWN")}
        # SSM command output is a snapshot.  Do not reuse a successful read
        # after the status file may have changed; the next observation must
        # issue a fresh, read-only command.
        self.command_id = None
        stdout = str(invocation.get("StandardOutputContent", "")).strip()
        try:
            status = json.loads(stdout) if stdout else {"terminal": False, "state": "NO_STATUS"}
        except json.JSONDecodeError:
            status = {"terminal": False, "state": "INVALID_STATUS"}
        if not isinstance(status, Mapping):
            status = {"terminal": False, "state": "INVALID_STATUS"}
        self.last_status = cast(Mapping[str, Any], status)
        terminal = status.get("terminal") is True and invocation.get("Status") == "Success"
        return {"terminal": terminal, "provider_state": status.get("state", invocation.get("Status")), "status_sha256": _sha(dict(status)), "status": dict(status)}

    def teardown(self, submission: ProductionSubmission | None) -> Mapping[str, Any] | None:
        instance_id = submission.parent_job_id if submission is not None else self.instance_id
        if instance_id:
            self.ec2.terminate_instances(InstanceIds=[instance_id])
            try:
                self.ec2.get_waiter("instance_terminated").wait(InstanceIds=[instance_id], WaiterConfig={"Delay": 5, "MaxAttempts": 36})
            except Exception:
                pass
        if self.security_group_id is None:
            groups = self.ec2.describe_security_groups(Filters=[{"Name": f"tag:{_TAG_KEY}", "Values": [self.config.action_id]}])["SecurityGroups"]
            self.security_group_id = groups[0]["GroupId"] if groups else None
        if self.security_group_id:
            for attempt in range(6):
                try:
                    self.ec2.delete_security_group(GroupId=self.security_group_id)
                    break
                except self.ec2.exceptions.ClientError as exc:
                    error = exc.response.get("Error", {})
                    if error.get("Code") != "DependencyViolation" or attempt == 5:
                        break
                    time.sleep(2**attempt)
        try:
            self.iam.remove_role_from_instance_profile(InstanceProfileName=self.profile_name, RoleName=self.role_name)
        except self.iam.exceptions.NoSuchEntityException:
            pass
        try:
            self.iam.delete_instance_profile(InstanceProfileName=self.profile_name)
        except self.iam.exceptions.NoSuchEntityException:
            pass
        try:
            self.iam.delete_role_policy(RoleName=self.role_name, PolicyName=self.policy_name)
        except self.iam.exceptions.NoSuchEntityException:
            pass
        try:
            self.iam.detach_role_policy(RoleName=self.role_name, PolicyArn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore")
            self.iam.delete_role(RoleName=self.role_name)
        except self.iam.exceptions.NoSuchEntityException:
            pass
        receipt = {
            "status": "COMPLETE",
            "instance_id": instance_id,
            "security_group_id": self.security_group_id,
            "iam_role": self.role_name,
            "instance_profile": self.profile_name,
            "fresh_provider_absence": self.fresh_absence(),
            "retained_ecr_images": True,
        }
        self.last_teardown = receipt
        return receipt

    def fresh_absence(self) -> bool:
        active = self._find_existing()
        groups = self.ec2.describe_security_groups(Filters=[{"Name": f"tag:{_TAG_KEY}", "Values": [self.config.action_id]}])["SecurityGroups"]
        try:
            self.iam.get_role(RoleName=self.role_name)
            role_absent = False
        except self.iam.exceptions.NoSuchEntityException:
            role_absent = True
        try:
            self.iam.get_instance_profile(InstanceProfileName=self.profile_name)
            profile_absent = False
        except self.iam.exceptions.NoSuchEntityException:
            profile_absent = True
        return active is None and not groups and role_absent and profile_absent


def collect_preflight(*, region: str = "us-east-1", action_id: str | None = None) -> dict[str, Any]:
    """Collect fresh read-only account, quota, capacity, and price evidence."""

    boto3 = _boto3()
    ec2 = boto3.client("ec2", region_name=region)
    sts = boto3.client("sts", region_name=region)
    quotas = boto3.client("service-quotas", region_name=region)
    pricing = boto3.client("pricing", region_name="us-east-1")
    identity = sts.get_caller_identity()
    account = str(identity["Account"])
    offerings = ec2.describe_instance_type_offerings(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": [INSTANCE_TYPE]}],
    )["InstanceTypeOfferings"]
    azs = sorted(item["Location"] for item in offerings if item.get("Location"))
    if not azs:
        raise CloudManifestError("fresh m7i.large capacity offering is absent")
    quota = quotas.get_service_quota(ServiceCode="ec2", QuotaCode="L-1216C47A")
    price_response = pricing.get_products(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": INSTANCE_TYPE},
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            {"Type": "TERM_MATCH", "Field": "location", "Value": "US East (N. Virginia)"},
        ],
        MaxResults=1,
    )
    if not price_response.get("PriceList"):
        raise CloudManifestError("fresh m7i.large On-Demand price is unavailable")
    price_document = json.loads(price_response["PriceList"][0])
    price = None
    for term in price_document.get("terms", {}).get("OnDemand", {}).values():
        for dimension in term.get("priceDimensions", {}).values():
            if dimension.get("unit") == "Hrs":
                price = Decimal(str(dimension["pricePerUnit"]["USD"]))
                break
        if price is not None:
            break
    if price is None:
        raise CloudManifestError("fresh m7i.large hourly price is malformed")
    max_seconds = Decimal(MAX_DURATION_SECONDS)
    ec2_cost = (price * max_seconds / Decimal(3600)).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    ebs_cost = (Decimal("80") * Decimal("0.08") * max_seconds / Decimal("2592000")).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)
    projected = (ec2_cost + ebs_cost + Decimal("0.50")).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    if projected > MAX_USD:
        raise CloudManifestError("bounded surface projected cost exceeds its admission ceiling")
    active_instances = []
    tagged_groups = []
    if action_id is not None:
        active_instances = [
            instance
            for reservation in ec2.describe_instances(
                Filters=[{"Name": f"tag:{_TAG_KEY}", "Values": [action_id]}, {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}]
            ).get("Reservations", [])
            for instance in reservation.get("Instances", [])
        ]
        tagged_groups = ec2.describe_security_groups(Filters=[{"Name": f"tag:{_TAG_KEY}", "Values": [action_id]}]).get("SecurityGroups", [])
    return {
        "record_kind": "cloud_production_surface_preflight",
        "schema_version": "0.1.0",
        "provider": "aws",
        "region": region,
        "account_id_sha256": hashlib.sha256(account.encode()).hexdigest(),
        "ami_id": AMI_ID,
        "instance_type": INSTANCE_TYPE,
        "capacity_offerings": azs,
        "quota": {"quota_code": "L-1216C47A", "value": quota["Quota"]["Value"], "unit": quota["Quota"]["Unit"]},
        "price": {"hourly_usd": str(price), "currency": "USD", "price_response_sha256": hashlib.sha256(canonical_bytes(price_document)).hexdigest()},
        "cost": {"max_duration_seconds": MAX_DURATION_SECONDS, "ec2_usd": str(ec2_cost), "ebs_usd": str(ebs_cost), "other_allowance_usd": "0.50", "projected_usd": str(projected), "ceiling_usd": str(MAX_USD)},
        "fresh_resource_absence_before": not active_instances and not tagged_groups,
    }


__all__ = ["AMI_ID", "AwsSurfaceConfig", "AwsSurfaceProvider", "INSTANCE_TYPE", "MAX_DURATION_SECONDS", "MAX_USD", "collect_preflight", "render_surface_user_data"]
