from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier
from dcqc.tests.constants import LIBTIFF_CONTAINER


class LibTiffInfoTest(ExternalBaseTest):
    """Tests if a file is valid TIFF."""

    tier = TestTier.INTERNAL_CONFORMANCE
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
            container=LIBTIFF_CONTAINER,
            command_args=command_args,
        )
        return process
