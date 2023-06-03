from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class TiffTag306DateTimeTest(ExternalBaseTest):
    tier = 4
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "!",  # negate exit status
            "tifftools",
            "dump",
            path,
            "|",
            "grep",  # pipe the output
            "-a",  # treat input as text
            "-q",  # suppress output
            "'DateTime 306 (0x132) ASCII'",  # match the DateTime 306 tag
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/tifftools:latest",
            command_args=command_args,
        )
        return process
