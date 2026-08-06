"""Autonomous, versioned PLACEBO experiment campaign control plane."""

from .impact import ImpactDecision, classify_change
from .decision import CampaignDecision, Evaluation, decide_result
from .orchestrator import CampaignOrchestrator
from .records import CampaignManifest, ExperimentVersion
from .spend import SpendLedger

__all__ = [
    "CampaignManifest",
    "CampaignDecision",
    "CampaignOrchestrator",
    "Evaluation",
    "ExperimentVersion",
    "ImpactDecision",
    "SpendLedger",
    "classify_change",
    "decide_result",
]
