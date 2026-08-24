"""Refresh signatures for the already-declared ASRQuant public API snapshot.

Run deliberately when a compatible additive signature change has been reviewed.
The script does not add new symbols automatically.
"""
from __future__ import annotations

import json
from pathlib import Path

from check_public_api import ROOT, descriptor, resolve


def main() -> int:
    path = ROOT / "PUBLIC_API_v1.3.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["symbols"] = {
        name: descriptor(resolve(name)) for name in sorted(payload["symbols"])
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Updated {len(payload['symbols'])} public API descriptors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
