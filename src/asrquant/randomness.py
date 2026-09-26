"""Central random-seed helpers for reproducible ASRQuant experiments."""
from __future__ import annotations

import os
import random as _random

import numpy as np

_CURRENT_SEED: int | None = None


def seed(value: int) -> np.random.Generator:
    """Seed Python and NumPy legacy RNGs and return a modern Generator."""
    global _CURRENT_SEED
    value = int(value)
    if value < 0:
        raise ValueError("seed must be non-negative")
    _CURRENT_SEED = value
    _random.seed(value)
    np.random.seed(value)
    os.environ["ASRQUANT_RANDOM_SEED"] = str(value)
    return np.random.default_rng(value)


def current_seed() -> int | None:
    return _CURRENT_SEED


def generator(value: int | None = None) -> np.random.Generator:
    return np.random.default_rng(_CURRENT_SEED if value is None else int(value))


__all__ = ["seed", "current_seed", "generator"]
