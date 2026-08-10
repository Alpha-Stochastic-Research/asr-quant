import numpy as np

from asrquant import QuantLab
from asrquant.validation import purged_kfold_splits, walk_forward_splits


def test_audit_grid(prices):
    lab = QuantLab(prices)
    audit = lab.audit("sma", fast=10, slow=40, execution_delays=(0, 1), linear_costs_bps=(0, 5, 10))
    assert len(audit.summary) == 6
    assert audit.diagnostics["return_engine_sensitivity"] >= 0
    assert 0 <= audit.diagnostics["conclusion_stability_index"] <= 1


def test_walk_forward_has_temporal_order():
    splits = list(walk_forward_splits(100, train_size=40, test_size=10))
    assert len(splits) > 0
    for split in splits:
        assert split.train.max() < split.test.min()


def test_purged_kfold_removes_neighbours():
    splits = list(purged_kfold_splits(50, n_splits=5, purge=2, embargo=3))
    assert len(splits) == 5
    for split in splits:
        assert len(np.intersect1d(split.train, split.test)) == 0
        if len(split.train):
            assert not any(abs(i - j) <= 2 for i in split.train for j in split.test)
