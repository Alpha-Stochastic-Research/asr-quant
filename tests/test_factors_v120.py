import numpy as np
import pandas as pd
import pytest

import asrquant as asr


def factor_sample(rows=500, seed=12):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-02", periods=rows, freq="B")
    factors = pd.DataFrame(
        rng.normal(0, [0.01, 0.007], size=(rows, 2)),
        index=idx,
        columns=["MKT", "TERM"],
    )
    betas = pd.DataFrame(
        [[1.2, 0.3], [0.8, -0.2], [0.5, 1.1]],
        index=["A", "B", "C"],
        columns=factors.columns,
    )
    noise = rng.normal(0, 0.002, size=(rows, 3))
    assets = pd.DataFrame(factors.to_numpy() @ betas.to_numpy().T + noise, index=idx, columns=betas.index)
    return assets, factors, betas


def test_pca_factor_contract_reconstructs_panel():
    assets, _, _ = factor_sample()
    result = asr.factors.pca(assets, n_components=2)
    assert result.loadings.shape == (3, 2)
    assert result.scores.shape == (500, 2)
    assert result.explained_variance_ratio.sum() > 0.95
    assert result.summary["residual_rmse"] < assets.std().mean()


def test_factor_exposures_recover_synthetic_betas():
    assets, factors, expected = factor_sample(rows=800)
    result = asr.factors.exposures(assets, factors, covariance="HC1")
    assert np.allclose(result.betas.loc[expected.index, expected.columns], expected, atol=0.04)
    assert (result.r_squared > 0.8).all()


def test_rolling_beta_is_finite_after_window():
    assets, factors, _ = factor_sample()
    beta = asr.factors.rolling_beta(assets["A"], factors["MKT"], window=63)
    assert beta.notna().sum() == len(assets) - 62
    assert beta.dropna().median() == pytest.approx(1.2, abs=0.1)


def test_factor_risk_decomposition_adds_to_total_variance():
    _, _, beta = factor_sample()
    factor_cov = pd.DataFrame([[0.04, 0.005], [0.005, 0.02]], index=beta.columns, columns=beta.columns)
    specific = pd.Series([0.01, 0.015, 0.008], index=beta.index)
    result = asr.factors.risk_decomposition(
        pd.Series([0.4, 0.35, 0.25], index=beta.index), beta, factor_cov, specific
    )
    assert result.total_variance == pytest.approx(result.factor_variance + result.specific_variance)
    assert result.factor_variance_contributions.sum() == pytest.approx(result.factor_variance)
    assert result.specific_variance_contributions.sum() == pytest.approx(result.specific_variance)


def test_factor_validation_fails_fast():
    with pytest.raises(ValueError):
        asr.factors.pca(pd.DataFrame({"A": [1, 2]}), n_components=1)
    with pytest.raises(ValueError):
        asr.factors.risk_decomposition([1, 0], [[1], [2]], [[1, 2], [2, 1]], [0.1, 0.2])
