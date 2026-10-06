# %% [markdown]
# # Baseline: cross-validation
#
# Kind classifier + baseline block grouping (`wapul_ml/models/baseline.py`), 5-fold CV scored on
# the human-reviewed solutions.
#
# Kinds: CodeBERT fine-tuned per fold on each unit with K units of context on each side
# (`kind_classifier.py`). `--model` is the frozen embedding the block grouping reads.
#
# Each training fold is split into fit and dev parts: the pair classifier learns on fit; the
# block scorer, alpha, and which scorer to use are chosen on dev, so test solutions never steer
# a choice.
#
#     python notebooks/baseline_cv.py [--model intfloat/e5-base-v2] [--sweep] [--pair-features structural]

# %%
import argparse

import numpy as np
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold
from transformers import AutoTokenizer

from wapul_ml.data.solutions import KINDS, context_text, load_solutions
from wapul_ml.evaluation.metrics import PartitionScore
from wapul_ml.models import baseline, kind_classifier
from wapul_ml.models.baseline import (
    ALPHAS,
    best_alpha,
    featurize,
    fit_block_clf,
    fit_pair_clf,
    full_partition,
    gold_kinds,
    logic_idx,
    predict_blocks,
)

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="intfloat/e5-base-v2")
ap.add_argument("--sweep", action="store_true", help="also score every alpha on test, to see the merge/split trade-off")
ap.add_argument("--pair-features", choices=("all", "structural"), default="all")
args = ap.parse_known_args()[0]  # known args only: a Jupyter kernel passes arguments of its own
baseline.PAIR_FEATURES = args.pair_features

# %%
sols = load_solutions()
feats = featurize(sols, args.model)
tok = AutoTokenizer.from_pretrained(kind_classifier.MODEL)
kind_true, kind_pred = [], []
scorers = ("closest-first", "block scoring")
# "chosen on dev": per fold, the scorer whose best alpha scores higher on dev
grouping = {s: PartitionScore() for s in (*scorers, "chosen on dev")}
end_to_end = {s: PartitionScore() for s in (*scorers, "chosen on dev")}
singletons, one_block = PartitionScore(), PartitionScore()
alphas = {s: [] for s in scorers}
chosen_per_fold = []
# Analysis only: alpha -> (score, predicted block count, gold block count) with block scoring
sweep = {a: [PartitionScore(), 0, 0] for a in ALPHAS}

for fold, (train, test) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
    shuffled = [train[i] for i in np.random.default_rng(0).permutation(len(train))]
    fit_ids, dev_ids = shuffled[: len(train) * 4 // 5], shuffled[len(train) * 4 // 5 :]
    fit_part, dev_part = [feats[i] for i in fit_ids], [feats[i] for i in dev_ids]
    kind_model = kind_classifier.train(
        kind_classifier.MODEL, tok, *kind_classifier.examples(sols, train), kind_classifier.EPOCHS, seed=fold
    )
    pair_clf = fit_pair_clf(fit_part)
    block_clfs = {"closest-first": None, "block scoring": fit_block_clf(dev_part, pair_clf)}
    best = {s: best_alpha(dev_part, pair_clf, block_clfs[s]) for s in scorers}
    alpha = {s: best[s][0] for s in scorers}
    for s in scorers:
        alphas[s].append(float(alpha[s]))
    chosen = max(scorers, key=lambda s: best[s][1])
    chosen_per_fold.append(chosen)

    for i in test:
        f = feats[i]
        if f.sol.source != "human":
            continue
        gold = gold_kinds(f)
        texts = [context_text(f.sol.units, j) for j in range(len(f.sol.units))]
        pred = [KINDS[k] for k in kind_classifier.predict(kind_model, tok, texts)]
        kind_true += gold
        kind_pred += pred
        gold_idx, pred_idx = logic_idx(gold), logic_idx(pred)
        gold_blocks = [f.sol.units[j].block for j in gold_idx]
        singletons.add(gold_blocks, list(range(len(gold_idx))))
        one_block.add(gold_blocks, [0] * len(gold_idx))
        gold_full = full_partition(gold, gold_idx, gold_blocks)
        if args.sweep:
            for a in ALPHAS:
                blocks = predict_blocks(f, gold_idx, pair_clf, block_clfs["block scoring"], a)
                sweep[a][0].add(gold_blocks, blocks)
                sweep[a][1] += len(set(blocks))
                sweep[a][2] += len(set(gold_blocks))
        for s in scorers:
            given = predict_blocks(f, gold_idx, pair_clf, block_clfs[s], alpha[s])
            full = full_partition(pred, pred_idx, predict_blocks(f, pred_idx, pair_clf, block_clfs[s], alpha[s]))
            grouping[s].add(gold_blocks, given)
            end_to_end[s].add(gold_full, full)
            if s == chosen:
                grouping["chosen on dev"].add(gold_blocks, given)
                end_to_end["chosen on dev"].add(gold_full, full)
    del kind_model

# %%
print(f"model: {args.model}  solutions: {len(sols)}  scored (human): {sum(s.source == 'human' for s in sols)}")
print(f"\nkinds  macro-F1 {f1_score(kind_true, kind_pred, average='macro'):.3f}")
print(classification_report(kind_true, kind_pred, labels=list(KINDS), digits=3))


def show(name, r):
    print(f"  {name:<24} " + "  ".join(f"{k} {v:.3f}" for k, v in r.items()))


print("logic grouping, given gold kinds")
show("each alone", singletons.result())
show("all one block", one_block.result())
for s in scorers:
    show(f"{s} (alpha {alphas[s]})", grouping[s].result())
show(f"chosen on dev {chosen_per_fold}", grouping["chosen on dev"].result())
print("end to end (predicted kinds, then grouping)")
for s in (*scorers, "chosen on dev"):
    show(s, end_to_end[s].result())
if args.sweep:
    print("alpha sweep, block scoring, given gold kinds (blocks = predicted / gold logic blocks)")
    for a, (score, n_pred, n_gold) in sweep.items():
        show(f"alpha {a}  blocks {n_pred / n_gold:.2f}x", score.result())
