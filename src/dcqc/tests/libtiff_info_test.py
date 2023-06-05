from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class LibTiffInfoTest(ExternalBaseTest):
    tier = 2
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "tiffinfo",
            path,
        ]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process
