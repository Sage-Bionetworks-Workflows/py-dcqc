import re

URI_REGEX = re.compile(r"(?P<scheme>\w+)://(?P<path>.*)")


class URI:
    uri: str
    scheme: str
    path: str

    def __init__(self, uri: str):
        self.uri = uri
        self.scheme, self.path = self._process_uri(uri)

    def __hash__(self):
        return hash(self.uri)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.uri == other.uri
        elif isinstance(other, str):
            return self.uri == other
        else:
            return False

    def __repr__(self):
        return f"URI({self.uri})"

    def _process_uri(self, uri: str) -> tuple[str, str]:
        match = URI_REGEX.match(uri)
        if match is None:
            message = f"URI ({uri}) doesn't match expected pattern (scheme://path)."
            raise ValueError(message)
        return match.group("scheme"), match.group("path")
