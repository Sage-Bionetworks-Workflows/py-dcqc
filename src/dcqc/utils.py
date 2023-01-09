from fs import open_fs
from fs.base import FS


def validate_from_dict(cls, dictionary):
    type_ = dictionary.pop("type")
    if type_ != cls.__name__:
        message = f"Type ({type_}) does not match the class ({cls.__name__})."
        raise ValueError(message)
    return dictionary


def open_parent_fs(url: str) -> tuple[FS, str]:
    # Split off prefix to avoid issues with `rpartition("/")`
    scheme, separator, path = url.rpartition("://")
    if separator == "":
        prefix = "osfs://"
    else:
        prefix = scheme + separator

    # TODO: Once Synapse supports root-less initialization,
    #       this part should be updated
    # Check if there is only one part in the file URL
    # If so, append `/..` to open its parent directory
    parent_path, _, base_name = path.rpartition("/")
    if parent_path == "":
        parent_path = f"{base_name}/.."

    parent_url = prefix + parent_path
    fs = open_fs(parent_url)
    return fs, base_name
