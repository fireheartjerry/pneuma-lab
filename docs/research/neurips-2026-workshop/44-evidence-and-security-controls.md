# 44 — Evidence, Blinding, and Security Controls

**Status:** Step 10 implementation complete; external verification pending

Local controls bind result fixtures to exact code, image, manifest, and lease
identities; reject worker environments containing arm identity, answer keys,
analysis thresholds, or controller credentials; and accept only Class-B
AWS-managed-secret references. Class A assignment/unblind material remains
owned exclusively by `resampling_null/secrets.py`.

Packet capabilities preserve peer-slot/donor opacity, not self-arm opacity: a
worker may read its own intervention packet. A test prevents Phase B wording
from claiming otherwise. The resumable journal is local and append-only; no
cloud execution journal, secret injection, image, worker, or forensic receipt
exists.
