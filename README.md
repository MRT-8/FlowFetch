# FlowFetch

[简体中文](README.zh-CN.md)

FlowFetch is a Linux-first terminal downloader for direct file URLs. It validates HTTP or HTTPS links, streams downloads with clear progress output, detects common archive formats, and can extract them safely on demand.

The project is intentionally lightweight:

- Python-first by default for downloading and extraction
- Friendly interactive flow with low input overhead
- Optional fallback to system tools for large files or special archive formats
- Safer extraction checks to block path traversal attempts

## Why FlowFetch

FlowFetch is designed for the common "paste a file URL and get the result locally" workflow:

- Download regular files from `http://` and `https://` links
- Show progress, speed, total size, and ETA during download
- Save to the current directory or a custom output directory
- Detect archives such as `zip`, `tar.gz`, and `gz`
- Ask whether to extract, or skip extraction in non-interactive mode
- Fall back to `curl`, `wget`, `unzip`, `tar`, or `7z` when the situation calls for them

## Features

- Interactive mode and direct CLI mode
- Metadata probing before download
- Automatic filename detection from headers or URL
- Temporary `.part` files during download to avoid half-finished target files
- Automatic rename strategy for name conflicts
- Retry handling for download failures
- Safe extraction checks for supported archive formats
- Clear exit codes for automation and scripting

## Supported Formats

Python standard library extraction currently supports:

- `zip`
- `tar`
- `tar.gz`
- `tgz`
- `tar.bz2`
- `tar.xz`
- `gz`

Enhanced support via system tools:

- `7z` with `7z` or `7zz`

## Installation From Source

FlowFetch currently ships as source code in this repository.

Requirements:

- Linux
- Python 3.9+
- `uv` for the preferred workflow, or `pip` as a fallback

Preferred setup with `uv`:

```bash
uv sync
uv run flowfetch --help
```

Example usage with `uv`:

```bash
uv run flowfetch https://example.com/demo.zip
uv run downloader.py --help
```

Alternative setup with `pip`:

```bash
pip install -r requirements.txt
python downloader.py --help
```

Important notes:

- The local `.venv` used during development is not part of the repository and is not meant to be distributed.
- Users cloning the repository should install dependencies locally instead of reusing a checked-in virtual environment.
- After `uv sync`, the project exposes a `flowfetch` CLI command through the project entry point.

## Optional System Tools

FlowFetch does not require system tools for its default path, but it can use them as an enhancement when:

- a file is large enough to trigger downloader switching
- a format is better handled by system extractors
- the Python path fails and fallback is allowed

Useful tools:

- `curl`
- `wget`
- `unzip`
- `tar`
- `gzip`
- `7z` or `7zz`

Common Linux install examples:

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y curl wget unzip tar gzip p7zip-full

# CentOS / RHEL
sudo yum install -y curl wget unzip tar gzip p7zip p7zip-plugins

# Fedora
sudo dnf install -y curl wget unzip tar gzip p7zip p7zip-plugins

# Arch Linux
sudo pacman -S curl wget unzip tar gzip p7zip
```

## Usage

Interactive mode:

```bash
uv run flowfetch
```

Download a file directly:

```bash
uv run flowfetch https://example.com/demo.zip
```

Download to a custom directory and extract automatically:

```bash
uv run flowfetch --output-dir ./downloads --extract https://example.com/demo.tar.gz
```

Force the Python downloader:

```bash
uv run flowfetch --downloader httpx https://example.com/file.bin
```

Force the system extractor:

```bash
uv run flowfetch --extractor system --extract https://example.com/demo.7z
```

## Key CLI Options

```bash
uv run flowfetch [options] [url]
```

- `-o, --output-dir`: target download directory
- `--filename`: force the saved filename
- `--downloader auto|httpx|curl|wget`: choose the downloader
- `--extractor auto|python|system`: choose the extraction strategy
- `--extract`: always extract archives after download
- `--no-extract`: never extract archives after download
- `--overwrite`: allow overwriting existing targets
- `--rename`: auto-rename conflicts
- `--download-threshold`: downloader switch threshold such as `1g`
- `--extract-threshold`: extractor switch threshold
- `--retry`: number of download retries
- `--timeout`: shared connect/read timeout
- `--keep-partial`: keep `.part` files on failure
- `--delete-partial`: remove `.part` files on failure
- `--no-fallback`: disable automatic fallback paths
- `--yes`: accept recommended prompts automatically
- `--verbose`: print more detailed error information

## Exit Codes

- `0`: success
- `2`: invalid arguments
- `3`: user cancelled
- `4`: invalid URL
- `5`: metadata fetch failed
- `6`: download failed
- `7`: downloaded file validation failed
- `8`: extraction failed
- `9`: missing system downloader
- `10`: missing system extractor
- `11`: unsupported format
- `12`: permission denied

## How FlowFetch Behaves

- FlowFetch tries to fetch metadata before downloading so it can show a filename and expected size.
- Downloads are written to a `.part` file first, then renamed after validation succeeds.
- Small and normal-sized files use the Python downloader by default.
- Very large files can switch to `curl` or `wget` when available.
- Supported archives use Python extraction by default, with safety checks against path traversal.
- Unsupported or large archive cases can use system extractors when available.

## Linux Release Binary

FlowFetch also supports a GitHub Release distribution for Linux `x86_64`.

Release asset:

- `flowfetch-linux-x86_64.tar.gz`

Usage after downloading the asset:

```bash
tar -xzf flowfetch-linux-x86_64.tar.gz
cd flowfetch-linux-x86_64
chmod +x flowfetch
./flowfetch --help
./flowfetch https://example.com/demo.zip
```

This Release binary is intended for users who want a direct "download and run" path without installing Python dependencies or running `pip install`.

Detailed release notes for the first public build:

- [`release/v0.1.0.md`](release/v0.1.0.md)

## Repository Layout

- `downloader.py`: current CLI entrypoint and main implementation
- `pyproject.toml`: project metadata and `flowfetch` console entrypoint
- `uv.lock`: locked runtime dependency set for the `uv` workflow
- `requirements.txt`: lightweight `pip` dependency list
- `release/v0.1.0.md`: notes for the first public GitHub Release
- `README.md`: English project documentation
- `README.zh-CN.md`: Simplified Chinese project documentation

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
