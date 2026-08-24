# ASR Research & Analyst Operating Model

The package is designed so that Research and Analyst teams can share one evidence chain instead of exchanging disconnected notebooks.

## Responsibilities

**Analyst team**
- collect and document data;
- inspect market structure and descriptive diagnostics;
- generate candidate observations;
- map definitions and market conventions;
- build figures/tables and interpret economic meaning;
- document data limitations and availability lags.

**Research team**
- formalize the question and falsifiable hypothesis;
- map the closest literature and prior art;
- select models and baselines;
- derive/implement methods;
- perform statistical testing, calibration and robustness;
- decide which claims are supported.

**Independent reviewer / reproducibility reviewer**
- rerun the work from clean inputs;
- inspect look-ahead, leakage and specification risk;
- challenge the novelty statement;
- verify formulas, conventions and limitations;
- approve/reject the public claim, not merely the code execution.

## Shared A-to-Z API

```python
import asrquant as asr

# 1. Discover
board = asr.discovery.weekly(data=data, domain="fixed_income", n=10)

# 2. Select and formalize
project = board.start(0)

# 3. Run the existing ASRQuant research workflow
# project.plan_data(...)
# project.attach_data(...)
# project.features(...)
# project.test_hypothesis(...)
# project.backtest(...)
# project.robustness(...)
# project.decide(...)

# 4. Package the Friday-to-Friday publication
cycle = asr.weekly_cycle(board, 0, launch_friday="2026-08-14")
cycle.publication_pack("WR-001")
```

The project manifest and publication pack are the hand-off between teams. The package does not replace scientific judgment or approval.
