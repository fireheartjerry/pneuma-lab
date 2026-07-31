import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.secrets_aws import validate_class_b_reference


def test_class_b_secret_ref_never_accepts_class_a_material() -> None:
    assert validate_class_b_reference("arn:aws:secretsmanager:us-east-1:1:secret:registry")
    with pytest.raises(CloudManifestError): validate_class_b_reference("arn:aws:secretsmanager:us-east-1:1:secret:unblind")
