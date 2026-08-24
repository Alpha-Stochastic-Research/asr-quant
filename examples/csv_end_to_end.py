"""One-import CSV -> quality -> backtest -> audit -> portable report."""
from pathlib import Path

import asrquant as asr

DATA = Path(__file__).with_name("sample_prices.csv")
OUTPUT = Path(__file__).with_name("csv_end_to_end_report.html")

lab = asr.open_lab(DATA, date_column="Date")
print(lab.quality)
result = lab.backtest("sma", fast=20, slow=100, costs_bps=5)
print(result.metrics)
print(lab.audit("sma", fast=20, slow=100, execution_delays=(0, 1, 2)).diagnostics)
asr.report(result, OUTPUT, title="ASRQuant CSV end-to-end example")
print(OUTPUT)
