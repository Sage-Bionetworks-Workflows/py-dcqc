from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestTier


class H5adHtanValidatorTest(ExternalBaseTest):
    """
    Based on [HTAN H5AD Validator](https://github.com/ncihtan/h5ad)
    This is an h5ad validator for HTAN Phase 2 single
     cell/single nuclei RNA-sequencing data.
    """

    tier = TestTier.INTERNAL_CONFORMANCE
    pass_code = 0
    fail_code = 1
    failure_reason_location = "std_out"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()
        command_args = [
            "python",
            "/usr/local/bin/h5ad.py",
            f"'{path.name}'",
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/htan-h5ad-validator:0.1.1",
            command_args=command_args,
        )
        return process
