"""Tiny fault-injection surface for the cloud control-plane logic."""

from dataclasses import dataclass

from ..errors import CloudManifestError


@dataclass
class LocalControlPlane:
    submitted: set[str]
    outputs: dict[str, bytes]
    torn_down: bool = False

    def __init__(self) -> None:
        self.submitted = set()
        self.outputs = {}

    def submit(self, assignment_id: str) -> None:
        if self.torn_down or assignment_id in self.submitted:
            raise CloudManifestError("duplicate delivery or post-teardown submit")
        self.submitted.add(assignment_id)

    def publish(self, assignment_id: str, payload: bytes, expected: bytes) -> None:
        if assignment_id not in self.submitted or payload != expected:
            raise CloudManifestError("corrupt or unowned output")
        self.outputs[assignment_id] = payload

    def teardown(self) -> None:
        self.torn_down = True
