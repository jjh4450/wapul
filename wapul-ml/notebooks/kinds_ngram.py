# %% [markdown]
# # Statement kinds: character n-grams for languages the model never saw
#
# segmenter-v2's kind features use whole tokens, so Rust's `scan.token`, `read_line` and
# `writeln!` match nothing from C++, Java and Python, and input / output are missed. Here every
# identifier token is also split into character 3-4-grams (`read_line` and Java's `readLine` share
# "read" and "line"; `writeln`, `BufferedWriter` and `bw.write` share "writ").
#
# 1. 5-fold CV on the 300 labeled C++ / Java / Python solutions, LightGBM as in segmenter-v2
# 2. train on all 300, test on 12 Rust solutions with Claude-labeled kinds
#    (data/labels/rust-test-kinds.json; Rust is never trained on), with v1's CodeBERT for reference
#
#     python notebooks/kinds_ngram.py

# %%
import json
import re

import numpy as np
import torch
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold

from wapul_ml.data.solutions import KINDS, Solution, Unit, context_text, load_solutions
from wapul_ml.features.kind_features import unit_features
from wapul_ml.models import kind_classifier, kind_lgbm, segmenter_v1
from wapul_ml.paths import DATA
from wapul_ml.units import units

IDENT = re.compile(r"[A-Za-z_]\w*")
N = (3, 4)


def char_grams(token: str) -> set[str]:
    t = token.lower()
    return {t[i : i + n] for n in N for i in range(len(t) - n + 1)}


def with_ngrams(feats: list[dict]) -> list[dict]:
    """Each identifier feature `prefix:tok` also gives `prefix#gram` for its character n-grams."""
    out = []
    for f in feats:
        g = dict(f)
        for name in f:
            prefix, sep, tok = name.partition(":")
            if sep and IDENT.fullmatch(tok):
                for c in char_grams(tok):
                    g[f"{prefix}#{c}"] = 1.0
        out.append(g)
    return out


VARIANTS = {"v2": lambda f: f, "+char n-grams": with_ngrams}

# %% [markdown]
# ## 1. Cross-validation on the labeled languages

# %%
sols = load_solutions()
base = [unit_features(s) for s in sols]
kinds = [[u.kind for u in s.units] for s in sols]
folds = list(KFold(5, shuffle=True, random_state=0).split(sols))
for name, variant in VARIANTS.items():
    feats = [variant(f) for f in base]
    y_true, y_pred = [], []
    for train_ids, test_ids in folds:
        model = kind_lgbm.train([f for i in train_ids for f in feats[i]], [k for i in train_ids for k in kinds[i]])
        y_pred += model.predict([f for i in test_ids for f in feats[i]])
        y_true += [k for i in test_ids for k in kinds[i]]
    print(f"CV  {name:24s} macro-F1 {f1_score(y_true, y_pred, average='macro'):.3f}", flush=True)

# %% [markdown]
# ## 2. Rust, never trained on

# %%
gold = json.loads((DATA / "labels" / "rust-test-kinds.json").read_text(encoding="utf-8"))["spec"]
rows = [
    r
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl"))
    for line in open(part, encoding="utf-8")
    if (r := json.loads(line))["language"] == "rust"
]
pick = [rows[i] for i in np.random.default_rng(0).choice(len(rows), len(gold), replace=False)]
rust, rust_gold, scored = [], [], []
for k, r in enumerate(pick):
    sol = Solution(r["id"], "rust", "test", r["code"], [])
    sol.units = [Unit(u.text, u.start[0], u.start[1], u.end, "none", None) for u in units(r["code"], "rust")]
    spec, scanner, keep, labels = gold[str(k)], False, [], []
    for j, u in enumerate(sol.units):
        if u.col == 0:
            scanner = u.text.startswith(("pub struct UnsafeScanner", "impl<R: io::BufRead> UnsafeScanner"))
        if scanner or j in spec.get("skip", []):
            continue
        keep.append(j)
        labels.append(next((kind for kind in ("none", "input", "output") if j in spec[kind]), "logic"))
    rust.append(sol)
    scored.append(keep)
    rust_gold += labels
print(f"\nRust test: {len(rust)} solutions, {len(rust_gold)} scored units")


def report(name: str, pred: list[str]) -> None:
    print(f"Rust  {name:24s} macro-F1 {f1_score(rust_gold, pred, average='macro'):.3f}")
    print(classification_report(rust_gold, pred, labels=list(KINDS), digits=3, zero_division=0))


for name, variant in VARIANTS.items():
    model = kind_lgbm.train([g for f in base for g in variant(f)], [k for ks in kinds for k in ks])
    pred = []
    for sol, keep in zip(rust, scored, strict=True):
        p = model.predict(variant(unit_features(sol)))
        pred += [p[j] for j in keep]
    report(name, pred)

v1 = segmenter_v1.BlockModel()
pred = []
for sol, keep in zip(rust, scored, strict=True):
    texts = [context_text(sol.units, j) for j in range(len(sol.units))]
    with torch.no_grad():
        enc = v1.tok(texts, truncation=True, max_length=kind_classifier.MAX_LEN, padding=True, return_tensors="pt")
        p = [KINDS[i] for i in v1.kind_model(**enc.to(v1.kind_model.device)).logits.argmax(-1).tolist()]
    pred += [p[j] for j in keep]
report("v1 CodeBERT", pred)
