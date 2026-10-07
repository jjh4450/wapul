# %% [markdown]
# # Shape feature: statements that look the same
#
# Error analysis (`block_errors.py`) found repeated statements the gold keeps in one block and the
# model splits: `if (v[i][0] == 'P') p = min(p, a[0]);` six times, two mirrored loops. The pair
# features compare only statement category and node type. Here each unit becomes its AST shape
# (leaf tokens, identifiers as ID, numbers as NUM, strings as STR), and a pair gets two features:
# same shape, and the shapes' sequence similarity.
#
# 1. how often similar-shaped logic pairs share a gold block, and where the model's errors fall
# 2. 5-fold blocks-ensemble with the two features added, seeds as in `blocks_cv.py`
#
#     python notebooks/shape_feature.py

# %%
from difflib import SequenceMatcher
from itertools import combinations

import numpy as np
from sklearn.model_selection import KFold
from tree_sitter import Node

from wapul_ml.data.solutions import load_solutions
from wapul_ml.evaluation.metrics import PartitionScore
from wapul_ml.features import candidates
from wapul_ml.features.unit_ast import _byte_offsets, analyze, segment_features
from wapul_ml.models.block_ranker import predict_blocks, train_ensemble
from wapul_ml.units import parser

SEEDS = 5
STRINGS = {"string_literal", "char_literal", "raw_string_literal", "string", "character_literal", "concatenated_string"}
NUMBERS = {
    "number_literal",
    "integer",
    "float",
    "decimal_integer_literal",
    "hex_integer_literal",
    "decimal_floating_point_literal",
}


def _leaves(n: Node, s: int, e: int, out: list[str]) -> None:
    if n.end_byte <= s or n.start_byte >= e:
        return
    if n.type in STRINGS:
        out.append("STR")
    elif n.type in NUMBERS:
        out.append("NUM")
    elif n.type == "identifier":
        out.append("ID")
    elif n.child_count == 0:
        if n.type != "comment":
            out.append(n.text.decode())
    else:
        for c in n.children:
            _leaves(c, s, e, out)


def shapes(code: str, language: str, spans) -> list[tuple[str, ...]]:
    data = code.encode()
    root = parser(language).parse(data).root_node
    offset = _byte_offsets(code, data)
    out = []
    for (l1, c1), (l2, c2) in spans:
        s, e = offset(l1, c1), offset(l2, c2)
        leaves: list[str] = []
        _leaves(root.descendant_for_byte_range(s, e), s, e, leaves)
        out.append(tuple(leaves))
    return out


def similarity(a: tuple, b: tuple) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


# %% [markdown]
# ## Signal before training
#
# Logic pairs by shape similarity: how often they share a gold block, and their share of the
# baseline's out-of-fold errors (blocks-ensemble, seed 0).

# %%
sols = load_solutions()
baseline = [candidates.BlockCandidates(s) for s in sols]
folds = list(KFold(5, shuffle=True, random_state=0).split(sols))
pred = [None] * len(sols)
for fold, (train_ids, test_ids) in enumerate(folds):
    score = train_ensemble([baseline[i] for i in train_ids], seed=fold)
    for i in test_ids:
        pred[i] = predict_blocks(score, baseline[i]) if len(baseline[i]) else []

rows = []
for s, p in zip(sols, pred, strict=True):
    sh = shapes(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
    logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
    for (a, x), (b, y) in combinations(enumerate(logic), 2):
        same, same_pred = s.units[x].block == s.units[y].block, p[a] == p[b]
        r = similarity(sh[x], sh[y])
        rows.append(
            dict(
                bucket="identical" if sh[x] == sh[y] else "0.8+" if r >= 0.8 else "0.5-0.8" if r >= 0.5 else "<0.5",
                near=b - a <= 8,
                same=same,
                outcome="merged" if same_pred and not same else "split" if same and not same_pred else "correct",
            )
        )
n_out = {o: sum(r["outcome"] == o for r in rows) for o in ("merged", "split", "correct")}
for near in (True, False):
    print(
        f"\nlogic pairs {'within' if near else 'beyond'} 8 units: shape bucket, gold same-block rate, share of errors"
    )
    for k in ("identical", "0.8+", "0.5-0.8", "<0.5"):
        g = [r for r in rows if r["bucket"] == k and r["near"] == near]
        share = "  ".join(f"{o} {sum(r['outcome'] == o for r in g) / n_out[o]:.3f}" for o in n_out)
        print(f"  {k:10s} n {len(g):6d}  same {np.mean([r['same'] for r in g]):.3f}  {share}")

# %% [markdown]
# ## Cross-validation with the shape features
#
# The two features join the pair features through the candidates module, so the library and the
# saved model stay as they are until the result is in.

# %%
_analyze = analyze


def analyze_with_shape(code, language, spans):
    out = _analyze(code, language, spans)
    for a, sh in zip(out, shapes(code, language, spans), strict=True):
        a.shape = sh
    return out


def pair_features(x, y):
    return [*segment_features(x, y), x.shape == y.shape, similarity(x.shape, y.shape)]


candidates.analyze, candidates.segment_features, candidates.N_PAIR = analyze_with_shape, pair_features, 16
data = [candidates.BlockCandidates(s) for s in sols]
results = []
for seed in range(SEEDS):
    grouping = PartitionScore()
    for fold, (train_ids, test_ids) in enumerate(folds):
        score = train_ensemble([data[i] for i in train_ids], seed=seed * 5 + fold)
        for i in test_ids:
            if len(data[i]):
                grouping.add(data[i].blocks, predict_blocks(score, data[i]))
    results.append(grouping.result())
    print(f"  seed {seed}  " + "  ".join(f"{k} {v:.3f}" for k, v in results[-1].items()), flush=True)
print(
    "blocks-ensemble + shape, mean ± std over seeds (blocks-ensemble alone: B3 0.816±0.002  CEAFe 0.742±0.004  pairF1 0.678±0.006)"
)
print(
    "  "
    + "  ".join(f"{k} {np.mean([r[k] for r in results]):.3f}±{np.std([r[k] for r in results]):.3f}" for k in results[0])
)
