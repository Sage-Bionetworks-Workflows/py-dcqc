from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier


class TiffDateTimeTest(ExternalBaseTest):
    """Tests if a TIFF file has the word "date" or "time" in its metadata.
    Used for detecting potential PHI in files.
    """

    tier = TestTier.SUBJECTIVE_CONFORMANCE
    pass_code = 1
    fail_code = 0
    failure_reason_location = "std_out"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "tifftools",
            "dump",
            f"'{path.name}'",
            "--json",
            "--silent",
            "|",
            "jq",
            "-e",
            "'.[].ifds[].tags[]'.data",
            "|",
            "grep",
            "-Ei",
            "'date|time'",
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/tifftools:latest",
            command_args=command_args,
        )
        return process
