"""문장 단위 분할과 Claude API 분할기 테스트 (API는 가짜 클라이언트로 대신한다)"""

from types import SimpleNamespace

from app.models.study import BlockKind, Language
from app.services.llm_segmenter import LLMSegmenter, LogicBlock, Segmentation, to_drafts, unit_kinds
from app.services.segmenter import BlockDraft, RuleSegmenter
from app.services.units import show, units

CPP_CODE = """#include <iostream>
using namespace std;

int main() {
    int n; cin >> n;  // 입력
    int ans = 0;
    for (int i = 1; i <= n; i++) {
        if (i % 2) ans += i;
        else ans -= i;
    }
    cout << ans;
}
"""


class FakeClient:
    """client.beta.messages.parse만 흉내 낸다"""

    def __init__(self, parsed: Segmentation | None) -> None:
        self.calls: list[dict] = []
        parse = self._parse
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=parse))
        self._parsed = parsed

    def _parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", stop_details=None, parsed_output=self._parsed)


def _segmentation() -> Segmentation:
    # u1 #include, u2 using, u3 int main(), u4 int n;, u5 cin >> n;, u6 int ans = 0;,
    # u7 for, u8 if, u9 ans += i;, u10 ans -= i;, u11 cout << ans;
    return Segmentation(
        procedure=["1부터 n까지 돈다", "홀수는 더하고 짝수는 뺀다"],
        input=[4, 5],
        output=[11],
        logic=[LogicBlock(units=[6, 7], guarantee="i를 차례로 본다"), LogicBlock(units=[8, 9, 10], guarantee="부호")],
        none=[1, 2, 3],
    )


def test_units_split_statements_and_skip_comments_and_bare_keywords():
    texts = [u.text for u in units(CPP_CODE, Language.CPP)]

    assert texts[3:5] == ["int n;", "cin >> n;"]
    assert "else" not in texts
    assert not any("//" in t for t in texts)
    assert len(texts) == 11


def test_show_keeps_else_as_context_without_numbering_it():
    us = units(CPP_CODE, Language.CPP)

    shown = show(CPP_CODE, us)

    assert "[u10]         else ans -= i;" in shown
    assert "입력" not in shown


def test_unit_kinds_rejects_missing_or_repeated_units():
    seg = _segmentation()
    seg.none = [1, 2]

    try:
        unit_kinds(seg, 11)
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_to_drafts_merges_lines_and_numbers_logic_blocks():
    us = units(CPP_CODE, Language.CPP)

    drafts = to_drafts(us, unit_kinds(_segmentation(), len(us)))

    assert drafts == [
        BlockDraft(kind=BlockKind.INPUT, name="입력 받기", start_line=5, end_line=5),
        BlockDraft(kind=BlockKind.LOGIC, name="로직 1", start_line=6, end_line=7),
        BlockDraft(kind=BlockKind.LOGIC, name="로직 2", start_line=8, end_line=9),
        BlockDraft(kind=BlockKind.OUTPUT, name="결과 출력", start_line=11, end_line=11),
    ]


def test_llm_segmenter_sends_numbered_units_and_returns_line_blocks():
    client = FakeClient(_segmentation())

    drafts = LLMSegmenter(client).segment(CPP_CODE, Language.CPP)

    assert [d.name for d in drafts] == ["입력 받기", "로직 1", "로직 2", "결과 출력"]
    assert "[u5]" in client.calls[0]["messages"][0]["content"]


def test_llm_segmenter_falls_back_to_rules_when_the_answer_is_unusable():
    no_answer = LLMSegmenter(FakeClient(None)).segment(CPP_CODE, Language.CPP)
    bad = _segmentation()
    bad.procedure = ["하나뿐"]
    mismatched = LLMSegmenter(FakeClient(bad)).segment(CPP_CODE, Language.CPP)

    expected = RuleSegmenter().segment(CPP_CODE, Language.CPP)
    assert no_answer == expected
    assert mismatched == expected
