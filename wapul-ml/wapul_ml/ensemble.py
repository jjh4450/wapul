"""Ensemble of the two disentanglement linkers: mix their link probabilities, weight chosen on dev.

    python -m wapul_ml.ensemble

disentangle_ast.py (small net over AST features) and disentangle.py (fine-tuned CodeBERT) score
the same candidates for each logic unit: every earlier logic unit, then the unit itself. Per
candidate, p = w * p_ast + (1 - w) * p_bert, and the unit links to the top one. Each fold trains
both on its fit part, picks w in 0, 0.1, ..., 1 by dev B3, and scores test once with that w.
Gold kinds, same 5 folds and fit/dev split as baseline.py.
"""

import time

import numpy as np
import torch
from sklearn.model_selection import KFold
from transformers import AutoTokenizer

from wapul_ml import codeseg, disentangle, disentangle_ast
from wapul_ml.data import load_solutions
from wapul_ml.metrics import PartitionScore

WEIGHTS = np.round(np.arange(0, 1.01, 0.1), 1)


def link(probs: list[np.ndarray]) -> list[int]:
    """Block id per logic unit from each unit's candidate probabilities (last candidate: itself)."""
    out: list[int] = []
    for t, p in enumerate(probs):
        best = int(np.argmax(p))
        out.append(out[best] if best < t else t)
    return out


def b3(blocks: list[list[int]], probs: list[list[np.ndarray]]) -> float:
    score = PartitionScore()
    for gold, p in zip(blocks, probs, strict=True):
        score.add(gold, link(p))
    return score.result()["B3"]


@torch.no_grad()
def probs(ast_score, model, tok, a: disentangle_ast.Candidates, b: disentangle.Candidates):
    """Each linker's candidate probabilities for every logic unit of one solution."""
    pa = [torch.softmax(torch.tensor(ast_score(r)), 0).numpy() for r in a.rows]
    pb = [torch.softmax(disentangle.scores(model, tok, x), 0).cpu().numpy() for x in b.texts]
    return pa, pb


def mixed(pairs, w: float) -> list[list[np.ndarray]]:
    return [[w * pa + (1 - w) * pb for pa, pb in zip(a, b, strict=True)] for a, b in pairs]


def main() -> None:
    sols = load_solutions()
    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    ast_data = [disentangle_ast.Candidates(s) for s in sols]
    bert_data = [disentangle.Candidates(s) for s in sols]
    scores = {name: PartitionScore() for name in ("ast", "bert", "ensemble")}
    chosen = []
    for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
        t = time.time()
        shuffled = [train_ids[i] for i in np.random.default_rng(0).permutation(len(train_ids))]
        cut = len(train_ids) * 4 // 5
        fit_ids, dev_ids = shuffled[:cut], shuffled[cut:]
        ast_score = disentangle_ast.train_mlp([ast_data[i] for i in fit_ids], seed=fold)
        model = disentangle.train(tok, [bert_data[i] for i in fit_ids], [bert_data[i] for i in dev_ids], seed=fold)
        dev = [i for i in dev_ids if len(ast_data[i])]
        dev_pairs = [probs(ast_score, model, tok, ast_data[i], bert_data[i]) for i in dev]
        dev_blocks = [ast_data[i].blocks for i in dev]
        w = max(WEIGHTS, key=lambda w: b3(dev_blocks, mixed(dev_pairs, w)))
        chosen.append(float(w))
        for i in test_ids:
            if not len(ast_data[i]):
                continue
            a, b = probs(ast_score, model, tok, ast_data[i], bert_data[i])
            gold = ast_data[i].blocks
            scores["ast"].add(gold, link(a))
            scores["bert"].add(gold, link(b))
            scores["ensemble"].add(gold, link(mixed([(a, b)], w)[0]))
        print(f"  fold {fold} done ({time.time() - t:.0f}s)  w {w}", flush=True)
        del model
        torch.cuda.empty_cache()
    print(f"logic grouping, given gold kinds; ensemble weight on the AST linker per fold: {chosen}")
    for name, score in scores.items():
        print(f"  {name:<9} " + "  ".join(f"{k} {v:.3f}" for k, v in score.result().items()))


if __name__ == "__main__":
    main()
