from dcqc.target import Target
from dcqc.tests.base_test import ExternalBaseTest, Process


class GrepDateTest(ExternalBaseTest):
    tier = 4
    target: Target

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "!",  # negate exit status
            "grep",
            "-E",  # extended regular expression
            "-i",  # case insensitive
            "-a",  # treat input as text
            "-q",  # suppress output
            "'date|time'",  # match date or time
            path,
        ]
        process = Process(
            container="quay.io/biocontainers/coreutils:8.30--h14c3975_1000",
            command_args=command_args,
        )
        return process
