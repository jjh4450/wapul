"""Logic blocks the conversation-disentanglement way: each unit links to one earlier unit or to itself.

    python -m wapul_ml.disentangle

Disentanglement (Kummerfeld et al. 2019) reads messages in order and, for each, picks the earlier
message it replies to, or itself to start a new conversation; conversations are the connected
links. Here messages are logic units in code order and conversations are blocks, so a unit can
link to a far earlier one and blocks need not be contiguous. No alpha: the self link competes
with the real candidates.

Each candidate link is scored by fine-tuned CodeBERT reading the SEGMENT rules between the two
units as words, the candidate unit and the target unit with context (the BERT pair scorers that
followed Kummerfeld et al.). A softmax over a target's candidates is trained to put its mass on
the correct ones, any earlier unit of the same block or itself when it opens one (Lee et al.
2017). Each fold trains on its fit part until the dev loss stops improving. Gold kinds, same 5
folds as baseline.py.
"""

import random
import time

import numpy as np
import torch
from sklearn.model_selection import KFold
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

from wapul_ml import codeseg
from wapul_ml.ast_features import analyze
from wapul_ml.boundary import facts_text
from wapul_ml.data import Solution, context_text, load_solutions
from wapul_ml.metrics import PartitionScore

MAX_EPOCHS = 10
PATIENCE = 2  # stop after this many epochs without a better dev loss, keep the best epoch
MAX_LEN = 128
ACCUM = 8  # targets per optimizer step


class Candidates:
    """For each logic unit t of a solution: one text per candidate link (every earlier logic unit,
    then t itself) and which of them are correct."""

    def __init__(self, s: Solution):
        logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
        asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
        self.blocks = [s.units[i].block for i in logic]
        self.texts: list[list[str]] = []
        self.gold: list[list[bool]] = []
        for t, i in enumerate(logic):
            target = context_text(s.units, i)
            texts = [
                f"<facts>{facts_text(asts[j], asts[i])} gap:{t - c}</facts><candidate>{s.units[j].text}</candidate>"
                f"{target}"
                for c, j in enumerate(logic[:t])
            ]
            texts.append(f"<facts>new block</facts>{target}")
            gold = [self.blocks[c] == self.blocks[t] for c in range(t)]
            self.texts.append(texts)
            self.gold.append([*gold, not any(gold)])

    def __len__(self) -> int:
        return len(self.blocks)


def scores(model, tok, texts: list[str]) -> torch.Tensor:
    enc = tok(texts, truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt").to("cuda")
    with torch.autocast("cuda", dtype=torch.bfloat16):
        return model(**enc).logits.float().squeeze(-1)


def link_loss(model, tok, d: Candidates, t: int) -> torch.Tensor:
    logp = torch.log_softmax(scores(model, tok, d.texts[t]), 0)
    return -torch.logsumexp(logp[torch.tensor(d.gold[t], device="cuda")], 0)


def train(tok, fit: list[Candidates], dev: list[Candidates], seed: int):
    """Train on fit until the dev loss stops improving; return the best epoch's model."""
    torch.manual_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(codeseg.MODEL, num_labels=1).to("cuda").train()
    targets = [(d, t) for d in fit for t in range(len(d))]
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    steps = MAX_EPOCHS * -(-len(targets) // ACCUM)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    rng = random.Random(seed)
    best_loss, best_state, waited = float("inf"), None, 0
    for ep in range(MAX_EPOCHS):
        model.train()
        rng.shuffle(targets)
        total = 0.0
        for k, (d, t) in enumerate(targets, 1):
            loss = link_loss(model, tok, d, t)
            (loss / ACCUM).backward()
            total += loss.item()
            if k % ACCUM == 0 or k == len(targets):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                sched.step()
                opt.zero_grad()
        model.eval()
        with torch.no_grad():
            dev_losses = [link_loss(model, tok, d, t).item() for d in dev for t in range(len(d))]
        dev_loss = sum(dev_losses) / len(dev_losses)
        print(f"    epoch {ep + 1} loss {total / len(targets):.4f}  dev {dev_loss:.4f}", flush=True)
        if dev_loss < best_loss:
            best_loss, waited = dev_loss, 0
            best_state = {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}
        else:
            waited += 1
            if waited >= PATIENCE:
                break
    model.load_state_dict(best_state)
    return model.eval()


@torch.no_grad()
def predict(model, tok, d: Candidates) -> list[int]:
    """Block id per logic unit: follow each unit's best link (an earlier unit's block, or a new one)."""
    out: list[int] = []
    for t, texts in enumerate(d.texts):
        best = int(scores(model, tok, texts).argmax())
        out.append(out[best] if best < t else t)
    return out


def main() -> None:
    sols = load_solutions()
    tok = AutoTokenizer.from_pretrained(codeseg.MODEL)
    data = [Candidates(s) for s in sols]
    grouping = PartitionScore()
    for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
        t = time.time()
        # The same fit/dev split of the training solutions as baseline.py
        shuffled = [train_ids[i] for i in np.random.default_rng(0).permutation(len(train_ids))]
        cut = len(train_ids) * 4 // 5
        model = train(tok, [data[i] for i in shuffled[:cut]], [data[i] for i in shuffled[cut:]], seed=fold)
        fold_score = PartitionScore()
        for i in test_ids:
            if len(data[i]):
                pred = predict(model, tok, data[i])
                grouping.add(data[i].blocks, pred)
                fold_score.add(data[i].blocks, pred)
        print(f"  fold {fold} done ({time.time() - t:.0f}s)  test B3 {fold_score.result()['B3']:.3f}", flush=True)
        del model
        torch.cuda.empty_cache()
    print("logic grouping, given gold kinds, link to one earlier unit or self")
    print("  " + "  ".join(f"{k} {v:.3f}" for k, v in grouping.result().items()))


if __name__ == "__main__":
    main()
