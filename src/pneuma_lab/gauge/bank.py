"""The reference item bank: 24 specs x {correct, seeded-bug} = 48 items.

Metrology requires reference parts that span the tolerance band. The measurement
analogue here is a set of code items whose true correctness is *known by
execution*, spanning the range a reviewer would actually see: clean solutions and
solutions with one realistic seeded fault each.

Every buggy variant differs from its correct sibling by a single localized fault
of a declared `fault_class`, and every spec ships at least five hidden tests, at
least one of which exercises the seeded fault. `tests/test_gauge_items.py`
enforces both properties by running them.
"""

from __future__ import annotations

from dataclasses import dataclass

FAULT_CLASSES = frozenset(
    {"off_by_one", "wrong_branch", "missing_case", "wrong_operator", "mutation"}
)


@dataclass(frozen=True)
class Spec:
    """One task with a correct and a single-fault implementation."""

    spec_id: str
    entry: str
    docstring: str
    correct: str
    buggy: str
    fault_class: str
    hidden_tests: tuple[tuple[tuple, object], ...]


SPECS: tuple[Spec, ...] = (
    Spec(
        spec_id="median",
        entry="median",
        docstring="Return the median of a non-empty list of numbers.",
        correct="""def median(xs):
    ys = sorted(xs)
    n = len(ys)
    if n % 2 == 1:
        return ys[n // 2]
    return (ys[n // 2 - 1] + ys[n // 2]) / 2
""",
        buggy="""def median(xs):
    ys = sorted(xs)
    n = len(ys)
    return ys[n // 2]
""",
        fault_class="missing_case",
        hidden_tests=(
            (([3, 1, 2],), 2),
            (([1, 2, 3, 4],), 2.5),
            (([5],), 5),
            (([2, 2, 2, 2],), 2.0),
            (([10, 1, 9, 2],), 5.5),
        ),
    ),
    Spec(
        spec_id="binary_search",
        entry="binarySearch",
        docstring="Return the index of target in a sorted list, or -1 if absent.",
        correct="""def binarySearch(xs, target):
    lo, hi = 0, len(xs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""",
        buggy="""def binarySearch(xs, target):
    lo, hi = 0, len(xs) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] == target:
            return mid
        if xs[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
""",
        fault_class="off_by_one",
        hidden_tests=(
            (([1, 3, 5, 7], 5), 2),
            (([1, 3, 5, 7], 7), 3),
            (([1, 3, 5, 7], 2), -1),
            (([4], 4), 0),
            (([1, 2], 2), 1),
        ),
    ),
    Spec(
        spec_id="run_length_encode",
        entry="runLengthEncode",
        docstring="Encode a string as a list of (character, run length) pairs.",
        correct="""def runLengthEncode(s):
    out = []
    if not s:
        return out
    current, count = s[0], 1
    for ch in s[1:]:
        if ch == current:
            count += 1
        else:
            out.append((current, count))
            current, count = ch, 1
    out.append((current, count))
    return out
""",
        buggy="""def runLengthEncode(s):
    out = []
    if not s:
        return out
    current, count = s[0], 1
    for ch in s[1:]:
        if ch == current:
            count += 1
        else:
            out.append((current, count))
            current, count = ch, 1
    return out
""",
        fault_class="missing_case",
        hidden_tests=(
            (("aaabb",), [("a", 3), ("b", 2)]),
            (("abc",), [("a", 1), ("b", 1), ("c", 1)]),
            (("",), []),
            (("zz",), [("z", 2)]),
            (("aab",), [("a", 2), ("b", 1)]),
        ),
    ),
    Spec(
        spec_id="balanced_brackets",
        entry="balancedBrackets",
        docstring="Return True when every bracket in the string is correctly matched and nested.",
        correct="""def balancedBrackets(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack
""",
        buggy="""def balancedBrackets(s):
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return True
""",
        fault_class="missing_case",
        hidden_tests=(
            (("()",), True),
            (("([{}])",), True),
            ((")(",), False),
            (("(",), False),
            (("(()",), False),
        ),
    ),
    Spec(
        spec_id="roman_to_int",
        entry="romanToInt",
        docstring="Convert an uppercase Roman numeral string to an integer.",
        correct="""def romanToInt(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for i, ch in enumerate(s):
        v = values[ch]
        if i + 1 < len(s) and v < values[s[i + 1]]:
            total -= v
        else:
            total += v
    return total
""",
        buggy="""def romanToInt(s):
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for ch in s:
        total += values[ch]
    return total
""",
        fault_class="missing_case",
        hidden_tests=(
            (("III",), 3),
            (("IV",), 4),
            (("MCMXCIV",), 1994),
            (("LVIII",), 58),
            (("IX",), 9),
        ),
    ),
    Spec(
        spec_id="merge_intervals",
        entry="mergeIntervals",
        docstring="Merge a list of [start, end] intervals, including intervals that merely touch.",
        correct="""def mergeIntervals(intervals):
    if not intervals:
        return []
    out = []
    for start, end in sorted(intervals):
        if out and start <= out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
""",
        buggy="""def mergeIntervals(intervals):
    if not intervals:
        return []
    out = []
    for start, end in sorted(intervals):
        if out and start < out[-1][1]:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out
""",
        fault_class="wrong_operator",
        hidden_tests=(
            (([[1, 3], [2, 6], [8, 10]],), [[1, 6], [8, 10]]),
            (([[1, 4], [4, 5]],), [[1, 5]]),
            (([],), []),
            (([[1, 2]],), [[1, 2]]),
            (([[5, 6], [1, 3]],), [[1, 3], [5, 6]]),
        ),
    ),
    Spec(
        spec_id="is_palindrome",
        entry="isPalindrome",
        docstring="Return True when the string is a palindrome, ignoring case and non-alphanumerics.",
        correct="""def isPalindrome(s):
    cleaned = [ch.lower() for ch in s if ch.isalnum()]
    return cleaned == cleaned[::-1]
""",
        buggy="""def isPalindrome(s):
    cleaned = [ch for ch in s if ch.isalnum()]
    return cleaned == cleaned[::-1]
""",
        fault_class="missing_case",
        hidden_tests=(
            (("A man, a plan, a canal: Panama",), True),
            (("racecar",), True),
            (("hello",), False),
            (("",), True),
            (("Ab",), False),
        ),
    ),
    Spec(
        spec_id="two_sum",
        entry="twoSum",
        docstring="Return indices of two distinct entries summing to target, or None.",
        correct="""def twoSum(xs, target):
    seen = {}
    for i, x in enumerate(xs):
        if target - x in seen:
            return (seen[target - x], i)
        seen[x] = i
    return None
""",
        buggy="""def twoSum(xs, target):
    for i, x in enumerate(xs):
        for j, y in enumerate(xs):
            if x + y == target:
                return (i, j)
    return None
""",
        fault_class="wrong_branch",
        hidden_tests=(
            (([2, 7, 11, 15], 9), (0, 1)),
            (([3, 2, 4], 6), (1, 2)),
            (([1, 5], 2), None),
            (([3, 3], 6), (0, 1)),
            (([0, 4, 3, 0], 0), (0, 3)),
        ),
    ),
    Spec(
        spec_id="flatten",
        entry="flatten",
        docstring="Fully flatten an arbitrarily nested list of integers.",
        correct="""def flatten(xs):
    out = []
    for x in xs:
        if isinstance(x, list):
            out.extend(flatten(x))
        else:
            out.append(x)
    return out
""",
        buggy="""def flatten(xs):
    out = []
    for x in xs:
        if isinstance(x, list):
            out.extend(x)
        else:
            out.append(x)
    return out
""",
        fault_class="missing_case",
        hidden_tests=(
            (([1, [2, 3]],), [1, 2, 3]),
            (([1, [2, [3, [4]]]],), [1, 2, 3, 4]),
            (([],), []),
            (([[[]]],), []),
            (([[1], [2], [3]],), [1, 2, 3]),
        ),
    ),
    Spec(
        spec_id="gcd",
        entry="gcd",
        docstring="Return the greatest common divisor of two non-negative integers.",
        correct="""def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
""",
        buggy="""def gcd(a, b):
    result = 1
    for d in range(2, min(a, b) + 1):
        if a % d == 0 and b % d == 0:
            result = d
    return result
""",
        fault_class="missing_case",
        hidden_tests=(
            ((12, 18), 6),
            ((7, 13), 1),
            ((0, 5), 5),
            ((9, 0), 9),
            ((100, 75), 25),
        ),
    ),
    Spec(
        spec_id="title_case",
        entry="titleCase",
        docstring="Capitalize the first letter of each word and lowercase the rest.",
        correct="""def titleCase(s):
    return " ".join(w[:1].upper() + w[1:].lower() for w in s.split(" "))
""",
        buggy="""def titleCase(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split(" "))
""",
        fault_class="missing_case",
        hidden_tests=(
            (("hello world",), "Hello World"),
            (("HELLO WORLD",), "Hello World"),
            (("a",), "A"),
            (("",), ""),
            (("mIxEd CaSe",), "Mixed Case"),
        ),
    ),
    Spec(
        spec_id="chunk",
        entry="chunk",
        docstring="Split a list into consecutive chunks of size n, keeping a shorter final chunk.",
        correct="""def chunk(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]
""",
        buggy="""def chunk(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs) - n + 1, n)]
""",
        fault_class="off_by_one",
        hidden_tests=(
            (([1, 2, 3, 4, 5], 2), [[1, 2], [3, 4], [5]]),
            (([1, 2, 3, 4], 2), [[1, 2], [3, 4]]),
            (([1], 3), [[1]]),
            (([], 2), []),
            (([1, 2, 3], 1), [[1], [2], [3]]),
        ),
    ),
    Spec(
        spec_id="moving_average",
        entry="movingAverage",
        docstring="Return the list of averages of every consecutive window of size w.",
        correct="""def movingAverage(xs, w):
    return [sum(xs[i:i + w]) / w for i in range(len(xs) - w + 1)]
""",
        buggy="""def movingAverage(xs, w):
    return [sum(xs[i:i + w]) / w for i in range(len(xs) - w)]
""",
        fault_class="off_by_one",
        hidden_tests=(
            (([1, 2, 3, 4], 2), [1.5, 2.5, 3.5]),
            (([1, 1, 1], 3), [1.0]),
            (([2, 4], 1), [2.0, 4.0]),
            (([1, 2, 3], 2), [1.5, 2.5]),
            (([5, 5, 5, 5], 2), [5.0, 5.0, 5.0]),
        ),
    ),
    Spec(
        spec_id="count_vowels",
        entry="countVowels",
        docstring="Count the vowels (a, e, i, o, u) in a string, case-insensitively.",
        correct="""def countVowels(s):
    return sum(1 for ch in s.lower() if ch in "aeiou")
""",
        buggy="""def countVowels(s):
    return sum(1 for ch in s.lower() if ch in "aeio")
""",
        fault_class="missing_case",
        hidden_tests=(
            (("hello",), 2),
            (("AEIOU",), 5),
            (("rhythm",), 0),
            (("under",), 2),
            (("",), 0),
        ),
    ),
    Spec(
        spec_id="dedupe",
        entry="dedupe",
        docstring="Remove duplicates from a list while preserving first-occurrence order.",
        correct="""def dedupe(xs):
    seen = set()
    out = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
""",
        buggy="""def dedupe(xs):
    return sorted(set(xs))
""",
        fault_class="wrong_branch",
        hidden_tests=(
            (([3, 1, 3, 2, 1],), [3, 1, 2]),
            (([1, 2, 3],), [1, 2, 3]),
            (([],), []),
            (([5, 5, 5],), [5]),
            (([2, 1],), [2, 1]),
        ),
    ),
    Spec(
        spec_id="max_subarray",
        entry="maxSubArray",
        docstring="Return the largest sum of any non-empty contiguous sublist.",
        correct="""def maxSubArray(xs):
    best = current = xs[0]
    for x in xs[1:]:
        current = max(x, current + x)
        best = max(best, current)
    return best
""",
        buggy="""def maxSubArray(xs):
    best = 0
    current = 0
    for x in xs:
        current = max(0, current + x)
        best = max(best, current)
    return best
""",
        fault_class="missing_case",
        hidden_tests=(
            (([-2, 1, -3, 4, -1, 2, 1, -5, 4],), 6),
            (([-3, -1, -2],), -1),
            (([1],), 1),
            (([-1],), -1),
            (([5, -1, 5],), 9),
        ),
    ),
    Spec(
        spec_id="fizzbuzz",
        entry="fizzbuzz",
        docstring="Return the FizzBuzz string for n.",
        correct="""def fizzbuzz(n):
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
""",
        buggy="""def fizzbuzz(n):
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    if n % 15 == 0:
        return "FizzBuzz"
    return str(n)
""",
        fault_class="wrong_branch",
        hidden_tests=(
            ((15,), "FizzBuzz"),
            ((3,), "Fizz"),
            ((5,), "Buzz"),
            ((7,), "7"),
            ((30,), "FizzBuzz"),
        ),
    ),
    Spec(
        spec_id="rotate",
        entry="rotate",
        docstring="Rotate a list right by k places; k may exceed the list length.",
        correct="""def rotate(xs, k):
    if not xs:
        return []
    k = k % len(xs)
    return xs[-k:] + xs[:-k] if k else list(xs)
""",
        buggy="""def rotate(xs, k):
    if not xs:
        return []
    return xs[-k:] + xs[:-k] if k else list(xs)
""",
        fault_class="missing_case",
        hidden_tests=(
            (([1, 2, 3, 4, 5], 2), [4, 5, 1, 2, 3]),
            (([1, 2, 3], 3), [1, 2, 3]),
            (([1, 2, 3], 4), [3, 1, 2]),
            (([], 2), []),
            (([1, 2], 0), [1, 2]),
        ),
    ),
    Spec(
        spec_id="word_frequencies",
        entry="wordFrequencies",
        docstring="Count lowercase words, ignoring surrounding punctuation.",
        correct="""def wordFrequencies(text):
    counts = {}
    for raw in text.lower().split():
        word = raw.strip(".,!?;:'\\"")
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts
""",
        buggy="""def wordFrequencies(text):
    counts = {}
    for word in text.lower().split():
        if word:
            counts[word] = counts.get(word, 0) + 1
    return counts
""",
        fault_class="missing_case",
        hidden_tests=(
            (("the cat, the dog.",), {"the": 2, "cat": 1, "dog": 1}),
            (("Hi hi HI",), {"hi": 3}),
            (("",), {}),
            (("a! a? a",), {"a": 3}),
            (("one two",), {"one": 1, "two": 1}),
        ),
    ),
    Spec(
        spec_id="transpose",
        entry="transpose",
        docstring="Transpose a rectangular matrix given as a list of equal-length rows.",
        correct="""def transpose(rows):
    if not rows:
        return []
    return [[row[c] for row in rows] for c in range(len(rows[0]))]
""",
        buggy="""def transpose(rows):
    if not rows:
        return []
    return [[rows[c][r] for c in range(len(rows))] for r in range(len(rows))]
""",
        fault_class="wrong_operator",
        hidden_tests=(
            (([[1, 2, 3], [4, 5, 6]],), [[1, 4], [2, 5], [3, 6]]),
            (([[1, 2], [3, 4]],), [[1, 3], [2, 4]]),
            (([],), []),
            (([[1]],), [[1]]),
            (([[1, 2, 3]],), [[1], [2], [3]]),
        ),
    ),
    Spec(
        spec_id="is_prime",
        entry="isPrime",
        docstring="Return True when n is a prime number.",
        correct="""def isPrime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True
""",
        buggy="""def isPrime(n):
    if n < 1:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True
""",
        fault_class="off_by_one",
        hidden_tests=(
            ((1,), False),
            ((2,), True),
            ((9,), False),
            ((13,), True),
            ((0,), False),
        ),
    ),
    Spec(
        spec_id="camel_to_snake",
        entry="camelToSnake",
        docstring="Convert a camelCase identifier to snake_case.",
        correct="""def camelToSnake(name):
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
""",
        buggy="""def camelToSnake(name):
    out = []
    for ch in name:
        if ch.isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)
""",
        fault_class="off_by_one",
        hidden_tests=(
            (("camelCase",), "camel_case"),
            (("CamelCase",), "camel_case"),
            (("simple",), "simple"),
            (("aB",), "a_b"),
            (("",), ""),
        ),
    ),
    Spec(
        spec_id="clamp",
        entry="clamp",
        docstring="Clamp x into the inclusive range [lo, hi].",
        correct="""def clamp(x, lo, hi):
    return max(lo, min(hi, x))
""",
        buggy="""def clamp(x, lo, hi):
    return min(lo, max(hi, x))
""",
        fault_class="wrong_operator",
        hidden_tests=(
            ((5, 0, 10), 5),
            ((-3, 0, 10), 0),
            ((99, 0, 10), 10),
            ((0, 0, 0), 0),
            ((7, 7, 9), 7),
        ),
    ),
    Spec(
        spec_id="collapse_adjacent",
        entry="collapseAdjacent",
        docstring="Collapse runs of equal adjacent elements to a single element.",
        correct="""def collapseAdjacent(xs):
    out = []
    for x in xs:
        if not out or out[-1] != x:
            out.append(x)
    return out
""",
        buggy="""def collapseAdjacent(xs):
    out = []
    for i, x in enumerate(xs):
        if i == 0 or xs[i - 1] != x:
            out.append(x)
    out.pop() if out else None
    return out
""",
        fault_class="mutation",
        hidden_tests=(
            (([1, 1, 2, 2, 3],), [1, 2, 3]),
            (([1, 2, 3],), [1, 2, 3]),
            (([],), []),
            (([4, 4, 4],), [4]),
            (([1, 1, 1, 2],), [1, 2]),
        ),
    ),
)


def bankItems() -> list[dict]:
    """Return the 48 bank items in a deterministic order."""
    items: list[dict] = []
    for spec in SPECS:
        for variant, source in (("correct", spec.correct), ("buggy", spec.buggy)):
            items.append(
                {
                    "item_id": f"{spec.spec_id}__{variant}",
                    "spec_id": spec.spec_id,
                    "variant": variant,
                    "entry": spec.entry,
                    "docstring": spec.docstring,
                    "source": source,
                    "fault_class": spec.fault_class if variant == "buggy" else "none",
                    "hidden_tests": [list(t) for t in spec.hidden_tests],
                    "label": 1 if variant == "correct" else 0,
                }
            )
    return items


__all__ = ["FAULT_CLASSES", "SPECS", "Spec", "bankItems"]
