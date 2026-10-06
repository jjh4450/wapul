"""Partition metrics from coreference evaluation, for grouping units into blocks.

Blocks can be non-contiguous, so segmentation metrics (Pk, WindowDiff) don't apply.
B3 and entity-based CEAF are used instead; MUC is skipped because it ignores
single-unit blocks and rewards making fewer blocks. Each metric is micro-averaged
over documents: totals are summed before dividing.
"""

from collections import defaultdict
from itertools import combinations

import numpy as np
from scipy.optimize import linear_sum_assignment


def clusters(labels: list) -> list[set[int]]:
    groups = defaultdict(set)
    for i, label in enumerate(labels):
        groups[label].add(i)
    return list(groups.values())


class PartitionScore:
    def __init__(self):
        self.b3 = np.zeros(3)  # precision sum, recall sum, item count
        self.ceaf = np.zeros(3)  # similarity sum, predicted count, gold count
        self.pairs = np.zeros(3)  # true positive, predicted, gold

    def add(self, gold: list, pred: list) -> None:
        g, p = clusters(gold), clusters(pred)
        g_of = {i: c for c in g for i in c}
        p_of = {i: c for c in p for i in c}
        for i in range(len(gold)):
            overlap = len(g_of[i] & p_of[i])
            self.b3 += (overlap / len(p_of[i]), overlap / len(g_of[i]), 1)
        # Built as 2-D even when a side is empty (a solution with no logic units)
        sim = np.zeros((len(g), len(p)))
        for r, a in enumerate(g):
            for c, b in enumerate(p):
                sim[r, c] = 2 * len(a & b) / (len(a) + len(b))
        rows, cols = linear_sum_assignment(-sim)
        self.ceaf += (sim[rows, cols].sum(), len(p), len(g))
        same_g = {(i, j) for i, j in combinations(range(len(gold)), 2) if gold[i] == gold[j]}
        same_p = {(i, j) for i, j in combinations(range(len(pred)), 2) if pred[i] == pred[j]}
        self.pairs += (len(same_g & same_p), len(same_p), len(same_g))

    def result(self) -> dict[str, float]:
        def f1(p, r):
            return 2 * p * r / (p + r) if p + r else 0.0

        b3 = f1(self.b3[0] / self.b3[2], self.b3[1] / self.b3[2])
        ceaf = f1(self.ceaf[0] / self.ceaf[1], self.ceaf[0] / self.ceaf[2])
        tp, n_pred, n_gold = self.pairs
        # Pair precision low = blocks wrongly merged; recall low = blocks wrongly split
        pair_p = tp / n_pred if n_pred else 0.0
        pair_r = tp / n_gold if n_gold else 0.0
        return {"B3": b3, "CEAFe": ceaf, "pairP": pair_p, "pairR": pair_r, "pairF1": f1(pair_p, pair_r)}
