"""Review page: the block model's labels on unlabeled corpus solutions, as one HTML file."""

import html
import json

import numpy as np

from wapul_ml.data.solutions import Solution
from wapul_ml.models.segmenter import LANGS, BlockModel
from wapul_ml.paths import CACHE, DATA

REVIEW = CACHE / "review.html"


def unlabeled_sample(n: int) -> list[dict]:
    labeled = {json.loads(line)["id"] for line in open(DATA / "labels" / "labels.jsonl", encoding="utf-8")}
    rows = []
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl")):
        for line in open(part, encoding="utf-8"):
            r = json.loads(line)
            if r["language"] in LANGS and r["id"] not in labeled:
                rows.append(r)
    pick = np.random.default_rng(0).choice(len(rows), n, replace=False)
    return [rows[i] for i in pick]


# Logic blocks cycle through these; other kinds get muted tints
PALETTE = ["#f4a261", "#2a9d8f", "#e76f51", "#8ab17d", "#b56576", "#4d96ff", "#e9c46a", "#9b5de5", "#00bbf9", "#f15bb5"]
KIND_STYLE = {"input": "background:#dbeafe", "output": "background:#dcfce7", "none": "color:#9ca3af"}


def render(sol: Solution, meta: dict) -> str:
    lines = sol.code.split("\n")
    starts = np.cumsum([0] + [len(x) + 1 for x in lines])
    spans = sorted((starts[u.line - 1] + u.col, starts[u.end[0] - 1] + u.end[1], u) for u in sol.units)
    out, at = [], 0
    for a, b, u in spans:
        out.append(html.escape(sol.code[at:a]))
        if u.kind == "logic":
            color = PALETTE[(u.block - 1) % len(PALETTE)]
            style = f"background:{color}40;border-bottom:2px solid {color}"
            tag = f'<sup style="color:{color}">{u.block}</sup>'
        else:
            style, tag = KIND_STYLE[u.kind], f"<sup>{u.kind[0]}</sup>"
        out.append(f'<span style="{style}" title="{u.kind} {u.block or ""}">{tag}{html.escape(sol.code[a:b])}</span>')
        at = b
    out.append(html.escape(sol.code[at:]))
    n_blocks = len({u.block for u in sol.units if u.kind == "logic"})
    title = f"{html.escape(meta['id'])} · {sol.language} · problem {meta.get('problem_id')} · {n_blocks} logic blocks"
    return f"<section><h2>{title}</h2><pre>{''.join(out)}</pre></section>"


def review(n: int) -> None:
    model = BlockModel()
    sections = []
    for k, r in enumerate(unlabeled_sample(n), 1):
        sections.append(render(model.solution(r["code"], r["language"], r["id"]), r))
        print(f"  {k}/{n} {r['id']}", flush=True)
    legend = (
        "<p>logic blocks: colored, numbered <sup>1</sup>, <sup>2</sup>, …; "
        f'<span style="{KIND_STYLE["input"]}"><sup>i</sup>input</span> '
        f'<span style="{KIND_STYLE["output"]}"><sup>o</sup>output</span> '
        f'<span style="{KIND_STYLE["none"]}"><sup>n</sup>none</span></p>'
    )
    page = (
        '<!doctype html><meta charset="utf-8"><title>Block review</title><style>'
        "body{font-family:system-ui;margin:24px;background:#fff;color:#111}"
        "pre{font:13px/1.6 ui-monospace,Consolas,monospace;background:#fafafa;padding:12px;border:1px solid #eee;"
        "overflow-x:auto}h2{font-size:15px;margin-top:32px}sup{font-size:9px;margin-right:1px}</style>"
        f"<h1>Model blocks on {n} unlabeled solutions</h1>{legend}{''.join(sections)}"
    )
    REVIEW.write_text(page, encoding="utf-8")
    print(f"wrote {REVIEW}")
