from pathlib import Path


SCRIPT = Path("scripts/research/build_step5b_c120_final_audits.py")


def test_final_audit_builder_fixes_registered_c120_terms_without_weakening() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert '"fixed_reserve": 1' in source
    assert '"pilot_units": 1' in source
    assert '"pairs_attempted": 3, "pairs_independent_pass": 3' in source
    assert '"proxy_basis": "base_commit_admissible"' in source
    assert '"proxy_basis": "pinned_objective_pool"' in source
    assert "require_isolation_receipt(" in source
