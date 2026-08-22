# Installation

## PyPI

When release `1.2.0` is available on the configured Python package index:

```bash
python -m pip install "asrquant==1.2.0"
```

For the complete optional feature set:

```bash
python -m pip install "asrquant[all]==1.2.0"
```

## From the repository

For development or for working directly from the tagged source tree:

```bash
python -m pip install -e .
```

Documentation dependencies are already declared in `pyproject.toml`:

```bash
python -m pip install -e ".[docs]"
```

Then serve the documentation locally:

```bash
mkdocs serve
```

## Verify the installation

```python
import asrquant as asr

print(asr.__version__)
assert asr.__version__ == "1.2.0"
```

The package declares Python `>=3.10` and the 1.2.0 release ships both a wheel and a source distribution.
