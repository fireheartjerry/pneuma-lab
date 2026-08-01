from __future__ import annotations

import hashlib
import io

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_mirror import (
    HostPolicyRedirect,
    host_is_allowed,
    source_url,
    upload_verified_object,
    validate_existing_head,
    verify_stored_object,
)


def _item(payload: bytes, *, algorithm: str = "sha256") -> dict:
    if algorithm == "sha256":
        identity = hashlib.sha256(payload).hexdigest()
    else:
        digest = hashlib.sha1()  # noqa: S324 - Git blob identity
        digest.update(f"blob {len(payload)}\0".encode())
        digest.update(payload)
        identity = digest.hexdigest()
    return {"object_id": "a" * 64, "identity_algorithm": algorithm, "identity": identity, "size_bytes": len(payload)}


class Body(io.BytesIO):
    pass


class FakeS3:
    def __init__(self) -> None:
        self.objects = {}
        self.uploads = {}
        self.completed = 0
        self.aborted = 0

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = (kwargs["Body"], kwargs["Metadata"])
        return {"VersionId": "v1", "ETag": '"small"'}

    def create_multipart_upload(self, **kwargs):
        self.uploads["u1"] = {"parts": [], "metadata": kwargs["Metadata"]}
        return {"UploadId": "u1"}

    def upload_part(self, **kwargs):
        self.uploads[kwargs["UploadId"]]["parts"].append(kwargs["Body"])
        return {"ETag": f'"p{kwargs["PartNumber"]}"'}

    def complete_multipart_upload(self, **kwargs):
        upload = self.uploads[kwargs["UploadId"]]
        self.objects[kwargs["Key"]] = (b"".join(upload["parts"]), upload["metadata"])
        self.completed += 1
        return {"VersionId": "v2", "ETag": '"multi"'}

    def abort_multipart_upload(self, **kwargs):
        self.aborted += 1

    def get_object(self, **kwargs):
        payload, metadata = self.objects[kwargs["Key"]]
        return {"Body": Body(payload), "Metadata": metadata, "ServerSideEncryption": "AES256", "VersionId": kwargs.get("VersionId", "v1"), "ETag": '"stored"'}


@pytest.mark.parametrize("algorithm", ["sha256", "git_sha1"])
def test_small_object_is_verified_before_publication_and_reread(algorithm: str) -> None:
    payload = b"verified payload"
    item = _item(payload, algorithm=algorithm)
    s3 = FakeS3()
    uploaded = upload_verified_object(item, Body(payload), s3, bucket="b", key="k", declared_size=len(payload), part_size=64)
    stored = verify_stored_object(item, s3, bucket="b", key="k", version_id=uploaded["version_id"])
    assert uploaded["payload_sha256"] == stored["payload_sha256"] == hashlib.sha256(payload).hexdigest()


def test_bad_small_identity_publishes_nothing() -> None:
    payload = b"bad"
    item = _item(payload)
    item["identity"] = "0" * 64
    s3 = FakeS3()
    with pytest.raises(CloudManifestError, match="upstream identity"):
        upload_verified_object(item, Body(payload), s3, bucket="b", key="k", declared_size=len(payload), part_size=64)
    assert s3.objects == {}


def test_bad_multipart_identity_aborts_without_completion() -> None:
    payload = b"0123456789"
    item = _item(payload)
    item["identity"] = "0" * 64
    s3 = FakeS3()
    with pytest.raises(CloudManifestError, match="upstream identity"):
        upload_verified_object(item, Body(payload), s3, bucket="b", key="k", declared_size=len(payload), part_size=4)
    assert s3.completed == 0 and s3.aborted == 1 and s3.objects == {}


def test_declared_size_and_existing_controls_fail_closed() -> None:
    payload = b"x"
    item = _item(payload)
    with pytest.raises(CloudManifestError, match="Content-Length"):
        upload_verified_object(item, Body(payload), FakeS3(), bucket="b", key="k", declared_size=2)
    with pytest.raises(CloudManifestError, match="wrong size"):
        validate_existing_head(item, {"ContentLength": 2})


def test_redirect_allowlist_supports_only_signed_exact_or_suffix_hosts() -> None:
    allowed = ("huggingface.co", "*.hf.co")
    assert host_is_allowed("huggingface.co", allowed)
    assert host_is_allowed("cas-bridge.xethub.hf.co", allowed)
    assert not host_is_allowed("hf.co.evil.example", allowed)
    assert not host_is_allowed("hf.co", allowed)


def test_cross_host_redirect_strips_authorization() -> None:
    handler = HostPolicyRedirect(("registry-1.docker.io", "production.cloudflare.docker.com"))
    import urllib.request

    request = urllib.request.Request(
        "https://registry-1.docker.io/v2/x/blobs/sha256:a", headers={"Authorization": "Bearer secret"}
    )
    redirected = handler.redirect_request(
        request, None, 307, "Temporary Redirect", {}, "https://production.cloudflare.docker.com/blob"
    )
    assert redirected is not None
    assert redirected.get_header("Authorization") is None


def test_huggingface_dataset_and_model_urls_use_distinct_namespaces() -> None:
    base = {"service": "huggingface", "repository": "org/repo", "revision": "abc", "path": "data/file.parquet"}
    assert source_url({**base, "consumers": ["swe_dataset"]}) == (
        "https://huggingface.co/datasets/org/repo/resolve/abc/data/file.parquet"
    )
    assert source_url({**base, "consumers": ["subject_model"]}) == (
        "https://huggingface.co/org/repo/resolve/abc/data/file.parquet"
    )
