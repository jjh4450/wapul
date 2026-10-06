"""The block model: statement kinds, then logic blocks, trained on every labeled solution.

1. kinds: CodeBERT fine-tuned on each unit with K units of context on each side
   (kind_classifier.py)
2. blocks: each logic unit, in code order, joins one of the blocks built so far or opens a new
   one, scored by the average of a small net and a LightGBM ranker over AST features
   (block_ranker.py); blocks may be non-contiguous

Output units follow labels.jsonl: start and end positions, kind, and a block number from 1 for
logic. `unit_kinds` gives the same as input / output / none / logic<n> per unit, the shape the
backend's LLM segmenter produces.
"""

import json
import sys
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from wapul_ml.data.solutions import KINDS, Solution, Unit, context_text, load_solutions
from wapul_ml.features.candidates import BlockCandidates
from wapul_ml.models import block_ranker, kind_classifier
from wapul_ml.paths import MODELS
from wapul_ml.units import units

OUT = MODELS / "segmenter-v1"  # a new training run gets a new version, never overwrites this one
LANGS = ("cpp", "java", "python")
FORMAT = 1  # bump when the saved files or the output change shape
# 5-fold CV on the 300 human-reviewed solutions (docs/ml/experiments.ko.md)
CV = {"kinds_macro_f1": 0.887, "blocks_given_gold_kinds": {"B3": 0.816, "CEAFe": 0.742, "pairF1": 0.678}}


def train() -> None:
    if (OUT / "model.json").exists():
        sys.exit(f"{OUT} already holds a trained model; bump the version in OUT instead of overwriting it")
    OUT.mkdir(parents=True, exist_ok=True)
    sols = load_solutions()
    tok = AutoTokenizer.from_pretrained(kind_classifier.MODEL)
    kinds = kind_classifier.train(
        kind_classifier.MODEL, tok, *kind_classifier.examples(sols, range(len(sols))), kind_classifier.EPOCHS, seed=0
    )
    kinds.save_pretrained(OUT / "kinds")
    tok.save_pretrained(OUT / "kinds")
    data = [BlockCandidates(s) for s in sols]
    block_ranker.train_mlp(data, seed=0).save(OUT / "blocks-mlp.pt")
    block_ranker.train_lgbm(data, seed=0).save(OUT / "blocks-lgbm.txt")
    meta = {
        "format": FORMAT,
        "languages": LANGS,
        "trained_on": len(sols),
        "kinds_base": kind_classifier.MODEL,
        "cv": CV,
    }
    (OUT / "model.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"saved to {OUT}")


class BlockModel:
    def __init__(self, path: Path = OUT):
        meta = json.loads((path / "model.json").read_text())
        if meta["format"] != FORMAT:
            raise ValueError(f"{path} has format {meta['format']}, this code reads {FORMAT}")
        self.tok = AutoTokenizer.from_pretrained(path / "kinds")
        self.kind_model = AutoModelForSequenceClassification.from_pretrained(path / "kinds").eval()
        if torch.cuda.is_available():
            self.kind_model = self.kind_model.to("cuda")
        self.blocks = block_ranker.ensemble(
            block_ranker.MlpScorer.load(path / "blocks-mlp.pt"),
            block_ranker.LgbmScorer.load(path / "blocks-lgbm.txt"),
        )

    @torch.no_grad()
    def solution(self, code: str, language: str, sid: str = "") -> Solution:
        """The code's units, each with a predicted kind and, for logic, a block number from 1."""
        if language not in LANGS:
            raise ValueError(f"language must be one of {LANGS}")
        sol = Solution(sid, language, "model", code, [])
        sol.units = [Unit(u.text, u.start[0], u.start[1], u.end, "none", None) for u in units(code, language)]
        texts = [context_text(sol.units, j) for j in range(len(sol.units))]
        preds = []
        for k in range(0, len(texts), kind_classifier.BATCH):
            enc = self.tok(
                texts[k : k + kind_classifier.BATCH], truncation=True, max_length=kind_classifier.MAX_LEN, padding=True
            )
            enc = {key: torch.tensor(v, device=self.kind_model.device) for key, v in enc.items()}
            preds += self.kind_model(**enc).logits.argmax(-1).tolist()
        for u, p in zip(sol.units, preds, strict=True):
            u.kind = KINDS[p]
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
