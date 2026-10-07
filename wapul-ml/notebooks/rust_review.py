# %% [markdown]
# # Qualitative check: Rust, a language the model never saw
#
# segmenter-v2 is trained on C++, Java and Python only. units.py and unit_ast.py know Rust's
# grammar, so its code can be split and featurized; the trained model is used as is. Writes the
# labels of N random Rust corpus solutions to cache/rust_review.html (private data, open locally)
# and prints them as text.
#
#     python notebooks/rust_review.py [N]

# %%
import json
import sys

import numpy as np

from wapul_ml.data.solutions import Solution, Unit
from wapul_ml.evaluation.review import KIND_STYLE, render
from wapul_ml.features.candidates import BlockCandidates
from wapul_ml.features.kind_features import unit_features
from wapul_ml.models import block_ranker
from wapul_ml.models.segmenter import BlockModel
from wapul_ml.paths import CACHE, DATA
from wapul_ml.units import units

N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12

rows = [
    r
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl"))
    for line in open(part, encoding="utf-8")
    if (r := json.loads(line))["language"] == "rust"
]
pick = [rows[i] for i in np.random.default_rng(0).choice(len(rows), N, replace=False)]

# %%
model = BlockModel()


def label(code: str, sid: str) -> Solution:
    """BlockModel.solution without its language check."""
    sol = Solution(sid, "rust", "model", code, [])
    sol.units = [Unit(u.text, u.start[0], u.start[1], u.end, "none", None) for u in units(code, "rust")]
    for u, kind in zip(sol.units, model.kinds.predict(unit_features(sol)), strict=True):
        u.kind = kind
    blocks = block_ranker.predict_blocks(model.blocks, BlockCandidates(sol, labeled=False))
    for u, b in zip([u for u in sol.units if u.kind == "logic"], blocks, strict=True):
        u.block = b + 1
    return sol


sections = []
for r in pick:
    sol = label(r["code"], r["id"])
    sections.append(render(sol, r))
    print(f"\n=== {r['id']} (problem {r.get('problem_id')})")
    for u in sol.units:
        tag = f"logic{u.block}" if u.kind == "logic" else u.kind
        print(f"  {tag:>8}  {' ' * u.col}{u.text.splitlines()[0][:100]}")

# %%
page = (
    '<!doctype html><meta charset="utf-8"><title>Rust review</title><style>'
    "body{font-family:system-ui;margin:24px;background:#fff;color:#111}"
    "pre{font:13px/1.6 ui-monospace,Consolas,monospace;background:#fafafa;padding:12px;border:1px solid #eee;"
    "overflow-x:auto}h2{font-size:15px;margin-top:32px}sup{font-size:9px;margin-right:1px}</style>"
    f"<h1>segmenter-v2 on {N} Rust solutions (never trained on Rust)</h1>"
    f'<p><span style="{KIND_STYLE["input"]}">input</span> <span style="{KIND_STYLE["output"]}">output</span> '
    f'<span style="{KIND_STYLE["none"]}">none</span>, logic blocks colored and numbered</p>{"".join(sections)}'
)
(CACHE / "rust_review.html").write_text(page, encoding="utf-8")
print(f"\nwrote {CACHE / 'rust_review.html'}")

# %% [markdown]
# ## segmenter-v1's CodeBERT kinds on the same units
#
# CodeBERT was pretrained on Python, Java, JavaScript, PHP, Ruby and Go, not Rust. Units where
# its kind differs from v2's are printed for reading.

# %%
import torch  # noqa: E402

from wapul_ml.data.solutions import KINDS, context_text  # noqa: E402
from wapul_ml.models import kind_classifier, segmenter_v1  # noqa: E402

v1 = segmenter_v1.BlockModel()
changed, total = {}, 0
for r in pick:
    sol = label(r["code"], r["id"])
    texts = [context_text(sol.units, j) for j in range(len(sol.units))]
    with torch.no_grad():
        enc = v1.tok(texts, truncation=True, max_length=kind_classifier.MAX_LEN, padding=True, return_tensors="pt")
        old = [KINDS[k] for k in v1.kind_model(**enc.to(v1.kind_model.device)).logits.argmax(-1).tolist()]
    total += len(sol.units)
    print(f"\n=== {r['id']}: v2 -> v1 where they differ")
    for u, k in zip(sol.units, old, strict=True):
        if k != u.kind:
            changed[(u.kind, k)] = changed.get((u.kind, k), 0) + 1
            print(f"  {u.kind:>6} -> {k:<6}  {' ' * u.col}{u.text.splitlines()[0][:90]}")
print(f"\n{sum(changed.values())} of {total} units differ:", sorted(changed.items(), key=lambda x: -x[1]))
