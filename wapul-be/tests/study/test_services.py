"""분할기, 정적 분석, 질문 생성, 배치안 단위 테스트"""

import uuid

from app.models.study import Block, BlockKind, Language, Question, QuestionKind, Record
from app.services.analysis import analyze
from app.services.layouts import build_layouts
from app.services.questions import BlockInfo, build_questions
from app.services.segmenter import RuleSegmenter

PY_CODE = """import sys

n = int(input())

def fact(k):
    if k <= 1:
        return 1
    return k * fact(k - 1)

print(fact(n))
"""

CPP_CODE = """#include <bits/stdc++.h>
using namespace std;

int main() {
    int n; cin >> n;
    vector<int> v(n);

    long long s = 0;
    for (int i = 0; i < n; i++) s += v[i];

    cout << s << '\\n';
}
"""

JAVA_CODE = """class Main {
    static int f(int n) {
        return n == 0 ? 0 : f(n - 1) + 1;
    }
}
"""


class TestAnalyze:
    def test_python_condition_and_recursion(self):
        facts = analyze(PY_CODE, Language.PYTHON)
        assert 6 in facts.condition_lines
        assert facts.recursion_lines == {8}
        assert facts.loop_lines == set()

    def test_cpp_loop_comparison_ignores_template_brackets(self):
        facts = analyze(CPP_CODE, Language.CPP)
        assert facts.loop_lines == {9}
        assert 9 in facts.condition_lines
        assert 6 not in facts.condition_lines  # vector<int>는 비교가 아니다

    def test_java_ternary_and_recursion(self):
        facts = analyze(JAVA_CODE, Language.JAVA)
        assert 3 in facts.condition_lines
        assert facts.recursion_lines == {3}


class TestRuleSegmenter:
    def test_splits_on_blank_lines_and_skips_preamble(self):
        drafts = RuleSegmenter().segment(CPP_CODE, Language.CPP)
        assert [(d.kind, d.start_line, d.end_line) for d in drafts] == [
            (BlockKind.INPUT, 4, 6),
            (BlockKind.LOGIC, 8, 9),
            (BlockKind.OUTPUT, 11, 12),  # 닫는 괄호 줄은 앞 블럭에 붙는다
        ]
        assert drafts[1].name == "로직 1"


class TestBuildQuestions:
    def _blocks(self):
        return [
            BlockInfo(uuid.uuid4(), BlockKind.INPUT, 3, 3),
            BlockInfo(uuid.uuid4(), BlockKind.LOGIC, 5, 8),
            BlockInfo(uuid.uuid4(), BlockKind.OUTPUT, 10, 10),
        ]

    def test_question_set_follows_block_kinds(self):
        blocks = self._blocks()
        drafts = build_questions("seed", blocks, analyze(PY_CODE, Language.PYTHON), initially_wrong=False)
        kinds = [d.kind for d in drafts if d.kind != QuestionKind.VARYING]
        assert kinds == [
            QuestionKind.PROBLEM,
            QuestionKind.INPUT_MEANING,
            QuestionKind.INPUT_CONDITION,
            QuestionKind.LOGIC,
            QuestionKind.BOUNDARY,  # 로직 블럭에 if가 있다
            QuestionKind.OUTPUT_MEANING,
            QuestionKind.OUTPUT_FORMAT,
        ]
        assert sum(d.kind == QuestionKind.VARYING for d in drafts) == 1

    def test_revision_only_when_initially_wrong_and_last(self):
        blocks = self._blocks()
        facts = analyze(PY_CODE, Language.PYTHON)
        assert all(d.kind != QuestionKind.REVISION for d in build_questions("s", blocks, facts, False))
        assert build_questions("s", blocks, facts, True)[-1].kind == QuestionKind.REVISION

    def test_same_seed_same_phrases(self):
        blocks = self._blocks()
        facts = analyze(PY_CODE, Language.PYTHON)
        assert build_questions("a", blocks, facts, False) == build_questions("a", blocks, facts, False)


class TestLayouts:
    def test_answers_are_copied_verbatim_and_empty_ones_skipped(self):
        record = Record(
            owner_id="u", owner_name="u", problem="BOJ 1000", key_idea="더한다", code="a\nb\n", language=Language.PYTHON
        )
        block = Block(record_id=record.id, position=0, kind=BlockKind.LOGIC, name="더하기", start_line=1, end_line=2)
        questions = [
            Question(
                record_id=record.id, position=0, kind=QuestionKind.PROBLEM, text="P?", answer="  내가 쓴 그대로 ㅋ  "
            ),
            Question(record_id=record.id, block_id=block.id, position=1, kind=QuestionKind.LOGIC, text="L?", answer=""),
        ]
        layouts = build_layouts(record, [block], questions)
        assert [lay.id for lay in layouts] == ["code-first", "interleaved", "notes-first"]
        for lay in layouts:
            assert "내가 쓴 그대로 ㅋ" in lay.markdown
            assert "L?" not in lay.markdown
            assert "더한다" in lay.markdown
