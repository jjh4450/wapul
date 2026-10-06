"""Logic blocks as contiguous segments: does a new block start at this logic unit?

    python -m wapul_ml.boundary

Read the logic units of a solution in order, skipping the other kinds, and cut wherever a new
block starts. 81% of gold blocks are contiguous in that order, so a perfect cutter scores B3
0.942 (pair precision 1, recall 0.824); the blocks it cannot express are the delocalized ones,
for a later step that links segments the way conversation disentanglement links messages.

The cutter is codeseg.py's fine-tuned CodeBERT on a binary label, reading the unit with
context, the previous logic unit, and the SEGMENT rules between the two written as words.
Gold kinds, same 5 folds as baseline.py.
"""

import time

import torch
from sklearn.metrics import f1_score
from sklearn.model_selection import KFold
from transformers import AutoTokenizer

from wapul_ml import codeseg
from wapul_ml.ast_features import UnitAst, analyze
from wapul_ml.baseline import segment_features
from wapul_ml.data import Solution, context_text, load_solutions
from wapul_ml.metrics import PartitionScore


EPOCHS = 5  # loss was still falling after codeseg's 3
# baseline.segment_features, in order, as words the encoder reads before the code
FACTS = ("flow", "back_flow", "same_write", "shared_reads", "encloses", "same_control", "same_loop",
         "same_function", "same_parent", "same_category", "same_node")  # fmt: skip


def facts_text(x: UnitAst, y: UnitAst) -> str:
    """The SEGMENT rules between the previous logic unit x and this one y, e.g. 'flow:1 same_loop:0'."""
    values = segment_features(x, y)
    return " ".join(f"{name}:{round(float(v), 1):g}" for name, v in zip(FACTS, values, strict=True))


def logic_examples(s: Solution) -> tuple[list[str], list[int]]:
    """One example per logic unit after the first: label 1 when it opens a new gold block."""
    logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
    asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
    texts, labels = [], []
    for prev, i in zip(logic, logic[1:], strict=False):
        texts.append(
            f"<facts>{facts_text(asts[prev], asts[i])} depth:{asts[i].depth - asts[prev].depth}</facts>"
            f"<previous_logic>{s.units[prev].text}</previous_logic>{context_text(s.units, i)}"
        )
        labels.append(int(s.units[i].block != s.units[prev].block))
    return texts, labels


def segments(starts: list[int]) -> list[int]:
    """Segment id per logic unit, from the start flags of every unit after the first."""
    out = [0]
    for start in starts:
        out.append(out[-1] + start)
    return out


def main() -> None:
    sols = load_solutions()
    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    grouping, cut_true, cut_pred = PartitionScore(), [], []
    for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
        t = time.time()
        texts, labels = [], []
        for i in train_ids:
            x, y = logic_examples(sols[i])
            texts += x
            labels += y
        model = codeseg.train(codeseg.MODEL, tok, texts, labels, EPOCHS, seed=fold, n_labels=2)
        for i in test_ids:
            s = sols[i]
            gold = [u.block for u in s.units if u.kind == "logic"]
            if not gold:
                continue
            x, y = logic_examples(s)
            pred = codeseg.predict(model, tok, x) if x else []
            cut_true += y
            cut_pred += pred
            grouping.add(gold, segments(pred))
        print(f"  fold {fold} done ({time.time() - t:.0f}s)", flush=True)
        del model
        torch.cuda.empty_cache()
    print(f"block starts  F1 {f1_score(cut_true, cut_pred):.3f}  (positives {sum(cut_true)} / {len(cut_true)})")
    print("logic grouping, given gold kinds, contiguous segments")
    print("  " + "  ".join(f"{k} {v:.3f}" for k, v in grouping.result().items()))


if __name__ == "__main__":
    main()
