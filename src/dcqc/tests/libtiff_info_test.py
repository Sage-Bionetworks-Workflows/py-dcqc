from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class LibTiffInfoTest(ExternalBaseTest):
    tier = 2
    pass_code = "0"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        # string_path = self._short_string_path(path, "dcqc-staged-")

        command_args = [
            "tiffinfo",
            f"'{path.name}'",
        ]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process
