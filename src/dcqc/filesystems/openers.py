import os

from fs.opener import Opener

from dcqc.filesystems.synapsefs import SynapseFS


class SynapseFSOpener(Opener):
    protocols = ["syn"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        auth_token = os.environ.get("SYNAPSE_AUTH_TOKEN")
        root = parse_result.resource
        fs = SynapseFS(root, auth_token)
        return fs
