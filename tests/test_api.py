from __future__ import annotations

from pathlib import Path

import pytest

from pydsscodec import DecryptingDecoderStreamer
from pydsscodec import DecryptStreamer
from pydsscodec import StreamingDecoder
from pydsscodec import decode_bytes
from pydsscodec import decode_file
from pydsscodec import decrypt_bytes
from pydsscodec import decrypt_file
from pydsscodec import detect_format


def make_truncated_ds2_qp_file(frame_count: int) -> bytes:
    data = bytearray(0x600)
    data[:4] = b"\x03ds2"

    block = bytearray(512)
    block[2] = frame_count
    block[4] = 6
    for index in range(6, len(block)):
        block[index] = ((index - 6) * 3 + 1) % 256

    data.extend(block)
    return bytes(data)


def make_truncated_ds2_sp_file(frame_count: int) -> bytes:
    data = bytearray(0x600)
    data[:4] = b"\x03ds2"

    block = bytearray(512)
    block[2] = frame_count
    block[4] = 0
    for index in range(6, len(block)):
        block[index] = ((index - 6) * 5 + 7) % 256

    data.extend(block)
    return bytes(data)


def make_truncated_dss_sp_file(frame_count: int) -> bytes:
    data = bytearray(1024)
    data[0] = 2
    data[1:4] = b"dss"

    block = bytearray(512)
    block[2] = frame_count
    for index in range(6, len(block)):
        block[index] = ((index - 6) * 7 + 3) % 256

    data.extend(block)
    return bytes(data)


@pytest.mark.parametrize(
    ("payload", "expected_format"),
    [
        (make_truncated_ds2_qp_file(10), "ds2_qp"),
        (make_truncated_ds2_sp_file(10), "ds2_sp"),
        (make_truncated_dss_sp_file(10), "dss_sp"),
    ],
)
def test_detect_format(payload: bytes, expected_format: str) -> None:
    assert detect_format(payload) == expected_format


@pytest.mark.parametrize(
    ("payload", "expected_format", "expected_rate"),
    [
        (make_truncated_ds2_qp_file(10), "ds2_qp", 16000),
        (make_truncated_ds2_sp_file(13), "ds2_sp", 12000),
        (make_truncated_dss_sp_file(13), "dss_sp", 11025),
    ],
)
def test_decode_bytes_returns_audio_metadata(
    payload: bytes,
    expected_format: str,
    expected_rate: int,
) -> None:
    audio = decode_bytes(payload)

    assert audio.format == expected_format
    assert audio.sample_rate == expected_rate
    assert audio.native_rate == expected_rate
    assert audio.sample_count > 0
    assert audio.duration_seconds > 0


def test_decrypt_bytes_passes_through_plain_ds2() -> None:
    data = make_truncated_ds2_qp_file(10)
    assert decrypt_bytes(data) == data


def test_decrypt_file_passes_through_plain_input(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.ds2"
    data = make_truncated_ds2_qp_file(10)
    input_path.write_bytes(data)

    assert decrypt_file(input_path) == data


@pytest.mark.parametrize(
    ("filename", "payload", "expected_format", "expected_rate"),
    [
        ("sample_qp.ds2", make_truncated_ds2_qp_file(10), "ds2_qp", 16000),
        ("sample_sp.ds2", make_truncated_ds2_sp_file(13), "ds2_sp", 12000),
        ("sample.dss", make_truncated_dss_sp_file(13), "dss_sp", 11025),
    ],
)
def test_decode_file_returns_audio_metadata(
    tmp_path: Path,
    filename: str,
    payload: bytes,
    expected_format: str,
    expected_rate: int,
) -> None:
    input_path = tmp_path / filename
    input_path.write_bytes(payload)

    audio = decode_file(input_path)

    assert audio.format == expected_format
    assert audio.sample_rate == expected_rate
    assert audio.native_rate == expected_rate
    assert audio.sample_count > 0


def test_streaming_decoder_detects_format_and_errors_on_truncated_finish() -> None:
    data = make_truncated_ds2_qp_file(10)
    decoder = StreamingDecoder()

    assert decoder.push(data[:4]) == []
    assert decoder.format() is None
    assert decoder.native_rate() is None

    streamed = decoder.push(data[4:])
    assert streamed
    assert decoder.format() == "ds2_qp"
    assert decoder.native_rate() == 16000

    with pytest.raises(RuntimeError, match="truncated"):
        decoder.finish()


def test_streaming_decoder_push_after_finish_errors() -> None:
    decoder = StreamingDecoder()
    decoder.finish()

    with pytest.raises(RuntimeError, match="already finished"):
        decoder.push(b"\x03ds2")


def test_decrypt_streamer_plain_passthrough_and_error() -> None:
    data = make_truncated_ds2_qp_file(10)
    decryptor = DecryptStreamer()

    assert decryptor.push(data[:4]) == data[:4]
    assert decryptor.push(data[4:]) == data[4:]
    assert decryptor.finish() == b""

    bad = DecryptStreamer()
    with pytest.raises(RuntimeError, match="unsupported"):
        bad.push(b"nope")


def test_decrypting_decoder_streamer_detects_format_and_errors_on_truncated_finish() -> None:
    data = make_truncated_ds2_qp_file(10)
    decoder = DecryptingDecoderStreamer()

    first = decoder.push(data[:4])
    second = decoder.push(data[4:])

    assert first == []
    assert second
    assert decoder.format() == "ds2_qp"
    assert decoder.native_rate() == 16000

    with pytest.raises(RuntimeError, match="truncated"):
        decoder.finish()


def test_decrypting_decoder_streamer_push_after_finish_errors() -> None:
    decoder = DecryptingDecoderStreamer()
    decoder.finish()

    with pytest.raises(RuntimeError, match="already finished"):
        decoder.push(b"\x03ds2")
