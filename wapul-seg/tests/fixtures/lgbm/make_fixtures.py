"""Regenerate the multiclass and ranking LightGBM fixtures and their expected outputs.

Run where lightgbm, numpy and scipy are installed (the wapul-ml image has the LightGBM the models
are trained with), from this directory:

    python make_fixtures.py

Each `.cases` line is one sample: `index:value` pairs (absent features are zero, as in LightGBM's
sparse input), then `|` and LightGBM's raw scores, then `|` and its transformed predictions.
"""

import lightgbm as lgb
import numpy as np
from scipy.sparse import csr_matrix


def write_cases(path, rows, raw, pred):
    with open(path, "w", newline="\n") as f:
        for row, r, p in zip(rows, raw, pred, strict=True):
            feats = " ".join(f"{i}:{v!r}" for i, v in row)
            f.write(f"{feats} | {' '.join(repr(float(x)) for x in np.atleast_1d(r))} | {' '.join(repr(float(x)) for x in np.atleast_1d(p))}\n")


def sparse_rows(X):
    X = csr_matrix(X)
    return [list(zip(X.indices[X.indptr[k] : X.indptr[k + 1]].tolist(), X.data[X.indptr[k] : X.indptr[k + 1]].tolist(), strict=True)) for k in range(X.shape[0])]


common = dict(deterministic=True, num_threads=1, seed=0, verbose=-1)

# Multiclass on sparse binary features plus two continuous ones, like the kind classifier's input
rng = np.random.default_rng(5)
N, F = 3000, 300
X = np.zeros((N, F + 2))
for k in range(N):
    X[k, rng.choice(F, 10, replace=False)] = 1.0
X[:, F] = rng.integers(0, 6, N) / 5
X[:, F + 1] = rng.random(N)
y = (X[:, :40].sum(1) > 1).astype(int) + 2 * (X[:, F + 1] > 0.6) + (X[:, 40:60].sum(1) > 0) * (X[:, F] > 0.5)
y = np.clip(y, 0, 3)
booster = lgb.train(
    dict(objective="multiclass", num_class=4, num_leaves=15, learning_rate=0.2, min_data_in_leaf=10, **common),
    lgb.Dataset(csr_matrix(X), y),
    num_boost_round=20,
)
booster.save_model("tiny_multiclass.lgb")
T = np.zeros((8, F + 2))
for k in range(1, 8):
    T[k, rng.choice(F, 10, replace=False)] = 1.0
T[1:, F] = [0.0, 0.2, 0.6, 1.0, 0.4, 0.8, 0.2]
T[1:, F + 1] = [0.1, 0.9, 0.5, 0.65, 0.0, 0.3, 0.99]  # row 0 is all zeros: every feature absent
Ts = csr_matrix(T)
write_cases("tiny_multiclass.cases", sparse_rows(Ts), booster.predict(Ts, raw_score=True), booster.predict(Ts))

# LambdaRank on dense features, like the block ranker
rng = np.random.default_rng(9)
Q, D = 200, 6
X = rng.standard_normal((Q * D, 10))
X[rng.random(X.shape) < 0.2] = 0.0
rel = np.clip((X[:, 0] + 0.5 * X[:, 1] + 0.3 * rng.standard_normal(Q * D) + 1.5).round(), 0, 3).astype(int)
booster = lgb.train(
    dict(objective="lambdarank", num_leaves=7, learning_rate=0.2, min_data_in_leaf=10, **common),
    lgb.Dataset(X, rel, group=[D] * Q),
    num_boost_round=15,
)
booster.save_model("tiny_rank.lgb")
T = rng.standard_normal((6, 10))
T[0] = 0.0
T[1, :5] = 0.0
write_cases("tiny_rank.cases", sparse_rows(T), booster.predict(T, raw_score=True), booster.predict(T))
print("lightgbm", lgb.__version__)
