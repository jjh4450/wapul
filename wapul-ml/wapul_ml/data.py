"""Labeled solutions: code from the corpus, statement units and labels from labels.jsonl."""

import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
KINDS = ("input", "output", "logic", "none")
K = 3  # context units on each side of the target


def context_text(units, i: int) -> str:
    """The unit with K units of context on each side, as in CodeSeg's line-by-line setup."""
    prev = "\n".join(u.text for u in units[max(0, i - K) : i])
    nxt = "\n".join(u.text for u in units[i + 1 : i + 1 + K])
    return f"<previous_context>{prev}</previous_context><target>{units[i].text}</target><next_context>{nxt}</next_context>"


@dataclass
class Unit:
    text: str
    line: int  # 1-based
    col: int  # 0-based, in characters; doubles as indentation
    end: tuple[int, int]  # (line, col), exclusive
    kind: str
    block: int | None  # logic block number from 1, None for other kinds


@dataclass
class Solution:
    id: str
    language: str
    source: str  # "human" (reviewed) or "auto" (LLM draft as-is)
    code: str  # normalized, as in the corpus
    units: list[Unit]


def _slice(lines: list[str], start: list[int], end: list[int]) -> str:
    (l1, c1), (l2, c2) = start, end
    if l1 == l2:
        return lines[l1 - 1][c1:c2]
    return "\n".join([lines[l1 - 1][c1:], *lines[l1 : l2 - 1], lines[l2 - 1][:c2]])


def load_solutions() -> list[Solution]:
    labels = [json.loads(line) for line in open(DATA / "labels" / "labels.jsonl", encoding="utf-8")]
    wanted = {r["id"] for r in labels}
    code = {}
    for part in sorted((DATA / "processed" / "corpus").glob("part-*.jsonl")):
        for line in open(part, encoding="utf-8"):
            row = json.loads(line)
            if row["id"] in wanted:
                code[row["id"]] = row["code"]
    out = []
    for r in labels:
        lines = code[r["id"]].split("\n")
        units = [
            Unit(
                _slice(lines, u["start"], u["end"]),
                u["start"][0],
                u["start"][1],
                tuple(u["end"]),
                u["kind"],
                u.get("block"),
            )
            for u in r["units"]
        ]
        out.append(Solution(r["id"], r["language"], r["source"], code[r["id"]], units))
    return out
