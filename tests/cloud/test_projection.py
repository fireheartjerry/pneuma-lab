import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.projection import require_within_projection


def test_projection_boundary_fails_closed() -> None:
    require_within_projection(10, 10)
    with pytest.raises(CloudManifestError): require_within_projection(10.01, 10)
