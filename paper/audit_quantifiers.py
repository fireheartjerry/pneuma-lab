"""List every absolute quantifier in the paper so each can be checked.

Defect ten was "the verbalized integer is worse than either logit readout on every
axis we measure", false on two of six, with the counterexample printed in the same
sentence. Absolute quantifiers are the highest-risk claims in a paper about
overstatement: they are the easiest for a reviewer to falsify, they need only one
counterexample, and they survive edits that change the underlying numbers because
the word itself does not change.

No mechanical check can decide whether "every" is true -- that needs the data and
the meaning. This produces the worklist.
"""

from __future__ import annotations

import re
from pathlib import Path

TEX = Path("C:/pneuma-lab/.claude/worktrees/neurips-2026-empirical/paper/placebo.tex")

ABSOLUTE = re.compile(
    r"\b(every|all four|all six|all of them|none of|nothing|never|always|"
    r"each of|no method|any of|entirely|exclusively|only)\b",
    re.IGNORECASE,
)


def sentences(text: str) -> list[str]:
    body = "\n".join(
        line for line in text.split("\n") if not line.strip().startswith("%")
    )
    body = re.sub(r"\\(textbf|emph|textit|texttt)\{([^{}]*)\}", r"\2", body)
    body = re.sub(r"\\citep?\{[^}]*\}", "", body)
    body = re.sub(r"\\ref\{[^}]*\}", "X", body)
    body = re.sub(r"\s+", " ", body)
    return re.split(r"(?<=[.!?]) (?=[A-Z\\])", body)


def main() -> None:
    text = TEX.read_text(encoding="utf-8")
    hits = []
    for sentence in sentences(text):
        found = ABSOLUTE.findall(sentence)
        if found and re.search(r"\d", sentence):
            hits.append((sorted(set(w.lower() for w in found)), sentence.strip()))

    print(f"{len(hits)} absolute claim(s) carrying at least one number\n")
    print("Each needs one counterexample to be false. Check against the artifact,")
    print("not against memory of what the artifact used to say.\n")
    for index, (words, sentence) in enumerate(hits, 1):
        condensed = re.sub(r"\$([^$]*)\$", r"\1", sentence)
        print(f"[{index}] {', '.join(words)}")
        print(f"    {condensed[:250]}")
        print()


if __name__ == "__main__":
    main()
