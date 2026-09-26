from __future__ import annotations

import builtins
import importlib.util
import inspect
import json
from pathlib import Path

import asrquant as asr

ROOT = Path(__file__).resolve().parents[1]


def _load_validation_template():
    path = ROOT / "scripts" / "asr_software_validation_template.py"
    spec = importlib.util.spec_from_file_location("asr_release_validation_template", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_v130_final_version_and_contributors():
    assert asr.__version__ == "1.3.0"
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    contributors = (ROOT / "CONTRIBUTORS.md").read_text(encoding="utf-8")
    assert "Alpha Kabinet" in citation
    assert 'given-names: "Srijan"' in citation
    assert "Srijan Mishra" in contributors
    assert "Software contribution and manuscript authorship are tracked separately" in contributors


def test_v130_public_signature_manifest_matches_current_surface():
    payload = json.loads((ROOT / "PUBLIC_API_SIGNATURES_v1.3.0.json").read_text(encoding="utf-8"))
    current = sorted(n for n in dir(asr) if not n.startswith("_") and callable(getattr(asr, n)))
    recorded = [item["name"] for item in payload["callables"]]
    assert payload["release"] == "1.3.0"
    assert payload["callable_count"] == 258
    assert recorded == current
    # Every current callable must have a recorded inspectable signature or an explicit unavailable marker.
    for item in payload["callables"]:
        assert item["signature"]


def test_validation_template_requires_distribution_metadata(monkeypatch):
    template = _load_validation_template()

    def missing(_name):
        raise template.metadata.PackageNotFoundError

    monkeypatch.setattr(template.metadata, "distribution", missing)
    try:
        template.check_version("asrquant", "1.3.0")
    except AssertionError as exc:
        assert "distribution" in str(exc)
        assert "not installed" in str(exc)
    else:
        raise AssertionError("version check must fail when distribution metadata is absent")


def test_validation_template_missing_required_numpy_is_not_pass(monkeypatch):
    template = _load_validation_template()
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "numpy":
            raise ImportError("synthetic missing NumPy")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(template, "_requires_numpy", lambda _package: True)
    monkeypatch.setattr(builtins, "__import__", blocked_import)
    try:
        template.check_numpy("asrquant")
    except AssertionError as exc:
        assert "required NumPy dependency is unavailable" in str(exc)
    else:
        raise AssertionError("required missing NumPy must be a failure")


def test_validation_template_generic_placeholder_is_coverage_gap():
    template = _load_validation_template()
    result = template.project_specific_checks("some-other-package")[0]
    assert result.status == "SKIP"
    assert "coverage" in result.detail.lower() or "project-specific" in result.detail.lower()
