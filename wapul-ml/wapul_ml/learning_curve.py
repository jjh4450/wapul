"""How much would more labels help? Learning curve plus evaluation noise.

    python -m wapul_ml.learning_curve [--model intfloat/e5-base-v2]

Learning curve: the same 5-fold CV, but each fold trains on a random fraction of its
training solutions (test folds unchanged), several seeds for small fractions. A power law
score = a - b * n^-c fitted to it extrapolates the score at more labeled solutions.

Evaluation noise: bootstrap over the scored solutions of the full-data run. The standard
error shrinks with 1/sqrt(scored solutions), which tells how many reviewed solutions are
needed before a given difference stands out from noise.
"""

import argparse

import numpy as np
from scipy.optimize import curve_fit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import KFold

from wapul_ml.baseline import (
    choose_alpha,
    featurize,
    fit_block_clf,
    fit_pair_clf,
    gold_kinds,
    logic_idx,
    predict_blocks,
)
from wapul_ml.data import load_solutions
from wapul_ml.metrics import PartitionScore

FRACTIONS = {0.25: 3, 0.5: 3, 0.75: 2, 1.0: 1}  # fraction of training solutions -> seeds


def run(feats, frac: float, seed: int):
    """Per scored solution: (gold kinds, predicted kinds, gold blocks, predicted blocks); and train size."""
    out, sizes = [], []
    for train, test in KFold(5, shuffle=True, random_state=0).split(feats):
        rng = np.random.default_rng(seed)
        train = rng.permutation(train)[: max(10, int(len(train) * frac))]
        cut = len(train) * 4 // 5
        fit_part, dev_part = [feats[i] for i in train[:cut]], [feats[i] for i in train[cut:]]
        tr = fit_part + dev_part
        sizes.append(len(tr))
        kind_clf = LogisticRegression(max_iter=3000).fit(
            np.vstack([f.kind_x for f in tr]), [k for f in tr for k in gold_kinds(f)]
        )
        pair_clf = fit_pair_clf(fit_part)
        block_clf = fit_block_clf(dev_part, pair_clf)
        alpha = choose_alpha(dev_part, pair_clf, block_clf)
        for i in test:
            f = feats[i]
            if f.sol.source != "human":
                continue
            gold = gold_kinds(f)
            idx = logic_idx(gold)
            out.append(
                (
                    gold,
                    list(kind_clf.predict(f.kind_x)),
                    [f.sol.units[j].block for j in idx],
                    predict_blocks(f, idx, pair_clf, block_clf, alpha),
                )
            )
    return out, float(np.mean(sizes))


def scores(rows) -> dict[str, float]:
    kind_true = [k for r in rows for k in r[0]]
    kind_pred = [k for r in rows for k in r[1]]
    grouping = PartitionScore()
    for r in rows:
        grouping.add(r[2], r[3])
    g = grouping.result()
    return {"kindF1": f1_score(kind_true, kind_pred, average="macro"), "B3": g["B3"], "pairF1": g["pairF1"]}


def power_law(n, a, b, c):
    return a - b * np.power(n, -c)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="intfloat/e5-base-v2")
    args = ap.parse_args()
    feats = featurize(load_solutions(), args.model)

    curve: dict[str, list[tuple[float, float]]] = {"kindF1": [], "B3": [], "pairF1": []}
    full_rows = None
    print("train solutions per fold -> mean score over seeds")
    for frac, seeds in FRACTIONS.items():
        per_seed = []
        for seed in range(seeds):
            rows, size = run(feats, frac, seed)
            per_seed.append(scores(rows))
            if frac == 1.0:
                full_rows = rows
        mean = {k: float(np.mean([s[k] for s in per_seed])) for k in curve}
        for k, v in mean.items():
            curve[k].append((size, v))
        print(f"  {size:6.0f}  " + "  ".join(f"{k} {v:.3f}" for k, v in mean.items()))

    print("\nextrapolated (power law fit; rough with 4 points)")
    for k, pts in curve.items():
        n, y = np.array(pts).T
        try:
            (a, b, c), _ = curve_fit(power_law, n, y, p0=(y[-1] + 0.05, 1.0, 0.5), maxfev=20000)
            preds = "  ".join(f"n={m}: {power_law(m, a, b, c):.3f}" for m in (240, 480, 800, 1600))
            print(f"  {k:<7} ceiling {a:.3f}  {preds}")
        except RuntimeError:
            print(f"  {k:<7} fit failed")

    rng = np.random.default_rng(0)
    boot = {k: [] for k in curve}
    for _ in range(1000):
        sample = [full_rows[i] for i in rng.integers(0, len(full_rows), len(full_rows))]
        for k, v in scores(sample).items():
            boot[k].append(v)
    n_eval = len(full_rows)
    print(f"\nevaluation noise: bootstrap over {n_eval} scored solutions")
    for k, vals in boot.items():
        se = float(np.std(vals))
        # A difference needs about 2 * sqrt(2) * SE to stand out between two independent runs
        print(
            f"  {k:<7} SE {se:.4f}  detectable diff ~{2.83 * se:.3f}  "
            + "  ".join(f"at {m} scored: ~{2.83 * se * np.sqrt(n_eval / m):.3f}" for m in (300, 600, 1000))
        )


if __name__ == "__main__":
    main()
