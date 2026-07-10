"""Pure, deterministic 3-candidate global-workspace competition.

Candidates: risk_instinct, memory_scar, uncertainty_self_model. Highest salience
wins; ties break by the fixed CANDIDATE_ORDER (deterministic). The named salience
terms map onto the WorkspaceBroadcast schema's risk / scar_tissue / uncertainty.
"""

from __future__ import annotations

CANDIDATE_ORDER = ("risk_instinct", "memory_scar", "uncertainty_self_model")
_TERM = {
    "risk_instinct": "risk",
    "memory_scar": "scar_tissue",
    "uncertainty_self_model": "uncertainty",
}


def compete(candidates: dict) -> dict:
    """Return the winning faculty + salience terms + losing competitors."""
    ordered = [
        (name, round(float(candidates.get(name, 0.0)), 6)) for name in CANDIDATE_ORDER
    ]
    winner_name, winner_sal = max(
        ordered, key=lambda kv: (kv[1], -CANDIDATE_ORDER.index(kv[0]))
    )
    salience_scores = {_TERM[name]: sal for name, sal in ordered}
    competitors = [
        {"faculty": name, "salience": sal}
        for name, sal in ordered
        if name != winner_name
    ]
    return {
        "winning_faculty": winner_name,
        "winning_salience": winner_sal,
        "salience_scores": salience_scores,
        "competitors": competitors,
        "conviction": min(1.0, max(0.0, winner_sal)),
    }
