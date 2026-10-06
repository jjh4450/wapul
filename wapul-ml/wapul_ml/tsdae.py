"""TSDAE domain adaptation of the embedding model on unlabeled corpus statements.

    python -m wapul_ml.tsdae --model intfloat/e5-base-v2 [--sentences 60000]

TSDAE (Wang, Reimers & Gurevych 2021): delete 60% of a text's tokens, encode the damaged
text to one vector, and train a decoder tied to the encoder to rebuild the original from it.
It beat MLM, SimCSE and CT for domain adaptation, and gains level off around 10k sentences.

Training texts are what the classifiers embed: single statements and statements with their
context window, from corpus solutions in the three supported languages. Labeled solutions
are left out, so evaluation stays on code the adaptation never saw.
"""

import argparse
import json
import random
import re
from pathlib import Path

from wapul_ml.data import DATA, context_text
from wapul_ml.units import units

OUT = Path(__file__).resolve().parent.parent / "models"
LANGS = {"cpp", "java", "python"}
TOKEN = re.compile(r"\w+|[^\w\s]")


def damage(text: str, rng: random.Random, ratio: float = 0.6) -> str:
    tokens = TOKEN.findall(text)
    kept = [t for t in tokens if rng.random() > ratio]
    return " ".join(kept or tokens[:1])


def corpus_texts(n: int, seed: int = 0) -> list[str]:
    labeled = {json.loads(line)["id"] for line in open(DATA / "labels" / "labels.jsonl", encoding="utf-8")}
    rows = []
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl")):
        for line in open(part, encoding="utf-8"):
            row = json.loads(line)
            if row["language"] in LANGS and row["id"] not in labeled:
                rows.append((row["code"], row["language"]))
    rng = random.Random(seed)
    rng.shuffle(rows)
    texts: list[str] = []
    for code, language in rows:
        us = units(code, language)
        # context_text only reads .text, so the units() output works as-is
        for i in rng.sample(range(len(us)), min(3, len(us))):
            texts.append(us[i].text)
            texts.append(context_text(us, i))
        if len(texts) >= n:
            break
    return texts[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="intfloat/e5-base-v2")
    ap.add_argument("--sentences", type=int, default=60000)
    ap.add_argument("--epochs", type=int, default=1)
    args = ap.parse_args()

    from datasets import Dataset
    from sentence_transformers import SentenceTransformer, SentenceTransformerTrainer, SentenceTransformerTrainingArguments
    from sentence_transformers.losses import DenoisingAutoEncoderLoss

    texts = corpus_texts(args.sentences)
    prefix = "query: " if "e5" in args.model else ""
    rng = random.Random(1)
    train = Dataset.from_dict({"damaged": [prefix + damage(t, rng) for t in texts], "original": [prefix + t for t in texts]})
    print(f"training texts: {len(texts)}")

    model = SentenceTransformer(args.model)
    # 256 overflowed a 16GB card by ~2GB (encoder + tied decoder, batch 32), so cut ~12%; long context
    # windows are the only texts this cuts, and their target statement sits in the middle
    model.max_seq_length = 224
    loss = DenoisingAutoEncoderLoss(model, decoder_name_or_path=args.model, tie_encoder_decoder=True)
    out = OUT / f"tsdae-{args.model.split('/')[-1]}"
    # Settings from the TSDAE paper: lr 3e-5, constant schedule, one epoch
    targs = SentenceTransformerTrainingArguments(
        output_dir=str(out / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=32,
        learning_rate=3e-5,
        lr_scheduler_type="constant",
        weight_decay=0.0,
        bf16=True,
        save_strategy="no",
        logging_steps=100,
        report_to="none",
    )
    SentenceTransformerTrainer(model=model, args=targs, train_dataset=train, loss=loss).train()
    model.save(str(out))
    print(f"saved {out}")


if __name__ == "__main__":
    main()
