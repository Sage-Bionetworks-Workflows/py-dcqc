from dcqc.tests.base import BaseTest, TestStatus


class FileExtensionTest(BaseTest):
    tier = 1
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.get_files(staged=False):
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not file.name.endswith(file_extensions):
                status = TestStatus.FAIL
                break
        return status
