"""Which pair classifier groups logic units best? Everything else as in the baseline.

    python -m wapul_ml.pair_clf [--model intfloat/e5-base-v2] [variant ...]

Logic grouping given gold kinds, same folds, fit/dev split, block scorer and alpha choice as
baseline.py; only the "same block?" classifier changes. "small" variants see only the
SEGMENT and position features (no embedding), the rest see the whole pair row.
rbf-svm-small is the baseline's own classifier.
"""

import argparse
import time

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.kernel_approximation import Nystroem
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import SVC, LinearSVC

import wapul_ml.baseline as B
from wapul_ml.data import load_solutions
from wapul_ml.metrics import PartitionScore

VARIANTS = {
    "lr": lambda: LogisticRegression(max_iter=3000),
    "gbm-small": lambda: make_pipeline(
        FunctionTransformer(B.structural_columns), HistGradientBoostingClassifier(random_state=0)
    ),
    "rbf-svm-small": lambda: make_pipeline(
        FunctionTransformer(B.structural_columns), StandardScaler(), SVC(probability=True, random_state=0)
    ),
    # Exact RBF SVM is quadratic in the tens of thousands of pairs: approximate the kernel
    "rbf-svm-full": lambda: CalibratedClassifierCV(
        make_pipeline(StandardScaler(), Nystroem(n_components=1000, random_state=0), LinearSVC(C=0.1, max_iter=5000)),
        cv=3,
    ),
}


def fit_with(factory):
    def fit_pair_clf(feats):
        X, y = [], []
        for f in feats:
            idx = B.logic_idx(B.gold_kinds(f))
            rows, pairs = B.pair_features(f, idx)
            X += rows
            y += [f.sol.units[idx[a]].block == f.sol.units[idx[b]].block for a, b in pairs]
        return factory().fit(np.array(X), np.array(y))

    return fit_pair_clf


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="intfloat/e5-base-v2")
    ap.add_argument("variants", nargs="*", default=list(VARIANTS))
    args = ap.parse_args()

    sols = load_solutions()
    feats = B.featurize(sols, args.model)
    for name in args.variants:
        t = time.time()
        fit = fit_with(VARIANTS[name])
        scores = {s: PartitionScore() for s in ("closest-first", "block scoring")}
        for train, test in KFold(5, shuffle=True, random_state=0).split(sols):
            shuffled = [train[i] for i in np.random.default_rng(0).permutation(len(train))]
            fit_ids, dev_ids = shuffled[: len(train) * 4 // 5], shuffled[len(train) * 4 // 5 :]
            dev_part = [feats[i] for i in dev_ids]
            pair_clf = fit([feats[i] for i in fit_ids])
            block_clfs = {"closest-first": None, "block scoring": B.fit_block_clf(dev_part, pair_clf)}
            for s, score in scores.items():
                alpha = B.choose_alpha(dev_part, pair_clf, block_clfs[s])
                for i in test:
                    f = feats[i]
                    if f.sol.source != "human":
                        continue
                    idx = B.logic_idx(B.gold_kinds(f))
                    score.add(
                        [f.sol.units[j].block for j in idx], B.predict_blocks(f, idx, pair_clf, block_clfs[s], alpha)
                    )
        for s, score in scores.items():
            print(f"{name:<14} {s:<14} " + "  ".join(f"{k} {v:.3f}" for k, v in score.result().items()), flush=True)
        print(f"  ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
