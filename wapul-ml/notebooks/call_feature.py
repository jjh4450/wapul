# %% [markdown]
# # Call feature: a helper function and the statement that calls it
#
# Error analysis (`block_errors.py`): 24% of wrongly split pairs sit in different functions, where
# the gold sometimes keeps a helper function with the statement calling it. The pair features
# have no call relation. Here a pair gets two: the later unit calls the user function holding
# the earlier one, and the other way round.
#
# 1. how often call-linked logic pairs share a gold block, and their share of the model's errors
# 2. 5-fold blocks-ensemble with the two features added, seeds as in `blocks_cv.py`
#
#     python notebooks/call_feature.py

# %%
from itertools import combinations

import numpy as np
from sklearn.model_selection import KFold
from tree_sitter import Node

from wapul_ml.data.solutions import load_solutions
from wapul_ml.evaluation.metrics import PartitionScore
from wapul_ml.features import candidates
from wapul_ml.features.unit_ast import DEFS, _byte_offsets, analyze, segment_features
from wapul_ml.models.block_ranker import predict_blocks, train_ensemble
from wapul_ml.units import parser

SEEDS = 5


def _def_name(n: Node) -> str | None:
    """`int dfs(int u)`, `def dfs(u):`, `static void dfs(int u)` -> "dfs"."""
    if (name := n.child_by_field_name("name")) is not None:
        return name.text.decode()
    d = n.child_by_field_name("declarator")
    while d is not None and d.type != "function_declarator":
        d = d.child_by_field_name("declarator")
    if d is not None and (inner := d.child_by_field_name("declarator")) is not None:
        return inner.text.decode().split("::")[-1]
    return None


def _callees(n: Node, s: int, e: int, out: set[str]) -> None:
    if n.end_byte <= s or n.start_byte >= e:
        return
    if n.type in ("call_expression", "call"):
        fn = n.child_by_field_name("function")
        if fn is not None and fn.type == "identifier":
            out.add(fn.text.decode())
    elif n.type == "method_invocation" and n.child_by_field_name("object") is None:
        out.add(n.child_by_field_name("name").text.decode())
    for c in n.children:
        _callees(c, s, e, out)


def calls(code: str, language: str, spans, asts) -> list[set[str]]:
    """User functions each unit calls; sets asts[i].function_name to the function holding it."""
    data = code.encode()
    root = parser(language).parse(data).root_node
    names, stack = {}, [root]
    while stack:
        n = stack.pop()
        if n.type in DEFS:
            names[n.start_byte] = _def_name(n)
        stack.extend(n.children)
    offset = _byte_offsets(code, data)
    out = []
    for ((l1, c1), (l2, c2)), a in zip(spans, asts, strict=True):
        got: set[str] = set()
        _callees(root, offset(l1, c1), offset(l2, c2), got)
        out.append(got & {v for v in names.values() if v})
        a.function_name = names.get(a.function)
    return out


def call_link(x, y) -> tuple[bool, bool]:
    return x.function_name in y.calls, y.function_name in x.calls


# %% [markdown]
# ## Signal before training

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
    spans = [((u.line, u.col), u.end) for u in s.units]
    asts = analyze(s.code, s.language, spans)
    for a, c in zip(asts, calls(s.code, s.language, spans, asts), strict=True):
        a.calls = c
    logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
    for (a, x), (b, y) in combinations(enumerate(logic), 2):
        X, Y = asts[x], asts[y]
        if X.function == Y.function:
            continue
        fwd, back = call_link(X, Y)
        same, same_pred = s.units[x].block == s.units[y].block, p[a] == p[b]
        rows.append(
            dict(
                link="later calls earlier's function"
                if fwd
                else "earlier calls later's function"
                if back
                else "no call",
                same=same,
                outcome="merged" if same_pred and not same else "split" if same and not same_pred else "correct",
            )
        )
print("logic pairs in different functions (or one global): call link, gold same-block rate, outcomes")
for k in ("later calls earlier's function", "earlier calls later's function", "no call"):
    g = [r for r in rows if r["link"] == k]
    out = "  ".join(f"{o} {sum(r['outcome'] == o for r in g)}" for o in ("merged", "split", "correct"))
    print(f"  {k:32s} n {len(g):5d}  same {np.mean([r['same'] for r in g]) if g else 0:.3f}  {out}")

# %% [markdown]
# ## Cross-validation with the call features
#
# The two features join the pair features through the candidates module, so the library and the
# saved model stay as they are until the result is in.

# %%
_analyze = analyze


def analyze_with_calls(code, language, spans):
    out = _analyze(code, language, spans)
    for a, c in zip(out, calls(code, language, spans, out), strict=True):
        a.calls = c
    return out


def pair_features(x, y):
    return [*segment_features(x, y), *call_link(x, y)]


candidates.analyze, candidates.segment_features, candidates.N_PAIR = analyze_with_calls, pair_features, 16
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
    "blocks-ensemble + calls, mean ± std over seeds (blocks-ensemble alone: B3 0.816±0.002  CEAFe 0.742±0.004  pairF1 0.678±0.006)"
)
print(
    "  "
    + "  ".join(f"{k} {np.mean([r[k] for r in results]):.3f}±{np.std([r[k] for r in results]):.3f}" for k in results[0])
)
