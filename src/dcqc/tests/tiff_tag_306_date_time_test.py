from dcqc.tests.base import BaseTest, ExternalTestMixin, Process


class TiffTag306DateTimeTest(ExternalTestMixin, BaseTest):
    tier = 4

    def generate_process(self) -> Process:
        file = self.get_file()
        path = file.local_path.as_posix()
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
