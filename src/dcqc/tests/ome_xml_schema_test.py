from dcqc.tests.base import BaseTest, ExternalTestMixin, Process


class OmeXmlSchemaTest(ExternalTestMixin, BaseTest):
    tier = 2

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = [
            "/opt/bftools/xmlvalid",
            file.local_path.as_posix(),
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process
