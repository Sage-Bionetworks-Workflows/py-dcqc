from dcqc.suites.suite_abc import SuiteABC
from dcqc.tests import tests


class FileSuite(SuiteABC):
    add_tests = (tests.FileExtensionTest, tests.Md5ChecksumTest)  # type: ignore


class TiffSuite(FileSuite):
    add_tests = (tests.LibTiffInfoTest,)  # type: ignore


class RedundantFileSuite(TiffSuite):
    del_tests = (tests.LibTiffInfoTest,)  # type: ignore


class OmeTiffSuite(TiffSuite):
    add_tests = (tests.OmeXmlSchemaTest, tests.BioFormatsInfoTest)  # type: ignore
