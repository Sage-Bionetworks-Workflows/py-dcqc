from dcqc.tests.base import BaseTest, ExternalTestMixin, Process


class GrepDateTest(ExternalTestMixin, BaseTest):
    tier = 4

    def generate_process(self) -> Process:
        file = self.get_file()
        path = file.local_path.as_posix()
        command_args = [
            "!",  # negate exit status
            "grep",
            "-E",  # extended regular expression
            "-i",  # case insensitive
            "-a",  # treat input as text
            "-q",  # suppress output
            "'date|time'",  # match date or time
            path,
        ]
        process = Process(
            container="quay.io/biocontainers/coreutils:8.30--h14c3975_1000",
            command_args=command_args,
        )
        return process
