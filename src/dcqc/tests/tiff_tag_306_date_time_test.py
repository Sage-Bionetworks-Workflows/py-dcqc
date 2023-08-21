from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class TiffTag306DateTimeTest(ExternalBaseTest):
    tier = 4
    pass_code = "1"
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
            "'.[].ifds[].tags['306']'",
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/tifftools:latest",
            command_args=command_args,
        )
        return process
