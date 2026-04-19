# pydsscodec

Python bindings for the Rust [`dss-codec`](https://github.com/gaspardpetit/dss-codec) decoder.

`pydsscodec` decodes Olympus DSS and DS2 audio directly in Python through a
native Rust extension. It mirrors the core `dss-codec` model: top-level decode
and decrypt functions plus streaming decoders.

## Features

- Decode DSS and DS2 files from paths or bytes
- Normalize encrypted DS2 input back to plain container bytes
- Stream decode in chunks without forcing a whole-file convenience path
- Load native Rust code in-process instead of shelling out to a CLI
- In our benchmark, achieved roughly 150x faster DSS decoding and 50x faster
  streamed DS2 decoding than the reference Python decoders

## Installation

```bash
pip install pydsscodec
```

If a prebuilt wheel is not available for your platform, installation will build
the Rust extension locally.

Prebuilt wheels are currently published for:

- Linux `x86_64`
- macOS `arm64`
- Windows `x86_64`

Other platforms install from source and require a local Rust toolchain.

## Usage

Decode a file:

```python
from pydsscodec import decode_file

audio = decode_file("recording.ds2")
print(audio.format, audio.sample_rate, audio.native_rate, audio.duration_seconds)
print(audio.sample_count)
```

Decode in-memory bytes:

```python
from pydsscodec import decode_bytes

audio = decode_bytes(data)
```

Decrypt encrypted DS2 input to plain container bytes:

```python
from pydsscodec import decrypt_file

plain_ds2 = decrypt_file("encrypted.ds2", password="secret")
```

Stream decode in chunks:

```python
from pydsscodec import DecryptingDecoderStreamer

decoder = DecryptingDecoderStreamer(password="secret")

with open("recording.ds2", "rb") as handle:
    while chunk := handle.read(4096):
        chunk_samples = decoder.push(chunk)
        # process chunk_samples here

final_samples = decoder.finish()

print(decoder.format(), decoder.native_rate(), len(final_samples))
```

Detect the container format without decoding:

```python
from pydsscodec import detect_format

fmt = detect_format(data)
print(fmt)  # "dss_sp", "ds2_sp", or "ds2_qp"
```

## API

Top-level functions:

- `decode_file(path, password=None) -> DecodedAudio`
- `decode_bytes(data, password=None) -> DecodedAudio`
- `decrypt_file(path, password=None) -> bytes`
- `decrypt_bytes(data, password=None) -> bytes`
- `detect_format(data) -> str | None`

Streamer classes:

- `StreamingDecoder()`
- `DecryptStreamer(password=None)`
- `DecryptingDecoderStreamer(password=None)`

Streamer methods mirror the Rust API:

- `push(data)`
- `finish()`
- `format()`
- `native_rate()`

Bulk decode returns a `DecodedAudio` object with:

- `samples`: decoded mono samples as `list[float]`
- `sample_rate`: sample rate of the returned samples
- `native_rate`: original sample rate of the source codec
- `format`: one of `"dss_sp"`, `"ds2_sp"`, or `"ds2_qp"`
- `sample_count`
- `duration_seconds`

## Notes

- The streaming classes are the preferred scalable interface for large inputs.
- Bulk decode returns samples as a Python list.
