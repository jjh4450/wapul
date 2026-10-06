"""The block model: statement kinds, then logic blocks, trained on every labeled solution.

    python -m wapul_ml.model train                    # fit and save to models/segmenter-v1/
    python -m wapul_ml.model predict FILE LANGUAGE    # print the labels of one file as JSON
    python -m wapul_ml.model review [N]               # N random unlabeled corpus solutions -> cache/review.html

1. kinds: CodeBERT fine-tuned on each unit with K units of context on each side (codeseg.py)
2. blocks: each logic unit, in code order, joins one of the blocks built so far or opens a new
   one, scored by the average of a small net and a LightGBM ranker over AST features
   (disentangle_ast.py, blocks-ensemble); blocks may be non-contiguous

Output units follow labels.jsonl: start and end positions, kind, and a block number from 1 for
logic. `unit_kinds` gives the same as input / output / none / logic<n> per unit, the shape the
backend's LLM segmenter produces.
"""

import html
import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from wapul_ml import codeseg, disentangle_ast
from wapul_ml.data import DATA, KINDS, Solution, Unit, context_text, load_solutions
from wapul_ml.units import units

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models" / "segmenter-v1"  # a new training run gets a new version, never overwrites this one
REVIEW = ROOT / "cache" / "review.html"
LANGS = ("cpp", "java", "python")
FORMAT = 1  # bump when the saved files or the output change shape
# 5-fold CV on the 300 human-reviewed solutions (docs/ml/experiments.ko.md)
CV = {"kinds_macro_f1": 0.887, "blocks_given_gold_kinds": {"B3": 0.816, "CEAFe": 0.742, "pairF1": 0.678}}


def train() -> None:
    if (OUT / "model.json").exists():
        sys.exit(f"{OUT} already holds a trained model; bump the version in OUT instead of overwriting it")
    OUT.mkdir(parents=True, exist_ok=True)
    sols = load_solutions()
    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    kinds = codeseg.train(codeseg.MODEL, tok, *codeseg.examples(sols, range(len(sols))), codeseg.EPOCHS, seed=0)
    kinds.save_pretrained(OUT / "kinds")
    tok.save_pretrained(OUT / "kinds")
    data = [disentangle_ast.BlockCandidates(s) for s in sols]
    disentangle_ast.train_mlp(data, seed=0).save(OUT / "blocks-mlp.pt")
    disentangle_ast.train_lgbm(data, seed=0).save(OUT / "blocks-lgbm.txt")
    meta = {"format": FORMAT, "languages": LANGS, "trained_on": len(sols), "kinds_base": codeseg.MODEL, "cv": CV}
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
        self.blocks = disentangle_ast.ensemble(
            disentangle_ast.MlpScorer.load(path / "blocks-mlp.pt"),
            disentangle_ast.LgbmScorer.load(path / "blocks-lgbm.txt"),
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
        for k in range(0, len(texts), codeseg.BATCH):
            enc = self.tok(texts[k : k + codeseg.BATCH], truncation=True, max_length=codeseg.MAX_LEN, padding=True)
            enc = {key: torch.tensor(v, device=self.kind_model.device) for key, v in enc.items()}
            preds += self.kind_model(**enc).logits.argmax(-1).tolist()
        for u, p in zip(sol.units, preds, strict=True):
            u.kind = KINDS[p]
        blocks = disentangle_ast.predict_blocks(self.blocks, disentangle_ast.BlockCandidates(sol, labeled=False))
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


def unlabeled_sample(n: int) -> list[dict]:
    labeled = {json.loads(line)["id"] for line in open(DATA / "labels" / "labels.jsonl", encoding="utf-8")}
    rows = []
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl")):
        for line in open(part, encoding="utf-8"):
            r = json.loads(line)
            if r["language"] in LANGS and r["id"] not in labeled:
                rows.append(r)
    pick = np.random.default_rng(0).choice(len(rows), n, replace=False)
    return [rows[i] for i in pick]


# Logic blocks cycle through these; other kinds get muted tints
PALETTE = ["#f4a261", "#2a9d8f", "#e76f51", "#8ab17d", "#b56576", "#4d96ff", "#e9c46a", "#9b5de5", "#00bbf9", "#f15bb5"]
KIND_STYLE = {"input": "background:#dbeafe", "output": "background:#dcfce7", "none": "color:#9ca3af"}


def render(sol: Solution, meta: dict) -> str:
    lines = sol.code.split("\n")
    starts = np.cumsum([0] + [len(x) + 1 for x in lines])
    spans = sorted((starts[u.line - 1] + u.col, starts[u.end[0] - 1] + u.end[1], u) for u in sol.units)
    out, at = [], 0
    for a, b, u in spans:
        out.append(html.escape(sol.code[at:a]))
        if u.kind == "logic":
            color = PALETTE[(u.block - 1) % len(PALETTE)]
            style = f"background:{color}40;border-bottom:2px solid {color}"
            tag = f'<sup style="color:{color}">{u.block}</sup>'
        else:
            style, tag = KIND_STYLE[u.kind], f"<sup>{u.kind[0]}</sup>"
        out.append(f'<span style="{style}" title="{u.kind} {u.block or ""}">{tag}{html.escape(sol.code[a:b])}</span>')
        at = b
    out.append(html.escape(sol.code[at:]))
    n_blocks = len({u.block for u in sol.units if u.kind == "logic"})
    title = f"{html.escape(meta['id'])} · {sol.language} · problem {meta.get('problem_id')} · {n_blocks} logic blocks"
    return f"<section><h2>{title}</h2><pre>{''.join(out)}</pre></section>"


def review(n: int) -> None:
    model = BlockModel()
    sections = []
    for k, r in enumerate(unlabeled_sample(n), 1):
        sections.append(render(model.solution(r["code"], r["language"], r["id"]), r))
        print(f"  {k}/{n} {r['id']}", flush=True)
    legend = (
        "<p>logic blocks: colored, numbered <sup>1</sup>, <sup>2</sup>, …; "
        f'<span style="{KIND_STYLE["input"]}"><sup>i</sup>input</span> '
        f'<span style="{KIND_STYLE["output"]}"><sup>o</sup>output</span> '
        f'<span style="{KIND_STYLE["none"]}"><sup>n</sup>none</span></p>'
    )
    page = (
        '<!doctype html><meta charset="utf-8"><title>Block review</title><style>'
        "body{font-family:system-ui;margin:24px;background:#fff;color:#111}"
        "pre{font:13px/1.6 ui-monospace,Consolas,monospace;background:#fafafa;padding:12px;border:1px solid #eee;"
        "overflow-x:auto}h2{font-size:15px;margin-top:32px}sup{font-size:9px;margin-right:1px}</style>"
        f"<h1>Model blocks on {n} unlabeled solutions</h1>{legend}{''.join(sections)}"
    )
    REVIEW.write_text(page, encoding="utf-8")
    print(f"wrote {REVIEW}")


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "train":
        train()
    elif cmd == "predict":
        code = Path(sys.argv[2]).read_text(encoding="utf-8")
        print(json.dumps(BlockModel().predict(code, sys.argv[3]), ensure_ascii=False))
    elif cmd == "review":
        review(int(sys.argv[2]) if len(sys.argv) > 2 else 40)


if __name__ == "__main__":
    main()
