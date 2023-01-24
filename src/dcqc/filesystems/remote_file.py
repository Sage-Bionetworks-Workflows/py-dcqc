from __future__ import annotations

import io
import os
from collections.abc import Callable, Iterable
from typing import IO, BinaryIO, Optional

from fs.mode import Mode


class RemoteFile(io.IOBase, BinaryIO):
    """Proxy for a remote file."""

    def __init__(
        self,
        f: IO,
        filename: str,
        mode: Mode,
        on_close: Optional[Callable] = None,
    ):
        self._f = f
        self.__filename = filename
        self.__mode = mode
        self._on_close = on_close

    def __enter__(self) -> RemoteFile:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore
        self.close()

    @property
    def raw(self) -> IO:
        return self._f

    def close(self) -> None:
        if self._on_close is not None:
            self._on_close(self)

    @property
    def closed(self) -> bool:
        return self._f.closed

    @property
    def mode(self) -> str:
        return self._f.mode

    def fileno(self) -> int:
        return self._f.fileno()

    def flush(self) -> None:
        self._f.flush()

    # def isatty(self):
    #     return self._f.asatty()

    def readable(self) -> bool:
        return self.__mode.reading

    def readline(self, limit: Optional[int] = -1) -> bytes:
        limit = limit or -1
        return self._f.readline(limit)

    def readlines(self, hint: int = -1) -> list[bytes]:
        if hint == -1:
            return self._f.readlines(hint)
        else:
            size = 0
            lines = []
            for line in iter(self._f.readline, b""):  # pragma: no cover
                lines.append(line)
                size += len(line)
                if size > hint:
                    break
            return lines

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if whence not in (os.SEEK_CUR, os.SEEK_END, os.SEEK_SET):
            raise ValueError("invalid value for 'whence'")
        self._f.seek(offset, whence)
        return self._f.tell()

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._f.tell()

    def writable(self) -> bool:
        return self.__mode.writing

    def writelines(self, lines: Iterable[bytes]) -> None:  # type: ignore
        return self._f.writelines(lines)

    def read(self, n: int = -1) -> bytes:
        if not self.__mode.reading:
            raise IOError("not open for reading")
        return self._f.read(n)

    # def readall(self):
    #     return self._f.readall()

    # def readinto(self, b):
    #     return self._f.readinto(b)

    def write(self, b: bytes) -> int:
        if not self.__mode.writing:
            raise IOError("not open for reading")
        self._f.write(b)
        return len(b)

    def truncate(self, size: Optional[int] = None) -> int:
        if size is None:
            size = self._f.tell()
        self._f.truncate(size)
        return size
