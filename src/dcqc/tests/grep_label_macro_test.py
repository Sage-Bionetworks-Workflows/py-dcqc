from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class GrepLabelMacroTest(ExternalBaseTest):
    tier = 4
    pass_code = "1"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "tifftools",
            "dump",
            f"'{path.name}'",
            "|",
            "grep",  # pipe the output
            "-E"  # extended regular expression
            "-i"  # Case insensitive
            "-a",  # treat input as text
            "-q",  # suppress output
            "'label|macro'",  # match the DateTime 306 tag
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/tifftools:latest",
            command_args=command_args,
        )
        return process
