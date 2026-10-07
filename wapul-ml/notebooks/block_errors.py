# %% [markdown]
# # Error analysis: block errors without data flow
#
# Most wrongly merged and wrongly split logic pairs have no data-flow link of any kind
# (`defuse_errors.py`). This notebook breaks those pairs down by distance, AST relation and
# statement categories, against the pairs the model gets right, and prints the solutions with the
# most such errors for reading. Predictions are the out-of-fold blocks-ensemble ones, seed 0.
#
#     python notebooks/block_errors.py

# %%
from collections import Counter
from itertools import combinations

import numpy as np
from sklearn.model_selection import KFold

from wapul_ml.data.solutions import load_solutions
from wapul_ml.features.candidates import BlockCandidates
from wapul_ml.features.unit_ast import analyze
from wapul_ml.models.block_ranker import predict_blocks, train_ensemble

sols = load_solutions()
data = [BlockCandidates(s) for s in sols]
pred = [None] * len(sols)
for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
    score = train_ensemble([data[i] for i in train_ids], seed=fold)
    for i in test_ids:
        pred[i] = predict_blocks(score, data[i]) if len(data[i]) else []

# %% [markdown]
# ## Pairs without data flow, by bucket
#
# For each bucket: its share of wrongly merged, wrongly split and correct pairs, and how often its
# pairs are in one gold block. A bucket much larger among errors than among correct pairs is where
# the model goes wrong.

# %%
rows = []
for s, p in zip(sols, pred, strict=True):
    asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
    logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
    for (a, x), (b, y) in combinations(enumerate(logic), 2):
        X, Y = asts[x], asts[y]
        if (X.writes & Y.reads) | (Y.writes & X.reads) | (X.writes & Y.writes):
            continue
        same, same_pred = s.units[x].block == s.units[y].block, p[a] == p[b]
        d = b - a
        if X.is_header and X.span[0] <= Y.span[0] and Y.span[1] <= X.span[1]:
            rel = "x encloses y"
        elif X.function != Y.function:
            rel = "other function"
        elif X.parent == Y.parent:
            rel = "siblings"
        elif X.control == Y.control:
            rel = "same control"
        else:
            rel = "different control"
        rows.append(
            dict(
                sol=s.id,
                outcome="wrongly merged"
                if same_pred and not same
                else "wrongly split"
                if same and not same_pred
                else "correct",
                same=same,
                distance="1" if d == 1 else "2-3" if d <= 3 else "4-8" if d <= 8 else "9+",
                relation=rel,
                gap="non-logic between"
                if any(s.units[k].kind != "logic" for k in range(x + 1, y))
                else "logic only between",
                categories=" / ".join(sorted((X.category, Y.category))),
                depth="same depth" if X.depth == Y.depth else "different depth",
            )
        )
outcomes = Counter(r["outcome"] for r in rows)
print("pairs without data flow:", dict(outcomes))


def table(key, top=None):
    print(f"\n{key}: share of wrongly merged / wrongly split / correct, gold same-block rate")
    by = Counter(r[key] for r in rows)
    for k, _ in by.most_common(top):
        g = [r for r in rows if r[key] == k]
        share = {o: sum(r["outcome"] == o for r in g) / outcomes[o] for o in outcomes}
        print(
            f"  {k:34s} merged {share['wrongly merged']:.3f}  split {share['wrongly split']:.3f}  "
            f"correct {share['correct']:.3f}  same {np.mean([r['same'] for r in g]):.3f}  n {len(g)}"
        )


for key in ("distance", "relation", "gap", "depth"):
    table(key)
table("categories", top=12)

# %% [markdown]
# ## Are errors spread or concentrated?

# %%
per_sol = Counter(r["sol"] for r in rows if r["outcome"] != "correct")
counts = sorted(per_sol.values(), reverse=True)
total = sum(counts)
for k in (10, 30, 60):
    print(f"top {k} solutions hold {sum(counts[:k]) / total:.2f} of error pairs without data flow")
print(f"solutions with any: {len(counts)} of {len(sols)}")

# %% [markdown]
# ## Solutions to read
#
# Logic units with gold and predicted block, for the solutions with the most error pairs and a
# few with a middling count. Private data: the log stays in cache/.

# %%
by_id = {s.id: (s, p) for s, p in zip(sols, pred, strict=True)}
picks = [sid for sid, _ in per_sol.most_common(6)] + [sid for sid, _ in per_sol.most_common()[40:46]]
for sid in picks:
    s, p = by_id[sid]
    print(f"\n=== {sid} ({s.language}) error pairs {per_sol[sid]}")
    t = 0
    for u in s.units:
        if u.kind == "logic":
            print(
                f"  gold {u.block:2d} pred {p[t] + 1:2d}  {'!' if False else ' '} {' ' * u.col}{u.text.splitlines()[0][:90]}"
            )
            t += 1
        else:
            print(f"  {u.kind:>13s}    {' ' * u.col}{u.text.splitlines()[0][:90]}")
