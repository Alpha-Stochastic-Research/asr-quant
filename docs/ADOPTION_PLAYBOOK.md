# ASRQuant Adoption Playbook

This document is an operational launch checklist for increasing **real ASRQuant adoption**, not artificial download volume.

## Primary conversion path

**Technical post / search / GitHub discovery → practical case → `pip install asrquant` → first result → docs → star / issue / contribution**

## Public assets to reuse

- PyPI: https://pypi.org/project/asrquant/
- GitHub: https://github.com/Alpha-Stochastic-Research/asr-quant
- Documentation: https://docs.asr-lab.online/
- Practical notebook: `notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb`
- Colab: https://colab.research.google.com/github/Alpha-Stochastic-Research/asr-quant/blob/main/notebooks/ASRQuant_v1.3.0_Public_Practical_Case.ipynb

## Content series

Publish technical demonstrations, not generic promotion.

1. **From ECB curve data to 5Y IRS DV01 in Python**
2. **Why a curve-node bump is not the same as a market-quote bump**
3. **A Sharpe ratio is not enough: PBO, Reality Check and SPA**
4. **How to make a quantitative result reproducible with data fingerprints**
5. **CPCV vs ordinary cross-validation for financial time series**
6. **P&L explain: moving from a position result to a curve explanation**
7. **Stress a rates position with parallel, steepener and flattener scenarios**
8. **Point-in-time data: observation time is not availability time**

Every post should end with one simple call to action:

```bash
pip install --upgrade asrquant
```

and links to the practical notebook, PyPI and documentation.

## GitHub conversion checklist

- [x] Clear one-line positioning
- [x] Install command above the fold
- [x] Dynamic PyPI / Python / license / star / download badges
- [x] Real-world public notebook above the fold
- [x] One-click Colab link
- [x] Capability map by quantitative-finance domain
- [x] Contribution call to action
- [ ] Add `good first issue` / `help wanted` labels to suitable issues
- [ ] Publish 2–3 self-contained beginner contribution issues
- [ ] Add a short demo GIF or static figure after the notebook output is stabilized

## Distribution channels

Prioritize audiences with a genuine reason to use the package:

- quantitative researchers;
- fixed-income / rates researchers;
- quant developers;
- quantitative analysts;
- financial-engineering students;
- researchers teaching reproducible quantitative finance.

Use LinkedIn, GitHub, technical communities and appropriate quant / Python communities. Follow community rules and lead with the tutorial or technical insight rather than promotional copy.

## Metrics to monitor weekly

- PyPI downloads (monthly / weekly trend, not a vanity one-day spike);
- GitHub stars and forks;
- unique repository visitors and clones where available;
- notebook views / Colab launches where observable;
- documentation traffic;
- issues opened by external users;
- first-time contributors;
- repeat contributors;
- external projects or notebooks citing ASRQuant.

## Principle

The goal is not to manufacture downloads. The goal is to shorten the path from **discovering ASRQuant** to **getting a credible quantitative result with it**.
