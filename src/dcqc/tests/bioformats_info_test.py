from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier


class BioFormatsInfoTest(ExternalBaseTest):
    """Tests if a file is valid OME-TIFF."""

    tier = TestTier.INTERNAL_CONFORMANCE
    pass_code = 0
    fail_code = 1
    failure_reason_location = "std_err"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "/opt/bftools/showinf",
            "-nopix",
            "-novalid",
            "-nocore",
            "-format",
            "OMETiff",
            f"'{path.name}'",
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process
