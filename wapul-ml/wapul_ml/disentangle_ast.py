"""disentangle.py's link-to-an-earlier-candidate-or-self, scored over AST features.

    python -m wapul_ml.disentangle_ast [variant]

The features are those of Kummerfeld et al. (2019): hand-made, here the SEGMENT rules, distance,
depth change, and facts about the unit itself (which drive the self link). Variants:
- scorer: mlp, a small net trained with a softmax over each unit's candidates, maximizing the
  summed probability of the correct ones (Lee et al. 2017); lgbm, LightGBM LambdaRank, which also
  ranks within each unit's candidates; rbf-svm, each candidate classified on its own; ensemble, the
  mlp and lgbm candidate probabilities averaged
- +relative: per candidate, whether it is the nearest one with each SEGMENT relation, so a
  candidate is judged against the others as well
- blocks-: candidates are the blocks built so far instead of earlier units, with block-level
  features (Clark & Manning 2016), trained on gold blocks and decoded greedily; +offset shifts
  the new-block score by an offset chosen on dev (pair F1), to trade cutting against merging
MLP variants repeat every fold over several seeds. Gold kinds, same 5 folds as baseline.py.
"""

import argparse
from functools import partial

import numpy as np
import torch
import torch.nn.functional as F
import lightgbm
from lightgbm import LGBMRanker
from sklearn.model_selection import KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from wapul_ml.ast_features import CATEGORIES, UnitAst, analyze
from wapul_ml.baseline import segment_features
from wapul_ml.data import Solution, load_solutions
from wapul_ml.metrics import PartitionScore

EPOCHS = 30
SEEDS = 5
N_PAIR = 14  # 11 SEGMENT rules + adjacent, log distance, depth change
# Relations whose nearest holder among the candidates gets a flag: flow, back flow, same control,
# same loop, same parent (indices into segment_features)
NEAREST = (0, 1, 5, 6, 8)


def unit_features(a: UnitAst) -> list[float]:
    return [*(a.category == c for c in CATEGORIES), a.is_header, a.depth]


class Units:
    """AST facts of a solution's logic units: per unit t, its own features and its pair features
    with every earlier logic unit."""

    def __init__(self, s: Solution):
        logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
        asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
        self.blocks = [s.units[i].block for i in logic]
        self.own = [unit_features(asts[i]) for i in logic]
        self.pairs = [
            np.array(
                [
                    [
                        *segment_features(asts[logic[c]], asts[i]),
                        t - c == 1,
                        np.log1p(t - c),
                        asts[i].depth - asts[logic[c]].depth,
                    ]
                    for c in range(t)
                ],
                dtype=np.float32,
            ).reshape(t, N_PAIR)
            for t, i in enumerate(logic)
        ]

    def __len__(self) -> int:
        return len(self.blocks)


class Candidates:
    """For each logic unit t: one feature row per candidate (every earlier logic unit, then t
    itself) and which candidates are correct."""

    def __init__(self, s: Solution, relative: bool = False):
        u = Units(s)
        self.blocks = u.blocks
        self.rows: list[torch.Tensor] = []
        self.gold: list[torch.Tensor] = []
        for t in range(len(u)):
            pair = u.pairs[t]
            if relative:
                flags = np.zeros((t, len(NEAREST)), dtype=np.float32)
                for k, col in enumerate(NEAREST):
                    holders = np.nonzero(pair[:, col] > 0)[0]
                    if len(holders):
                        flags[holders.max(), k] = 1.0
                pair = np.hstack([pair, flags])
            n = pair.shape[1]
            rows = [[0.0, *p, *u.own[t]] for p in pair]
            rows.append([1.0, *[0.0] * n, *u.own[t]])  # self link: a new block starts here
            gold = [u.blocks[c] == u.blocks[t] for c in range(t)]
            self.rows.append(torch.tensor(rows, dtype=torch.float32))
            self.gold.append(torch.tensor([*gold, not any(gold)]))

    def __len__(self) -> int:
        return len(self.blocks)


class BlockCandidates:
    """For each logic unit t: one row per block built before it (teacher-forced on gold blocks for
    training), then t itself; block_rows builds the same rows for any blocks, for decoding.
    Unlabeled code (labeled=False) keeps only what decoding needs."""

    def __init__(self, s: Solution, labeled: bool = True):
        self.u = Units(s)
        self.blocks = self.u.blocks
        self.rows: list[torch.Tensor] = []
        self.gold: list[torch.Tensor] = []
        for t in range(len(self.u) if labeled else 0):
            groups: dict[int, list[int]] = {}
            for c in range(t):
                groups.setdefault(self.blocks[c], []).append(c)
            self.rows.append(self.block_rows(t, list(groups.values())))
            gold = [b == self.blocks[t] for b in groups]
            self.gold.append(torch.tensor([*gold, not any(gold)]))

    def block_rows(self, t: int, groups: list[list[int]]) -> torch.Tensor:
        pair, own = self.u.pairs[t], self.u.own[t]
        last = max((g[-1] for g in groups), default=-1)
        rows = [
            [0.0, *pair[g].max(0), *pair[g].mean(0), np.log1p(len(g)), np.log1p(t - g[-1]), g[-1] == last, *own]
            for g in groups
        ]
        rows.append([1.0, *[0.0] * (2 * N_PAIR + 3), *own])
        return torch.tensor(rows, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.blocks)


class MlpScorer:
    """The small net with the feature standardization it was trained with; called on candidate rows."""

    def __init__(self, n_features: int, mean: torch.Tensor, std: torch.Tensor):
        self.net = torch.nn.Sequential(torch.nn.Linear(n_features, 64), torch.nn.ReLU(), torch.nn.Linear(64, 1))
        self.mean, self.std = mean, std

    @torch.no_grad()
    def __call__(self, r: torch.Tensor) -> np.ndarray:
        return self.net((r - self.mean) / self.std).squeeze(-1).numpy()

    def save(self, path) -> None:
        torch.save({"net": self.net.state_dict(), "mean": self.mean, "std": self.std}, path)

    @classmethod
    def load(cls, path) -> "MlpScorer":
        state = torch.load(path)
        scorer = cls(len(state["mean"]), state["mean"], state["std"])
        scorer.net.load_state_dict(state["net"])
        scorer.net.eval()
        return scorer


def train_mlp(data, seed: int) -> MlpScorer:
    torch.manual_seed(seed)
    rows = torch.cat([r for d in data for r in d.rows])
    scorer = MlpScorer(rows.shape[1], rows.mean(0), rows.std(0) + 1e-6)
    net, mean, std = scorer.net, scorer.mean, scorer.std
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    for _ in range(EPOCHS):
        for k in rng.permutation(len(data)):
            d = data[k]
            if not len(d):
                continue
            loss = 0.0
            for r, g in zip(d.rows, d.gold, strict=True):
                logp = F.log_softmax(net((r - mean) / std).squeeze(-1), 0)
                loss = loss - torch.logsumexp(logp[g], 0)
            opt.zero_grad()
            (loss / len(d)).backward()
            opt.step()
    net.eval()
    return scorer


class LgbmScorer:
    """A LightGBM ranker's booster, called on candidate rows."""

    def __init__(self, booster: lightgbm.Booster):
        self.booster = booster

    def __call__(self, r: torch.Tensor) -> np.ndarray:
        return self.booster.predict(r.numpy())

    def save(self, path) -> None:
        self.booster.save_model(str(path))

    @classmethod
    def load(cls, path) -> "LgbmScorer":
        return cls(lightgbm.Booster(model_file=str(path)))


def train_lgbm(data, seed: int) -> LgbmScorer:
    """LambdaRank over each unit's candidates as one query, correct candidates relevant."""
    X = torch.cat([r for d in data for r in d.rows]).numpy()
    y = torch.cat([g for d in data for g in d.gold]).numpy().astype(int)
    group = [len(r) for d in data for r in d.rows]
    ranker = LGBMRanker(n_estimators=300, learning_rate=0.05, num_leaves=15, random_state=seed, verbose=-1)
    ranker.fit(X, y, group=group)
    return LgbmScorer(ranker.booster_)


def train_svm(data, seed: int):
    """RBF SVM on each candidate row, correct link or not."""
    X = torch.cat([r for d in data for r in d.rows]).numpy()
    y = torch.cat([g for d in data for g in d.gold]).numpy()
    svm = make_pipeline(StandardScaler(), SVC(random_state=seed)).fit(X, y)
    return lambda r: svm.decision_function(r.numpy())


def predict(score, d: Candidates) -> list[int]:
    """Block id per logic unit: follow each unit's best link (an earlier unit's block, or a new one)."""
    out: list[int] = []
    for t, r in enumerate(d.rows):
        best = int(np.argmax(score(r)))
        out.append(out[best] if best < t else t)
    return out


def predict_blocks(score, d: BlockCandidates, offset: float = 0.0) -> list[int]:
    """Block id per logic unit, joining the best block built so far or opening a new one.
    offset is added to the new-block score: below 0 merges more, above 0 cuts more."""
    groups: list[list[int]] = []
    out: list[int] = []
    for t in range(len(d)):
        s = score(d.block_rows(t, groups))
        s[-1] += offset
        best = int(np.argmax(s))
        if best == len(groups):
            groups.append([])
        groups[best].append(t)
        out.append(best)
    return out


def ensemble(*scorers):
    """Scorers each turned into probabilities over the candidates, averaged (as log, so the
    new-block offset stays additive)."""

    def score(r: torch.Tensor) -> np.ndarray:
        p = [torch.softmax(torch.tensor(f(r), dtype=torch.float32), 0).numpy() for f in scorers]
        return np.log(np.mean(p, axis=0))

    return score


def train_ensemble(data, seed: int):
    """The MLP and LightGBM scorers, averaged."""
    return ensemble(train_mlp(data, seed), train_lgbm(data, seed))


SCORERS = {
    "mlp": (train_mlp, SEEDS),
    "lgbm": (train_lgbm, 1),  # deterministic
    "rbf-svm": (train_svm, 1),  # deterministic
    "ensemble": (train_ensemble, SEEDS),
}
VARIANTS = [
    *SCORERS,
    "mlp+relative",
    "lgbm+relative",
    "blocks-mlp",
    "blocks-lgbm",
    "blocks-lgbm+offset",
    "blocks-ensemble",
]
OFFSETS = np.arange(-3, 3.01, 0.25)


def offset_on_dev(score, dev: list[BlockCandidates]) -> float:
    """The new-block offset with the best same-block pair F1 on dev, as baseline.py picks alpha."""

    def f1(offset: float) -> float:
        s = PartitionScore()
        for d in dev:
            s.add(d.blocks, predict_blocks(score, d, offset))
        return s.result()["pairF1"]

    return float(max(OFFSETS, key=f1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("variant", nargs="?", choices=VARIANTS, default="mlp")
    args = ap.parse_args()
    blocks = args.variant.startswith("blocks-")
    tune = args.variant.endswith("+offset")
    fit, seeds = SCORERS[args.variant.removeprefix("blocks-").removesuffix("+relative").removesuffix("+offset")]

    sols = load_solutions()
    if blocks:
        data, decode = [BlockCandidates(s) for s in sols], predict_blocks
    else:
        data, decode = [Candidates(s, relative=args.variant.endswith("+relative")) for s in sols], predict
    results = []
    for seed in range(seeds):
        grouping = PartitionScore()
        for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
            if tune:
                # The same fit/dev split of the training solutions as baseline.py
                shuffled = [train_ids[i] for i in np.random.default_rng(0).permutation(len(train_ids))]
                cut = len(train_ids) * 4 // 5
                score = fit([data[i] for i in shuffled[:cut]], seed=seed * 5 + fold)
                offset = offset_on_dev(score, [data[i] for i in shuffled[cut:] if len(data[i])])
                print(f"  fold {fold}: new-block offset {offset:+.2f}", flush=True)
                decode = partial(predict_blocks, offset=offset)
            else:
                score = fit([data[i] for i in train_ids], seed=seed * 5 + fold)
            for i in test_ids:
                if len(data[i]):
                    grouping.add(data[i].blocks, decode(score, data[i]))
        r = grouping.result()
        results.append(r)
        print(f"  seed {seed}  " + "  ".join(f"{k} {v:.3f}" for k, v in r.items()), flush=True)
    print(f"logic grouping, given gold kinds, {args.variant}, mean ± std over {seeds} seeds")
    print(
        "  "
        + "  ".join(
            f"{k} {np.mean([r[k] for r in results]):.3f}±{np.std([r[k] for r in results]):.3f}" for k in results[0]
        )
    )


if __name__ == "__main__":
    main()
