"""Deterministic repo-grouped dev/eval split.

Mirrors the estimator split method ``sha256_repo_mod10_lt3_eval_v1``: repos whose
sha256 digit sum mod 10 is < 3 go to eval, the rest to dev. Because the split is
a pure function of the repository, every example for one repo lands in the same
split, so no repository can straddle train and eval.
"""

from __future__ import annotations

import hashlib

SPLIT_METHOD = "sha256_repo_mod10_lt3_eval_v1"


def split_of_repo(repo: str) -> str:
    """'eval' if sha256(repo) mod 10 < 3 else 'dev'. Deterministic."""
    digest = hashlib.sha256((repo or "").encode("utf-8")).hexdigest()
    return "eval" if (int(digest, 16) % 10) < 3 else "dev"


def assign(examples: list[dict]) -> dict[int, str]:
    """Map each example index to its split by repository."""
    result: dict[int, str] = {}
    for index, example in enumerate(examples):
        repo = (example.get("split_group") or {}).get("repo") or ""
        result[index] = split_of_repo(repo)
    return result


__all__ = ["SPLIT_METHOD", "split_of_repo", "assign"]
