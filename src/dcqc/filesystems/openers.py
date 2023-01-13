import os

from fs.opener import Opener
from fs.opener.parse import ParseResult

from dcqc.filesystems.synapsefs import SynapseFS


class SynapseFSOpener(Opener):
    protocols = ["syn"]

    def open_fs(
        self,
        fs_url: str,
        parse_result: ParseResult,
        writeable: bool,
        create: bool,
        cwd: str,
    ) -> SynapseFS:
        auth_token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        root = parse_result.resource
        fs = SynapseFS(root, auth_token)
        return fs
