from dcqc.tests.base_test import ExternalBaseTest, Process


class LibTiffInfoTest(ExternalBaseTest):
    tier = 2
    pass_code = "0"

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = ["tiffinfo", file.local_path.as_posix()]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process
