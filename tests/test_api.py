from __future__ import annotations

from pathlib import Path

import pytest

from pydsscodec import DecryptingDecoderStreamer
from pydsscodec import DecryptStreamer
from pydsscodec import StreamingDecoder
from pydsscodec import decode_bytes
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


def test_detect_format_for_qp_bytes() -> None:
    assert detect_format(make_truncated_ds2_qp_file(10)) == "ds2_qp"


def test_decode_bytes_returns_audio_metadata() -> None:
    audio = decode_bytes(make_truncated_ds2_qp_file(10))

    assert audio.format == "ds2_qp"
    assert audio.sample_rate == 16000
    assert audio.native_rate == 16000
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
