# %% [markdown]
# # Statement kinds without a transformer: cross-validation
#
# CodeBERT (`kinds_cv.py`, macro-F1 0.887) is nearly all of the model's size and CPU time. Here
# each unit becomes a dict of string features that a browser can rebuild with web-tree-sitter
# and a regex, and a linear model or LightGBM classifies it. Same 5 folds; C and the model are
# chosen on a dev part of each training fold.
#
# Features: `wapul_ml/features/kind_features.py`. The final model uses LightGBM
# (`wapul_ml/models/kind_lgbm.py`).
#
#     python notebooks/kinds_light_cv.py

# %%
import time

import lightgbm
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.svm import LinearSVC

from wapul_ml.data.solutions import KINDS, load_solutions
from wapul_ml.features.kind_features import unit_features

# %%
sols = load_solutions()
t0 = time.time()
feats = [unit_features(s) for s in sols]
print(f"features for {sum(map(len, feats))} units in {time.time() - t0:.1f}s")


def gather(ids):
    X = [f for i in ids for f in feats[i]]
    y = [KINDS.index(u.kind) for i in ids for u in sols[i].units]
    return X, np.array(y)


MODELS = {
    **{f"lr C={c}": (lambda c=c: LogisticRegression(C=c, max_iter=3000, class_weight="balanced")) for c in (0.3, 1, 3)},
    **{f"svm C={c}": (lambda c=c: LinearSVC(C=c, class_weight="balanced")) for c in (0.03, 0.1, 0.3)},
    "lgbm": lambda: lightgbm.LGBMClassifier(
        n_estimators=400, learning_rate=0.05, num_leaves=31, class_weight="balanced", verbose=-1
    ),
}
y_true, y_pred, chosen = [], {name: [] for name in MODELS}, []
picked = []
for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
    fit_ids, dev_ids = train_test_split(train_ids, test_size=0.2, random_state=fold)
    vec = DictVectorizer()
    Xf, yf = gather(fit_ids)
    Xd, yd = gather(dev_ids)
    Xf = vec.fit_transform(Xf)
    Xd = vec.transform(Xd)
    dev = {}
    for name, make in MODELS.items():
        m = make().fit(Xf.astype(np.float32), yf)
        dev[name] = f1_score(yd, m.predict(Xd.astype(np.float32)), average="macro")
    best = max(dev, key=dev.get)
    # each model refit on the whole training fold and scored, the dev pick recorded
    vec = DictVectorizer()
    Xt, yt = gather(train_ids)
    Xt = vec.fit_transform(Xt).astype(np.float32)
    Xs, ys = gather(test_ids)
    Xs = vec.transform(Xs).astype(np.float32)
    y_true += ys.tolist()
    for name, make in MODELS.items():
        pred = make().fit(Xt, yt).predict(Xs).tolist()
        y_pred[name] += pred
        if name == best:
            picked += pred
    chosen.append(best)
    print(f"  fold {fold}: dev pick {best} ({dev[best]:.3f}), {len(vec.vocabulary_)} features", flush=True)

# %%
print("\nmacro-F1 per model, all folds (CodeBERT fine-tuned: 0.887)")
for name, pred in y_pred.items():
    print(f"  {name:12s} {f1_score(y_true, pred, average='macro'):.3f}")
print(f"\ndev-picked per fold {chosen}: macro-F1 {f1_score(y_true, picked, average='macro'):.3f}")
print(classification_report([KINDS[i] for i in y_true], [KINDS[i] for i in picked], labels=list(KINDS), digits=3))
