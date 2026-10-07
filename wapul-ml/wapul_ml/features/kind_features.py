"""String features for the statement-kind classifier, rebuildable outside Python.

Each unit becomes a dict of features from a regex tokenizer and the tree-sitter facts in
unit_ast, so a browser can compute the same dict with web-tree-sitter. Tokens are prefixed by
where they come from:
- `t:` the unit's tokens and token bigrams; `p1:`..`p3:` / `n1:`..`n3:` the neighbours' tokens
- `b:` for a header, its body's tokens (a loop that only reads input is input)
- `c:` the innermost enclosing loop or branch header, `f:` the enclosing function header
- AST: category, node type, header, depth, relative position, first/last unit of the function
"""

import re

from wapul_ml.data.solutions import Solution
from wapul_ml.features.unit_ast import _byte_offsets, analyze
from wapul_ml.units import parser

TOKEN = re.compile(r"[A-Za-z_]\w*|\d+|\S")
MAX_TOKENS = 64  # a long body says enough in its first tokens
K = 3  # neighbours on each side


def tokens(text: str) -> list[str]:
    return ["NUM" if t.isdigit() else t for t in TOKEN.findall(text)[:MAX_TOKENS]]


# String and character literals, outermost, across the supported grammars (segmenter-v3 and
# later): their contents differ from problem to problem, so tokens see `""` in their place
LITERALS = {
    "string_literal",
    "raw_string_literal",
    "char_literal",
    "character_literal",
    "multiline_string_literal",
    "string",
    "template_string",
    "interpreted_string_literal",
    "rune_literal",
    "interpolated_string_expression",
    "verbatim_string_literal",
    "line_string_literal",
    "multi_line_string_literal",
    "heredoc_body",
    "encapsed_string",
    "heredoc",
    "nowdoc",
}


def literal_spans(code: str, language: str) -> list[tuple[int, int]]:
    """Byte ranges of the outermost literals, in order."""
    out, stack = [], [parser(language).parse(code.encode()).root_node]
    while stack:
        node = stack.pop()
        # Named only: some grammars spell a type keyword like a literal (C#'s `string`)
        if node.is_named and node.type in LITERALS:
            out.append((node.start_byte, node.end_byte))
        else:
            stack.extend(node.children)
    return sorted(out)


def masked(data: bytes, start: int, end: int, literals: list[tuple[int, int]]) -> str:
    """`data[start:end]` with each literal (or the part of it inside) replaced by `""`."""
    parts, at = [], start
    for s, e in literals:
        if e <= start or s >= end:
            continue
        s, e = max(s, start), min(e, end)
        parts += [data[at:s], b'""']
        at = e
    parts.append(data[at:end])
    return b"".join(parts).decode(errors="replace")


def unit_features(s: Solution, mask_literals: bool = False) -> list[dict[str, float]]:
    """`mask_literals`: tokens see `""` in place of each literal (segmenter-v3 and later)."""
    asts = analyze(s.code, s.language, [((u.line, u.col), u.end) for u in s.units])
    data = s.code.encode()
    offset = _byte_offsets(s.code, data)
    header_at = {a.span[0]: j for j, a in enumerate(asts) if a.is_header}
    literals = literal_spans(s.code, s.language) if mask_literals else []
    toks = [tokens(masked(data, offset(u.line, u.col), offset(*u.end), literals)) for u in s.units]
    n = len(s.units)
    out = []
    for j, (u, a) in enumerate(zip(s.units, asts, strict=True)):
        f = {"lang=" + s.language: 1.0, "cat=" + a.category: 1.0, "node=" + a.node_type: 1.0}
        f["header"] = float(a.is_header)
        f["depth"] = min(a.depth, 5) / 5
        f["pos"] = j / max(n - 1, 1)
        for t in set(toks[j]):
            f["t:" + t] = 1.0
        for x, y in zip(toks[j], toks[j][1:], strict=False):
            f[f"t:{x} {y}"] = 1.0
        for k in range(1, K + 1):
            for side, i in (("p", j - k), ("n", j + k)):
                if 0 <= i < n:
                    for t in set(toks[i]):
                        f[f"{side}{k}:{t}"] = 1.0
                else:
                    f[f"{side}{k}:EDGE"] = 1.0
        if a.is_header:
            body = masked(data, offset(*u.end), a.span[1], literals)
            for t in set(tokens(body)):
                f["b:" + t] = 1.0
        for prefix, at in (("c", a.control), ("f", a.function)):
            if at >= 0 and at in header_at and header_at[at] != j:
                for t in set(toks[header_at[at]]):
                    f[f"{prefix}:{t}"] = 1.0
        same_fn = [i for i in range(n) if asts[i].function == a.function and not asts[i].is_header or i == j]
        f["fn_first"] = float(j == same_fn[0])
        f["fn_last"] = float(j == same_fn[-1])
        f["in_function"] = float(a.function >= 0)
        out.append(f)
    return out


IDENT = re.compile(r"[A-Za-z_]\w*")
NGRAMS = (3, 4)


def char_ngrams(token: str) -> set[str]:
    t = token.lower()
    return {t[i : i + n] for n in NGRAMS for i in range(len(t) - n + 1)}


def with_ngrams(feats: list[dict[str, float]]) -> list[dict[str, float]]:
    """Each identifier feature `prefix:tok` also gives `prefix#gram` for its character 3- and
    4-grams, so input/output idioms of an unseen language (`read_line`, `writeln!`) share pieces
    with known ones (`readLine`, `bw.write`). segmenter-v3 and later."""
    out = []
    for f in feats:
        g = dict(f)
        for name in f:
            prefix, sep, tok = name.partition(":")
            if sep and IDENT.fullmatch(tok):
                for c in char_ngrams(tok):
                    g[f"{prefix}#{c}"] = 1.0
        out.append(g)
    return out


def source_of(solution_id: str) -> str:
    """The repository a solution came from, from its id."""
    return "/".join(solution_id.split("/")[:3])


def common_features(feats: list[list[dict[str, float]]], sources: list[str], min_sources: int) -> set[str]:
    """Feature names that solutions from at least `min_sources` distinct sources contain, given
    each solution's unit features. A feature only one repository has does not carry over to
    other code (segmenter-v3 and later)."""
    seen: dict[str, set[str]] = {}
    for sol_feats, source in zip(feats, sources, strict=True):
        for name in {n for f in sol_feats for n in f}:
            seen.setdefault(name, set()).add(source)
    return {n for n, s in seen.items() if len(s) >= min_sources}
