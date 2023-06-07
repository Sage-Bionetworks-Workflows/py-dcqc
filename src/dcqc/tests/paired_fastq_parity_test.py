import gzip
from pathlib import Path
from typing import TextIO

from dcqc.target import PairedTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class PairedFastqParityTest(InternalBaseTest):
    tier = 2
    target: PairedTarget

    def compute_status(self) -> TestStatus:
        """Compute test status."""
        counts = list()
        for file in self.target.files:
            path = file.stage()
            try:
                count = self._count_fastq_lines(path)
            except Exception:
                return TestStatus.FAIL
            counts.append(count)

        # Check that there counts are all the same (i.e., equal)
        if len(set(counts)) <= 1:
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
        return status

    def _count_fastq_lines(self, path: Path) -> int:
        """Count the number of lines in a FASTQ file.

        Args:
            path: Path to the FASTQ file.

        Returns:
            Number of lines in the given FASTQ file.
        """
        # Source: https://stackoverflow.com/a/1019572/21077945
        with self._open_fastq(path) as fastq:
            num_lines = sum(1 for _ in fastq)
        return num_lines

    def _open_fastq(self, path: Path) -> TextIO:
        """Open a FASTQ file regardless of compression.

        Args:
            path: Path to the FASTQ file.

        Returns:
            Opened FASTQ file (in text mode).
        """
        # TODO: This logic should ideally live in the File class, and a
        #       test should confirm the integrity of compressed files
        if path.name.endswith(".gz"):
            return gzip.open(path, "rt")
        else:
            return path.open("rt")
