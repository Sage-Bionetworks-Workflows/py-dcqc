from dcqc.tests.base import BaseTest, ExternalTestMixin, Process


class LibTiffInfoTest(ExternalTestMixin, BaseTest):
    tier = 2

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = ["tiffinfo", file.local_path.as_posix()]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process
