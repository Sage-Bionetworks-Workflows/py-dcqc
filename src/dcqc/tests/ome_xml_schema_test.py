from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process


class OmeXmlSchemaTest(ExternalBaseTest):
    tier = 2
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "/opt/bftools/xmlvalid",
            path,
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process
