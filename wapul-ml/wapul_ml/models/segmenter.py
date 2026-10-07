"""The block model v2: statement kinds, then logic blocks, both with LightGBM (no neural net).

1. kinds: LightGBM over string features of each unit and its neighbours
   (kind_lgbm.py, features/kind_features.py)
2. blocks: each logic unit, in code order, joins one of the blocks built so far or opens a new
   one, scored by a LightGBM ranker over AST features (block_ranker.py); blocks may be
   non-contiguous

Output units follow labels.jsonl: start and end positions, kind, and a block number from 1 for
logic. `unit_kinds` gives the same as input / output / none / logic<n> per unit, the shape the
backend's LLM segmenter produces.

segmenter-v1 (CodeBERT kinds, MLP + LightGBM blocks) stays readable through segmenter_v1.py,
which is frozen.
"""

import json
import sys
from pathlib import Path

from wapul_ml.data.solutions import Solution, Unit, load_solutions
from wapul_ml.features.candidates import BlockCandidates
from wapul_ml.features.kind_features import unit_features
from wapul_ml.models import block_ranker, kind_lgbm
from wapul_ml.paths import MODELS
from wapul_ml.units import units

OUT = MODELS / "segmenter-v2"  # a new training run gets a new version, never overwrites this one
LANGS = ("cpp", "java", "python")
FORMAT = 2  # bump when the saved files or the output change shape
# 5-fold CV on the 300 human-reviewed solutions (docs/ml/experiments.ko.md)
CV = {"kinds_macro_f1": 0.891, "blocks_given_gold_kinds": {"B3": 0.809, "CEAFe": 0.732, "pairF1": 0.668}}


def train() -> None:
    if (OUT / "model.json").exists():
        sys.exit(f"{OUT} already holds a trained model; bump the version in OUT instead of overwriting it")
    OUT.mkdir(parents=True, exist_ok=True)
    sols = load_solutions()
    feats = [f for s in sols for f in unit_features(s)]
    kinds = kind_lgbm.train(feats, [u.kind for s in sols for u in s.units])
    kinds.save(OUT / "kinds-lgbm.txt", OUT / "kinds-features.json")
    block_ranker.train_lgbm([BlockCandidates(s) for s in sols], seed=0).save(OUT / "blocks-lgbm.txt")
    meta = {"format": FORMAT, "languages": LANGS, "trained_on": len(sols), "cv": CV}
    (OUT / "model.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"saved to {OUT}")


class BlockModel:
    def __init__(self, path: Path = OUT):
        meta = json.loads((path / "model.json").read_text())
        if meta["format"] != FORMAT:
            raise ValueError(f"{path} has format {meta['format']}, this code reads {FORMAT}")
        self.kinds = kind_lgbm.LgbmKinds.load(path / "kinds-lgbm.txt", path / "kinds-features.json")
        self.blocks = block_ranker.LgbmScorer.load(path / "blocks-lgbm.txt")

    def solution(self, code: str, language: str, sid: str = "") -> Solution:
        """The code's units, each with a predicted kind and, for logic, a block number from 1."""
        if language not in LANGS:
            raise ValueError(f"language must be one of {LANGS}")
        sol = Solution(sid, language, "model", code, [])
        sol.units = [Unit(u.text, u.start[0], u.start[1], u.end, "none", None) for u in units(code, language)]
        for u, kind in zip(sol.units, self.kinds.predict(unit_features(sol)), strict=True):
            u.kind = kind
        blocks = block_ranker.predict_blocks(self.blocks, BlockCandidates(sol, labeled=False))
        for u, b in zip([u for u in sol.units if u.kind == "logic"], blocks, strict=True):
            u.block = b + 1
        return sol

    def predict(self, code: str, language: str) -> list[dict]:
        """Units as in labels.jsonl: {"start": [line, col], "end": [line, col], "kind", "block"?}."""
        return [
            {"start": [u.line, u.col], "end": list(u.end), "kind": u.kind} | ({"block": u.block} if u.block else {})
            for u in self.solution(code, language).units
        ]

    def unit_kinds(self, code: str, language: str) -> list[str]:
        """input / output / none / logic<n> per unit, as the backend's LLM segmenter returns."""
        return [f"logic{u['block']}" if u["kind"] == "logic" else u["kind"] for u in self.predict(code, language)]
