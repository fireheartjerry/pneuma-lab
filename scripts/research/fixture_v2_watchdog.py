"""Independent kill switch for one FIXTURE-NONSCI v2 AWS attempt.

The controller, instance, user-data, SSM, and observer do not own this
process.  It only terminates the exact action tag after the pre-established
deadline; it never launches, retries, or observes a scientific workload.
"""

from __future__ import annotations

import argparse
import re
import time


ACTION_RE = re.compile(r"^FIXTURE-NONSCI-[0-9]{8}-v2-[a-z0-9]{8}$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", required=True)
    parser.add_argument("--action-id", required=True)
    parser.add_argument("--deadline-epoch", required=True, type=int)
    args = parser.parse_args(argv)
    if args.region != "us-east-1" or not ACTION_RE.fullmatch(args.action_id):
        parser.error("watchdog accepts only the registered FIXTURE-NONSCI v2 action")
    import boto3  # type: ignore[import-not-found]

    ec2 = boto3.client("ec2", region_name=args.region)
    while time.time() < args.deadline_epoch:
        time.sleep(min(5.0, max(0.1, args.deadline_epoch - time.time())))
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:PneumaSurfaceAction", "Values": [args.action_id]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )
    instances = [
        instance["InstanceId"]
        for reservation in response.get("Reservations", [])
        for instance in reservation.get("Instances", [])
        if isinstance(instance.get("InstanceId"), str)
    ]
    if instances:
        ec2.terminate_instances(InstanceIds=sorted(set(instances)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
