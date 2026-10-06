"""Per-unit AST facts from tree-sitter, for kind features and the SEGMENT block rules.

SEGMENT (Wang, Pollock & Vijay-Shanker 2011) finds "meaningful blocks" of three types,
strongest first: data-flow chains (a statement reads what an earlier one wrote),
control blocks (statements under the same if/for/while), and runs of the same
syntactic category. The facts here let the pair classifier test each of these.
"""

from dataclasses import dataclass

from tree_sitter import Node

from wapul_ml.units import parser

# Coarse statement categories shared across C++, Java and Python node types
CATEGORIES = ("import", "def", "loop", "branch", "return", "jump", "declaration", "expression", "other")
_CATEGORY_BY_TYPE = {
    "preproc_include": "import", "using_declaration": "import", "import_statement": "import",
    "import_from_statement": "import", "import_declaration": "import", "package_declaration": "import",
    "preproc_def": "import", "alias_declaration": "import", "type_definition": "import",
    "function_definition": "def", "method_declaration": "def", "constructor_declaration": "def",
    "class_definition": "def", "class_declaration": "def", "class_specifier": "def", "struct_specifier": "def",
    "for_statement": "loop", "for_range_loop": "loop", "while_statement": "loop", "do_statement": "loop",
    "enhanced_for_statement": "loop",
    "if_statement": "branch", "else_clause": "branch", "elif_clause": "branch", "switch_statement": "branch",
    "case_statement": "branch", "switch_block_statement_group": "branch", "switch_rule": "branch",
    "try_statement": "branch", "catch_clause": "branch", "except_clause": "branch",
    "return_statement": "return",
    "break_statement": "jump", "continue_statement": "jump",
    "declaration": "declaration", "local_variable_declaration": "declaration", "field_declaration": "declaration",
    "expression_statement": "expression",
}
LOOPS = {t for t, c in _CATEGORY_BY_TYPE.items() if c == "loop"}
DEFS = {t for t, c in _CATEGORY_BY_TYPE.items() if c == "def"}
CONTROL = LOOPS | {t for t, c in _CATEGORY_BY_TYPE.items() if c == "branch"}


@dataclass
class UnitAst:
    category: str
    node_type: str
    is_header: bool  # header of a compound statement whose body holds other units
    depth: int  # enclosing loops and branches
    reads: set[str]  # every identifier in the unit
    writes: set[str]  # identifiers assigned, declared, read into, or incremented
    span: tuple[int, int]  # owner node bytes: for a header, the whole compound statement
    loop: int  # start byte of the innermost enclosing loop, -1 if none
    control: int  # start byte of the innermost enclosing loop or branch, -1 if none
    function: int  # start byte of the enclosing definition, -1 if none
    parent: int  # start byte of the parent node: siblings share it


def _byte_offsets(code: str, data: bytes):
    lines = code.split("\n")
    starts, at = [], 0
    for line in lines:
        starts.append(at)
        at += len(line.encode()) + 1

    def offset(line: int, col: int) -> int:
        return starts[line - 1] + len(lines[line - 1][:col].encode())

    return offset


def _identifiers(node: Node, start: int, end: int, out: set[str]) -> None:
    if node.end_byte <= start or node.start_byte >= end:
        return
    if node.type == "identifier":
        out.add(node.text.decode())
        return
    for child in node.children:
        _identifiers(child, start, end, out)


def _target_name(node: Node | None) -> str | None:
    """`a`, `a[i]`, `a.b`, `*a` -> "a"."""
    while node is not None and node.type != "identifier":
        node = node.named_children[0] if node.named_children else None
    return node.text.decode() if node is not None else None


def _writes(node: Node, start: int, end: int, out: set[str]) -> None:
    if node.end_byte <= start or node.start_byte >= end:
        return
    t = node.type
    target = None
    if t in ("assignment_expression", "assignment", "augmented_assignment"):
        target = node.child_by_field_name("left")
    elif t in ("init_declarator", "variable_declarator"):
        target = node.child_by_field_name("declarator") or node.child_by_field_name("name")
    elif t == "update_expression":
        target = node.child_by_field_name("argument") or (node.named_children[0] if node.named_children else None)
    elif t in ("for_range_loop",):
        target = node.child_by_field_name("declarator")
    elif t == "for_statement" and node.child_by_field_name("left") is not None:  # Python `for x in`
        target = node.child_by_field_name("left")
    elif t == "binary_expression" and node.child_by_field_name("operator") is not None:
        if node.child_by_field_name("operator").text == b">>":  # cin >> a >> b
            target = node.child_by_field_name("right")
    elif t == "pointer_expression" and node.text.startswith(b"&"):  # scanf("%d", &n)
        target = node.child_by_field_name("argument")
    if target is not None:
        if target.type in ("pattern_list", "tuple_pattern", "tuple", "list_pattern"):
            for part in target.named_children:
                if (name := _target_name(part)) is not None:
                    out.add(name)
        elif (name := _target_name(target)) is not None:
            out.add(name)
    for child in node.children:
        _writes(child, start, end, out)


def analyze(code: str, language: str, spans: list[tuple[tuple[int, int], tuple[int, int]]]) -> list[UnitAst]:
    """AST facts for each unit, given its ((line, col), (line, col)) span from `units()`."""
    data = code.encode()
    root = parser(language).parse(data).root_node
    offset = _byte_offsets(code, data)
    out = []
    for (l1, c1), (l2, c2) in spans:
        s, e = offset(l1, c1), offset(l2, c2)
        # The owner is the smallest node covering the unit, raised to a statement that starts
        # where the unit starts (a header's owner is its whole compound statement)
        node = root.descendant_for_byte_range(s, e)
        while node.type not in _CATEGORY_BY_TYPE and node.parent is not None and node.parent.start_byte == s:
            node = node.parent
        reads, writes = set(), set()
        _identifiers(node, s, e, reads)
        _writes(node, s, e, writes)
        depth, loop, control, function = 0, -1, -1, -1
        anc = node.parent
        while anc is not None:
            if anc.type in CONTROL:
                depth += 1
                if control < 0:
                    control = anc.start_byte
                if loop < 0 and anc.type in LOOPS:
                    loop = anc.start_byte
            if function < 0 and anc.type in DEFS:
                function = anc.start_byte
            anc = anc.parent
        out.append(
            UnitAst(
                category=_CATEGORY_BY_TYPE.get(node.type, "other"),
                node_type=node.type,
                is_header=node.end_byte > e,
                depth=depth,
                reads=reads,
                writes=writes,
                span=(node.start_byte, node.end_byte),
                loop=loop,
                control=control,
                function=function,
                parent=node.parent.start_byte if node.parent is not None else -1,
            )
        )
    return out
