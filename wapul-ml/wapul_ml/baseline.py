"""Baseline: kind classifier + AST-feature block grouping, 5-fold CV scored on human-reviewed solutions.

    python -m wapul_ml.baseline [--model intfloat/e5-base-v2]

Kinds: CodeBERT fine-tuned per fold on each unit with K units of context on each side
(line-by-line with context, CodeSeg, DocEng 2026; codeseg.py). --model is the frozen
embedding the block grouping reads.

Logic blocks, as incremental coreference clustering (Xia et al. 2020; Grenander et al. 2022):
logic units are read in code order and each joins an earlier block or opens a new one when
no block scores above alpha. Two scorers are compared:
- closest-first: a block scores its best pair probability with the unit
- block scoring: a second classifier scores the unit against the block as a whole
Pair probabilities come from a "same block?" RBF SVM over the SEGMENT block rules (data
flow, shared control statement, same syntactic category) and position features.

Each training fold is split into fit and dev parts: the pair classifier learns on fit;
the block scorer, alpha, and which scorer to use are chosen on dev, so test solutions
never steer a choice.
"""

import argparse
import hashlib
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import SVC

from wapul_ml.ast_features import CATEGORIES, UnitAst, analyze
from wapul_ml.data import KINDS, Solution, context_text, load_solutions
from wapul_ml.metrics import PartitionScore

CACHE = Path(__file__).resolve().parent.parent / "cache"
LANGS = ("cpp", "java", "python")
ALPHAS = np.round(np.arange(0.2, 0.86, 0.05), 2)
PAIR_FEATURES = "all"  # "structural" drops every embedding-derived pair feature (ablation)
N_STRUCTURAL = 15  # the 11 SEGMENT + 4 position features that end every pair_features row
# Identifiers that mark reading input or writing output, across the three languages
INPUT_NAMES = {
    "cin",
    "scanf",
    "input",
    "stdin",
    "readline",
    "readLine",
    "BufferedReader",
    "Scanner",
    "StringTokenizer",
    "nextInt",
    "nextLine",
    "getline",
    "InputStreamReader",
}
OUTPUT_NAMES = {
    "cout",
    "printf",
    "print",
    "println",
    "puts",
    "stdout",
    "BufferedWriter",
    "PrintWriter",
    "flush",
    "putchar",
}


def embed(model_name: str, texts: list[str]) -> np.ndarray:
    key = hashlib.sha1("\0".join([model_name, *texts]).encode()).hexdigest()[:16]
    path = CACHE / f"{model_name.replace('/', '__')}-{key}.npy"
    if path.exists():
        return np.load(path)
    if "codet5p" in model_name:
        vecs = _encode_codet5p(model_name, texts)
    else:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(model_name, trust_remote_code=True)
        prefix = "query: " if "e5" in model_name else ""
        vecs = model.encode(
            [prefix + t for t in texts], batch_size=64, normalize_embeddings=True, show_progress_bar=True
        )
    CACHE.mkdir(exist_ok=True)
    np.save(path, vecs)
    return vecs


def _encode_codet5p(model_name: str, texts: list[str]) -> np.ndarray:
    """CodeT5+ embedding: T5 encoder -> first token -> linear to 256 -> L2 normalize.

    Its bundled remote code no longer loads on transformers 5, so the same model is
    rebuilt from the standard T5 encoder and the checkpoint's weights.
    """
    import json

    import torch
    import torch.nn.functional as F
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer, T5Config, T5EncoderModel

    cfg = json.load(open(hf_hub_download(model_name, "config.json")))
    state = torch.load(hf_hub_download(model_name, "pytorch_model.bin"), map_location="cpu")
    encoder = T5EncoderModel(
        T5Config(**{k: v for k, v in cfg.items() if k not in ("auto_map", "architectures", "model_type")})
    )
    missing, unexpected = encoder.load_state_dict(state, strict=False)
    assert not [k for k in missing if k != "encoder.embed_tokens.weight"], missing
    assert unexpected == ["proj.weight", "proj.bias"], unexpected
    proj = torch.nn.Linear(cfg["d_model"], cfg["embed_dim"])
    proj.load_state_dict({"weight": state["proj.weight"], "bias": state["proj.bias"]})
    encoder, proj = encoder.to("cuda").eval(), proj.to("cuda").eval()
    tok = AutoTokenizer.from_pretrained(model_name)
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), 64):
            batch = tok(texts[i : i + 64], padding=True, truncation=True, max_length=512, return_tensors="pt").to(
                "cuda"
            )
            hidden = encoder(**batch).last_hidden_state[:, 0, :]
            out.append(F.normalize(proj(hidden), dim=-1).cpu().numpy())
    return np.vstack(out)


def ast_kind_features(a: UnitAst) -> list[float]:
    return [
        *(a.category == c for c in CATEGORIES),
        a.is_header,
        a.depth,
        a.function >= 0,
        bool(a.writes),
        bool(a.reads & INPUT_NAMES),
        bool(a.reads & OUTPUT_NAMES),
    ]


class Featurized:
    def __init__(self, sol: Solution, vecs: np.ndarray, kind_x: np.ndarray, asts: list[UnitAst]):
        self.sol, self.vecs, self.kind_x, self.asts = sol, vecs, kind_x, asts


def featurize(sols: list[Solution], model_name: str) -> list[Featurized]:
    flat = [(s, i) for s in sols for i in range(len(s.units))]
    unit_vecs = embed(model_name, [s.units[i].text for s, i in flat])
    ctx_vecs = embed(model_name, [context_text(s.units, i) for s, i in flat])
    out, at = [], 0
    for s in sols:
        n = len(s.units)
        asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
        extra = np.array(
            [[i / n, *(s.language == lang for lang in LANGS), *ast_kind_features(a)] for i, a in enumerate(asts)],
            dtype=float,
        )
        vecs = unit_vecs[at : at + n]
        out.append(Featurized(s, vecs, np.hstack([ctx_vecs[at : at + n], vecs, extra]), asts))
        at += n
    return out


def segment_features(x: UnitAst, y: UnitAst) -> list[float]:
    """The SEGMENT block rules for unit x before unit y."""
    return [
        # data-flow chain
        bool(x.writes & y.reads),
        bool(y.writes & x.reads),
        bool(x.writes & y.writes),
        len(x.reads & y.reads) / (len(x.reads | y.reads) or 1),
        # control block
        x.is_header and x.span[0] <= y.span[0] and y.span[1] <= x.span[1],
        x.control == y.control,
        x.loop == y.loop,
        x.function == y.function,
        x.parent == y.parent,
        # same syntactic category
        x.category == y.category,
        x.node_type == y.node_type,
    ]


def pair_features(f: Featurized, idx: list[int]):
    """Rows for every pair (a, b), a before b, of the given unit indices."""
    rows, pairs = [], []
    for a, b in combinations(range(len(idx)), 2):
        i, j = idx[a], idx[b]
        u, v, x, y = f.vecs[i], f.vecs[j], f.asts[i], f.asts[j]
        segment = segment_features(x, y)
        position = [float(u @ v), b - a == 1, np.log1p(j - i), y.depth - x.depth]
        structural = np.array(segment + position, dtype=float)
        if PAIR_FEATURES == "structural":  # ablation: no embedding dimensions (cosine stays in position)
            structural[len(segment)] = 0.0
            rows.append(structural)
        else:
            rows.append(np.concatenate([u * v, np.abs(u - v), structural]))
        pairs.append((a, b))
    return rows, pairs


def logic_idx(kinds) -> list[int]:
    return [i for i, k in enumerate(kinds) if k == "logic"]


def gold_kinds(f: Featurized) -> list[str]:
    return [u.kind for u in f.sol.units]


def pair_probs(pair_clf, f: Featurized, idx: list[int]) -> dict[tuple[int, int], float]:
    rows, pairs = pair_features(f, idx)
    return dict(zip(pairs, pair_clf.predict_proba(np.array(rows))[:, 1], strict=True)) if rows else {}


def block_features(f: Featurized, idx: list[int], probs, b: int, members: list[int], latest: bool) -> list[float]:
    p = [probs[a, b] for a in members]
    mean_vec = f.vecs[[idx[a] for a in members]].mean(axis=0)
    return [
        max(p),
        float(np.mean(p)),
        probs[members[-1], b],
        np.log1p(len(members)),
        np.log1p(b - members[-1]),
        latest,
        0.0 if PAIR_FEATURES == "structural" else float(f.vecs[idx[b]] @ mean_vec / (np.linalg.norm(mean_vec) or 1)),
    ]


def cluster(n: int, score, alpha: float) -> list[int]:
    """Join the best-scoring earlier block, or open a new one if none clears alpha."""
    blocks: list[list[int]] = []
    block_of: list[int] = []
    for b in range(n):
        best, top = None, alpha
        for k, members in enumerate(blocks):
            s = score(b, members, k == len(blocks) - 1)
            if s > top:
                best, top = k, s
        if best is None:
            blocks.append([])
            best = len(blocks) - 1
        blocks[best].append(b)
        block_of.append(best)
    return block_of


def predict_blocks(f, idx, pair_clf, block_clf, alpha) -> list[int]:
    if not idx:
        return []
    probs = pair_probs(pair_clf, f, idx)
    if block_clf is None:
        return cluster(len(idx), lambda b, members, latest: max(probs[a, b] for a in members), alpha)

    def score(b, members, latest):
        return block_clf.predict_proba([block_features(f, idx, probs, b, members, latest)])[0, 1]

    return cluster(len(idx), score, alpha)


def structural_columns(X):
    """The SEGMENT and position features, the last N_STRUCTURAL columns of a pair row."""
    return np.asarray(X)[:, -N_STRUCTURAL:]


def fit_pair_clf(feats: list[Featurized]):
    """RBF SVM on the SEGMENT and position features only. On the embedding dimensions the
    kernel does worse, and a linear model on everything does no better (pair_clf.py)."""
    X, y = [], []
    for f in feats:
        idx = logic_idx(gold_kinds(f))
        rows, pairs = pair_features(f, idx)
        X += rows
        y += [f.sol.units[idx[a]].block == f.sol.units[idx[b]].block for a, b in pairs]
    # probability=True: alpha and the block scorer read pair probabilities (Platt scaling)
    clf = make_pipeline(
        FunctionTransformer(structural_columns), StandardScaler(), SVC(probability=True, random_state=0)
    )
    return clf.fit(np.array(X), np.array(y))


def fit_block_clf(feats: list[Featurized], pair_clf):
    """Teacher forcing: score each logic unit against the gold blocks formed before it."""
    X, y = [], []
    for f in feats:
        idx = logic_idx(gold_kinds(f))
        probs = pair_probs(pair_clf, f, idx)
        blocks: dict[int, list[int]] = {}
        for b, i in enumerate(idx):
            gold = f.sol.units[i].block
            for k, (block, members) in enumerate(blocks.items()):
                X.append(block_features(f, idx, probs, b, members, k == len(blocks) - 1))
                y.append(block == gold)
            blocks.setdefault(gold, []).append(b)
    return LogisticRegression(max_iter=3000).fit(np.array(X), np.array(y))


def choose_alpha(feats, pair_clf, block_clf, beta: float = 1.0) -> float:
    return best_alpha(feats, pair_clf, block_clf, beta)[0]


def best_alpha(feats, pair_clf, block_clf, beta: float = 1.0) -> tuple[float, float]:
    """Alpha with the best same-block pair F-beta on dev, and that F-beta, for logic grouping given gold kinds.

    beta 1 weighs not cutting a job into pieces (recall) and not merging two jobs (precision)
    alike. Precision-first (beta 0.5) cut too many blocks midway, and a cut block cannot be
    explained; recall-first (beta 2) buys little more recall for much less precision.
    """
    best, best_score = ALPHAS[0], -1.0
    for a in ALPHAS:
        score = PartitionScore()
        for f in feats:
            idx = logic_idx(gold_kinds(f))
            score.add([f.sol.units[i].block for i in idx], predict_blocks(f, idx, pair_clf, block_clf, a))
        r = score.result()
        p, rc = r["pairP"], r["pairR"]
        f_beta = (1 + beta**2) * p * rc / (beta**2 * p + rc) if p + rc else 0.0
        if f_beta > best_score:
            best, best_score = a, f_beta
    return best, best_score


def full_partition(kinds, idx, blocks) -> list:
    """One cluster per non-logic kind, one per logic block."""
    label = list(kinds)
    for i, b in zip(idx, blocks, strict=True):
        label[i] = ("logic", b)
    return label


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="intfloat/e5-base-v2")
    ap.add_argument(
        "--sweep", action="store_true", help="also score every alpha on test, to see the merge/split trade-off"
    )
    ap.add_argument("--pair-features", choices=("all", "structural"), default="all")
    args = ap.parse_args()
    global PAIR_FEATURES
    PAIR_FEATURES = args.pair_features

    # Imports torch and transformers, which the classical parts here do not need
    from transformers import AutoTokenizer

    from wapul_ml import codeseg

    sols = load_solutions()
    feats = featurize(sols, args.model)
    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    kind_true, kind_pred = [], []
    scorers = ("closest-first", "block scoring")
    # "chosen on dev": per fold, the scorer whose best alpha scores higher on dev
    grouping = {s: PartitionScore() for s in (*scorers, "chosen on dev")}
    end_to_end = {s: PartitionScore() for s in (*scorers, "chosen on dev")}
    singletons, one_block = PartitionScore(), PartitionScore()
    alphas = {s: [] for s in scorers}
    chosen_per_fold = []
    # Analysis only: alpha -> (score, predicted block count, gold block count) with block scoring
    sweep = {a: [PartitionScore(), 0, 0] for a in ALPHAS}

    for fold, (train, test) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
        shuffled = [train[i] for i in np.random.default_rng(0).permutation(len(train))]
        fit_ids, dev_ids = shuffled[: len(train) * 4 // 5], shuffled[len(train) * 4 // 5 :]
        fit_part, dev_part = [feats[i] for i in fit_ids], [feats[i] for i in dev_ids]
        kind_model = codeseg.train(codeseg.MODEL, tok, *codeseg.examples(sols, train), codeseg.EPOCHS, seed=fold)
        pair_clf = fit_pair_clf(fit_part)
        block_clfs = {"closest-first": None, "block scoring": fit_block_clf(dev_part, pair_clf)}
        best = {s: best_alpha(dev_part, pair_clf, block_clfs[s]) for s in scorers}
        alpha = {s: best[s][0] for s in scorers}
        for s in scorers:
            alphas[s].append(float(alpha[s]))
        chosen = max(scorers, key=lambda s: best[s][1])
        chosen_per_fold.append(chosen)

        for i in test:
            f = feats[i]
            if f.sol.source != "human":
                continue
            gold = gold_kinds(f)
            texts = [context_text(f.sol.units, j) for j in range(len(f.sol.units))]
            pred = [KINDS[k] for k in codeseg.predict(kind_model, tok, texts)]
            kind_true += gold
            kind_pred += pred
            gold_idx, pred_idx = logic_idx(gold), logic_idx(pred)
            gold_blocks = [f.sol.units[j].block for j in gold_idx]
            singletons.add(gold_blocks, list(range(len(gold_idx))))
            one_block.add(gold_blocks, [0] * len(gold_idx))
            gold_full = full_partition(gold, gold_idx, gold_blocks)
            if args.sweep:
                for a in ALPHAS:
                    blocks = predict_blocks(f, gold_idx, pair_clf, block_clfs["block scoring"], a)
                    sweep[a][0].add(gold_blocks, blocks)
                    sweep[a][1] += len(set(blocks))
                    sweep[a][2] += len(set(gold_blocks))
            for s in scorers:
                given = predict_blocks(f, gold_idx, pair_clf, block_clfs[s], alpha[s])
                full = full_partition(pred, pred_idx, predict_blocks(f, pred_idx, pair_clf, block_clfs[s], alpha[s]))
                grouping[s].add(gold_blocks, given)
                end_to_end[s].add(gold_full, full)
                if s == chosen:
                    grouping["chosen on dev"].add(gold_blocks, given)
                    end_to_end["chosen on dev"].add(gold_full, full)
        del kind_model

    print(f"model: {args.model}  solutions: {len(sols)}  scored (human): {sum(s.source == 'human' for s in sols)}")
    print(f"\nkinds  macro-F1 {f1_score(kind_true, kind_pred, average='macro'):.3f}")
    print(classification_report(kind_true, kind_pred, labels=list(KINDS), digits=3))

    def show(name, r):
        print(f"  {name:<24} " + "  ".join(f"{k} {v:.3f}" for k, v in r.items()))

    print("logic grouping, given gold kinds")
    show("each alone", singletons.result())
    show("all one block", one_block.result())
    for s in scorers:
        show(f"{s} (alpha {alphas[s]})", grouping[s].result())
    show(f"chosen on dev {chosen_per_fold}", grouping["chosen on dev"].result())
    print("end to end (predicted kinds, then grouping)")
    for s in (*scorers, "chosen on dev"):
        show(s, end_to_end[s].result())
    if args.sweep:
        print("alpha sweep, block scoring, given gold kinds (blocks = predicted / gold logic blocks)")
        for a, (score, n_pred, n_gold) in sweep.items():
            show(f"alpha {a}  blocks {n_pred / n_gold:.2f}x", score.result())


if __name__ == "__main__":
    main()
