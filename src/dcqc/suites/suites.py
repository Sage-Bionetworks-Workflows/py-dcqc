from dcqc import tests
from dcqc.file import FileType
from dcqc.suites.suite_abc import SuiteABC


class FileSuite(SuiteABC):
    """Base class for all file-based test suites."""

    file_type = FileType.get_file_type("*")
    add_tests = (tests.FileExtensionTest, tests.Md5ChecksumTest)


class JsonSuite(FileSuite):
    """Suite class for JSON files."""

    file_type = FileType.get_file_type("JSON")
    add_tests = (tests.JsonLoadTest,)


class JsonLdSuite(JsonSuite):
    """Suite class for JSON-LD files."""

    file_type = FileType.get_file_type("JSON-LD")
    add_tests = (tests.JsonLdLoadTest,)


class TiffSuite(FileSuite):
    """Suite class for TIFF files."""

    file_type = FileType.get_file_type("TIFF")
    add_tests = (
        tests.LibTiffInfoTest,
        tests.TiffDateTimeTest,
        tests.TiffTag306DateTimeTest,
    )


class OmeTiffSuite(TiffSuite):
    """Suite class for OME-TIFF files."""

    file_type = FileType.get_file_type("OME-TIFF")
    add_tests = (tests.OmeXmlSchemaTest, tests.BioFormatsInfoTest)


class TSVSuite(FileSuite):
    """Suite class for TSV files."""

    file_type = FileType.get_file_type("TSV")


class BAMSuite(FileSuite):
    """Suite class for BAM files."""

    file_type = FileType.get_file_type("BAM")


class FastqSuite(FileSuite):
    """Suite class for FASTQ files."""

    file_type = FileType.get_file_type("FASTQ")
    add_tests = (tests.PairedFastqParityTest,)


class TXTSuite(FileSuite):
    """Suite class for TXT files."""

    file_type = FileType.get_file_type("TXT")


class CSVSuite(FileSuite):
    """Suite class for CSV files."""

    file_type = FileType.get_file_type("CSV")


class HDF5Suite(FileSuite):
    """Suite class for HDF5 files."""

    file_type = FileType.get_file_type("HDF5")


class H5ADSuite(FileSuite):
    """Suite class for H5AD files."""

    file_type = FileType.get_file_type("H5AD")
