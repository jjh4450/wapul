"""CPU inference time of the saved block model, per solution.

    python -m wapul_ml.cpu_time    # run the container without --gpus

Times model.BlockModel on a fixed random sample of labeled solutions plus the one with the most
logic units, with torch capped at THREADS threads as on a small server: the whole call, and the
block stage alone (AST features and the two small rankers) on the same units.
"""

import time

import numpy as np
import torch

from wapul_ml import disentangle_ast
from wapul_ml.data import load_solutions
from wapul_ml.model import BlockModel

THREADS = 4
SAMPLE = 40


def report(name: str, seconds: list[float]) -> None:
    s = np.array(seconds)
    print(f"  {name:<12} median {np.median(s):6.2f}s  p90 {np.percentile(s, 90):6.2f}s  max {s.max():6.2f}s")


def main() -> None:
    torch.set_num_threads(THREADS)
    sols = load_solutions()
    n_logic = np.array([sum(u.kind == "logic" for u in s.units) for s in sols])
    pick = sorted({*np.random.default_rng(0).choice(len(sols), SAMPLE, replace=False).tolist(), int(n_logic.argmax())})
    model = BlockModel()
    total, blocks = [], []
    for i in pick:
        s = sols[i]
        t = time.perf_counter()
        model.solution(s.code, s.language)
        total.append(time.perf_counter() - t)
        t = time.perf_counter()
        disentangle_ast.predict_blocks(model.blocks, disentangle_ast.BlockCandidates(s, labeled=False))
        blocks.append(time.perf_counter() - t)
    print(
        f"{len(pick)} solutions, units median {int(np.median([len(sols[i].units) for i in pick]))}, {THREADS} threads"
    )
    report("whole model", total)
    report("blocks only", blocks)


if __name__ == "__main__":
    main()
