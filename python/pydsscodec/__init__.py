from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from os import PathLike, fspath
from typing import Optional, Union

from ._core import DecodedAudio
from ._core import DecryptingDecoderStreamer as _CoreDecryptingDecoderStreamer
from ._core import DecryptStreamer as _CoreDecryptStreamer
from ._core import StreamingDecoder
from ._core import crate_version as _crate_version
from ._core import decode_bytes as _decode_bytes
from ._core import decode_file as _decode_file
from ._core import decrypt_bytes as _decrypt_bytes
from ._core import decrypt_file as _decrypt_file
from ._core import detect_format

Pathish = Union[str, PathLike[str]]
Password = Optional[Union[str, bytes]]


def decode_bytes(data: bytes, password: Password = None) -> DecodedAudio:
    return _decode_bytes(data, _normalize_password(password))


def decode_file(path: Pathish, password: Password = None) -> DecodedAudio:
    return _decode_file(fspath(path), _normalize_password(password))


def decrypt_bytes(data: bytes, password: Password = None) -> bytes:
    return _decrypt_bytes(data, _normalize_password(password))


def decrypt_file(path: Pathish, password: Password = None) -> bytes:
    return _decrypt_file(fspath(path), _normalize_password(password))


class DecryptStreamer:
    def __init__(self, password: Password = None) -> None:
        self._inner = _CoreDecryptStreamer(_normalize_password(password))

    def push(self, data: bytes) -> bytes:
        return self._inner.push(data)

    def finish(self) -> bytes:
        return self._inner.finish()


class DecryptingDecoderStreamer:
    def __init__(self, password: Password = None) -> None:
        self._inner = _CoreDecryptingDecoderStreamer(_normalize_password(password))

    def push(self, data: bytes) -> list[float]:
        return self._inner.push(data)

    def finish(self) -> list[float]:
        return self._inner.finish()

    def format(self) -> Optional[str]:
        return self._inner.format()

    def native_rate(self) -> Optional[int]:
        return self._inner.native_rate()


def _normalize_password(password: Password) -> Optional[bytes]:
    if password is None:
        return None
    if isinstance(password, str):
        return password.encode("utf-8")
    if isinstance(password, bytes):
        return password
    raise TypeError("password must be str, bytes, or None")


try:
    __version__ = version("pydsscodec")
except PackageNotFoundError:
    __version__ = _crate_version()


__all__ = [
    "DecodedAudio",
    "DecryptStreamer",
    "DecryptingDecoderStreamer",
    "StreamingDecoder",
    "__version__",
    "decode_bytes",
    "decode_file",
    "decrypt_bytes",
    "decrypt_file",
    "detect_format",
]
