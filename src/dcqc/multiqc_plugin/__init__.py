"""MultiQC plugin for DCQC validation results.

Registered as a MultiQC v1 module via the ``multiqc.modules.v1`` entry point in
py-dcqc's ``setup.cfg``. When MultiQC starts up it discovers the plugin,
imports :mod:`dcqc.multiqc_plugin.dcqc_validation`, and the parent package
import below runs — which registers the module order and search pattern
defaults so the plugin works without a user-supplied ``multiqc_config.yaml``.
"""

from multiqc import config

config.module_order.append(
    {
        "dcqc_validation": {
            "module_tag": ["QC", "Validation"],
            "name": "DCQC Validation",
            "anchor": "dcqc-validation",
            "target": "DCQC Validation",
            "info": "displays validation results from DCQC suite testing",
        }
    }
)

config.sp["dcqc_validation"] = {"fn": "suites.json"}

from dcqc.multiqc_plugin import dcqc_validation  # noqa: E402,F401
