# ASRQuant 1.1.0 — PyPI publish checklist

## Identity
- PyPI project: `asrquant`
- GitHub owner: `Alpha-Stochastic-Research`
- GitHub repository: `asrquant`
- Workflow: `release.yml`
- GitHub environment: `pypi`
- Release/tag: `v1.1.0`

## PyPI Pending Trusted Publisher
In PyPI account settings → Publishing, add a pending GitHub publisher with the values above.

## GitHub
Create an environment named `pypi` in repository Settings → Environments.
Ensure `.github/workflows/release.yml` is visible in the Actions workflow list.

## Release
Create/publish GitHub Release `ASRQuant 1.1.0` from tag `v1.1.0`.
The release workflow builds the wheel/sdist and publishes them through OIDC.

## Verify
```bash
python3 -m venv asrquant-110-check
source asrquant-110-check/bin/activate
python -m pip install --upgrade pip
python -m pip install asrquant==1.1.0
python -c "import asrquant as asr; print(asr.__version__)"
asrquant --version
```
Expected version: `1.1.0`.
