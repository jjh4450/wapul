# %% [markdown]
# # Statement kinds: cross-validation
#
# Fine-tunes the kind classifier (`wapul_ml/models/kind_classifier.py`) on each fold's training
# solutions and scores macro-F1 on the human-reviewed test solutions. Same 5 folds as the other
# notebooks.
#
#     python notebooks/kinds_cv.py [--model microsoft/codebert-base] [--epochs 3]

# %%
import argparse
import time

import torch
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold
from transformers import AutoTokenizer

from wapul_ml.data.solutions import KINDS, load_solutions
from wapul_ml.models.kind_classifier import EPOCHS, MODEL, examples, predict, train

ap = argparse.ArgumentParser()
ap.add_argument("--model", default=MODEL)
ap.add_argument("--epochs", type=int, default=EPOCHS)
args = ap.parse_known_args()[0]  # known args only: a Jupyter kernel passes arguments of its own

# %%
sols = load_solutions()
tok = AutoTokenizer.from_pretrained(args.model)
y_true, y_pred = [], []
for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
    t = time.time()
    model = train(args.model, tok, *examples(sols, train_ids), args.epochs, seed=fold)
    texts, labels = examples(sols, [i for i in test_ids if sols[i].source == "human"])
    y_true += labels
    y_pred += predict(model, tok, texts)
    print(f"  fold {fold} done ({time.time() - t:.0f}s)", flush=True)
    del model
    torch.cuda.empty_cache()

# %%
names = [KINDS[i] for i in y_true], [KINDS[i] for i in y_pred]
print(f"model: {args.model} fine-tuned, {args.epochs} epochs")
print(f"kinds  macro-F1 {f1_score(*names, average='macro'):.3f}")
print(classification_report(*names, labels=list(KINDS), digits=3))
