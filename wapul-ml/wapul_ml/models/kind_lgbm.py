"""Statement kinds with LightGBM over string features (features/kind_features.py).

Matches the fine-tuned CodeBERT on 5-fold macro-F1 (docs/ml/experiments.ko.md) at a fraction of
the size and time, and uses the same runtime as the block ranker. The feature names are saved
next to the trees in column order, so a unit's feature dict maps to the model's input.
"""

import json

import lightgbm
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction import DictVectorizer

from wapul_ml.data.solutions import KINDS

PARAMS = dict(n_estimators=400, learning_rate=0.05, num_leaves=31, class_weight="balanced")


class LgbmKinds:
    def __init__(self, names: list[str], booster: lightgbm.Booster):
        self.names, self.booster = names, booster
        self.column = {name: i for i, name in enumerate(names)}

    def predict(self, feats: list[dict[str, float]]) -> list[str]:
        if not feats:
            return []
        rows, cols, vals = [], [], []
        for r, f in enumerate(feats):
            for name, value in f.items():
                if (c := self.column.get(name)) is not None:
                    rows.append(r)
                    cols.append(c)
                    vals.append(value)
        X = csr_matrix((vals, (rows, cols)), shape=(len(feats), len(self.names)), dtype=np.float32)
        return [KINDS[i] for i in self.booster.predict(X).argmax(1)]

    def save(self, trees, names) -> None:
        self.booster.save_model(str(trees))
        names.write_text(json.dumps({"kinds": KINDS, "features": self.names}, ensure_ascii=False))

    @classmethod
    def load(cls, trees, names) -> "LgbmKinds":
        state = json.loads(names.read_text())
        if tuple(state["kinds"]) != KINDS:
            raise ValueError(f"{names} has kinds {state['kinds']}, this code uses {KINDS}")
        return cls(state["features"], lightgbm.Booster(model_file=str(trees)))


def train(feats: list[dict[str, float]], kinds: list[str], seed: int = 0, keep: set[str] | None = None) -> LgbmKinds:
    """`keep`: only these feature names enter the model (segmenter-v3 and later)."""
    if keep is not None:
        feats = [{n: v for n, v in f.items() if n in keep} for f in feats]
    vec = DictVectorizer()
    X = vec.fit_transform(feats).astype(np.float32)
    clf = lightgbm.LGBMClassifier(**PARAMS, random_state=seed, verbose=-1)
    clf.fit(X, [KINDS.index(k) for k in kinds])  # every kind occurs, so classes are KINDS in order
    return LgbmKinds(list(vec.feature_names_), clf.booster_)
