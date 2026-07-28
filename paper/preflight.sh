#!/usr/bin/env sh
# Pre-submission checks that run against the BUILT PDF and its source.
#
#     ./preflight.sh              check main.pdf
#     ./preflight.sh placebo      check placebo.pdf
#     JOB=placebo ./preflight.sh  same thing
#
# This exists because of a class of defect that the LaTeX build cannot catch. An
# editing accident turned `\textbf` into a literal tab followed by "extbf", and
# `\ref` into a carriage return followed by "ef". Both are valid LaTeX input, so
# latexmk exited 0, the log was clean, and the PDF silently printed
# "extbf{...}" and "ef{sec:...}" as body text. Only reading the output found it.
# Anything checkable mechanically belongs here rather than in a human checklist.

set -eu

# Accept the job as an argument as well as an env var. Previously a positional
# argument was silently ignored, so `./preflight.sh placebo` printed a full report
# -- for main.pdf. A checker that confidently checks the wrong artifact is worse
# than one that fails.
JOB="${1:-${JOB:-main}}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

TEX="$JOB.tex"
PDF="$JOB.pdf"
LOG="$JOB.log"
fail=0

report() {
    set -- "$1" "$(printf %s "$2" | tr -d " 

")"
    # report <label> <count> <expected-zero:1|0>
    if [ "$2" -eq 0 ]; then
        printf '  ok    %-42s %s\n' "$1" "$2"
    else
        printf '  FAIL  %-42s %s\n' "$1" "$2"
        fail=$((fail + 1))
    fi
}

[ -f "$PDF" ] || { echo "$PDF not found -- build first"; exit 2; }

echo "preflight: $JOB"

# --- source integrity ------------------------------------------------------
# Was two grep checks. The carriage-return one could never fire: Git Bash grep
# normalises CRLF before matching, so it reported 0 on a file with 898 carriage
# returns AND on a live injection that reached the PDF. Both are now done in
# Python against raw bytes; see check_source_integrity.py for the incident.
if command -v python >/dev/null 2>&1 || command -v py >/dev/null 2>&1; then
    PY="$(command -v python || command -v py)"
    if "$PY" check_source_integrity.py "$JOB" >/dev/null 2>&1; then
        report "injected control characters" 0
    else
        printf "  FAIL  %-42s see below\n" "injected control characters"
        "$PY" check_source_integrity.py "$JOB" | tail -n +2
        fail=$((fail + 1))
    fi
fi

# --- build cleanliness -----------------------------------------------------
if [ -f "$LOG" ]; then
    report "undefined references" "$(grep -c 'undefined' "$LOG" || true)"
    report "overfull boxes" "$(grep -c 'Overfull' "$LOG" || true)"
fi

if command -v pdftotext >/dev/null 2>&1; then
    TXT="$(pdftotext "$PDF" - 2>/dev/null)"

    # --- mangled control sequences leaking as body text --------------------
    report "leaked LaTeX fragments in text" \
        "$(printf '%s' "$TXT" | grep -cE 'extbf|extit|emph\{|ef\{?sec|egin\{|ewcommand|rac\{|ootnote|space\{' || true)"

    # --- unfilled placeholders ---------------------------------------------
    report "unfilled placeholders in PDF" \
        "$(printf '%s' "$TXT" | grep -cE '\[TODO:|\[[A-Z][A-Z ._-]+\]' || true)"

    # --- double-blind ------------------------------------------------------
    report "identifying strings in text" \
        "$(printf '%s' "$TXT" | grep -ciE 'pneuma|C:/Users|/home/|fireh' || true)"
fi

# Raw-stream scan catches paths embedded outside the text layer.
report "identifying strings in raw PDF" \
    "$(grep -a -ciE 'pneuma|C:/Users|/home/' "$PDF" || true)"

# --- fonts -----------------------------------------------------------------
if command -v pdffonts >/dev/null 2>&1; then
    report "Type 3 fonts" "$(pdffonts "$PDF" | grep -c 'Type 3' || true)"
    report "fonts not embedded" \
        "$(pdffonts "$PDF" | awk 'NR>2 && $(NF-3)!="yes"' | wc -l | tr -d ' ')"
fi

# --- metadata --------------------------------------------------------------
if command -v pdfinfo >/dev/null 2>&1; then
    report "populated identifying metadata" \
        "$(pdfinfo "$PDF" | grep -E '^(Author|Subject|Keywords|Creator|Producer):' \
            | sed -E 's/^[A-Za-z]+: *//' | grep -c '.' || true)"
fi

# --- every number traces to a persisted artifact ---------------------------
# The repository rejects a claim with no matching artifact. Numbers accumulate
# across drafts and some get retracted; an orphan is invisible without this.
if command -v python >/dev/null 2>&1 || command -v py >/dev/null 2>&1; then
    PY="$(command -v python || command -v py)"
    if "$PY" audit_numbers.py "$JOB" >/dev/null 2>&1; then
        report "untraced numbers in paper" 0
    else
        printf "  FAIL  %-42s see below
" "untraced numbers in paper"
        "$PY" audit_numbers.py "$JOB" | tail -n +4
        fail=$((fail + 1))
    fi
fi

# --- superseded numbers that survived an edit -------------------------------
# Traceability is not consistency: when a quantity is recomputed, the old value
# and the new one both trace to artifacts, so the paper can contradict itself
# while every number checks out. This catches that.
if [ -n "${PY:-}" ]; then
    if "$PY" check_stale.py "$JOB" >/dev/null 2>&1; then
        report "superseded numbers in paper" 0
    else
        printf "  FAIL  %-42s see below
" "superseded numbers in paper"
        "$PY" check_stale.py "$JOB" | tail -n +2
        fail=$((fail + 1))
    fi
fi

# --- one experiment's numbers reappearing in another's artifact -------------
# Traceability and currency both pass on a COPIED number: it is in an artifact,
# and it is the latest one. What they cannot see is that the artifact did not
# measure it. A re-measurement of the same quantity agrees to a few decimals; two
# artifacts agreeing to all seventeen shared the value rather than measured it.
if [ -n "${PY:-}" ]; then
    if "$PY" check_instrument_reuse.py >/dev/null 2>&1; then
        report "undeclared cross-artifact reuse" 0
    else
        printf "  FAIL  %-42s see below\n" "undeclared cross-artifact reuse"
        "$PY" check_instrument_reuse.py | tail -n +2
        fail=$((fail + 1))
    fi
fi

# --- comparisons whose two sides were never measured together ---------------
# Seven defects in this paper compared quantities from different measurement
# systems. If a sentence says X falls below Y, some artifact should contain both;
# when none does, the relationship was never measured. Declared cross-artifact
# comparisons (cross-model, cross-task, before/after) are exempt with a reason.
if [ -n "${PY:-}" ]; then
    if "$PY" check_comparisons.py "$JOB" >/dev/null 2>&1; then
        report "unmatched comparisons" 0
    else
        printf "  FAIL  %-42s see below
" "unmatched comparisons"
        "$PY" check_comparisons.py "$JOB" | tail -n +2
        fail=$((fail + 1))
    fi
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "preflight PASSED"
else
    echo "preflight FAILED: $fail check(s)"
    exit 1
fi
