"""SetFit-style contrastive fine-tuning of the embedding model on labeled pairs.

SetFit (Tunstall et al. 2022): pull same-class pairs together and push different-class
pairs apart with a cosine-similarity loss, then fit a simple head on the new embeddings.
Two kinds of pairs are used, matching what each classifier embeds:
- kind pairs: units with context, same kind -> 1, different kind -> 0
- block pairs: logic units of one solution, same block -> 1, different block -> 0

It uses labels, so it must only ever see training solutions: run it per CV fold.
"""

import random
from itertools import combinations
from pathlib import Path

from wapul_ml.data import Solution, context_text

KIND_PAIRS_PER_UNIT = 4  # SetFit samples a fixed number of pairs per example (R)


def kind_pairs(sols: list[Solution], rng: random.Random) -> list[tuple[str, str, float]]:
    items = [(context_text(s.units, i), u.kind) for s in sols for i, u in enumerate(s.units)]
    by_kind: dict[str, list[str]] = {}
    for text, kind in items:
        by_kind.setdefault(kind, []).append(text)
    pairs = []
    for text, kind in items:
        others = [k for k in by_kind if k != kind]
        for _ in range(KIND_PAIRS_PER_UNIT // 2):
            pairs.append((text, rng.choice(by_kind[kind]), 1.0))
            pairs.append((text, rng.choice(by_kind[rng.choice(others)]), 0.0))
    return pairs


def block_pairs(sols: list[Solution]) -> list[tuple[str, str, float]]:
    pairs = []
    for s in sols:
        logic = [u for u in s.units if u.kind == "logic"]
        for a, b in combinations(logic, 2):
            pairs.append((a.text, b.text, float(a.block == b.block)))
    return pairs


def finetune(base: str, sols: list[Solution], out: Path, seed: int = 0) -> str:
    """Fine-tune `base` on pairs from `sols`, save to `out`, return the path. Reuses `out` if present."""
    if (out / "config.json").exists():
        return str(out)
    from datasets import Dataset
    from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer, SentenceTransformerTrainingArguments
    from sentence_transformers.losses import CosineSimilarityLoss

    rng = random.Random(seed)
    pairs = kind_pairs(sols, rng) + block_pairs(sols)
    rng.shuffle(pairs)
    prefix = "query: " if "e5" in base else ""
    train = Dataset.from_dict(
        {
            "sentence1": [prefix + a for a, _, _ in pairs],
            "sentence2": [prefix + b for _, b, _ in pairs],
            "score": [y for _, _, y in pairs],
        }
    )
    model = SentenceTransformer(base)
    model.max_seq_length = 256
    # SetFit defaults: lr 2e-5, one epoch over the sampled pairs
    args = SentenceTransformerTrainingArguments(
        output_dir=str(out / "checkpoints"),
        num_train_epochs=1,
        per_device_train_batch_size=32,
        learning_rate=2e-5,
        warmup_ratio=0.1,
        bf16=True,
        save_strategy="no",
        logging_steps=200,
        report_to="none",
        seed=seed,
    )
    SentenceTransformerTrainer(model=model, args=args, train_dataset=train, loss=CosineSimilarityLoss(model)).train()
    model.save(str(out))
    return str(out)
