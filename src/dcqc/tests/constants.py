"""Container images used by the external QC tests."""

# docker containers for external tests
BFTOOLS_CONTAINER = "quay.io/sagebionetworks/bftools:latest"
COREUTILS_CONTAINER = "quay.io/biocontainers/coreutils:9.3"
HTAN_H5AD_VALIDATOR_CONTAINER = (
    "ghcr.io/sage-bionetworks-workflows/htan-h5ad-validator:0.1.1"
)
LIBTIFF_CONTAINER = "quay.io/sagebionetworks/libtiff:2.0"
TIFFTOOLS_CONTAINER = "ghcr.io/sage-bionetworks-workflows/tifftools:latest"
