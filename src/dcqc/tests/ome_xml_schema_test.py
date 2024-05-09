from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier


class OmeXmlSchemaTest(ExternalBaseTest):
    """Tests if OME-TIFF file has valid XML metadata."""

    tier = TestTier.INTERNAL_CONFORMANCE
    pass_code = 0
    fail_code = 1
    failure_reason_location = "std_out"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "/opt/bftools/xmlvalid",
            f"'{path.name}'",
            "|",
            "grep",
            "'No validation errors found.'",
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process
