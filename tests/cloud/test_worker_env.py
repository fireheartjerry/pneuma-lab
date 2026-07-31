import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.worker_env import build_worker_env


def test_worker_env_rejects_arm_and_authority_material() -> None:
    assert build_worker_env({"TASK_PACKET": "opaque"}) == {"TASK_PACKET": "opaque"}
    with pytest.raises(CloudManifestError): build_worker_env({"ARM": "REAL"})
