"""Statement kinds the CodeSeg way: fine-tune a code encoder to classify each unit with context.

CodeSeg (DocEng 2026) classifies each line with K lines of context on each side and found
fine-tuned CodeBERT / CodeT5+ encoders beat LLMs. Here the input is solutions.context_text and
the labels are the four kinds.
"""

import random

import torch
import torch.nn.functional as F
from transformers import AutoModelForSequenceClassification, get_linear_schedule_with_warmup

from wapul_ml.data.solutions import KINDS, context_text

MODEL = "microsoft/codebert-base"
EPOCHS = 3
MAX_LEN = 256
BATCH = 16


def examples(sols, ids) -> tuple[list[str], list[int]]:
    texts, labels = [], []
    for i in ids:
        for j, u in enumerate(sols[i].units):
            texts.append(context_text(sols[i].units, j))
            labels.append(KINDS.index(u.kind))
    return texts, labels


def batches(tok, texts, labels, order):
    for k in range(0, len(order), BATCH):
        pick = order[k : k + BATCH]
        enc = tok([texts[i] for i in pick], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt")
        yield enc.to("cuda"), torch.tensor([labels[i] for i in pick], device="cuda")


def train(model_name, tok, texts, labels, epochs: int, seed: int, n_labels: int = len(KINDS)):
    torch.manual_seed(seed)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=n_labels).to("cuda").train()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    steps = epochs * -(-len(texts) // BATCH)
    sched = get_linear_schedule_with_warmup(opt, int(0.1 * steps), steps)
    rng = random.Random(seed)
    for ep in range(epochs):
        order = list(range(len(texts)))
        rng.shuffle(order)
        total = 0.0
        for enc, y in batches(tok, texts, labels, order):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss = F.cross_entropy(model(**enc).logits.float(), y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            total += loss.item() * len(y)
        print(f"    epoch {ep + 1} loss {total / len(texts):.4f}", flush=True)
    return model.eval()


@torch.no_grad()
def predict(model, tok, texts) -> list[int]:
    out = []
    for enc, _ in batches(tok, texts, [0] * len(texts), list(range(len(texts)))):
        with torch.autocast("cuda", dtype=torch.bfloat16):
            out += model(**enc).logits.argmax(-1).tolist()
    return out
