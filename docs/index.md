# dcqc

Python package for performing quality control (QC) for data coordination (DC).

It runs tiered QC checks on data files, from low-level integrity checks such as
MD5 checksums and file extensions to high-level checks such as conformance to a
format specification. It is both a library and a command-line tool, and it is
designed to be driven by
[nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc), the Nextflow
workflow that runs the QC steps in parallel.

## Contents

```{toctree}
:maxdepth: 2

Overview <readme>
Contributions & Help <contributing>
License <license>
Authors <authors>
Changelog <changelog>
Module Reference <api/modules>
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
