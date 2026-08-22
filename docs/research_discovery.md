# ASRQuant Research Discovery

ASRQuant 1.1.0 introduced, and 1.2.0 preserves, a conservative research-discovery layer for the ASR Research and Analyst teams. Its job is to transform evidence into **falsifiable research candidates**. It never treats an automatically generated idea as a proven novelty claim.

## One workflow

```python
import asrquant as asr

board = asr.discovery.weekly(
    data=curve_history,
    domain="fixed_income",
    n=10,
)

print(board.to_frame())
project = board.start(0)
cycle = asr.weekly_cycle(board, 0, launch_friday="2026-08-14")
cycle.publication_pack("weekly/WR-001")
```

The pipeline is:

`evidence -> observation -> research question -> hypothesis -> falsification rule -> ResearchProject -> robustness -> claim audit -> publication pack`.

## Discovery sources

`asr.discovery.weekly()` can combine several independent sources:

- **market or curve data**: mean/variance shifts, tails, serial dependence, relationship breaks, PCA residuals and curve-regime changes;
- **literature**: source-linked hypotheses, limitations, assumptions and corpus-relative novelty evidence;
- **model disagreement**: points where competing models give materially different predictions;
- **robustness grids**: specifications for which a reported result is unstable;
- **curated research catalogues**: testable starting points that remain explicitly labelled `NOT_ESTABLISHED` for novelty.

## Friday-to-Friday contract

The ASR weekly cycle is eight dated checkpoints, including both Fridays:

| Day | Stage | Required result |
|---|---|---|
| Friday N | Launch | question, hypothesis, owners, falsification rule, evidence contract |
| Saturday | Prior art | nearest literature, competing explanations, definitions |
| Sunday | Data design | frozen sample, provenance, lags, validation split |
| Monday | Baseline | simplest valid benchmark/reproduction |
| Tuesday | Main experiment | primary estimate/model and diagnostics |
| Wednesday | Robustness | alternatives, subperiods, costs, stress and falsification |
| Thursday | Review | independent reproduction, limitations, claim audit |
| Friday N+1 | Publish | research note, notebook, figure, evidence and next question |

`board.weekly_plan(...)` returns this plan as a dataframe.

## Evidence, not automatic novelty

Every `ResearchCandidate` contains:

- `research_question`;
- `hypothesis`;
- `falsification_rule`;
- `methods`;
- `data_requirements`;
- `source_observations`;
- `risks`;
- `priority_score`;
- `novelty_status`.

The default novelty status is `NOT_ESTABLISHED`. A research team must perform and document the prior-art search before words such as *new*, *novel*, *first* or *original* are used in public communication.

## Hand-off to the existing research engine

`ResearchBoard.start()` creates the normal ASRQuant `ResearchProject`; nothing is lost by starting from discovery. The project can then use literature ingestion, data planning/fetching, feature and signal construction, hypothesis tests, backtests, robustness, decisions, manifests and HTML reports.

## Publication pack

`WeeklyResearchCycle.publication_pack()` creates a reproducibility-oriented directory containing:

- `research_brief.md`;
- `RESEARCH_NOTE.md`;
- `REPRODUCIBILITY_CHECKLIST.md`;
- `CLAIM_AUDIT.md`;
- `weekly_plan.csv`;
- `cycle_status.csv`;
- `project_manifest.json`;
- standard folders for data, notebooks, figures, tables, source code and evidence.

This is a starting contract, not evidence that a result is scientifically correct. The independent review step remains mandatory.
