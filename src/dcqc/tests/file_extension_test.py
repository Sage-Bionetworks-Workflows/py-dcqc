from dcqc.target import SingleTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class FileExtensionTest(InternalBaseTest):
    tier = 1
    target: SingleTarget

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not file.name.endswith(file_extensions):
                status = TestStatus.FAIL
                break
        return status
