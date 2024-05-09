from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class LibTiffInfoTest(ExternalBaseTest):
    """Tests if a file is valid TIFF."""

    tier = 2
    pass_code = 0
    fail_code = 1
    failure_reason_location = "std_err"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "tiffinfo",
            f"'{path.name}'",
        ]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process
