"""Logic blocks the conversation-disentanglement way: scorers over candidate rows, and decoding.

Disentanglement (Kummerfeld et al. 2019) reads messages in order and, for each, picks the earlier
message it replies to, or itself to start a new conversation. Here messages are logic units in
code order and conversations are blocks, so blocks may be non-contiguous, and no threshold is
needed: the new-block candidate competes with the real ones (features/candidates.py).

Scorers rank within each unit's candidates:
- mlp: a small net trained with a softmax over the candidates, maximizing the summed probability
  of the correct ones (Lee et al. 2017)
- lgbm: LightGBM LambdaRank, each unit's candidates one query
- ensemble: the two, each as probabilities over the candidates, averaged
"""

import lightgbm
import numpy as np
import torch
import torch.nn.functional as F
from lightgbm import LGBMRanker

from wapul_ml.features.candidates import BlockCandidates, Candidates

EPOCHS = 30


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


def ensemble(*scorers):
    """Scorers each turned into probabilities over the candidates, averaged."""

    def score(r: torch.Tensor) -> np.ndarray:
        p = [torch.softmax(torch.tensor(f(r), dtype=torch.float32), 0).numpy() for f in scorers]
        return np.mean(p, axis=0)

    return score


def train_ensemble(data, seed: int):
    """The MLP and LightGBM scorers, averaged."""
    return ensemble(train_mlp(data, seed), train_lgbm(data, seed))


def predict(score, d: Candidates) -> list[int]:
    """Block id per logic unit: follow each unit's best link (an earlier unit's block, or a new one)."""
    out: list[int] = []
    for t, r in enumerate(d.rows):
        best = int(np.argmax(score(r)))
        out.append(out[best] if best < t else t)
    return out


def predict_blocks(score, d: BlockCandidates) -> list[int]:
    """Block id per logic unit, joining the best block built so far or opening a new one."""
    groups: list[list[int]] = []
    out: list[int] = []
    for t in range(len(d)):
        best = int(np.argmax(score(d.block_rows(t, groups))))
        if best == len(groups):
            groups.append([])
        groups[best].append(t)
        out.append(best)
    return out
