from __future__ import annotations

from types import SimpleNamespace

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from scripts.research.execute_step5b_payload_mirror import require_bucket_controls, require_execution_environment


class FakeSTS:
    meta = SimpleNamespace(endpoint_url="https://sts.us-east-1.amazonaws.com")

    def get_caller_identity(self):
        return {"Account": "892077329800", "Arn": "arn:aws:iam::892077329800:root"}


class FakeS3:
    meta = SimpleNamespace(endpoint_url="https://s3.us-east-1.amazonaws.com")

    def get_bucket_encryption(self, **kwargs):
        return {"ServerSideEncryptionConfiguration": {"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}}

    def get_bucket_versioning(self, **kwargs):
        return {"Status": "Enabled"}

    def get_public_access_block(self, **kwargs):
        return {"PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True}}

    def get_bucket_ownership_controls(self, **kwargs):
        return {"OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}}

    def get_bucket_lifecycle_configuration(self, **kwargs):
        return {"Rules": [{"ID": "expire-step5b-payloads", "Status": "Enabled", "Filter": {"Prefix": "runs/step5b/payloads/"}, "Expiration": {"Days": 35}, "NoncurrentVersionExpiration": {"NoncurrentDays": 30}, "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}}]}


def test_execution_identity_and_lifecycle_are_exact(monkeypatch) -> None:
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    identity = require_execution_environment(FakeSTS(), FakeS3(), expected_account="892077329800", expected_region="us-east-1")
    assert identity["account_id"] == "892077329800"
    controls = require_bucket_controls(FakeS3(), bucket="pneuma-phase-b-892077329800", prefix="runs/step5b/payloads/" + "a" * 64, retention_days=35)
    assert controls["lifecycle_rule_id"] == "expire-step5b-payloads"


def test_missing_or_lax_lifecycle_fails_closed() -> None:
    s3 = FakeS3()
    s3.get_bucket_lifecycle_configuration = lambda **kwargs: {"Rules": []}
    with pytest.raises(CloudManifestError, match="absent"):
        require_bucket_controls(s3, bucket="b", prefix="runs/step5b/payloads/" + "a" * 64, retention_days=35)
    s3 = FakeS3()
    original = s3.get_bucket_lifecycle_configuration
    s3.get_bucket_lifecycle_configuration = lambda **kwargs: {"Rules": [{**original()["Rules"][0], "Expiration": {"Days": 36}}]}
    with pytest.raises(CloudManifestError, match="retention"):
        require_bucket_controls(s3, bucket="b", prefix="runs/step5b/payloads/" + "a" * 64, retention_days=35)
