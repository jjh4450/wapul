# %% [markdown]
# # Statement kinds: literal contents left out of the tokens
#
# String and character literals hold text that differs from problem to problem (messages,
# expected words). Here the tokens see `""` in place of each literal, so the features keep the
# fact that a literal is there but not its contents. Features from at least MIN_SOURCES
# repositories, as segmenter-v3; same 5 folds.
#
#     python notebooks/kinds_literals.py

# %%
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import KFold

from wapul_ml.data.solutions import load_solutions
from wapul_ml.features.kind_features import common_features, source_of, unit_features, with_ngrams
from wapul_ml.models import kind_lgbm
from wapul_ml.models.segmenter import MIN_SOURCES

sols = load_solutions()
kinds = [[u.kind for u in s.units] for s in sols]
sources = [source_of(s.id) for s in sols]
folds = list(KFold(5, shuffle=True, random_state=0).split(sols))
for mask in (False, True):
    feats = [with_ngrams(unit_features(s, mask_literals=mask)) for s in sols]
    y_true, y_pred = [], []
    for train_ids, test_ids in folds:
        keep = common_features([feats[i] for i in train_ids], [sources[i] for i in train_ids], MIN_SOURCES)
        model = kind_lgbm.train(
            [f for i in train_ids for f in feats[i]], [k for i in train_ids for k in kinds[i]], keep=keep
        )
        y_pred += model.predict([f for i in test_ids for f in feats[i]])
        y_true += [k for i in test_ids for k in kinds[i]]
    print(f"literals {'masked' if mask else 'kept'}: macro-F1 {f1_score(y_true, y_pred, average='macro'):.3f}")
    print(classification_report(y_true, y_pred, digits=3))
