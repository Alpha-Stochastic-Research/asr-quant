# Hypothesis Discovery — ASRQuant 1.2.0

ASRQuant 1.2.0 promotes hypothesis discovery to a first-class quantitative research API.

The design separates two questions that must never be conflated:

1. **Is there evidence worth testing?** — data/literature/model/robustness evidence.
2. **Is the idea novel?** — a separate prior-art question that cannot be established automatically from one corpus.

## Public API

```python
import asrquant as asr

asr.hypotheses.from_data(...)
asr.hypotheses.from_literature(...)
asr.hypotheses.from_model_disagreement(...)
asr.hypotheses.from_robustness(...)
asr.hypotheses.discover(...)
asr.hypotheses.search(...)
asr.hypotheses.audit(...)
```

## Data-driven discovery

```python
ideas = asr.hypotheses.from_data(
    data={
        "rates": rates,
        "macro": macro,
        "equities": equities,
    },
    domain="fixed_income",
    targets="equities::VALUE_MINUS_GROWTH",
    horizons=(1, 5, 20),
    lags=(0, 1, 5),
)

print(ideas.to_frame())
```

The default screening layer can generate candidates from:

- chronology-safe lagged relationships;
- high/low state or regime differences;
- cointegration candidates;
- structural mean/variance changes;
- serial dependence and tail behaviour;
- correlation breaks;
- yield-curve factor and regime diagnostics through the existing discovery engine.

### Data-mining controls

Every statistical screening run records:

- total number of tests performed;
- chronological discovery and holdout sample sizes;
- discovery effect size;
- raw discovery p-value;
- Benjamini-Hochberg FDR q-value;
- holdout effect and p-value;
- transformation applied to each variable;
- data status and falsification rule.

Data statuses are deliberately explicit:

- `EXPLORATORY`
- `DATA_SUPPORTED`
- `OUT_OF_SAMPLE_SUPPORTED`
- `INCONCLUSIVE`
- `FALSIFIED`
- `LITERATURE_DERIVED`

A data status is **not** a novelty status.

## Literature-driven discovery

The existing source-linked literature engine is preserved:

```python
corpus = asr.LiteratureCorpus.from_pdfs("papers/", topic="interest rates")
ideas = asr.hypotheses.from_literature(corpus, topic="interest rates")
```

Page-level source excerpts, corpus fingerprints and conservative corpus-relative labels remain part of the workflow.

## Combined discovery

```python
ideas = asr.hypotheses.discover(
    data=research_panel,
    papers="papers/",
    domain="fixed_income",
)
```

When both data and literature are supplied, data-generated candidates are audited against the supplied corpus. The audit may return:

- `PRIOR_ART_FOUND`
- `CORPUS_RELATED`
- `POTENTIAL_GAP`
- `CONTRADICTORY_LITERATURE`
- `NOVELTY_NOT_ESTABLISHED`

None of these labels means global novelty has been proven.

## Search

```python
matches = asr.hypotheses.search(
    "forward curve instability before rate regime transitions",
    hypotheses=ideas,
    papers=corpus,
)

print(matches.hypotheses)
print(matches.excerpts)
```

The search surface returns generated hypothesis matches and source-linked literature excerpts separately.

## Novelty audit

```python
audit = ideas.audit(0, corpus=corpus)
print(audit.summary)
print(audit.closest_matches)
```

The novelty audit is intentionally fail-safe. Without a supplied corpus it returns `NOVELTY_NOT_ESTABLISHED`. Even with a corpus, the result is explicitly corpus-relative and must be followed by a documented prior-art review before public novelty language is used.

## ResearchProject hand-off

A selected hypothesis enters the existing ASRQuant research pipeline directly:

```python
project = ideas.start(0)
```

The hand-off preserves:

- hypothesis statement;
- research question;
- predictor and target;
- expected sign and horizon;
- data evidence;
- suggested methods;
- falsification criteria;
- prior-art references;
- data and novelty statuses.

From there the normal ASRQuant workflow continues through data planning, feature construction, econometrics/ML, portfolio/backtest experiments, robustness, decision governance and publication artifacts.

## Research rule

ASRQuant may automate **candidate generation, screening, ranking and evidence organization**. It does not automate scientific truth. A candidate remains a research object until the evidence, assumptions, prior art and falsification tests have been reviewed.
