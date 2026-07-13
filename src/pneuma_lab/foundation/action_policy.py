"""Signed local-repository scopes with sole-operator high-impact denial."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


HIGH_IMPACT_CLASSES = frozenset(
    {
        "deployment",
        "spending",
        "public_communication",
        "credentials",
        "destructive_operation",
        "privilege_change",
        "self_modification",
    }
)
LOCAL_ACTION_CLASSES = frozenset({"local_read", "local_write", "local_test"})


class ActionDenied(PermissionError):
    """Raised before execution when an action is outside its signed scope."""


@dataclass(frozen=True)
class SignedLocalScope:
    repository_root: str
    allowed_tools: tuple[str, ...]
    expires_at: int
    signer_id: str
    nonce: str
    signature: str

    def unsigned_payload(self) -> bytes:
        value = {
            "repository_root": self.repository_root,
            "allowed_tools": list(self.allowed_tools),
            "expires_at": self.expires_at,
            "signer_id": self.signer_id,
            "nonce": self.nonce,
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def issue(
        cls,
        *,
        repository_root: Path,
        allowed_tools: tuple[str, ...],
        expires_at: int,
        signer_id: str,
        nonce: str,
        signing_key: bytes,
    ) -> "SignedLocalScope":
        if not signer_id or not nonce or not signing_key:
            raise ValueError("scope signer, nonce, and signing key are required")
        unsigned = cls(
            repository_root=str(Path(repository_root).resolve()),
            allowed_tools=tuple(sorted(set(allowed_tools))),
            expires_at=int(expires_at),
            signer_id=signer_id,
            nonce=nonce,
            signature="",
        )
        signature = hmac.new(
            signing_key,
            unsigned.unsigned_payload(),
            hashlib.sha256,
        ).hexdigest()
        return cls(
            repository_root=unsigned.repository_root,
            allowed_tools=unsigned.allowed_tools,
            expires_at=unsigned.expires_at,
            signer_id=unsigned.signer_id,
            nonce=unsigned.nonce,
            signature=signature,
        )


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    action_class: str
    scope_signer: str


class LocalActionGuard:
    def __init__(
        self,
        *,
        signing_keys: Mapping[str, bytes],
        sole_operator: bool,
    ) -> None:
        self.signing_keys = dict(signing_keys)
        self.sole_operator = sole_operator

    def _verify_scope(self, scope: SignedLocalScope, *, now: int) -> None:
        key = self.signing_keys.get(scope.signer_id)
        if key is None:
            raise ActionDenied("scope signer is unknown")
        expected = hmac.new(key, scope.unsigned_payload(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, scope.signature):
            raise ActionDenied("scope signature is invalid")
        if now > scope.expires_at:
            raise ActionDenied("scope has expired")

    def authorize(
        self,
        *,
        action_class: str,
        tool: str,
        target: Path,
        scope: SignedLocalScope,
        now: int,
    ) -> ActionDecision:
        if action_class in HIGH_IMPACT_CLASSES:
            if self.sole_operator:
                raise ActionDenied(
                    "high-impact actions are disabled for a sole operator"
                )
            raise ActionDenied(
                "high-impact authority requires a separately implemented "
                "independent-principal protocol"
            )
        if action_class not in LOCAL_ACTION_CLASSES:
            raise ActionDenied(f"unknown or unsupported action class: {action_class}")
        self._verify_scope(scope, now=now)
        if tool not in scope.allowed_tools:
            raise ActionDenied(f"tool is outside the signed scope: {tool}")
        root = Path(scope.repository_root).resolve()
        resolved_target = Path(target).resolve()
        if resolved_target != root and root not in resolved_target.parents:
            raise ActionDenied("target is outside the signed repository scope")
        return ActionDecision(
            allowed=True,
            action_class=action_class,
            scope_signer=scope.signer_id,
        )
