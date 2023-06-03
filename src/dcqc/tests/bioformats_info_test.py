from dcqc.target import Target
from dcqc.tests.base_test import ExternalBaseTest, Process


class BioFormatsInfoTest(ExternalBaseTest):
    tier = 2
    target: Target

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "/opt/bftools/showinf",
            "-nopix",
            "-novalid",
            "-nocore",
            path,
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process
