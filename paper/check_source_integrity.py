"""Detect control characters injected into the LaTeX source by editing accidents.

preflight.sh has checked for carriage returns since the first time this happened.
That check has never worked. It runs

    grep -c "$(printf '\\r')" placebo.tex

and under Git Bash on Windows grep normalises CRLF before matching, so it reports
0 on a file containing 898 carriage returns. The check most specific to this
defect was decorative, and it stayed decorative through every run because a
passing check is not investigated.

It failed live on 2026-07-27: a patch script written through a bash heredoc lost
one backslash level, so ``"Section~\\ref{...}"`` reached Python as ``"Section~"``
plus a CARRIAGE RETURN plus ``"ef{...}"``. LaTeX treated the CR as a line break,
consumed the brace as a group, and typeset ``Section efsec:population.`` into the
appendix. The build exited 0, the log was clean, and the PDF-side leak check
missed it too, because that check looks for ``ef{sec`` while the rendered text
reads ``efsec`` -- the brace is gone by then.

So this checks the CAUSE rather than the symptom, in Python where the bytes are
visible:

  * a carriage return anywhere other than immediately before a line feed
  * a literal tab, which is how ``\\t`` in an unescaped patch string arrives
  * any other C0 control character except tab, LF and CR

Run: python paper/check_source_integrity.py [job]
Exit 0 when the source carries no injected control characters.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Escapes that a lost backslash level turns into a control character. \r is the
# dangerous one because \ref is the most common macro in cross-referenced prose.
DANGEROUS = {
    "\r": r"\r -- from \ref, \right, \rule",
    "\t": r"\t -- from \textbf, \textit, \texttt, \table",
    "\n": r"\n -- from \newcommand, \newline, \node",
    "\f": r"\f -- from \frac, \footnote",
    "\v": r"\v -- from \vspace, \vfill",
    "\b": r"\b -- from \begin, \bibliography, \bf",
    "\a": r"\a -- from \alpha, \author",
}


# Macro tails that can only appear at the start of a line if the backslash was
# lost. Each is a real macro minus its first character.
REMNANTS = (
    "ef{",  # \ref
    "extbf{",  # \textbf
    "extit{",  # \textit
    "exttt{",  # \texttt
    "emph{",  # \emph -- \e is not an escape, but a lost backslash still lands here
    "egin{",  # \begin
    "nd{",  # \end
    "ite{",  # \cite
    "itep{",  # \citep
    "abel{",  # \label
    "ection{",  # \section
    "ubsection{",  # \subsection
    "ewcommand",  # \newcommand
    "rac{",  # \frac
    "ootnote{",  # \footnote
)


def main() -> int:
    job = sys.argv[1] if len(sys.argv) > 1 else "placebo"
    source = HERE / f"{job}.tex"
    if not source.is_file():
        print(f"no source at {source}")
        return 0

    data = source.read_bytes()
    # Split on the line terminator so a well-formed CRLF does not look like a
    # stray CR. Whatever remains inside a line is an injection.
    lines = data.replace(b"\r\n", b"\n").split(b"\n")

    problems: list[str] = []
    for number, line in enumerate(lines, 1):
        for raw, why in DANGEROUS.items():
            if raw == "\n":
                continue  # cannot survive the split
            if raw.encode() in line:
                text = line.decode("utf-8", errors="replace")
                index = text.find(raw)
                context = text[max(0, index - 30) : index + 30]
                readable = context.replace(raw, f"<{raw.encode().hex().upper()}>")
                problems.append(f"line {number}: {why}\n      ...{readable}...")

    # A carriage return that lands directly before the line's own line feed is
    # indistinguishable from an ordinary CRLF terminator, so the scan above cannot
    # see it -- the remnant simply becomes the start of the NEXT line. That case
    # was live in this paper and printed "Section efsec:floors" into the PDF.
    #
    # The complementary signal is a line that BEGINS with a macro remnant. No
    # sentence here starts with "ef{" or "extbf{"; such a line is the tail of a
    # macro whose backslash was consumed by a line break.
    for number, line in enumerate(lines, 1):
        text = line.decode("utf-8", errors="replace")
        for remnant in REMNANTS:
            if text.startswith(remnant):
                problems.append(
                    f"line {number}: begins with {remnant!r} -- a macro remnant, "
                    f"so the backslash was eaten by the preceding line break\n"
                    f"      ...{text[:60]}..."
                )
                break

    if not problems:
        print(f"OK    no injected control characters in {job}.tex")
        return 0

    print(f"FAIL  {len(problems)} injected control character(s) in {job}.tex.")
    print("      A lost backslash level turns a macro into a control character.")
    print("      LaTeX accepts the result and typesets the remainder literally,")
    print("      so the build exits 0 and the damage is only visible in the PDF.")
    print("      Write patch scripts to a file and run the file; do not pipe a")
    print("      heredoc, which strips one backslash level.")
    for problem in problems:
        print(f"\n  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
