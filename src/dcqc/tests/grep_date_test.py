from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier


class GrepDateTest(ExternalBaseTest):
    """Tests if a file has the word "date" or "time" in it.
    Used for dtecting potential PHI in files.
    """

    tier = TestTier.SUBJECTIVE_CONFORMANCE
    pass_code = 1
    fail_code = 0
    failure_reason_location = "std_out"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "grep",
            "-E",  # extended regular expression
            "-i",  # case insensitive
            "-a",  # treat input as text
            "'date|time'",  # match date or time
            f"'{path.name}'",
        ]
        process = Process(
            container="quay.io/biocontainers/coreutils:8.30--h14c3975_1000",
            command_args=command_args,
        )
        return process
