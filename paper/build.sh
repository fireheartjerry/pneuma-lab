#!/usr/bin/env sh
# Build the NeurIPS 2026 workshop submission to main.pdf.
#
# Usage:
#     ./build.sh          compile main.tex -> main.pdf
#     ./build.sh clean    remove LaTeX build artifacts (keeps the PDF)
#     ./build.sh distclean  remove build artifacts and the PDF
#
#     JOB=placebo ./build.sh    build the placebo study draft instead
#
# Prefers latexmk (handles the bibtex/rerun loop). Falls back to a manual
# pdflatex/bibtex/pdflatex/pdflatex sequence when latexmk is unavailable.

set -eu

# Which document to build. Override to build a sibling document that shares
# refs.bib and the style file, e.g. JOB=placebo ./build.sh
JOB="${JOB:-main}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

ARTIFACTS="aux fdb_latexmk fls log out bbl blg synctex.gz toc nav snm vrb spl"

clean_artifacts() {
    for ext in $ARTIFACTS; do
        rm -f "$JOB.$ext"
    done
}

case "${1:-build}" in
    clean)
        clean_artifacts
        echo "cleaned build artifacts"
        exit 0
        ;;
    distclean)
        clean_artifacts
        rm -f "$JOB.pdf"
        echo "cleaned build artifacts and $JOB.pdf"
        exit 0
        ;;
    build)
        ;;
    *)
        echo "unknown target: $1" >&2
        exit 2
        ;;
esac

if command -v latexmk >/dev/null 2>&1; then
    latexmk -pdf -halt-on-error -interaction=nonstopmode "$JOB.tex"
elif command -v pdflatex >/dev/null 2>&1; then
    pdflatex -halt-on-error -interaction=nonstopmode "$JOB.tex"
    if command -v bibtex >/dev/null 2>&1; then
        # refs.bib is empty until the verified-bibliography pass lands, so a
        # bibtex failure here is non-fatal.
        bibtex "$JOB" || echo "bibtex reported an issue (expected while refs.bib is empty)"
    fi
    pdflatex -halt-on-error -interaction=nonstopmode "$JOB.tex"
    pdflatex -halt-on-error -interaction=nonstopmode "$JOB.tex"
else
    echo "no LaTeX toolchain found: install TeX Live, MiKTeX, or tectonic" >&2
    exit 127
fi

echo "built $HERE/$JOB.pdf"
