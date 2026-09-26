"""Friendly estimator factories that keep scikit-learn behind ASRQuant's API."""
from __future__ import annotations

from typing import Any


def _common(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Translate friendly ASRQuant names into backend estimator arguments."""
    out = dict(kwargs)
    aliases = {
        "seed": "random_state",
        "trees": "n_estimators",
        "depth": "max_depth",
        "jobs": "n_jobs",
        "iterations": "max_iter",
        "learning_rate_value": "learning_rate",
        "neighbors": "n_neighbors",
        "components": "n_components",
        "clusters": "n_clusters",
    }
    for friendly, backend in aliases.items():
        if friendly in out and backend not in out:
            out[backend] = out.pop(friendly)
    return out


def linear_regression(**kwargs: Any):
    from sklearn.linear_model import LinearRegression
    return LinearRegression(**_common(kwargs))


def ridge(alpha: float = 1.0, **kwargs: Any):
    from sklearn.linear_model import Ridge
    return Ridge(alpha=alpha, **_common(kwargs))


def lasso(alpha: float = 1.0, **kwargs: Any):
    from sklearn.linear_model import Lasso
    return Lasso(alpha=alpha, **_common(kwargs))


def elastic_net(alpha: float = 1.0, l1_ratio: float = 0.5, **kwargs: Any):
    from sklearn.linear_model import ElasticNet
    return ElasticNet(alpha=alpha, l1_ratio=l1_ratio, **_common(kwargs))


def logistic_regression(**kwargs: Any):
    from sklearn.linear_model import LogisticRegression
    options = _common(kwargs)
    options.setdefault("max_iter", 1000)
    return LogisticRegression(**options)


def decision_tree(*, task: str = "regression", **kwargs: Any):
    options = _common(kwargs)
    if task == "classification":
        from sklearn.tree import DecisionTreeClassifier
        return DecisionTreeClassifier(**options)
    if task == "regression":
        from sklearn.tree import DecisionTreeRegressor
        return DecisionTreeRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def random_forest(*, task: str = "regression", trees: int = 300, seed: int | None = 7, **kwargs: Any):
    options = _common({"trees": trees, "seed": seed, **kwargs})
    if task == "classification":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(**options)
    if task == "regression":
        from sklearn.ensemble import RandomForestRegressor
        return RandomForestRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def extra_trees(*, task: str = "regression", trees: int = 300, seed: int | None = 7, **kwargs: Any):
    options = _common({"trees": trees, "seed": seed, **kwargs})
    if task == "classification":
        from sklearn.ensemble import ExtraTreesClassifier
        return ExtraTreesClassifier(**options)
    if task == "regression":
        from sklearn.ensemble import ExtraTreesRegressor
        return ExtraTreesRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def gradient_boosting(*, task: str = "regression", seed: int | None = 7, **kwargs: Any):
    options = _common({"seed": seed, **kwargs})
    if task == "classification":
        from sklearn.ensemble import GradientBoostingClassifier
        return GradientBoostingClassifier(**options)
    if task == "regression":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def histogram_gradient_boosting(*, task: str = "regression", seed: int | None = 7, **kwargs: Any):
    options = _common({"seed": seed, **kwargs})
    if task == "classification":
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(**options)
    if task == "regression":
        from sklearn.ensemble import HistGradientBoostingRegressor
        return HistGradientBoostingRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def knn(*, task: str = "regression", neighbors: int = 5, **kwargs: Any):
    options = _common({"neighbors": neighbors, **kwargs})
    if task == "classification":
        from sklearn.neighbors import KNeighborsClassifier
        return KNeighborsClassifier(**options)
    if task == "regression":
        from sklearn.neighbors import KNeighborsRegressor
        return KNeighborsRegressor(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def svm(*, task: str = "regression", **kwargs: Any):
    options = _common(kwargs)
    if task == "classification":
        from sklearn.svm import SVC
        options.setdefault("probability", True)
        return SVC(**options)
    if task == "regression":
        from sklearn.svm import SVR
        return SVR(**options)
    raise ValueError("task must be 'regression' or 'classification'")


def naive_bayes(**kwargs: Any):
    from sklearn.naive_bayes import GaussianNB
    return GaussianNB(**_common(kwargs))


def pca(components: int | float | None = None, **kwargs: Any):
    from sklearn.decomposition import PCA
    options = _common(kwargs)
    if components is not None:
        options["n_components"] = components
    return PCA(**options)


def kmeans(clusters: int = 8, seed: int | None = 7, **kwargs: Any):
    from sklearn.cluster import KMeans
    options = _common({"clusters": clusters, "seed": seed, **kwargs})
    options.setdefault("n_init", "auto")
    return KMeans(**options)


def isolation_forest(trees: int = 200, seed: int | None = 7, **kwargs: Any):
    from sklearn.ensemble import IsolationForest
    return IsolationForest(**_common({"trees": trees, "seed": seed, **kwargs}))


def create(name: str, *, task: str | None = None, **kwargs: Any):
    """Create an estimator from a stable ASRQuant name.

    Examples
    --------
    >>> model = create("random_forest", task="regression", trees=500)
    >>> classifier = create("logistic")
    """
    key = name.lower().strip().replace("-", "_").replace(" ", "_")
    aliases = {
        "linear": "linear_regression",
        "ols": "linear_regression",
        "logistic": "logistic_regression",
        "rf": "random_forest",
        "randomforest": "random_forest",
        "gbm": "gradient_boosting",
        "gradient_boosted_trees": "gradient_boosting",
        "hist_gbm": "histogram_gradient_boosting",
        "nearest_neighbors": "knn",
        "support_vector_machine": "svm",
        "support_vector": "svm",
        "gaussian_nb": "naive_bayes",
    }
    key = aliases.get(key, key)
    factories = {
        "linear_regression": linear_regression,
        "ridge": ridge,
        "lasso": lasso,
        "elastic_net": elastic_net,
        "logistic_regression": logistic_regression,
        "decision_tree": decision_tree,
        "random_forest": random_forest,
        "extra_trees": extra_trees,
        "gradient_boosting": gradient_boosting,
        "histogram_gradient_boosting": histogram_gradient_boosting,
        "knn": knn,
        "svm": svm,
        "naive_bayes": naive_bayes,
        "pca": pca,
        "kmeans": kmeans,
        "isolation_forest": isolation_forest,
    }
    if key not in factories:
        raise ValueError(f"unknown model {name!r}; available: {sorted(factories)}")
    factory = factories[key]
    if task is not None and key in {
        "decision_tree", "random_forest", "extra_trees", "gradient_boosting",
        "histogram_gradient_boosting", "knn", "svm"
    }:
        kwargs["task"] = task
    return factory(**kwargs)


class ModelFactory:
    """Attribute-based model factory exposed as ``asrquant.models``."""

    create = staticmethod(create)
    linear_regression = staticmethod(linear_regression)
    ridge = staticmethod(ridge)
    lasso = staticmethod(lasso)
    elastic_net = staticmethod(elastic_net)
    logistic_regression = staticmethod(logistic_regression)
    decision_tree = staticmethod(decision_tree)
    random_forest = staticmethod(random_forest)
    extra_trees = staticmethod(extra_trees)
    gradient_boosting = staticmethod(gradient_boosting)
    histogram_gradient_boosting = staticmethod(histogram_gradient_boosting)
    knn = staticmethod(knn)
    svm = staticmethod(svm)
    naive_bayes = staticmethod(naive_bayes)
    pca = staticmethod(pca)
    kmeans = staticmethod(kmeans)
    isolation_forest = staticmethod(isolation_forest)


models = ModelFactory()

__all__ = [
    "ModelFactory", "models", "create", "linear_regression", "ridge", "lasso",
    "elastic_net", "logistic_regression", "decision_tree", "random_forest",
    "extra_trees", "gradient_boosting", "histogram_gradient_boosting", "knn",
    "svm", "naive_bayes", "pca", "kmeans", "isolation_forest",
]
