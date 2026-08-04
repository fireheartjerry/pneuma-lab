# PLACEBO Trial paper materials

`paper/placebo_protocol.tex` is the maintained manuscript, and `paper/main.tex`
is its conventional build entrypoint. The retired `paper/placebo.tex` draft and
the upstream `paper/neurips_2026.sty` remain unchanged.

| path | what it is |
| --- | --- |
| `../placebo_protocol.tex` | canonical pre-results, double-blind manuscript |
| `refs-placebo.bib` | PLACEBO-specific records; `../refs.bib` is the shared library |
| `citation-queue.json` | primary-record checks; every entry is verified |
| `source-ledger.md` | all 26 active citation keys and the claim each supports |
| `claims.json` | declared claims and the receipt that would support each |
| `generated/` | emitted tables, figure data, claim matrix, artifact appendix — never hand-edited |

## Commands

```sh
# every manuscript check; exits 1 while blocked
python -m pneuma_lab.placebo_paper preflight

# regenerate the scaffold (or the filled assets, with --package)
python -m pneuma_lab.placebo_paper render --out paper/placebo/generated

# admit a sealed Task 10 package, or see exactly why it was refused
python -m pneuma_lab.placebo_paper admit --package <dir>
```

## State

The scientific preflight **blocks**, and should. No arm result or sealed
evidence package exists, so the draft notice and result slots remain visible.
The citation blocker is closed, and the canonical source compiles to 8 body
pages plus 2 reference pages. See
`docs/research/placebo-paper/00-result-to-paper-pipeline.md` for the live failure
list and what discharges each item.
