"""Reproducibility manifests for research artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class Manifest:
    created_at_utc: str
    python: str
    platform: str
    numpy: str
    pandas: str
    experiment_fingerprint: str
    data_fingerprint: str
    spec_fingerprint: str
    metadata: dict[str, Any]

    def to_json(self, path: str | Path | None = None) -> str:
        text = json.dumps(asdict(self), indent=2, sort_keys=True, default=str)
        if path is not None:
            Path(path).write_text(text, encoding="utf-8")
        return text


def build_manifest(result: Any, **metadata: Any) -> Manifest:
    """Build a machine-readable manifest from a BacktestResult."""
    return Manifest(
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version.split()[0],
        platform=platform.platform(),
        numpy=np.__version__,
        pandas=pd.__version__,
        experiment_fingerprint=result.fingerprint,
        data_fingerprint=result.metadata["data_fingerprint"],
        spec_fingerprint=result.metadata["spec_fingerprint"],
        metadata=metadata,
    )
