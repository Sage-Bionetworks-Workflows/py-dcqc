import os

from fs.opener import Opener
from fs.opener.errors import OpenerError

from dcqc.filesystems.synapsefs import SynapseFS


class SynapseFSOpener(Opener):
    protocols = ["syn"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        root = parse_result.resource
        if SynapseFS.SYNID_REGEX.match(root) is None:
            message = f"Root ({root}) must start with a Synapse ID."
            raise OpenerError(message)
        auth_token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        synapsefs = SynapseFS(root, auth_token)
        return synapsefs
