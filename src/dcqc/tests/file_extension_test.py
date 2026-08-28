from dcqc.target import SingleTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus, TestTier


class FileExtensionTest(InternalBaseTest):
    """Tests if a file has a valid extension for its file type."""

    tier = TestTier.FILE_INTEGRITY
    target: SingleTarget

    def compute_status(self) -> TestStatus:
        """Check every file name against the extensions for its file type.

        A file passes if its name ends with any one of the extensions. The
        extensions are tested one at a time rather than passed to str.endswith
        as a group, so that any collection of strings works and not only a
        tuple. The first file that matches none of them fails the whole test.

        Returns:
            TestStatus.PASS if all file names have a valid extension,
            otherwise TestStatus.FAIL.
        """
        status = TestStatus.PASS
        for file in self.target.files:
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not any(file.name.endswith(ext) for ext in file_extensions):
                status = TestStatus.FAIL
                self.status_reason = (
                    f"File extension does not match one of: {file_extensions}"
                )
                break
        return status
