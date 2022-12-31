import os

from fs.opener import Opener
from fs.opener.errors import OpenerError
from fs.subfs import SubFS

from dcqc.filesystems.synapsefs import SynapseFS


class SynapseFSOpener(Opener):
    protocols = ["syn"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        root, _, subdir = parse_result.resource.partition(SynapseFS.DELIMITER)
        if not root:
            message = f"Invalid Synapse URL ({fs_url}). Must start with project/folder."
            raise OpenerError(message)
        auth_token = os.environ["SYNAPSE_AUTH_TOKEN"]
        synapsefs = SynapseFS(root, auth_token)
        if subdir:
            synapsefs = SubFS(synapsefs, subdir)
        return synapsefs
