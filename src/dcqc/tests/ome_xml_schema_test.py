from dcqc.tests.base_test import ExternalBaseTest, Process


class OmeXmlSchemaTest(ExternalBaseTest):
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
