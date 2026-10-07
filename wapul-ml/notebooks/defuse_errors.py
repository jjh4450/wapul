# %% [markdown]
# # Error analysis: do name-only data-flow links cause block errors?
#
# The data-flow features (`segment_features`) compare variable names, so `i` reused by two loops
# counts as one variable. This notebook builds a unit-level def-use link instead (the most recent
# definition that reaches a use, as in reaching definitions over structured code) and checks,
# before changing any feature:
#
# 1. how often name links and def-use links disagree, and how often each kind joins units of one block
# 2. whether the model's out-of-fold errors (blocks-ensemble, seed 0) sit on the links def-use would drop
#
#     python notebooks/defuse_errors.py

# %%
from collections import Counter
from itertools import combinations

import numpy as np
from sklearn.model_selection import KFold
from tree_sitter import Node

from wapul_ml.data.solutions import load_solutions
from wapul_ml.features.candidates import BlockCandidates
from wapul_ml.features.unit_ast import _CATEGORY_BY_TYPE, CONTROL, DEFS, LOOPS, _byte_offsets, analyze
from wapul_ml.models.block_ranker import predict_blocks, train_ensemble
from wapul_ml.units import parser, units

# %% [markdown]
# ## Def-use events per unit
#
# Each unit becomes an ordered list of (op, name): `use`, `def` (the whole variable is replaced, so
# earlier definitions die) or `part` (an element, field or method call on it: read and extended,
# earlier definitions live on). Right-hand sides come before the target, as they are evaluated.
# Callee names, attribute and field names, and names bound inside a comprehension or lambda are skipped.

# %%
ASSIGN = {"assignment_expression", "assignment"}
DECLARATORS = {"init_declarator", "variable_declarator"}
SUBSCRIPT = {"subscript_expression", "subscript", "array_access"}
FIELD = {"field_expression", "attribute", "field_access"}
CALLS = {"call_expression", "call", "method_invocation"}
SCOPED = {"list_comprehension", "set_comprehension", "dictionary_comprehension", "generator_expression", "lambda"}
PARAMS = {
    "parameter_declaration",
    "optional_parameter_declaration",
    "formal_parameter",
    "default_parameter",
    "typed_parameter",
    "typed_default_parameter",
}


def _name(node: Node | None) -> str | None:
    while node is not None and node.type != "identifier":
        node = node.named_children[0] if node.named_children else None
    return node.text.decode() if node is not None else None


class Events:
    def __init__(self, start: int, end: int):
        self.start, self.end, self.out, self.skip = start, end, [], set()

    def inside(self, n: Node) -> bool:
        return n.end_byte > self.start and n.start_byte < self.end

    def add(self, op: str, name: str | None) -> None:
        if name is not None and name not in self.skip:
            self.out.append((op, name))

    def part(self, n: Node) -> None:
        """An element or field of a variable is written: the base is read and extended."""
        if not self.inside(n):
            return
        if n.type == "identifier":
            self.add("use", n.text.decode())
            self.add("part", n.text.decode())
        elif n.type in SUBSCRIPT and n.named_children:
            self.part(n.named_children[0])
            for c in n.named_children[1:]:
                self.visit(c)
        elif n.type in FIELD and n.named_children:
            self.part(n.named_children[0])
        elif n.type in ("pointer_expression", "parenthesized_expression") and n.named_children:
            self.part(n.named_children[-1])
        else:
            self.visit(n)

    def define(self, n: Node | None) -> None:
        if n is None or not self.inside(n):
            return
        if n.type == "identifier":
            self.add("def", n.text.decode())
        elif n.type in (
            "pattern_list",
            "tuple_pattern",
            "tuple",
            "list_pattern",
            "list",
            "structured_binding_declarator",
        ):
            for c in n.named_children:
                self.define(c)
        elif n.type in ("list_splat_pattern", "reference_declarator", "pointer_declarator", "parenthesized_expression"):
            self.define(n.named_children[-1] if n.named_children else None)
        elif n.type == "array_declarator":
            self.define(n.child_by_field_name("declarator"))
            if (size := n.child_by_field_name("size")) is not None:
                self.visit(size)
        else:
            self.part(n)

    def visit(self, n: Node) -> None:
        if not self.inside(n):
            return
        t, f = n.type, n.child_by_field_name
        if t == "identifier":
            self.add("use", n.text.decode())
        elif t in ASSIGN:
            op = f("operator")
            if op is not None and op.text != b"=":  # C++/Java compound assignment
                self.visit(f("right"))
                self._update(f("left"))
            else:
                self.visit(f("right"))
                self.define(f("left"))
        elif t == "augmented_assignment":
            self.visit(f("right"))
            self._update(f("left"))
        elif t == "update_expression":
            self._update(f("argument") or (n.named_children[0] if n.named_children else None))
        elif t in DECLARATORS:
            if (v := f("value")) is not None:
                self.visit(v)
            self.define(f("declarator") or f("name"))
        elif t == "declaration" or t == "local_variable_declaration" or t == "field_declaration":
            for c in n.named_children:
                if c.type in DECLARATORS or c.type == "array_declarator":
                    self.visit(c) if c.type in DECLARATORS else self.define(c)
                elif c.type == "identifier" and c == f("declarator"):
                    self.define(c)
                elif c.type in ("identifier", "array_declarator", "pointer_declarator", "reference_declarator"):
                    self.define(c)
        elif t in PARAMS:
            self.define(f("declarator") or f("name") or (n.named_children[0] if n.named_children else None))
            if (v := f("value") or f("default_value")) is not None:
                self.visit(v)
        elif t == "parameters" or t == "lambda_parameters":
            for c in n.named_children:
                self.define(c) if c.type == "identifier" else self.visit(c)
        elif t == "for_range_loop":
            self.visit(f("right"))
            self.define(f("declarator"))
        elif t == "enhanced_for_statement":
            self.visit(f("value"))
            self.define(f("name"))
        elif t == "for_statement" and f("left") is not None:  # Python `for x in`
            self.visit(f("right"))
            self.define(f("left"))
        elif t in CALLS:
            fn = f("function")
            if t == "method_invocation":
                if (obj := f("object")) is not None:
                    self.part(obj)
            elif fn is not None and fn.type in FIELD and fn.named_children:
                self.part(fn.named_children[0])  # v.push_back(x), a.append(x), adj[u].append(v)
            elif fn is not None and fn.type not in ("identifier", "qualified_identifier", "template_function"):
                self.visit(fn)
            if (a := f("arguments")) is not None:
                self.visit(a)
        elif t in FIELD and n.named_children:
            self.visit(n.named_children[0])
        elif t == "keyword_argument":
            self.visit(f("value"))
        elif t == "function_declarator":
            self.visit(f("parameters"))
        elif t in ("function_definition", "method_declaration", "constructor_declaration"):
            for c in n.named_children:
                if c.type in ("parameters", "formal_parameters", "function_declarator"):
                    self.visit(c)
        elif (
            t == "binary_expression"
            and f("operator") is not None
            and f("operator").text == b">>"
            and self._reads_input(n)
        ):
            self._shift(n)
        elif t == "pointer_expression" and n.text.startswith(b"&"):  # scanf("%d", &n)
            self.define(f("argument"))
        elif t in SCOPED:
            bound = {_name(c.child_by_field_name("left")) for c in n.named_children if c.type == "for_in_clause"}
            if t == "lambda" and (p := f("parameters")) is not None:
                bound |= {c.text.decode() for c in p.named_children if c.type == "identifier"}
            before, self.skip = self.skip, self.skip | {b for b in bound if b}
            for c in n.children:
                self.visit(c)
            self.skip = before
        elif t in ("global_statement", "nonlocal_statement", "import_statement", "import_from_statement"):
            pass
        else:
            for c in n.children:
                self.visit(c)

    def _update(self, n: Node | None) -> None:
        if n is None:
            return
        if n.type == "identifier":
            self.add("use", n.text.decode())
            self.add("def", n.text.decode())
        else:
            self.part(n)

    def _reads_input(self, n: Node) -> bool:
        while n.type == "binary_expression":
            n = n.child_by_field_name("left")
        return n.text in (b"cin", b"std::cin")

    def _shift(self, n: Node) -> None:
        left = n.child_by_field_name("left")
        if left.type == "binary_expression":
            self._shift(left)
        self.define(n.child_by_field_name("right"))


def unit_events(code: str, language: str, spans) -> list[dict]:
    """Per unit: def-use sets, and the enclosing controls, loops and function as start bytes."""
    data = code.encode()
    root = parser(language).parse(data).root_node
    offset = _byte_offsets(code, data)
    out = []
    for (l1, c1), (l2, c2) in spans:
        s, e = offset(l1, c1), offset(l2, c2)
        node = root.descendant_for_byte_range(s, e)
        while node.type not in _CATEGORY_BY_TYPE and node.parent is not None and node.parent.start_byte == s:
            node = node.parent
        ev = Events(s, e)
        ev.visit(node)
        exposed, defined, killed, gen = set(), set(), set(), set()
        for op, name in ev.out:
            if op == "use" and name not in defined:
                exposed.add(name)
            elif op in ("def", "part"):
                gen.add(name)
                if op == "def":
                    defined.add(name)
                    killed.add(name)
        controls, loops, function = [], set(), -1
        if node.type in LOOPS:
            loops.add(node.start_byte)  # a loop header runs every iteration
        anc = node.parent
        while anc is not None:
            if anc.type in CONTROL:
                controls.append(anc.start_byte)
                if anc.type in LOOPS:
                    loops.add(anc.start_byte)
            if function < 0 and anc.type in DEFS:
                function = anc.start_byte
            anc = anc.parent
        out.append(
            dict(
                exposed=exposed,
                killed=killed,
                gen=gen,
                controls=set(controls),
                loops=loops,
                function=function,
                events=ev.out,
            )
        )
    return out


def def_use(ev: list[dict], x: int, y: int) -> tuple[set[str], set[str]]:
    """Names whose definition in unit x reaches a use in later unit y; and names killed on the way.

    A unit k between them kills a name when it replaces it and runs on every path to y: in
    structured code, when every control statement around k also surrounds y."""
    a, b = ev[x], ev[y]
    if a["function"] >= 0 and a["function"] != b["function"]:
        return set(), set()
    names = a["gen"] & b["exposed"]
    dead = set()
    for k in range(x + 1, y):
        c = ev[k]
        if c["function"] == b["function"] and c["controls"] <= b["controls"]:
            dead |= names & c["killed"]
    return names - dead, dead


def loop_back(ev: list[dict], x: int, y: int) -> set[str]:
    """Names y (later) defines that x (earlier) reads in a later iteration of a loop around both."""
    a, b = ev[x], ev[y]
    return (b["gen"] & a["exposed"]) if a["loops"] & b["loops"] else set()


# %% [markdown]
# ## Checks on small programs

# %%
CHECKS = [
    (
        "cpp",
        "int main(){\nint n; cin >> n;\nfor (int i = 0; i < n; i++) a[i] = i;\nfor (int i = 0; i < n; i++) s += a[i];\n}",
        (4, 6),
        {"a"},
    ),
    ("cpp", "int main(){\nint i;\nfor (i = 0; i < n; i++) x += i;\nfor (i = 0; i < n; i++) y += i;\n}", (2, 3), {"i"}),
    ("cpp", "int main(){\nint i;\nfor (i = 0; i < n; i++) x += i;\nfor (i = 0; i < n; i++) y += i;\n}", (2, 5), set()),
    ("cpp", "int main(){\nint s = 0;\nfor (int i = 0; i < n; i++) s += v[i];\ncout << s;\n}", (1, 3), {"s"}),
    ("cpp", "int main(){\nint s = 0;\nfor (int i = 0; i < n; i++) s += v[i];\ncout << s;\n}", (3, 4), {"s"}),
    ("python", "for i in range(n):\n    a.append(i)\nfor i in range(m):\n    b.append(i)\nprint(a)\n", (0, 3), set()),
    ("python", "for i in range(n):\n    a.append(i)\nfor i in range(m):\n    b.append(i)\nprint(a)\n", (1, 4), {"a"}),
    ("python", "dist = [0] * n\nq = deque([s])\nwhile q:\n    u = q.popleft()\n    dist[u] += 1\n", (0, 4), {"dist"}),
    (
        "java",
        "class M { void f() {\nint n = sc.nextInt();\nfor (int i = 0; i < n; i++) { sum += i; }\nfor (int i = 0; i < n; i++) { cnt += i; }\n} }",
        (3, 6),
        set(),
    ),
    (
        "java",
        "class M { void f() {\nint n = sc.nextInt();\nfor (int i = 0; i < n; i++) { sum += i; }\nfor (int i = 0; i < n; i++) { cnt += i; }\n} }",
        (2, 5),
        {"n"},
    ),
]
for lang, code, (x, y), want in CHECKS:
    us = units(code, lang)
    ev = unit_events(code, lang, [(u.start, u.end) for u in us])
    got = def_use(ev, x, y)[0]
    print("ok " if got == want else "BAD", lang, repr(us[x].text), "->", repr(us[y].text), got)

# %% [markdown]
# ## Name links against def-use links, on the labeled logic pairs
#
# A pair (x before y) has a name link when the current features fire (x writes what y reads, y
# writes what x reads, or both write one name), and a def-use link when x's definition reaches a
# use in y or, inside a shared loop, y's reaches x. Name-only links whose names are redefined in
# between are the reused `i`, `j` case.

# %%
sols = load_solutions()
rows = []  # one per logic pair
for s in sols:
    spans = [((u.line, u.col), u.end) for u in s.units]
    asts, ev = analyze(s.code, s.language, spans), unit_events(s.code, s.language, spans)
    logic = [i for i, u in enumerate(s.units) if u.kind == "logic"]
    for (a, x), (b, y) in combinations(enumerate(logic), 2):
        p, q = asts[x], asts[y]
        name = (p.writes & q.reads) | (q.writes & p.reads) | (p.writes & q.writes)
        fwd, dead = def_use(ev, x, y)
        du = fwd | loop_back(ev, x, y)
        if name and du:
            link = "both"
        elif name:
            link = "name only: redefined" if name & dead else "name only: other"
        else:
            link = "def-use only" if du else "none"
        rows.append(
            dict(
                sol=s.id,
                lang=s.language,
                a=a,
                b=b,
                same=s.units[x].block == s.units[y].block,
                link=link,
                redefined=name & dead,
            )
        )
print(f"{len(sols)} solutions, {len(rows)} logic pairs")


def table(rows, key="link"):
    by = {}
    for r in rows:
        by.setdefault(r[key], []).append(r)
    for k in sorted(by):
        g = by[k]
        print(
            f"  {k:24s} pairs {len(g):6d}  same-block {np.mean([r['same'] for r in g]):.3f}  solutions {len({r['sol'] for r in g}):3d}"
        )


table(rows)
print("names redefined in between:", Counter(n for r in rows for n in r["redefined"]).most_common(12))
for lang in ("cpp", "java", "python"):
    print(lang)
    table([r for r in rows if r["lang"] == lang])

# %% [markdown]
# ## Where the model's errors fall
#
# Out-of-fold block predictions (blocks-ensemble, seed 0, the folds of `blocks_cv.py`). A pair is
# wrongly merged when predicted in one block but gold in two, wrongly split the other way round.

# %%
data = [BlockCandidates(s) for s in sols]
pred = [None] * len(sols)
for fold, (train_ids, test_ids) in enumerate(KFold(5, shuffle=True, random_state=0).split(sols)):
    score = train_ensemble([data[i] for i in train_ids], seed=fold)
    for i in test_ids:
        pred[i] = predict_blocks(score, data[i]) if len(data[i]) else []
pred_of = {s.id: p for s, p in zip(sols, pred, strict=True)}
for r in rows:
    p = pred_of[r["sol"]]
    same_pred = p[r["a"]] == p[r["b"]]
    r["outcome"] = (
        "wrongly merged"
        if same_pred and not r["same"]
        else "wrongly split"
        if r["same"] and not same_pred
        else "correct"
    )

print("pairs by outcome:", Counter(r["outcome"] for r in rows))
for outcome in ("wrongly merged", "wrongly split", "correct"):
    g = [r for r in rows if r["outcome"] == outcome]
    c = Counter(r["link"] for r in g)
    print(outcome, "  " + "  ".join(f"{k} {c[k] / len(g):.3f}" for k in sorted(c)))
merged_redef = [r for r in rows if r["outcome"] == "wrongly merged" and r["link"] == "name only: redefined"]
print(
    f"wrongly merged on a redefined name only: {len(merged_redef)} pairs in {len({r['sol'] for r in merged_redef})} solutions"
)
