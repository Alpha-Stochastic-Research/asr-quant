"""ASRQuant 1.3 data snapshot and point-in-time example."""
from __future__ import annotations

from pathlib import Path
import tempfile
import pandas as pd
import asrquant as asr

idx = pd.date_range("2026-01-01", periods=5, freq="D")
data = pd.DataFrame({"rate": [0.020, 0.021, 0.022, 0.0215, 0.023]}, index=idx)

with tempfile.TemporaryDirectory(prefix="asrquant-v130-") as tmp:
    store = asr.data.DataStore(Path(tmp) / "data")
    snap = store.put("rates", data, source="deterministic-example")
    loaded = store.get("rates")
    assert loaded.hash == snap.hash
    print(snap.summary.to_string())

revisions = pd.DataFrame(
    {
        "observation_date": ["2026-01-01", "2026-01-01", "2026-02-01"],
        "available_date": ["2026-01-05", "2026-01-20", "2026-02-05"],
        "revision_date": ["2026-01-05", "2026-01-20", "2026-02-05"],
        "value": [100.0, 101.0, 102.0],
    }
)
pit = asr.data.PointInTimeFrame(revisions)
print("\nAS OF 2026-01-10")
print(pit.as_of("2026-01-10").to_string(index=False))
