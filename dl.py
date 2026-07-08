#!/usr/bin/env python3
"""
download_full.py

One-command SWE-chat full downloader for Pneuma.

Run:
    python download_full.py

What it does:
    - Uses /c/pneuma-data by default.
    - Prompts for HF token if HF_TOKEN is not already set.
    - Downloads SWE-chat structured parquet/metadata first.
    - Verifies parquet row counts and checksums.
    - Extracts transcript paths.
    - Downloads ALL transcript files slowly and resumably.
    - Verifies JSONL/JSON transcript row counts.
    - Writes inventory/provenance/status files.

Before running:
    1. Accept SWE-chat terms on Hugging Face:
       https://huggingface.co/datasets/SALT-NLP/SWE-chat
    2. Install deps:
       python -m pip install -U "huggingface_hub>=0.32.0" hf_xet pandas pyarrow rich

Exit codes:
    0  success (all transcripts downloaded and verified)
    1  finished but with per-file errors or interrupted (partial)
    2  missing dependencies
    3  aborted (auth/gated/repo/revision problem; retrying would not help)
"""

from __future__ import annotations

import datetime as dt
import getpass
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable


# =============================================================================
# CONFIG: edit here, not through command-line arguments
# =============================================================================

REPO_ID = "SALT-NLP/SWE-chat"
DATA_ROOT = Path("/c/pneuma-data")
DATASET_NAME = "swe-chat"

# Conservative by default to avoid HF 429s.
STRUCTURED_MAX_WORKERS = 2

# Full transcript download settings.
# 1 worker + delay is boring. Boring means fewer rate-limit headaches.
TRANSCRIPT_WORKERS = 1          # intentionally unused parallelism for now; keep 1
DELAY_SECONDS = 3.5             # delay after every transcript request
RETRIES = 8
MAX_BACKOFF_SECONDS = 900.0

# Verification settings.
STRICT_JSON_VERIFY = True
CHECKSUM_TRANSCRIPTS = False    # set True if you want SHA256 for 5,851 small files

# hf_hub_download already hash-verifies bytes against the hub, so a JSON parse
# issue means the SOURCE content is quirky, not that the transfer broke.
# Re-downloading yields identical bytes, so parse issues are recorded as
# warnings and never trigger a re-download. Set True only if you want parse
# warnings to also count toward the nonzero exit code.
FAIL_ON_PARSE_ERROR = False

# Our own rich bar tracks overall progress; silence HF's noisy per-file bars.
QUIET_HF_PROGRESS = True

# Re-examine parse-warning files on each run (cheap, local). Keeps the run
# self-correcting: a file logged as a warning that is actually corrupt gets
# caught and re-downloaded. Set False once the set has settled to skip them.
RECHECK_WARNINGS = True

# Small inspection sample size per parquet.
SAMPLE_HEAD_ROWS = 20

# For testing only. Set to None for full suite.
MAX_TRANSCRIPTS = None          # e.g. 20 for smoke test, None for all

# Hugging Face timeouts / cache.
HF_ETAG_TIMEOUT = "30"
HF_DOWNLOAD_TIMEOUT = "60"
HF_XET_NUM_CONCURRENT_RANGE_GETS = "8"

# The xet backend downloads large files as concurrent chunk range-GETs and
# reconstructs them locally. On some Windows setups that reconstruction has
# dropped a chunk and zero-padded the gap, yielding NUL-corrupt files that fail
# the same way on every retry. Disabling xet falls back to plain, hash-verified
# HTTP downloads: slower for big files, but robust. Set False to re-enable xet.
DISABLE_XET = True
DISABLE_HF_TRANSFER = False


# =============================================================================
# Paths
# =============================================================================

RAW_DIR = DATA_ROOT / "raw" / DATASET_NAME
PROCESSED_DIR = DATA_ROOT / "processed" / DATASET_NAME
SAMPLES_DIR = DATA_ROOT / "samples" / DATASET_NAME
MANIFESTS_DIR = DATA_ROOT / "manifests"
LOGS_DIR = DATA_ROOT / "logs"
HF_CACHE_DIR = DATA_ROOT / "cache" / "huggingface"

PROVENANCE_PATH = PROCESSED_DIR / "provenance.json"
PARQUET_VERIFY_PATH = PROCESSED_DIR / "parquet_verification.json"
TRANSCRIPT_PATHS_PATH = PROCESSED_DIR / "transcript_paths.txt"
TRANSCRIPT_STATUS_PATH = PROCESSED_DIR / "transcript_status.jsonl"
TRANSCRIPT_SUMMARY_PATH = PROCESSED_DIR / "transcript_summary.json"
INVENTORY_PATH = MANIFESTS_DIR / "swe_chat_inventory.json"
LOCAL_README_PATH = PROCESSED_DIR / "README_swe_chat_local.md"
LOG_PATH = LOGS_DIR / "swe_chat_download_full.log"

# Matches a repo-relative transcript path inside an arbitrary string.
TRANSCRIPT_RE = re.compile(r"(transcripts/[^\s'\"<>]+\.(?:jsonl|json))")


# =============================================================================
# Small utilities
# =============================================================================

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def mkdirs() -> None:
    for p in [RAW_DIR, PROCESSED_DIR, SAMPLES_DIR, MANIFESTS_DIR, LOGS_DIR, HF_CACHE_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def configure_env() -> None:
    os.environ.setdefault("HF_HOME", str(HF_CACHE_DIR))
    os.environ.setdefault("HF_HUB_CACHE", str(HF_CACHE_DIR / "hub"))
    os.environ.setdefault("HF_XET_CACHE", str(HF_CACHE_DIR / "xet"))
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", HF_ETAG_TIMEOUT)
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", HF_DOWNLOAD_TIMEOUT)
    os.environ.setdefault("HF_XET_NUM_CONCURRENT_RANGE_GETS", HF_XET_NUM_CONCURRENT_RANGE_GETS)
    os.environ.setdefault("HF_HUB_VERBOSITY", "warning")
    if QUIET_HF_PROGRESS:
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    if DISABLE_XET:
        # Force the classic hash-verified HTTP download path (set before any
        # huggingface_hub import so it takes effect).
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    if DISABLE_HF_TRANSFER:
        os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"


def log(msg: str) -> None:
    line = f"[{now_iso()}] {msg}"
    print(line, flush=True)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line + "\n")
    except Exception:
        pass


def require_deps() -> None:
    missing = []
    for mod in ["huggingface_hub", "pyarrow", "pandas", "rich"]:
        try:
            __import__(mod)
        except Exception:
            missing.append(mod)

    if missing:
        print("Missing dependencies:", ", ".join(missing), file=sys.stderr)
        print(
            "\nInstall:\n"
            '  python -m pip install -U "huggingface_hub>=0.32.0" hf_xet pandas pyarrow rich\n',
            file=sys.stderr,
        )
        raise SystemExit(2)


def get_token() -> str:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")

    # Fall back to a token already stored by `huggingface-cli login`.
    if not token:
        try:
            from huggingface_hub import get_token as hf_get_token
            token = hf_get_token()
        except Exception:
            token = None

    if not token:
        if sys.stdin.isatty():
            token = getpass.getpass("HF token, hidden input: ").strip()
        else:
            raise SystemExit(
                "Missing HF token and no interactive terminal to prompt. "
                "Accept dataset terms, then set HF_TOKEN in the environment."
            )

    token = (token or "").strip()
    if not token:
        raise SystemExit("Missing HF token. Accept dataset terms, then set HF_TOKEN or paste token here.")
    return token


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path, root: Path = RAW_DIR) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


def load_status_by_path() -> dict[str, dict[str, Any]]:
    if not TRANSCRIPT_STATUS_PATH.exists():
        return {}

    out: dict[str, dict[str, Any]] = {}
    with TRANSCRIPT_STATUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            p = row.get("path")
            if p:
                out[p] = row  # last write wins, so reruns supersede stale rows
    return out


def safe_rel_path(filename: str) -> str:
    """Normalize a repo-relative path and strip any traversal segments."""
    f = (filename or "").replace("\\", "/").strip().lstrip("/")
    parts = [seg for seg in f.split("/") if seg not in ("", ".", "..")]
    return "/".join(parts)


def is_within(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def iter_data_files():
    """All real data files under RAW_DIR, excluding the HF cache/lock metadata."""
    cache_dir = (RAW_DIR / ".cache").resolve()
    for p in RAW_DIR.rglob("*"):
        if not p.is_file():
            continue
        try:
            if cache_dir in p.resolve().parents:
                continue
        except OSError:
            continue
        yield p


def rich_progress():
    try:
        from rich.progress import (
            BarColumn,
            DownloadColumn,
            MofNCompleteColumn,
            Progress,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
            TransferSpeedColumn,
        )
        return Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=False,
        )
    except Exception:
        return NullProgress()


class NullProgress:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def add_task(self, description: str, total: int | None = None):
        print(f"{description} total={total}", flush=True)
        return 0
    def advance(self, task_id, advance: int = 1): return None


# =============================================================================
# Error classification for HF requests
# =============================================================================

class AbortDownload(RuntimeError):
    """Raised for non-recoverable conditions (auth/gated/repo/revision)."""


_HF_ERRORS: dict[str, Any] | None = None


def _load_hf_errors() -> dict[str, Any]:
    names = [
        "EntryNotFoundError",
        "GatedRepoError",
        "RepositoryNotFoundError",
        "RevisionNotFoundError",
        "HfHubHTTPError",
        "LocalEntryNotFoundError",
    ]
    for modname in ("huggingface_hub.errors", "huggingface_hub.utils"):
        try:
            mod = __import__(modname, fromlist=names)
        except Exception:
            continue
        found = {n: getattr(mod, n, None) for n in names}
        if any(isinstance(v, type) for v in found.values()):
            return found
    return {n: None for n in names}


def hf_errors() -> dict[str, Any]:
    global _HF_ERRORS
    if _HF_ERRORS is None:
        _HF_ERRORS = _load_hf_errors()
    return _HF_ERRORS


def _types(*keys: str) -> tuple:
    errs = hf_errors()
    return tuple(errs[k] for k in keys if isinstance(errs.get(k), type))


def _http_status(exc: BaseException) -> int | None:
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def classify_hf_error(exc: BaseException) -> str:
    """Return one of: 'abort', 'fatal_file', 'retry'."""
    if isinstance(exc, AbortDownload):
        return "abort"

    abort_types = _types("GatedRepoError", "RepositoryNotFoundError", "RevisionNotFoundError")
    if abort_types and isinstance(exc, abort_types):
        return "abort"

    file_types = _types("EntryNotFoundError")
    if file_types and isinstance(exc, file_types):
        return "fatal_file"

    code = _http_status(exc)
    if code in (401, 403):
        return "abort"
    if code == 404:
        return "fatal_file"
    if code == 429 or (code is not None and 500 <= code < 600):
        return "retry"

    # Timeouts, connection resets, xet hiccups, unknown -> worth retrying.
    return "retry"


def backoff_wait(exc: BaseException, attempt: int) -> float:
    fallback = min(MAX_BACKOFF_SECONDS, 10.0 * (2 ** (attempt - 1)))
    wait = min(MAX_BACKOFF_SECONDS, parse_retry_after(exc, fallback))
    wait += random.uniform(0, min(10.0, wait * 0.1))
    return wait


def run_with_retries(fn: Callable[[], Any], what: str, retries: int = RETRIES) -> Any:
    """Run fn(), retrying on transient errors, aborting on fatal ones."""
    attempt = 0
    while True:
        try:
            return fn()
        except AbortDownload:
            raise
        except Exception as e:
            kind = classify_hf_error(e)
            if kind == "abort":
                raise AbortDownload(f"{what}: {type(e).__name__}: {e}") from e
            if kind == "fatal_file":
                raise
            attempt += 1
            if attempt > retries:
                raise
            wait = backoff_wait(e, attempt)
            log(f"{what}: attempt {attempt}/{retries} failed ({type(e).__name__}); sleeping {wait:.1f}s")
            time.sleep(wait)


# =============================================================================
# Hugging Face
# =============================================================================

def get_revision(token: str) -> str:
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    info = run_with_retries(lambda: api.dataset_info(REPO_ID, token=token), "dataset_info")
    return info.sha


def write_provenance(revision: str) -> None:
    obj = {
        "dataset_name": DATASET_NAME,
        "repo_id": REPO_ID,
        "repo_type": "dataset",
        "huggingface_revision": revision,
        "source_url": f"https://huggingface.co/datasets/{REPO_ID}",
        "paper_url": "https://arxiv.org/abs/2604.20779",
        "license": "odc-by",
        "local_root": str(RAW_DIR),
        "acquired_at": now_iso(),
    }
    PROVENANCE_PATH.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def download_structured_files(token: str, revision: str) -> None:
    from huggingface_hub import snapshot_download

    allow_patterns = [
        "*.parquet",
        "*.md",
        "README*",
        "LICENSE*",
        ".gitattributes",
    ]

    log(f"Downloading structured files first: {allow_patterns}")
    run_with_retries(
        lambda: snapshot_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            revision=revision,
            token=token,
            local_dir=str(RAW_DIR),
            allow_patterns=allow_patterns,
            max_workers=STRUCTURED_MAX_WORKERS,
        ),
        "structured snapshot_download",
    )
    log("Structured download complete")


# =============================================================================
# Structured verification
# =============================================================================

def write_parquet_sample(p: Path) -> str | None:
    """Write a small head sample without loading the whole parquet into memory."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        pf = pq.ParquetFile(p)
        batch = next(pf.iter_batches(batch_size=SAMPLE_HEAD_ROWS), None)
        if batch is None:
            return None  # empty parquet, nothing to sample
        df = pa.Table.from_batches([batch]).to_pandas()
        out = SAMPLES_DIR / f"{p.stem}_head{SAMPLE_HEAD_ROWS}.jsonl"
        df.head(SAMPLE_HEAD_ROWS).to_json(out, orient="records", lines=True, force_ascii=False, date_format="iso")
        return None
    except Exception as e:
        return repr(e)


def verify_parquets() -> dict[str, Any]:
    import pyarrow.parquet as pq

    parquet_files = sorted(RAW_DIR.rglob("*.parquet"))
    rows_by_file: dict[str, int] = {}
    file_meta: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    with rich_progress() as progress:
        task = progress.add_task("Verifying parquet files", total=len(parquet_files))

        for p in parquet_files:
            r = rel(p)
            try:
                pf = pq.ParquetFile(p)
                n = int(pf.metadata.num_rows)
                rows_by_file[r] = n

                file_meta.append({
                    "path": r,
                    "bytes": p.stat().st_size,
                    "rows": n,
                    "sha256": sha256_file(p),
                    "columns": list(pf.schema_arrow.names),
                })

                sample_err = write_parquet_sample(p)
                if sample_err is not None:
                    errors.append({"path": r, "phase": "sample_head", "error": sample_err})

            except Exception as e:
                errors.append({"path": r, "phase": "verify_parquet", "error": repr(e)})
            finally:
                progress.advance(task)

    obj = {
        "parquet_files": file_meta,
        "row_counts": rows_by_file,
        "total_rows": sum(rows_by_file.values()),
        "errors": errors,
        "verified_at": now_iso(),
    }
    PARQUET_VERIFY_PATH.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    log(f"Parquet verified: files={len(file_meta)} total_rows={obj['total_rows']} errors={len(errors)}")
    return obj


def _column_to_paths(values) -> set[str]:
    out: set[str] = set()
    for x in values:
        if x is None:
            continue
        s = str(x).strip().replace("\\", "/")
        if not s:
            continue
        m = TRANSCRIPT_RE.search(s)
        if m:
            out.add(m.group(1).lstrip("/"))
        elif s.lower().endswith((".jsonl", ".json")):
            cleaned = safe_rel_path(s)
            if cleaned:
                out.add(cleaned)
    return out


def extract_transcript_paths() -> list[str]:
    import pyarrow.parquet as pq

    paths: set[str] = set()

    # Primary: session_logs.parquet exposes transcript_path directly.
    for p in RAW_DIR.rglob("session_logs.parquet"):
        try:
            pf = pq.ParquetFile(p)
            if "transcript_path" in pf.schema_arrow.names:
                col = pf.read(columns=["transcript_path"]).column("transcript_path").to_pylist()
                for x in col:
                    if x is None:
                        continue
                    cleaned = safe_rel_path(str(x))
                    if cleaned:
                        paths.add(cleaned)
        except Exception as e:
            log(f"WARNING: could not read {p}: {e!r}")

    # Fallback: scan any parquet column that looks path-ish, read only those columns.
    if not paths:
        log("No transcript_path column found; falling back to scanning parquet columns")
        for p in RAW_DIR.rglob("*.parquet"):
            try:
                pf = pq.ParquetFile(p)
                names = list(pf.schema_arrow.names)
            except Exception:
                continue
            candidates = [
                c for c in names
                if any(k in c.lower() for k in ("transcript", "path", "log"))
            ]
            if not candidates:
                continue
            try:
                table = pf.read(columns=candidates)
            except Exception:
                continue
            for c in candidates:
                paths |= _column_to_paths(table.column(c).to_pylist())

    out = sorted(paths)
    TRANSCRIPT_PATHS_PATH.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    log(f"Transcript paths extracted: {len(out)} -> {TRANSCRIPT_PATHS_PATH}")
    return out


# =============================================================================
# Transcript download + verification
# =============================================================================

def parse_retry_after(exc: BaseException, fallback: float) -> float:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            header = response.headers.get("Retry-After")
            if header:
                return max(float(header), fallback)
        except Exception:
            pass  # non-numeric (HTTP-date) Retry-After; fall through

    text = str(exc)
    m = re.search(r"Waiting\s+([0-9]+(?:\.[0-9]+)?)s", text)
    if m:
        return max(float(m.group(1)), fallback)

    if "429" in text or "Rate limited" in text:
        return max(120.0, fallback)

    return fallback


def _count_json_stream(text: str) -> tuple[int, str | None]:
    """Count JSON values in a string, tolerant of layout.

    Accepts line-delimited JSONL, a single pretty-printed object/array, and
    multiple JSON values concatenated with or without newlines between them.
    Still fails on genuine truncation or non-JSON garbage.
    """
    decoder = json.JSONDecoder()
    idx, n, count = 0, len(text), 0
    first: Any = None
    while idx < n:
        if text[idx] in " \t\r\n":
            idx += 1
            continue
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError as e:
            return count, f"parse error near char {idx} (value #{count + 1}): {e!r}"
        if count == 0:
            first = obj
        count += 1
        idx = end if end > idx else idx + 1
    # A single top-level array is reported by element count, matching JSONL rows.
    if count == 1 and isinstance(first, list):
        return len(first), None
    return count, None


def classify_transcript(path: Path) -> tuple[str, int, str | None]:
    """Classify an on-disk transcript.

    Returns (verdict, rows, detail) where verdict is one of:
      - "ok":            well-formed; safe to keep.
      - "corrupt":       truncated/interrupted write (NUL padding, empty, bad
                         encoding). The bytes are wrong, so a clean re-download
                         should fix it.
      - "parse_warning": bytes are intact and text decodes, but the content has a
                         record that isn't strictly valid JSON. Re-downloading
                         yields identical bytes, so keep the file and warn.
    """
    if not path.exists():
        return "corrupt", 0, "file does not exist"
    if path.stat().st_size == 0:
        return "corrupt", 0, "empty file"

    suffix = path.suffix.lower()
    if suffix not in (".jsonl", ".json"):
        return "parse_warning", 0, f"unsupported extension: {suffix}"

    raw = path.read_bytes()

    # A raw NUL byte is never valid inside a JSON document. In practice it means
    # the file was allocated at full size but the transfer never finished, so the
    # tail is zero-padding. That is corruption, not a content quirk.
    nul = raw.find(b"\x00")
    if nul != -1:
        return "corrupt", 0, f"NUL byte at offset {nul} (truncated/interrupted write)"

    try:
        text = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM if present
    except Exception as e:
        return "corrupt", 0, f"utf-8 decode error: {e!r}"

    if not STRICT_JSON_VERIFY:
        return "ok", (1 if text.strip() else 0), None

    rows, err = _count_json_stream(text)
    if err is None:
        return "ok", rows, None
    return "parse_warning", rows, err


def _salvage_prefix_rows(path: Path) -> int:
    """Count valid JSON records in the bytes before any NUL padding."""
    try:
        raw = path.read_bytes()
    except OSError:
        return 0
    nul = raw.find(b"\x00")
    prefix = raw[:nul] if nul != -1 else raw
    text = prefix.decode("utf-8-sig", errors="ignore")
    rows, _ = _count_json_stream(text)  # trailing partial record (if any) is ignored
    return rows


def _pacing_sleep() -> None:
    time.sleep(DELAY_SECONDS + random.uniform(0, min(1.0, DELAY_SECONDS / 2)))


def _record_status(filename: str, status: str, path_obj: Path | None = None,
                   rows: int = 0, err: str | None = None, attempts: int = 1) -> dict[str, Any]:
    exists = bool(path_obj and path_obj.exists())
    row = {
        "path": filename,
        "status": status,
        "local_path": str(path_obj) if path_obj else None,
        "bytes": path_obj.stat().st_size if exists else 0,
        "rows": rows,
        "sha256": sha256_file(path_obj) if (CHECKSUM_TRANSCRIPTS and exists) else None,
        "error": err,
        "attempts": attempts,
        "finished_at": now_iso(),
    }
    append_jsonl(TRANSCRIPT_STATUS_PATH, row)
    return row


def download_one_transcript(token: str, revision: str, filename: str) -> dict[str, Any]:
    from huggingface_hub import hf_hub_download

    filename = safe_rel_path(filename)
    if not filename:
        return _record_status(filename, "failed", err="empty path after sanitize")

    local_path = RAW_DIR / filename
    if not is_within(RAW_DIR, local_path):
        return _record_status(filename, "failed", local_path, err="unsafe path escapes RAW_DIR")

    # Inspect any file already on disk. "ok" and "parse_warning" are keepers
    # (a parse quirk is source content, not a broken transfer). "corrupt" means
    # a truncated write, so drop it and fetch a clean copy.
    force = False
    if local_path.exists() and local_path.stat().st_size > 0:
        verdict, rows, detail = classify_transcript(local_path)
        if verdict == "ok":
            return _record_status(filename, "already_present_verified", local_path, rows)
        if verdict == "parse_warning":
            return _record_status(filename, "present_parse_warning", local_path, rows, detail)
        log(f"Corrupt on disk: {filename} ({detail}); re-downloading clean copy")
        try:
            local_path.unlink()
        except OSError:
            pass
        force = True  # bypass any corrupt cached blob

    attempt = 0
    corrupt_refetch_done = force  # a corrupt-on-disk file's first fetch is its repair attempt
    while True:
        try:
            got = hf_hub_download(
                repo_id=REPO_ID,
                repo_type="dataset",
                revision=revision,
                filename=filename,
                token=token,
                local_dir=str(RAW_DIR),
                force_download=force,
            )
            local_path = Path(got)

            # Gentle pacing. This is the point. Do not "optimize" into rate-limit soup.
            _pacing_sleep()

            verdict, rows, detail = classify_transcript(local_path)
            if verdict == "ok":
                return _record_status(filename, "downloaded_verified", local_path, rows, attempts=attempt + 1)
            if verdict == "parse_warning":
                # Byte-complete download whose content just doesn't fully parse.
                return _record_status(filename, "downloaded_parse_warning", local_path, rows, detail, attempts=attempt + 1)

            # Corrupt after a download. Force exactly one clean re-fetch before deciding.
            if not corrupt_refetch_done and attempt < RETRIES:
                log(f"Corrupt after download: {filename} ({detail}); forcing one clean re-download")
                corrupt_refetch_done = True
                force = True
                attempt += 1
                try:
                    local_path.unlink()
                except OSError:
                    pass
                continue
            # Still corrupt after a hash-verified re-download => the hub's canonical
            # copy is itself truncated/NUL-padded. Nothing cleaner exists to fetch, so
            # keep the file and salvage its valid prefix instead of failing.
            rows = _salvage_prefix_rows(local_path)
            log(f"Source-truncated (hub copy is NUL-padded): {filename}; salvaged {rows} prefix records")
            return _record_status(filename, "source_truncated_warning", local_path, rows,
                                  detail or "source file truncated (NUL padding)", attempts=attempt + 1)

        except AbortDownload:
            raise
        except Exception as e:
            kind = classify_hf_error(e)

            if kind == "abort":
                # Auth/gated/repo problems affect every file. Stop the whole run.
                raise AbortDownload(f"{filename}: {type(e).__name__}: {e}") from e

            if kind == "fatal_file":
                # File genuinely not in the repo at this revision. Retrying is pointless.
                log(f"Non-retryable on {filename}: {type(e).__name__}")
                return _record_status(filename, "failed", local_path, err=repr(e), attempts=attempt + 1)

            attempt += 1
            if attempt > RETRIES:
                return _record_status(filename, "failed", local_path, err=repr(e), attempts=attempt)

            wait = backoff_wait(e, attempt)
            log(f"Rate/error on {filename}; attempt {attempt}/{RETRIES}; sleeping {wait:.1f}s; err={type(e).__name__}")
            time.sleep(wait)


ACQUIRED_STATUSES = {
    "downloaded_verified",
    "already_present_verified",
    "downloaded_parse_warning",
    "present_parse_warning",
    "source_truncated_warning",
}
FAILED_STATUSES = {"failed"}
PARSE_WARNING_STATUSES = {"downloaded_parse_warning", "present_parse_warning"}
SOURCE_TRUNCATED_STATUSES = {"source_truncated_warning"}


def summarize_transcripts() -> dict[str, Any]:
    rows_by_path = load_status_by_path()
    by_status: dict[str, int] = {}
    total_rows = 0
    total_bytes = 0
    errors: list[dict[str, Any]] = []
    parse_warnings: list[dict[str, Any]] = []
    source_truncated: list[dict[str, Any]] = []

    for row in rows_by_path.values():
        status = row.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        if isinstance(row.get("rows"), int):
            total_rows += int(row["rows"])
        if isinstance(row.get("bytes"), int):
            total_bytes += int(row["bytes"])
        entry = {"path": row.get("path"), "status": status, "error": row.get("error")}
        if status in FAILED_STATUSES:
            errors.append(entry)
        elif status in SOURCE_TRUNCATED_STATUSES:
            source_truncated.append(entry)
        elif status in PARSE_WARNING_STATUSES:
            parse_warnings.append(entry)

    summary = {
        "status_counts": by_status,
        "total_transcript_records": len(rows_by_path),
        "total_transcript_rows": total_rows,
        "total_transcript_bytes": total_bytes,
        "acquired_count": sum(by_status.get(s, 0) for s in ACQUIRED_STATUSES),
        "error_count": len(errors),           # genuine acquisition failures only
        "errors_first_200": errors[:200],
        "parse_warning_count": len(parse_warnings),  # downloaded fine, content has JSON quirks
        "parse_warnings_first_200": parse_warnings[:200],
        "source_truncated_count": len(source_truncated),  # hub's own copy is NUL-truncated
        "source_truncated_first_200": source_truncated[:200],
        "status_path": str(TRANSCRIPT_STATUS_PATH),
        "summarized_at": now_iso(),
    }
    TRANSCRIPT_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def download_all_transcripts(token: str, revision: str, transcript_paths: list[str]) -> dict[str, Any]:
    existing = load_status_by_path()
    skip_statuses = {"downloaded_verified", "already_present_verified"} if RECHECK_WARNINGS else ACQUIRED_STATUSES
    already_ok = {
        path for path, row in existing.items()
        if row.get("status") in skip_statuses
    }

    todo = [p for p in transcript_paths if p not in already_ok]
    if MAX_TRANSCRIPTS is not None:
        todo = todo[:MAX_TRANSCRIPTS]

    log(
        f"Transcript plan: expected={len(transcript_paths)} "
        f"already_verified={len(already_ok)} todo={len(todo)} "
        f"delay={DELAY_SECONDS}s retries={RETRIES}"
    )

    with rich_progress() as progress:
        task = progress.add_task("Downloading/verifying transcripts", total=len(todo))
        for filename in todo:
            download_one_transcript(token, revision, filename)
            progress.advance(task)

    summary = summarize_transcripts()
    log(
        f"Transcript summary: {summary['status_counts']} "
        f"failed={summary['error_count']} parse_warnings={summary['parse_warning_count']} "
        f"source_truncated={summary['source_truncated_count']}"
    )
    return summary


# =============================================================================
# Final inventory
# =============================================================================

def build_inventory(revision: str, parquet_info: dict[str, Any], transcript_paths: list[str], transcript_summary: dict[str, Any]) -> dict[str, Any]:
    regular_files = list(iter_data_files())
    by_ext: dict[str, int] = {}
    for p in regular_files:
        ext = p.suffix.lower() or "<none>"
        by_ext[ext] = by_ext.get(ext, 0) + 1

    failed = transcript_summary.get("error_count", 0)
    warned = transcript_summary.get("parse_warning_count", 0)
    truncated = transcript_summary.get("source_truncated_count", 0)
    if failed:
        status = "downloaded_partial_or_with_errors"
    elif warned or truncated:
        status = "downloaded_full_with_warnings"
    else:
        status = "downloaded_verified_full"

    inventory = {
        "dataset_name": DATASET_NAME,
        "status": status,
        "local_root": str(RAW_DIR),
        "source_urls": [
            f"https://huggingface.co/datasets/{REPO_ID}",
            "https://www.swe-chat.com/",
        ],
        "paper_urls": ["https://arxiv.org/abs/2604.20779"],
        "licenses": ["odc-by"],
        "acquired_at": now_iso(),
        "provenance": {
            "huggingface_snapshots": [
                {
                    "repo_id": REPO_ID,
                    "repo_type": "dataset",
                    "revision": revision,
                    "local_path": str(RAW_DIR),
                }
            ]
        },
        "files": {
            "total_count": len(regular_files),
            "total_bytes": sum(p.stat().st_size for p in regular_files),
            "by_extension": by_ext,
            "parquet": [x["path"] for x in parquet_info.get("parquet_files", [])],
            "transcripts_expected": len(transcript_paths),
        },
        "row_counts": {
            "parquet_total_rows": parquet_info.get("total_rows", 0),
            "parquet_by_file": parquet_info.get("row_counts", {}),
            "transcript_total_rows": transcript_summary.get("total_transcript_rows", 0),
        },
        "transcripts": transcript_summary,
        "sample_records": {
            "sample_dir": str(SAMPLES_DIR),
            "sample_files": [rel(p, SAMPLES_DIR) for p in SAMPLES_DIR.rglob("*") if p.is_file()],
        },
        "usefulness_for_pneuma": {
            "world_frame": "repo/session/task metadata, branch, checkpoints, language, duration, repo settings",
            "agent_trace_frame": "conversation turns, assistant responses, thinking traces, tool calls, commands, file paths, tool results",
            "memory_frame": "pushback/correction patterns, repeated failures, queue events, session summaries, tool-thrashing motifs",
            "governance_frame": "agent/tool constraints, queued user prompts, strategy fields, CLI metadata",
            "outcome_frame": "commits, diffs, agent_percentage, session_success, files touched, token/tool counts",
            "training_targets": [
                "operator_attention_pressure",
                "tool_use_quality",
                "pushback_prediction",
                "verification_pressure",
                "authority_request",
                "failure_recovery",
                "scar_motifs",
                "self_model_calibration",
                "workspace_salience",
            ],
        },
        "known_issues": [],
    }

    if failed:
        inventory["known_issues"].append(
            f"{failed} transcript files failed to download"
        )
    if warned:
        inventory["known_issues"].append(
            f"{warned} transcript files downloaded but contain non-JSON-parseable records "
            f"(source content quirk, not a transfer error)"
        )
    if truncated:
        inventory["known_issues"].append(
            f"{truncated} transcript files are NUL-truncated in the hub's own copy; "
            f"the valid prefix was kept and its records counted"
        )

    INVENTORY_PATH.write_text(json.dumps(inventory, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return inventory


def write_local_readme(inventory: dict[str, Any], revision: str) -> None:
    text = f"""# SWE-chat local acquisition

Generated: {now_iso()}

- Status: `{inventory["status"]}`
- Local root: `{inventory["local_root"]}`
- HF repo: `{REPO_ID}`
- HF revision: `{revision}`
- Total files: `{inventory["files"]["total_count"]}`
- Total bytes: `{inventory["files"]["total_bytes"]}`
- Parquet rows: `{inventory["row_counts"]["parquet_total_rows"]}`
- Transcript expected: `{inventory["files"]["transcripts_expected"]}`
- Transcript rows verified: `{inventory["row_counts"]["transcript_total_rows"]}`

Inventory:
`{INVENTORY_PATH}`

Transcript status:
`{TRANSCRIPT_STATUS_PATH}`

No ML training was performed.
"""
    LOCAL_README_PATH.write_text(text, encoding="utf-8")


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    mkdirs()
    configure_env()
    require_deps()

    log("Starting SWE-chat full acquisition")
    log(f"Repo: {REPO_ID}")
    log(f"Data root: {DATA_ROOT}")
    log(f"Raw dir: {RAW_DIR}")
    log("No command-line args. Edit constants at top of file if needed.")

    token = get_token()
    log("HF token loaded. Not printing it, because we are not gremlins.")

    try:
        revision = get_revision(token)
    except AbortDownload as e:
        log(f"ABORT before download: {e}")
        log("Check that you accepted the dataset terms and that HF_TOKEN is valid.")
        return 3
    log(f"HF revision: {revision}")

    write_provenance(revision)

    try:
        download_structured_files(token, revision)
    except AbortDownload as e:
        log(f"ABORT during structured download: {e}")
        return 3

    parquet_info = verify_parquets()
    transcript_paths = extract_transcript_paths()

    interrupted = False
    if not transcript_paths:
        log("WARNING: no transcript paths found. Writing structured-only inventory.")
        transcript_summary = summarize_transcripts()
    else:
        try:
            transcript_summary = download_all_transcripts(token, revision, transcript_paths)
        except AbortDownload as e:
            log(f"ABORT during transcript download: {e}")
            transcript_summary = summarize_transcripts()
            interrupted = True
        except KeyboardInterrupt:
            log("Interrupted by user (Ctrl-C). Writing partial summary; rerun to resume.")
            transcript_summary = summarize_transcripts()
            interrupted = True

    inventory = build_inventory(revision, parquet_info, transcript_paths, transcript_summary)
    write_local_readme(inventory, revision)

    log(f"Inventory written: {INVENTORY_PATH}")
    log(f"Local README written: {LOCAL_README_PATH}")

    failed = transcript_summary.get("error_count", 0)
    warned = transcript_summary.get("parse_warning_count", 0)
    truncated = transcript_summary.get("source_truncated_count", 0)

    print("\n=== DONE ===")
    print(json.dumps({
        "status": inventory["status"],
        "hf_revision": revision,
        "files": inventory["files"]["total_count"],
        "bytes": inventory["files"]["total_bytes"],
        "parquet_rows": inventory["row_counts"]["parquet_total_rows"],
        "transcripts_expected": inventory["files"]["transcripts_expected"],
        "transcripts_acquired": transcript_summary.get("acquired_count", 0),
        "transcript_rows": inventory["row_counts"]["transcript_total_rows"],
        "transcript_download_failures": failed,
        "transcript_parse_warnings": warned,
        "transcript_source_truncated": truncated,
        "interrupted": interrupted,
        "inventory": str(INVENTORY_PATH),
    }, indent=2, sort_keys=True))

    if interrupted or failed or (FAIL_ON_PARSE_ERROR and (warned or truncated)):
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        log("Interrupted by user before completion.")
        raise SystemExit(130)
