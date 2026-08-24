"""Numerical helpers exposed through ASRQuant so user code needs one import."""
from __future__ import annotations

from typing import Any

import numpy as _np
from scipy.special import expit as _expit
from scipy.special import logsumexp as _logsumexp
from scipy.stats import norm as _norm

expit = _expit
logsumexp = _logsumexp

# Array and grid construction
array = _np.array
asarray = _np.asarray
arange = _np.arange
linspace = _np.linspace
logspace = _np.logspace
meshgrid = _np.meshgrid
zeros = _np.zeros
ones = _np.ones
full = _np.full
zeros_like = _np.zeros_like
ones_like = _np.ones_like
vstack = _np.vstack
hstack = _np.hstack
concatenate = _np.concatenate
stack = _np.stack
reshape = _np.reshape
ravel = _np.ravel
cumsum = _np.cumsum
cumprod = _np.cumprod
diff = _np.diff

# Elementary functions
abs = _np.abs
exp = _np.exp
log = _np.log
log1p = _np.log1p
sqrt = _np.sqrt
sin = _np.sin
cos = _np.cos
tan = _np.tan
tanh = _np.tanh
maximum = _np.maximum
minimum = _np.minimum
clip = _np.clip
where = _np.where
isfinite = _np.isfinite
isnan = _np.isnan

# Reductions and statistics
mean = _np.mean
median = _np.median
std = _np.std
var = _np.var
sum = _np.sum
min = _np.min
max = _np.max
quantile = _np.quantile
percentile = _np.percentile
corrcoef = _np.corrcoef
cov = _np.cov

pi = _np.pi
nan = _np.nan
inf = _np.inf


def normal_pdf(x: Any, mean: float = 0.0, std: float = 1.0):
    return _norm.pdf(x, loc=mean, scale=std)


def normal_cdf(x: Any, mean: float = 0.0, std: float = 1.0):
    return _norm.cdf(x, loc=mean, scale=std)


def normal_ppf(q: Any, mean: float = 0.0, std: float = 1.0):
    return _norm.ppf(q, loc=mean, scale=std)


def random_generator(seed: int | None = None):
    """Return NumPy's modern generator without requiring a NumPy import."""
    return _np.random.default_rng(seed)


__all__ = [name for name in globals() if not name.startswith("_")]
