# %% [markdown]
# # Statement kinds: keep only features seen in several repositories
#
# Most kind features are tokens that only one repository's solutions contain; they do not carry
# over to other people's code. Here a feature is kept only when solutions from at least M
# distinct repositories contain it, counted on each training fold alone.
#
#     python notebooks/kinds_min_sources.py

# %%
import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import KFold

from wapul_ml.data.solutions import load_solutions
from wapul_ml.features.kind_features import common_features, source_of, unit_features, with_ngrams
from wapul_ml.models import kind_lgbm

sols = load_solutions()
feats = [with_ngrams(unit_features(s)) for s in sols]
kinds = [[u.kind for u in s.units] for s in sols]
sources = [source_of(s.id) for s in sols]
folds = list(KFold(5, shuffle=True, random_state=0).split(sols))
print(f"{len(set(sources))} repositories")
for m in (1, 2, 3, 5):
    y_true, y_pred, sizes = [], [], []
    for train_ids, test_ids in folds:
        keep = common_features([feats[i] for i in train_ids], [sources[i] for i in train_ids], m)
        model = kind_lgbm.train(
            [f for i in train_ids for f in feats[i]], [k for i in train_ids for k in kinds[i]], keep=keep
        )
        y_pred += model.predict([f for i in test_ids for f in feats[i]])
        y_true += [k for i in test_ids for k in kinds[i]]
        sizes.append(len(model.names))
    print(
        f"min repositories {m}: macro-F1 {f1_score(y_true, y_pred, average='macro'):.3f}, {int(np.mean(sizes))} features"
    )
