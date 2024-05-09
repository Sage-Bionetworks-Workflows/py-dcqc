from dcqc.target import SingleTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class FileExtensionTest(InternalBaseTest):
    """Tests if a file has a valid extension for its file type."""

    tier = 1
    target: SingleTarget

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not file.name.endswith(file_extensions):
                status = TestStatus.FAIL
                self.failure_reason = (
                    f"File extension does not match one of: {file_extensions}"
                )
                break
        return status
