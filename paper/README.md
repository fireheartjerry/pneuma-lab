# NeurIPS 2026 workshop submission

Skeleton for a submission to **"Who Verifies the Agents? Toward Reliable Agent
Development"** at NeurIPS 2026.

Working title: _Ten Conversations, Two Thousand Questions: What Agent-Memory
Evaluations Could Actually Have Detected_

## Venue facts

| Item                       | Value                                                                         |
| -------------------------- | ----------------------------------------------------------------------------- |
| Workshop                   | Who Verifies the Agents? Toward Reliable Agent Development                    |
| CFP                        | <https://verify-agents-workshop.github.io/>                                   |
| Page limit                 | **4-9 pages**, excluding references and appendices (demo papers: 4 pages max) |
| Body budget for this draft | ~7.0 pages (see per-section notes in `main.tex`)                              |
| Review                     | **Double-blind**                                                              |
| Archival                   | Non-archival; accepted work appears on OpenReview, not formal proceedings     |
| Deadline                   | **2026-08-29, 23:59 AoE**                                                     |
| Submission site            | OpenReview                                                                    |
| Template                   | NeurIPS 2026 official template, `dblblindworkshop` option                     |

Concurrent submission to other venues is permitted per the CFP.

## Style file provenance

Downloaded 2026-07-24 from the canonical NeurIPS media host. The primary URL
worked; no fallback source was needed.

**Archive:** <https://media.neurips.cc/Conferences/NeurIPS2026/Formatting_Instructions_For_NeurIPS_2026.zip>

| File                                                          | Bytes | SHA-256                                                            |
| ------------------------------------------------------------- | ----- | ------------------------------------------------------------------ |
| `Formatting_Instructions_For_NeurIPS_2026.zip` (the download) | 20259 | `82473931E3EF710FCD3F4A8CD4119B9DE32E56825F90F9E5A6D55F2D01B817D9` |
| `neurips_2026.sty`                                            | 13704 | `C3FC2894E83D2517CA18B66741D6C595986D97957DC08EC08BB2125A7EC4555A` |
| `neurips_2026.tex` (upstream template)                        | 19118 | `CF4CEE7991665306D1DAAA3985BE4FEEC7F8889D6D072FFA12F99A8E1537D797` |
| `checklist.tex` (upstream checklist)                          | 26167 | `780BA13C480F652DCC42E69ED61A752CE0EA270F15D332D4A45B059DABAD84F6` |

The `.sty` self-identifies as
`[2026-01-29 NeurIPS 2026 submission/camera-ready style file]`.

Files in this directory:

- `neurips_2026.sty` -- unmodified upstream copy. **Do not edit.**
- `neurips_2026_template_upstream.tex` -- unmodified copy of the upstream
  `neurips_2026.tex`, kept for reference only; it is not compiled.
- `neurips_2026_checklist_upstream.tex` -- unmodified copy of the upstream
  `checklist.tex`. The NeurIPS paper checklist is a main-conference
  requirement; the workshop CFP does not require it. Kept for reference.

To re-verify integrity:

```sh
sha256sum neurips_2026.sty
```

## Files

- `main.tex` -- the paper. Section stubs with per-section page budgets only;
  no prose (prose is authored in a separate pass).
- `refs.bib` -- empty placeholder. Entries arrive from a separate
  verified-bibliography pass. **No entry may be added without primary-source
  verification.**
- `build.sh` -- POSIX build script (`./build.sh`, `./build.sh clean`,
  `./build.sh distclean`).
- `Makefile` -- same targets plus `make blindcheck`. Requires GNU make.
- `.gitignore` -- LaTeX build artifacts and the compiled PDF.

## Building

```sh
./build.sh          # -> main.pdf
./build.sh clean    # remove aux/log/out/bbl/blg/fls/fdb/synctex, keep the PDF
./build.sh distclean

make                # same, if GNU make is available
make blindcheck     # fail if a forbidden string survives into main.pdf
```

Requires `latexmk` + `pdflatex` (TeX Live or MiKTeX). `build.sh` falls back to
a manual `pdflatex`/`bibtex`/`pdflatex`/`pdflatex` sequence if `latexmk` is
missing, and exits 127 with a clear message if no LaTeX toolchain is present.

`bibtex` emits an "Empty `thebibliography' environment" warning while
`refs.bib` is still empty. That is expected and disappears once entries land.

### Note on the first-page footer

In submission mode the style file prints _"Submitted to 40th Conference on
Neural Information Processing Systems (NeurIPS 2026). Do not distribute."_ The
workshop name set via `\workshoptitle{}` only appears in the footer for a
`final` (camera-ready) build. This is upstream behavior, not a configuration
error -- `\workshoptitle{}` is nonetheless required and is already set.

## Pre-submission checklist

Run every item against the **actual PDF being uploaded**, after the final
build. Do not check anything off from memory.

### Anonymization (double-blind)

- [ ] `main.tex` still uses `\usepackage[dblblindworkshop]{neurips_2026}` with
      **no** `final` and **no** `preprint` option; the title block must read
      "Anonymous Author(s)".
- [ ] The real `\author{...}` block is still commented out.
- [ ] **The string `Pneuma` does not appear anywhere in the PDF.** This is the
      repository/project name and it is identifying. Check the body, figures,
      table cells, code listings, file paths in screenshots, URLs, the
      reproducibility statement, and the PDF metadata.
      `sh
    pdftotext main.pdf - | grep -i pneuma        # must print nothing
    make blindcheck                              # same check, exits 1 on hit
    `
- [ ] No institution, funder, grant number, or acknowledgments section. The
      style file suppresses the `ack` environment in submission mode, but do
      not rely on that -- verify in the rendered PDF.
- [ ] No de-anonymizing URLs: no GitHub/GitLab org or user names, no personal
      or lab domains, no Hugging Face account names, no OpenReview profile
      links. Use an anonymized artifact host and cite it as such.
- [ ] Self-citations are phrased in the third person ("prior work by X shows"),
      never "our previous work".
- [ ] No identifying strings inside embedded figures. Vector figures carry
      searchable text -- run `pdftotext` on the _final_ PDF, not on the body
      source, so figure text is included.
- [ ] Supplementary material and appendices are anonymized to the same
      standard as the body.

### PDF metadata scrubbing

- [ ] `Author`, `Subject`, `Keywords`, `Creator`, and `Producer` are empty or
      non-identifying. `main.tex` already sets these to empty via
      `\hypersetup`. Verify:
      `sh
    pdfinfo main.pdf
    exiftool main.pdf        # if available; checks XMP too
    `
- [ ] No XMP metadata stream leaks a username or a local file path
      (`pdfinfo` reports `Metadata Stream: no` for the current build).
- [ ] No local filesystem paths from the build machine are embedded (these can
      contain a real name or the repository name). Grep the raw PDF:
      `sh
    grep -a -i -e pneuma -e "C:/Users" -e "/home/" main.pdf
    `
- [ ] If anything identifying is found and cannot be removed at the LaTeX
      level, scrub it before upload:
      `sh
    exiftool -all:all= -overwrite_original main.pdf
    `
      Then re-run `pdffonts` and `pdftotext` to confirm nothing else broke.

### Fonts and rendering

- [ ] **All fonts embedded.** Every row of `pdffonts main.pdf` must show
      `emb = yes`. The current build embeds four Type 1 faces
      (NimbusRomNo9L Medi/Regu, SFTT1000, NimbusSanL Regu), all `yes`.
      `sh
    pdffonts main.pdf
    `
- [ ] No Type 3 bitmap fonts (these come from bitmap `cm` fonts and render
      badly). If any appear, rebuild with `cm-super` / Type 1 fonts available.
- [ ] Page size is US Letter, 612 x 792 pt (`pdfinfo`). The style file sets
      `letterpaper`; do not override it with A4.
- [ ] Figures are vector (PDF) where possible; raster figures are >= 300 dpi.
- [ ] `main.log` is free of `!` errors and of `Overfull \hbox` warnings that
      push text into the margin.

### Length and structure

- [ ] Body is between 4 and 9 pages, counting from the title through the last
      numbered section. References and appendices are excluded.
- [ ] The reproducibility statement does not name the repository or any
      hosting account.
- [ ] Line numbers are present (submission mode adds them automatically) --
      their absence means a `final` or `preprint` option leaked in.
- [ ] Every citation resolves; no `[?]` markers in the rendered PDF.
- [ ] Every bibliography entry passed primary-source verification.
