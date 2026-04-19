# Build Notes

This repository packages the Rust `dss-codec` project as a Python extension
module.

## Repository Layout

- Python packaging is configured in `pyproject.toml`
- The Rust extension crate for Python lives in `Cargo.toml` and `src/lib.rs`
- The upstream `dss-codec` repository is included as a git submodule at
  `ext/dss-codec`
- The Rust crate used by this package is `ext/dss-codec/dss-codec`

## Clone

Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/gaspardpetit/pydsscodec.git
```

If you already cloned the repository:

```bash
git submodule update --init --recursive
```

## Development

Install the project and development dependencies with `uv`:

```bash
uv sync --group dev
```

Run tests:

```bash
uv run pytest
```

Build and install the extension directly in the active environment:

```bash
uv run --with maturin maturin develop
```

## Build Artifacts

Build an sdist and wheel:

```bash
uv build
```

The source distribution includes the Rust sources from the submodule so source
installs do not need to fetch `dss-codec` from the network.

## Publish

Publish to PyPI with:

```bash
uv run --with maturin maturin publish
```
