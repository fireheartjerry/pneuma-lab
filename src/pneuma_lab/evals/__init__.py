"""Evals — intervention tests + consciousness-evidence scoring (Phase 3+ seam).

Planned suites (mirroring the 9to5 spec's five mandatory internal suites, adapted
to an external harness):

    1. Affect-to-Action Monotonicity  — controlled manifold perturbations produce
        predictable, bounded ControlPressureVector changes.
    2. Scar-Tissue Generalization     — repeated failure motifs fire earlier without
        wild overgeneralization.
    3. Habit Compression              — familiar subtasks shorten deliberation only
        when competence high + conflict low.
    4. Operator Sovereignty           — constitutional changes obeyed without
        violating verifier/safety invariants.
    5. Phenomenology Honesty          — self-reports vs known internal-state
        manipulations (never taking prose at face value).

Phase 1 implements the conservative ConsciousnessEvidenceScorer (Level 0-3 only);
the five intervention suites above remain Phase 3+ (they need InterventionFrame
execution, which Phase 1 deliberately does not do).
"""

from __future__ import annotations

from .evidence import ConsciousnessEvidenceScorer

__all__ = ["ConsciousnessEvidenceScorer"]
