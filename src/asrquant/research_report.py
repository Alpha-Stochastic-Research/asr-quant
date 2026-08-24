"""Cross-domain research report container for structured ASRQuant results."""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import json
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class ResearchReport:
    title: str = "ASRQuant Research Report"
    artifacts: list[tuple[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, result: Any, name: str | None = None) -> "ResearchReport":
        label = name or getattr(result, "result_type", type(result).__name__)
        self.artifacts.append((str(label), result))
        return self

    def audit(self) -> pd.DataFrame:
        rows = []
        for name, result in self.artifacts:
            rows.append(
                {
                    "artifact": name,
                    "has_summary": hasattr(result, "summary"),
                    "has_to_dict": hasattr(result, "to_dict"),
                    "has_fingerprint": hasattr(result, "fingerprint"),
                    "result_type": getattr(result, "result_type", type(result).__name__),
                }
            )
        return pd.DataFrame(rows).set_index("artifact") if rows else pd.DataFrame(columns=["has_summary", "has_to_dict", "has_fingerprint", "result_type"])

    def to_dict(self) -> dict[str, Any]:
        artifacts = []
        for name, result in self.artifacts:
            if hasattr(result, "to_dict"):
                payload = result.to_dict()
            elif hasattr(result, "summary"):
                summary = result.summary
                payload = {"summary": summary.to_dict() if hasattr(summary, "to_dict") else str(summary)}
            else:
                payload = {"value": str(result)}
            artifacts.append({"name": name, "payload": payload})
        return {"title": self.title, "metadata": self.metadata, "artifacts": artifacts}

    def _markdown(self) -> str:
        lines = [f"# {self.title}", ""]
        for name, result in self.artifacts:
            lines.extend([f"## {name}", ""])
            if hasattr(result, "summary"):
                summary = result.summary
                if isinstance(summary, pd.Series):
                    lines.append(summary.rename("value").to_frame().to_markdown())
                else:
                    lines.append(str(summary))
            else:
                lines.append(str(result))
            lines.append("")
        lines.extend(["## Audit", "", self.audit().to_markdown() if len(self.artifacts) else "No artifacts.", ""])
        return "\n".join(lines)

    def _html(self) -> str:
        sections = []
        for name, result in self.artifacts:
            if hasattr(result, "summary") and isinstance(result.summary, pd.Series):
                body = result.summary.rename("value").to_frame().to_html(border=0)
            elif hasattr(result, "to_frame"):
                body = pd.DataFrame(result.to_frame()).head(200).to_html(border=0)
            else:
                body = f"<pre>{escape(str(result))}</pre>"
            sections.append(f"<section><h2>{escape(name)}</h2>{body}</section>")
        audit = self.audit().to_html(border=0) if len(self.artifacts) else "<p>No artifacts.</p>"
        return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>{escape(self.title)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#102d4e}}h1,h2{{color:#102d4e}}table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}th,td{{border-bottom:1px solid #dce4ed;padding:7px;text-align:left}}section{{margin-bottom:34px}}</style></head>
<body><h1>{escape(self.title)}</h1>{''.join(sections)}<section><h2>Audit</h2>{audit}</section></body></html>"""

    def export(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        suffix = target.suffix.lower()
        if suffix == ".json":
            target.write_text(json.dumps(self.to_dict(), indent=2, default=str), encoding="utf-8")
        elif suffix in {".md", ".markdown"}:
            target.write_text(self._markdown(), encoding="utf-8")
        elif suffix in {".html", ".htm"}:
            target.write_text(self._html(), encoding="utf-8")
        else:
            raise ValueError("report export supports .html, .md, or .json")
        return target


__all__ = ["ResearchReport"]
