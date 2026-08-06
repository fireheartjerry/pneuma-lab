"""Pessimistic campaign-wide spend reservations and observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class SpendError(ValueError):
    """A spend operation violates campaign accounting."""


@dataclass(slots=True)
class SpendEntry:
    reservation_id: str
    version_id: str
    reserved_microusd: int
    version_ceiling_microusd: int
    observed_microusd: int | None = None
    released: bool = False

    @property
    def controlled_microusd(self) -> int:
        if self.released:
            return 0
        if self.observed_microusd is not None:
            return self.observed_microusd
        return self.reserved_microusd


class SpendLedger:
    def __init__(self, *, ceiling_microusd: int) -> None:
        if type(ceiling_microusd) is not int or ceiling_microusd <= 0:
            raise SpendError("campaign ceiling must be a positive integer")
        self.ceiling_microusd = ceiling_microusd
        self._entries: dict[str, SpendEntry] = {}

    @property
    def controlled_total_microusd(self) -> int:
        return sum(entry.controlled_microusd for entry in self._entries.values())

    @property
    def observed_microusd(self) -> int:
        return sum(
            entry.observed_microusd or 0
            for entry in self._entries.values()
            if not entry.released
        )

    @property
    def outstanding_microusd(self) -> int:
        return sum(
            entry.reserved_microusd
            for entry in self._entries.values()
            if not entry.released and entry.observed_microusd is None
        )

    @property
    def remaining_microusd(self) -> int:
        return max(0, self.ceiling_microusd - self.controlled_total_microusd)

    @property
    def breached(self) -> bool:
        return self.controlled_total_microusd > self.ceiling_microusd

    def _version_total(self, version_id: str) -> int:
        return sum(
            entry.controlled_microusd
            for entry in self._entries.values()
            if entry.version_id == version_id
        )

    def reserve(
        self,
        reservation_id: str,
        *,
        version_id: str,
        amount_microusd: int,
        version_ceiling_microusd: int,
    ) -> None:
        if reservation_id in self._entries:
            existing = self._entries[reservation_id]
            expected = (version_id, amount_microusd, version_ceiling_microusd)
            actual = (
                existing.version_id,
                existing.reserved_microusd,
                existing.version_ceiling_microusd,
            )
            if actual != expected:
                raise SpendError(
                    "reservation identity was reused with different bindings"
                )
            return
        if type(amount_microusd) is not int or amount_microusd <= 0:
            raise SpendError("reservation amount must be positive")
        if type(version_ceiling_microusd) is not int or version_ceiling_microusd <= 0:
            raise SpendError("version ceiling must be positive")
        if self._version_total(version_id) + amount_microusd > version_ceiling_microusd:
            raise SpendError("reservation exceeds version ceiling")
        if self.controlled_total_microusd + amount_microusd > self.ceiling_microusd:
            raise SpendError("reservation exceeds campaign ceiling")
        self._entries[reservation_id] = SpendEntry(
            reservation_id=reservation_id,
            version_id=version_id,
            reserved_microusd=amount_microusd,
            version_ceiling_microusd=version_ceiling_microusd,
        )

    def observe(self, reservation_id: str, *, observed_microusd: int) -> None:
        entry = self._require(reservation_id)
        if type(observed_microusd) is not int or observed_microusd < 0:
            raise SpendError("observed cost must be a non-negative integer")
        if (
            entry.observed_microusd is not None
            and entry.observed_microusd != observed_microusd
        ):
            raise SpendError("observed cost is immutable once recorded")
        entry.observed_microusd = observed_microusd

    def retain_unknown(self, reservation_id: str) -> None:
        entry = self._require(reservation_id)
        if entry.released or entry.observed_microusd is not None:
            raise SpendError("only an outstanding reservation can remain unknown")

    def release(self, reservation_id: str) -> None:
        entry = self._require(reservation_id)
        if entry.observed_microusd is not None:
            raise SpendError("an observed charge cannot be released")
        entry.released = True

    def _require(self, reservation_id: str) -> SpendEntry:
        try:
            return self._entries[reservation_id]
        except KeyError as exc:
            raise SpendError(f"unknown reservation {reservation_id!r}") from exc

    def to_mapping(self) -> dict[str, object]:
        return {
            "record_kind": "rapid_campaign_spend_ledger",
            "schema_version": "0.1.0",
            "ceiling_microusd": self.ceiling_microusd,
            "entries": [
                {
                    "reservation_id": entry.reservation_id,
                    "version_id": entry.version_id,
                    "reserved_microusd": entry.reserved_microusd,
                    "version_ceiling_microusd": entry.version_ceiling_microusd,
                    "observed_microusd": entry.observed_microusd,
                    "released": entry.released,
                }
                for entry in sorted(
                    self._entries.values(), key=lambda item: item.reservation_id
                )
            ],
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> SpendLedger:
        if set(payload) != {
            "record_kind",
            "schema_version",
            "ceiling_microusd",
            "entries",
        }:
            raise SpendError("spend ledger fields differ")
        if (
            payload["record_kind"] != "rapid_campaign_spend_ledger"
            or payload["schema_version"] != "0.1.0"
        ):
            raise SpendError("spend ledger kind/version differs")
        entries = payload["entries"]
        if not isinstance(entries, list):
            raise SpendError("spend entries must be a list")
        ledger = cls(ceiling_microusd=payload["ceiling_microusd"])
        for item in entries:
            if not isinstance(item, dict) or set(item) != {
                "reservation_id",
                "version_id",
                "reserved_microusd",
                "version_ceiling_microusd",
                "observed_microusd",
                "released",
            }:
                raise SpendError("spend entry fields differ")
            ledger.reserve(
                item["reservation_id"],
                version_id=item["version_id"],
                amount_microusd=item["reserved_microusd"],
                version_ceiling_microusd=item["version_ceiling_microusd"],
            )
            if item["observed_microusd"] is not None:
                ledger.observe(
                    item["reservation_id"], observed_microusd=item["observed_microusd"]
                )
            if item["released"]:
                ledger.release(item["reservation_id"])
        return ledger
