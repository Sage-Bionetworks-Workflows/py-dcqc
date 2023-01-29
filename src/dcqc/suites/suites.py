from dcqc.file import FileType
from dcqc.suites.suite_abc import SuiteABC
from dcqc.tests import tests


# TODO: Consider moving the filetype-test association logic
#       to the file types
class FileSuite(SuiteABC):
    file_type = FileType.get_file_type("*")
    add_tests = (tests.FileExtensionTest, tests.Md5ChecksumTest)


class JsonSuite(FileSuite):
    file_type = FileType.get_file_type("JSON")
    add_tests = (tests.JsonLoadTest,)


class JsonLdSuite(JsonSuite):
    file_type = FileType.get_file_type("JSON-LD")
    add_tests = (tests.JsonLdLoadTest,)


class TiffSuite(FileSuite):
    file_type = FileType.get_file_type("TIFF")
    add_tests = (tests.LibTiffInfoTest,)


class OmeTiffSuite(TiffSuite):
    file_type = FileType.get_file_type("OME-TIFF")
    add_tests = (tests.OmeXmlSchemaTest, tests.BioFormatsInfoTest)
