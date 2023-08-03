from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class GrepDateTest(ExternalBaseTest):
    tier = 4
    pass_code = "1"
    fail_code = "0"
    reason = ""
    reason_location = "std_out"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "grep",
            "-E",  # extended regular expression
            "-i",  # case insensitive
            "-a",  # treat input as text
            # "-q",  # suppress output
            "'date|time'",  # match date or time
            f"'abc.txt'",
        ]
        process = Process(
            container="quay.io/biocontainers/coreutils:8.30--h14c3975_1000",
            command_args=command_args,
        )
        return process
