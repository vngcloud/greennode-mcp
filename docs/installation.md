# Installation

## Prerequisites

- Python 3.10 or later
- `pip` 21.0 or greater
- `setuptools` 68.0 or greater

## Install from PyPI

The recommended way to install the Greenode CLI is to use `pip` in a `virtualenv`:

```bash
python -m pip install grncli
```

or, if you are not installing in a `virtualenv`, to install globally:

```bash
sudo python -m pip install grncli
```

or for your user:

```bash
python -m pip install --user grncli
```

If you have the grncli package installed and want to upgrade to the latest version:

```bash
python -m pip install --upgrade grncli
```

## Install from source

```bash
git clone https://github.com/vngcloud/greennode-cli.git
cd greennode-cli
python -m pip install .
```

To install with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

## Bundled installer

On Linux and macOS, the Greenode CLI can be installed using a standalone installer that creates an isolated virtualenv:

```bash
./scripts/install
```

This installs to `~/.local/lib/greenode` and symlinks `grn` to `~/.local/bin/`. Make sure `~/.local/bin` is in your `PATH`.

## Offline install

For environments without internet access, you can build a self-contained bundle:

```bash
# On a machine with internet access
./scripts/make-bundle

# Transfer dist/grncli-bundle.zip to target machine, then:
unzip grncli-bundle.zip
cd grncli-bundle
./install-offline
```

## Verify installation

```bash
grn --version
# grn-cli/0.1.0 Python/3.13.5 Darwin/25.2.0
```
