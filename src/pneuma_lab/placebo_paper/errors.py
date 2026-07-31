"""Fail-closed errors for the PLACEBO result-to-paper pipeline.

Each of these means the manuscript does not get its numbers. There is no
partial fill and no warning-and-continue: a paper that renders some numbers
from a verified package and others from a rejected one is worse than a paper
with visible empty slots, because the reader cannot tell which is which.
"""

from __future__ import annotations


class PlaceboPaperError(Exception):
    """Base class for every result-to-paper failure."""


class PackageRejected(PlaceboPaperError):
    """The supplied evidence package is not an admissible source of numbers."""


class WrongLineage(PackageRejected):
    """The package comes from a lineage that may not produce paper numbers."""


class UnsealedPackage(PackageRejected):
    """The package or its artifact root is not sealed and verified."""


class WrongAuthority(PackageRejected):
    """The package was produced under an authority that does not license it."""


class MissingReceipt(PackageRejected):
    """A required receipt is absent from the package."""


class ManualNumberError(PlaceboPaperError):
    """A scientific number was supplied by hand rather than emitted."""


class PlaceholderError(PlaceboPaperError):
    """The manuscript still contains an unresolved placeholder."""


class AnonymityError(PlaceboPaperError):
    """The manuscript would break double-blind review."""


class PageBudgetError(PlaceboPaperError):
    """The manuscript exceeds the venue's body page budget."""


class BibliographyError(PlaceboPaperError):
    """A citation is unresolved, undefined, or unused."""
