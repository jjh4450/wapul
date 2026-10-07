"""Expected outputs of wapul-ml's Python model for the TS parity tests: per solution, what each
stage computes, so a TS stage can be checked on its own (docs/ml/deploy.ko.md, "검증"). Run in
the wapul-ml image with the monorepo mounted at /wapul:

    docker run --rm -v "$(pwd):/wapul" -e PYTHONPATH=/wapul/wapul-ml wapul-ml \\
        python /wapul/wapul-seg/js/tests/make_cases.py [--corpus N]

Without --corpus: the public snippets in cases/ -> cases.json next to this file (committed; the
tests read it). With --corpus N: N random corpus solutions (private data) ->
wapul-ml/cache/seg-parity/cases.json, which the tests read when WAPUL_SEG_CASES points at it.
"""

import json
import sys
from pathlib import Path

import numpy as np
from wapul_ml.data.solutions import Solution, Unit
from wapul_ml.features.candidates import BlockCandidates, Units
from wapul_ml.features.kind_features import unit_features, with_ngrams
from wapul_ml.features.unit_ast import analyze
from wapul_ml.models import block_ranker
from wapul_ml.models.segmenter import LANGS, BlockModel
from wapul_ml.normalize import normalize
from wapul_ml.paths import CACHE, DATA
from wapul_ml.units import units

HERE = Path(__file__).resolve().parent
LANGUAGE = {".cpp": "cpp", ".py": "python", ".java": "java", ".rs": "rust"}


def case(model: BlockModel, sid: str, code: str, language: str) -> dict:
    code = normalize(code)
    sol = Solution(sid, language, "model", code, [])
    sol.units = [Unit(u.text, u.start[0], u.start[1], u.end, "none", None) for u in units(code, language)]
    asts = analyze(code, language, [((u.line, u.col), u.end) for u in sol.units])
    feats = with_ngrams(unit_features(sol, mask_literals=True))
    for u, kind in zip(sol.units, model.kinds.predict(feats), strict=True):
        u.kind = kind
    logic = Units(sol)
    blocks = block_ranker.predict_blocks(model.blocks, BlockCandidates(sol, labeled=False))
    for u, b in zip([u for u in sol.units if u.kind == "logic"], blocks, strict=True):
        u.block = b + 1
    return {
        "id": sid,
        "language": language,
        "code": code,
        "units": [{"start": [u.line, u.col], "end": list(u.end), "text": u.text} for u in sol.units],
        "asts": [
            {
                "category": a.category,
                "node_type": a.node_type,
                "is_header": a.is_header,
                "depth": a.depth,
                "reads": sorted(a.reads),
                "writes": sorted(a.writes),
            }
            for a in asts
        ],
        # Sorted so the file is the same on every run: Python's set order varies
        "features": [dict(sorted(f.items())) for f in feats],
        "kinds": [u.kind for u in sol.units],
        "own": [[float(x) for x in o] for o in logic.own],
        "pairs": [p.reshape(-1).tolist() for p in logic.pairs],
        "blocks": [u.block for u in sol.units],
    }


def corpus_sample(n: int) -> list[tuple[str, str, str]]:
    rows = [
        r
        for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl"))
        for line in open(part, encoding="utf-8")
        if (r := json.loads(line))["language"] in LANGS
    ]
    pick = np.random.default_rng(0).choice(len(rows), n, replace=False)
    return [(rows[i]["id"], rows[i]["code"], rows[i]["language"]) for i in pick]


def main() -> None:
    model = BlockModel()
    if "--corpus" in sys.argv:
        todo = corpus_sample(int(sys.argv[sys.argv.index("--corpus") + 1]))
        out = CACHE / "seg-parity" / "cases.json"
    else:
        paths = sorted((HERE / "cases").iterdir())
        todo = [(p.name, p.read_text(encoding="utf-8"), LANGUAGE[p.suffix]) for p in paths]
        out = HERE / "cases.json"
    cases = [case(model, *t) for t in todo]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(cases, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(cases)} cases, {sum(len(c['units']) for c in cases)} units -> {out}")


if __name__ == "__main__":
    main()
