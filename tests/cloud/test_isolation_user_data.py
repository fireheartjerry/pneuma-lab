from pathlib import Path


USER_DATA = Path("infra/aws/qualification-isolation-user-data.sh")


def test_isolation_action_has_bounded_public_pull_and_teardown_surface() -> None:
    script = USER_DATA.read_text(encoding="utf-8")

    assert 'ACTION_PREFIX="runs/qualification/isolation-001"' in script
    assert "--on-active=220m" in script
    assert "timeout 12600 python3" in script
    assert "--manifest \"$ROOT/inputs/cases.json\"" in script
    assert "--output \"$ROOT/outputs/isolation-receipt.json\"" in script
    assert "shutdown -h now" in script
