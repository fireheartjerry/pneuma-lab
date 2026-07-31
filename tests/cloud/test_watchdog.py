import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.watchdog import require_fresh_watchdog


def test_stale_watchdog_or_overrun_blocks_new_work() -> None:
    require_fresh_watchdog(11, 10, 9, 10)
    with pytest.raises(CloudManifestError): require_fresh_watchdog(10, 10, 9, 10)
    with pytest.raises(CloudManifestError): require_fresh_watchdog(11, 10, 11, 10)
