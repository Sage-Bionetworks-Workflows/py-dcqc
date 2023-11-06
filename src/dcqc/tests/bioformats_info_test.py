from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class BioFormatsInfoTest(ExternalBaseTest):
    tier = 2
    pass_code = "0"
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
