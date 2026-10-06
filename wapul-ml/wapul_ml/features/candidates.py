"""Candidate rows for the block scorers: what each logic unit could link to, as features.

Candidates are either every earlier logic unit (Candidates) or the blocks built so far
(BlockCandidates: cluster ranking as in Clark & Manning 2016, block-level features, built on gold
blocks for training). Features are hand-made as in Kummerfeld et al. 2019: the SEGMENT rules,
distance, depth change, and facts about the unit itself, which drive the new-block choice.
"""

import numpy as np
import torch

from wapul_ml.data.solutions import Solution
from wapul_ml.features.unit_ast import CATEGORIES, UnitAst, analyze, segment_features

N_PAIR = 14  # 11 SEGMENT rules + adjacent, log distance, depth change


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

    def __init__(self, s: Solution):
        u = Units(s)
        self.blocks = u.blocks
        self.rows: list[torch.Tensor] = []
        self.gold: list[torch.Tensor] = []
        for t in range(len(u)):
            rows = [[0.0, *p, *u.own[t]] for p in u.pairs[t]]
            rows.append([1.0, *[0.0] * N_PAIR, *u.own[t]])  # self link: a new block starts here
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
