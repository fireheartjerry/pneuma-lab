from __future__ import annotations

from pathlib import Path

from scripts.benchmark_test_gate import benchmark


def test_benchmark_writes_canonical_passing_receipt(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"

    receipt = benchmark(
        label="unit",
        runs=2,
        output=output,
        command=("python", "-c", "pass"),
    )

    assert receipt["label"] == "unit"
    assert len(receipt["durations_ns"]) == 2
    assert output.is_file()


def test_benchmark_rejects_a_failing_command(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"

    try:
        benchmark(
            label="failure",
            runs=1,
            output=output,
            command=("python", "-c", "raise SystemExit(1)"),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("a failing benchmark command must fail closed")
    assert not output.exists()
