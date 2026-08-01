"""Stream verified upstream payloads into content-addressed S3 objects."""

from __future__ import annotations

import base64
import hashlib
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from typing import Any, BinaryIO

from .errors import CloudManifestError
from .payload_pricing import PART_SIZE


READ_SIZE = 1024 * 1024


def _identity_hasher(algorithm: str, size_bytes: int) -> Any:
    if algorithm == "sha256":
        return hashlib.sha256()
    if algorithm == "git_sha1":
        digest = hashlib.sha1()  # noqa: S324 - verifies a frozen Git object identity
        digest.update(f"blob {size_bytes}\0".encode("ascii"))
        return digest
    raise CloudManifestError(f"unsupported upstream identity algorithm {algorithm!r}")


def _metadata(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "pneuma-object-id": str(item["object_id"]),
        "pneuma-upstream-algorithm": str(item["identity_algorithm"]),
        "pneuma-upstream-identity": str(item["identity"]),
    }


def _verify_stream_digests(item: Mapping[str, Any], received: int, payload: Any, upstream: Any) -> str:
    expected_size = int(item["size_bytes"])
    if received != expected_size:
        raise CloudManifestError(f"payload ended at {received} bytes, not authenticated size {expected_size}")
    if upstream.hexdigest() != item["identity"]:
        raise CloudManifestError("payload does not match its authenticated upstream identity")
    return payload.hexdigest()


def _read_chunks(stream: BinaryIO, expected_size: int) -> Iterable[bytes]:
    received = 0
    while True:
        chunk = stream.read(READ_SIZE)
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise CloudManifestError("payload stream returned non-byte content")
        received += len(chunk)
        if received > expected_size:
            raise CloudManifestError("payload exceeded its authenticated size")
        yield chunk


def upload_verified_object(
    item: Mapping[str, Any], stream: BinaryIO, s3: Any, *, bucket: str, key: str,
    declared_size: int, content_encoding: str | None = None, part_size: int = PART_SIZE,
) -> dict[str, Any]:
    """Verify before publication; multipart failures leave no completed object."""

    expected_size = int(item["size_bytes"])
    if declared_size != expected_size:
        raise CloudManifestError("HTTP Content-Length does not match the authenticated size")
    if content_encoding not in {None, "", "identity"}:
        raise CloudManifestError("encoded HTTP payloads are forbidden")
    payload = hashlib.sha256()
    upstream = _identity_hasher(str(item["identity_algorithm"]), expected_size)
    received = 0
    put_requests = 0

    if expected_size <= part_size:
        body = bytearray()
        for chunk in _read_chunks(stream, expected_size):
            received += len(chunk)
            payload.update(chunk)
            upstream.update(chunk)
            body.extend(chunk)
        payload_sha256 = _verify_stream_digests(item, received, payload, upstream)
        response = s3.put_object(
            Bucket=bucket, Key=key, Body=bytes(body), ContentLength=received,
            ChecksumSHA256=base64.b64encode(bytes.fromhex(payload_sha256)).decode("ascii"),
            ServerSideEncryption="AES256", Metadata=_metadata(item), IfNoneMatch="*",
        )
        put_requests = 1
    else:
        created = s3.create_multipart_upload(
            Bucket=bucket, Key=key, ServerSideEncryption="AES256", Metadata=_metadata(item)
        )
        put_requests += 1
        upload_id = created["UploadId"]
        parts: list[dict[str, Any]] = []
        buffer = bytearray()
        try:
            for chunk in _read_chunks(stream, expected_size):
                received += len(chunk)
                payload.update(chunk)
                upstream.update(chunk)
                buffer.extend(chunk)
                if len(buffer) >= part_size:
                    part = bytes(buffer[:part_size])
                    del buffer[:part_size]
                    number = len(parts) + 1
                    uploaded = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=number, Body=part)
                    put_requests += 1
                    parts.append({"ETag": uploaded["ETag"], "PartNumber": number})
            if buffer:
                number = len(parts) + 1
                uploaded = s3.upload_part(Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=number, Body=bytes(buffer))
                put_requests += 1
                parts.append({"ETag": uploaded["ETag"], "PartNumber": number})
            payload_sha256 = _verify_stream_digests(item, received, payload, upstream)
            response = s3.complete_multipart_upload(
                Bucket=bucket, Key=key, UploadId=upload_id,
                MultipartUpload={"Parts": parts}, IfNoneMatch="*",
            )
            put_requests += 1
        except BaseException:
            s3.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
            raise

    return {
        "payload_sha256": payload_sha256, "size_bytes": received,
        "version_id": response.get("VersionId"), "etag": str(response.get("ETag", "")).strip('"'),
        "put_requests": put_requests,
    }


def verify_stored_object(
    item: Mapping[str, Any], s3: Any, *, bucket: str, key: str, version_id: str | None = None,
) -> dict[str, Any]:
    """Independently reread S3 and verify both upstream and payload digests."""

    arguments = {"Bucket": bucket, "Key": key}
    if version_id:
        arguments["VersionId"] = version_id
    response = s3.get_object(**arguments)
    if response.get("ServerSideEncryption") != "AES256":
        raise CloudManifestError("stored payload is not encrypted with the bound S3 control")
    metadata = response.get("Metadata", {})
    if metadata != _metadata(item):
        raise CloudManifestError("stored payload metadata does not match the bound object")
    expected_size = int(item["size_bytes"])
    payload = hashlib.sha256()
    upstream = _identity_hasher(str(item["identity_algorithm"]), expected_size)
    received = 0
    body = response["Body"]
    try:
        for chunk in _read_chunks(body, expected_size):
            received += len(chunk)
            payload.update(chunk)
            upstream.update(chunk)
    finally:
        body.close()
    payload_sha256 = _verify_stream_digests(item, received, payload, upstream)
    return {
        "payload_sha256": payload_sha256, "size_bytes": received,
        "version_id": response.get("VersionId", version_id),
        "etag": str(response.get("ETag", "")).strip('"'), "get_requests": 1,
    }


def validate_existing_head(item: Mapping[str, Any], head: Mapping[str, Any]) -> str | None:
    if int(head.get("ContentLength", -1)) != int(item["size_bytes"]):
        raise CloudManifestError("existing S3 object has the wrong size")
    if head.get("ServerSideEncryption") != "AES256" or head.get("Metadata", {}) != _metadata(item):
        raise CloudManifestError("existing S3 object has incompatible controls or identity metadata")
    return head.get("VersionId")


def object_key(prefix: str, item: Mapping[str, Any]) -> str:
    return f"{prefix}/objects/{item['object_id']}"


def source_url(item: Mapping[str, Any]) -> str:
    repository = str(item["repository"])
    revision = str(item["revision"])
    path = item.get("path")
    if item["service"] == "huggingface":
        return f"https://huggingface.co/{repository}/resolve/{revision}/{urllib.parse.quote(str(path), safe='/')}"
    if item["service"] == "github":
        return f"https://raw.githubusercontent.com/{repository}/{revision}/{urllib.parse.quote(str(path), safe='/')}"
    if item["service"] == "docker_registry":
        name = repository.removeprefix("docker.io/")
        return f"https://registry-1.docker.io/v2/{name}/blobs/sha256:{item['identity']}"
    raise CloudManifestError(f"unsupported payload service {item['service']!r}")


def host_is_allowed(host: str, allowed: Iterable[str]) -> bool:
    normalized = host.lower().rstrip(".")
    for rule in allowed:
        if rule.startswith("*.") and normalized.endswith(rule[1:]) and normalized != rule[2:]:
            return True
        if normalized == rule:
            return True
    return False


class HostPolicyRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts: Iterable[str]) -> None:
        self.allowed_hosts = tuple(allowed_hosts)

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        host = urllib.parse.urlsplit(newurl).hostname or ""
        if not host_is_allowed(host, self.allowed_hosts):
            raise CloudManifestError(f"redirect target host is outside the signed allowlist: {host}")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        original_host = urllib.parse.urlsplit(req.full_url).hostname or ""
        if redirected is not None and host.lower() != original_host.lower():
            redirected.remove_header("Authorization")
            redirected.remove_header("authorization")
        return redirected
