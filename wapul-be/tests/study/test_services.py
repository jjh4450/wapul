"""분할기, 배치안 단위 테스트"""

from app.models.study import Block, BlockKind, Language, Question, QuestionKind, Record
from app.services.layouts import build_layouts
from app.services.segmenter import RuleSegmenter

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


def _unit(line: int, start: int, end: int) -> dict:
    return {"start": [line, start], "end": [line, end], "condition": False, "loop": False, "recursion": False}


class TestRuleSegmenter:
    def test_splits_on_blank_lines_and_skips_preamble(self):
        drafts = RuleSegmenter().segment(CPP_CODE, Language.CPP)
        assert [(d.kind, d.start_line, d.end_line) for d in drafts] == [
            (BlockKind.INPUT, 4, 6),
            (BlockKind.LOGIC, 8, 9),
            (BlockKind.OUTPUT, 11, 12),  # 닫는 괄호 줄은 앞 블럭에 붙는다
        ]
        assert drafts[1].name == "로직 1"


class TestLayouts:
    def test_answers_are_copied_verbatim_and_empty_ones_skipped(self):
        record = Record(
            owner_id="u",
            owner_name="u",
            problem="BOJ 1000",
            key_idea="더한다",
            code="a\nb\n",
            language=Language.PYTHON,
            units=[_unit(1, 0, 1), _unit(2, 0, 1)],
        )
        block = Block(record_id=record.id, position=0, kind=BlockKind.LOGIC, units=[0, 1])
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

    def test_scattered_block_is_shown_with_gap(self):
        record = Record(
            owner_id="u",
            owner_name="u",
            problem="p",
            key_idea="k",
            code="int s = 0;\nint n;\ncin >> n;\ns += n;\n",
            language=Language.CPP,
            units=[_unit(1, 0, 10), _unit(2, 0, 6), _unit(3, 0, 9), _unit(4, 0, 7)],
        )
        blocks = [
            Block(record_id=record.id, position=0, kind=BlockKind.INPUT, units=[1, 2]),
            Block(record_id=record.id, position=1, kind=BlockKind.LOGIC, units=[0, 3]),
        ]
        interleaved = build_layouts(record, blocks, [])[1].markdown
        assert "### 입력 (2~3줄)" in interleaved
        assert "### 로직 1 (1, 4줄)\n\n```cpp\nint s = 0;\n...\ns += n;\n```" in interleaved
