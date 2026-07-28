# Makefile for the NeurIPS 2026 workshop submission.
#
#     make            build main.pdf
#     make clean      remove LaTeX build artifacts (keeps the PDF)
#     make distclean  remove build artifacts and the PDF
#     make blindcheck fail if an identifying string survives into main.pdf
#
# Recipe lines below are TAB-indented because GNU make requires it; every
# other file in this directory uses 4-space indentation.

JOB = main
ARTIFACT_EXTS = aux fdb_latexmk fls log out bbl blg synctex.gz toc
ARTIFACTS = $(foreach ext,$(ARTIFACT_EXTS),$(JOB).$(ext))

# Strings that must never appear in a submitted double-blind PDF.
BLIND_FORBIDDEN = Pneuma

.PHONY: all clean distclean blindcheck preflight

all: $(JOB).pdf

$(JOB).pdf: $(JOB).tex refs.bib neurips_2026.sty
	latexmk -pdf -halt-on-error -interaction=nonstopmode $(JOB).tex

clean:
	rm -f $(ARTIFACTS)

distclean: clean
	rm -f $(JOB).pdf

blindcheck: $(JOB).pdf
	@pdftotext $(JOB).pdf - > $(JOB).blindcheck.txt 2>/dev/null || \
	    { echo "blindcheck SKIPPED: pdftotext not installed"; exit 0; }
	@if grep -i -e "$(BLIND_FORBIDDEN)" $(JOB).blindcheck.txt; then \
	    echo "BLINDCHECK FAILED: forbidden string found in $(JOB).pdf"; \
	    rm -f $(JOB).blindcheck.txt; exit 1; \
	else \
	    echo "blindcheck OK: no forbidden string in $(JOB).pdf text layer"; \
	    rm -f $(JOB).blindcheck.txt; \
	fi

# Mechanical pre-submission checks against the BUILT pdf and its source.
# Supersedes blindcheck, which only looked for one forbidden string in the text
# layer. preflight additionally catches silently mangled control sequences
# (a stray tab turns 	extbf into literal "extbf{...}" and LaTeX exits 0),
# unfilled placeholders, Type 3 fonts, unembedded fonts, populated metadata,
# and identifying strings in the raw stream as well as the text layer.
preflight: $(JOB).pdf
	@JOB=$(JOB) ./preflight.sh
