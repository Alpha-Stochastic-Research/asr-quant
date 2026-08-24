"""Friday-to-Friday research operations and publication packaging."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
import json
import shutil

import pandas as pd

from .discovery import ResearchBoard, ResearchCandidate
from .workflow import ResearchProject


REPRODUCIBILITY_CHECKLIST = """# ASRQuant Reproducibility Checklist

- [ ] Research question frozen before the main experiment.
- [ ] Null hypothesis and falsification rule documented.
- [ ] Literature/nearest-prior-art review completed; novelty claim manually verified.
- [ ] Raw data source, retrieval time, licence and provenance recorded.
- [ ] Point-in-time availability and publication lags verified where relevant.
- [ ] Data-cleaning decisions are deterministic and logged.
- [ ] Train/validation/test chronology is leakage-safe.
- [ ] Baseline model or known identity reproduced before extension.
- [ ] Parameter choices have an economic/statistical rationale.
- [ ] Multiple testing/data snooping is controlled or explicitly disclosed.
- [ ] Standard errors/inference are appropriate for dependence/heteroskedasticity.
- [ ] Robustness includes subperiods and reasonable alternative specifications.
- [ ] Transaction costs/execution assumptions are included if a trading claim is made.
- [ ] Model and implementation risk are documented.
- [ ] A second reviewer can run the notebook/script from a clean environment.
- [ ] Figures/tables can be regenerated from code.
- [ ] Package version, environment and random seeds are recorded.
- [ ] Results that failed are retained, not silently removed.
- [ ] Limitations are explicit and proportional to the evidence.
- [ ] Public language distinguishes evidence from hypothesis and avoids unsupported "first/new" claims.
"""

CLAIM_AUDIT = """# ASRQuant Claim Audit

For every public claim, complete the table before publication.

| Claim | Evidence artifact | Robustness evidence | Prior-art checked? | Allowed wording |
|---|---|---|---|---|
|  |  |  |  |  |

## Wording rules

- **Observed:** supported directly by the current sample/experiment.
- **Robust in tested specifications:** survived the documented robustness set only.
- **Candidate contribution:** proposed definition/method whose novelty remains to be established.
- **Novel / first:** use only after a documented literature and prior-art review supports the wording.
"""


def research_note_template(candidate: ResearchCandidate) -> str:
    methods = "\n".join(f"- {m}" for m in candidate.methods) or "- TBD"
    data = "\n".join(f"- {d}" for d in candidate.data_requirements) or "- TBD"
    return f"""# ASR Weekly Research — {candidate.title}

**Candidate ID:** `{candidate.candidate_id}`  
**Domain:** {candidate.domain}  
**Contribution type:** {candidate.contribution_type}  
**Novelty status:** {candidate.novelty_status} — do not upgrade without prior-art evidence.

## Abstract

Write 120–200 words only after the results are frozen. State the question, method, main result, uncertainty and limitation.

## 1. Research question

{candidate.research_question}

## 2. Hypothesis and falsification

**Hypothesis:** {candidate.hypothesis}

**Falsification rule:** {candidate.falsification_rule}

## 3. Prior literature and nearest methods

Document the closest papers/methods, what they already establish, and exactly what remains unresolved. Every novelty statement must be supported here.

## 4. Data and provenance

{data}

Record source, sample, retrieval timestamp, cleaning, units, calendars/day-count conventions, availability lags and point-in-time limitations.

## 5. Methodology

{methods}

Write definitions, assumptions, equations, estimators, algorithms and numerical settings precisely enough for independent reproduction.

## 6. Baseline / benchmark

Reproduce the simplest known benchmark or identity before reporting the proposed extension.

## 7. Main experiment

Pre-specify the principal metric and the main statistical/economic test.

## 8. Results

Report estimates, uncertainty, effect sizes and diagnostics. Do not report only the best specification.

## 9. Robustness and falsification tests

Include subperiods, parameter sensitivity, alternative data/model choices, bootstrap or dependence-robust inference, and negative/placebo tests where relevant.

## 10. Model / implementation risk

Separate market/economic uncertainty from model risk, numerical risk, interpolation/calibration risk and software risk.

## 11. Limitations

State where the result should *not* be generalized.

## 12. Contribution statement

Describe only what is supported by the evidence and prior-art review. Current automatic status: **{candidate.novelty_status}**.

## 13. Reproducibility

List package version, environment, data fingerprints, seeds, scripts/notebooks and generated artifacts.

## 14. Conclusion

Answer the original question, state whether the hypothesis survived, and define the next research question.

## References

Use primary literature wherever possible.
"""


@dataclass
class WeeklyResearchCycle:
    """One ASR Friday-to-Friday research cycle."""

    candidate: ResearchCandidate
    project: ResearchProject
    launch_friday: date
    publication_friday: date
    plan: pd.DataFrame

    @classmethod
    def from_board(
        cls,
        board: ResearchBoard,
        identifier: str | int,
        *,
        launch_friday: date | str | None = None,
        name: str | None = None,
    ) -> "WeeklyResearchCycle":
        candidate = board.select(identifier)
        plan = board.weekly_plan(identifier, launch_friday=launch_friday)
        launch = pd.Timestamp(plan.iloc[0]["date"]).date()
        project = board.start(identifier, name=name)
        return cls(candidate, project, launch, launch + timedelta(days=7), plan)

    def checklist(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                ("Question locked", self.project.hypothesis is not None),
                ("Literature corpus attached", self.project.corpus is not None),
                ("Data attached", self.project.data is not None),
                ("Features built", self.project.features is not None),
                ("Hypothesis tested", self.project.hypothesis_test_result is not None),
                ("Backtest/experiment run", self.project.backtest_result is not None),
                ("Robustness completed", self.project.robustness_result is not None),
                ("Decision recorded", self.project.decision_result is not None),
            ],
            columns=["stage", "complete"],
        )

    def publication_pack(self, directory: str | Path, *, include_project_report: bool = True) -> Path:
        """Create a publication-ready folder skeleton from the live project state."""
        root = Path(directory)
        root.mkdir(parents=True, exist_ok=True)
        (root / "research_brief.md").write_text(self.candidate.brief(), encoding="utf-8")
        (root / "RESEARCH_NOTE.md").write_text(research_note_template(self.candidate), encoding="utf-8")
        (root / "REPRODUCIBILITY_CHECKLIST.md").write_text(REPRODUCIBILITY_CHECKLIST, encoding="utf-8")
        (root / "CLAIM_AUDIT.md").write_text(CLAIM_AUDIT, encoding="utf-8")
        self.plan.to_csv(root / "weekly_plan.csv", index=False)
        self.checklist().to_csv(root / "cycle_status.csv", index=False)
        manifest = self.project.manifest()
        manifest["weekly_cycle"] = {
            "candidate": self.candidate.to_dict(),
            "launch_friday": self.launch_friday.isoformat(),
            "publication_friday": self.publication_friday.isoformat(),
        }
        (root / "project_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        for folder in ("data", "notebooks", "figures", "tables", "src", "evidence"):
            (root / folder).mkdir(exist_ok=True)
        if include_project_report:
            try:
                self.project.report(root / "research_dossier.html")
            except Exception:
                # The skeleton remains useful before enough project state exists.
                pass
        return root

    def archive(self, output_zip: str | Path, *, working_directory: str | Path | None = None) -> Path:
        """Build the publication pack and zip it for review/release."""
        target = Path(output_zip)
        staging = Path(working_directory or target.with_suffix(""))
        self.publication_pack(staging)
        base = target.with_suffix("")
        archive = shutil.make_archive(str(base), "zip", root_dir=staging)
        return Path(archive)


def weekly_cycle(
    board: ResearchBoard,
    identifier: str | int,
    *,
    launch_friday: date | str | None = None,
    name: str | None = None,
) -> WeeklyResearchCycle:
    """Convenience constructor."""
    return WeeklyResearchCycle.from_board(board, identifier, launch_friday=launch_friday, name=name)


__all__ = [
    "REPRODUCIBILITY_CHECKLIST", "CLAIM_AUDIT", "research_note_template",
    "WeeklyResearchCycle", "weekly_cycle",
]
