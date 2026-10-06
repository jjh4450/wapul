# %% [markdown]
# # Logic blocks: cross-validation
#
# Scores a block scorer (`wapul_ml/models/block_ranker.py`) given gold kinds, on the same 5 folds
# as the other notebooks. Candidates are every earlier logic unit (mlp, lgbm, ensemble) or the
# blocks built so far (blocks-*). MLP variants repeat every fold over several seeds.
#
#     python notebooks/blocks_cv.py [--variant blocks-ensemble]

# %%
import argparse

import numpy as np
from sklearn.model_selection import KFold

from wapul_ml.data.solutions import load_solutions
from wapul_ml.evaluation.metrics import PartitionScore
from wapul_ml.features.candidates import BlockCandidates, Candidates
from wapul_ml.models.block_ranker import predict, predict_blocks, train_ensemble, train_lgbm, train_mlp

SEEDS = 5
SCORERS = {
    "mlp": (train_mlp, SEEDS),
    "lgbm": (train_lgbm, 1),
    "ensemble": (train_ensemble, SEEDS),
}  # lgbm: deterministic
VARIANTS = [*SCORERS, *(f"blocks-{s}" for s in SCORERS)]

ap = argparse.ArgumentParser()
ap.add_argument("--variant", choices=VARIANTS, default="blocks-ensemble")
args = ap.parse_known_args()[0]  # known args only: a Jupyter kernel passes arguments of its own
blocks = args.variant.startswith("blocks-")
fit, seeds = SCORERS[args.variant.removeprefix("blocks-")]

# %%
sols = load_solutions()
if blocks:
    data, decode = [BlockCandidates(s) for s in sols], predict_blocks
else:
    data, decode = [Candidates(s) for s in sols], predict
results = []
for seed in range(seeds):
    grouping = PartitionScore()
    for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
        score = fit([data[i] for i in train_ids], seed=seed * 5 + fold)
        for i in test_ids:
            if len(data[i]):
                grouping.add(data[i].blocks, decode(score, data[i]))
    r = grouping.result()
    results.append(r)
    print(f"  seed {seed}  " + "  ".join(f"{k} {v:.3f}" for k, v in r.items()), flush=True)

# %%
print(f"logic grouping, given gold kinds, {args.variant}, mean ± std over {seeds} seeds")
print(
    "  "
    + "  ".join(f"{k} {np.mean([r[k] for r in results]):.3f}±{np.std([r[k] for r in results]):.3f}" for k in results[0])
)
