import numpy as np
from scipy.stats import chi2_contingency, ks_2samp


def psi(expected, observed):
    a = np.asarray(expected, dtype=float) + .5
    b = np.asarray(observed, dtype=float) + .5
    a /= a.sum()
    b /= b.sum()
    return float(((b - a) * np.log(b / a)).sum())


def compare(train, current, categorical=False):
    train, current = train.dropna(), current.dropna()
    if train.empty or current.empty:
        return {"psi": None, "p_value": None}
    if categorical:
        categories = sorted(set(train) | set(current))
        a = train.value_counts().reindex(categories, fill_value=0)
        b = current.value_counts().reindex(categories, fill_value=0)
        p = chi2_contingency([a, b], correction=False).pvalue
    else:
        cut = np.unique(np.quantile(train, np.arange(1, 10) / 10))
        bins = np.r_[-np.inf, cut, np.inf]
        a, b = (np.histogram(values, bins)[0] for values in (train, current))
        p = ks_2samp(train, current).pvalue
    return {"psi": psi(a, b), "p_value": float(p)}
