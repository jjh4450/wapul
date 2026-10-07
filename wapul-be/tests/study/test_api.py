"""기록·그룹 API E2E 테스트"""

import pytest

pytestmark = pytest.mark.e2e

CODE = "n = int(input())\n\nans = n * 2 if n > 0 else 0\n\nprint(ans)\n"
# 브라우저의 wapul-seg가 보내는 모양: 모든 문장과, 문장 번호로 적은 블럭
NO_TAGS = {"condition": False, "loop": False, "recursion": False}
UNITS = [
    {"start": [1, 0], "end": [1, 16], **NO_TAGS},
    {"start": [3, 0], "end": [3, 27], **NO_TAGS, "condition": True},
    {"start": [5, 0], "end": [5, 10], **NO_TAGS},
]
BLOCKS = [{"kind": "input", "units": [0]}, {"kind": "logic", "units": [1]}, {"kind": "output", "units": [2]}]
# 질문도 브라우저가 만들어 보낸다
QUESTIONS = [
    {"kind": "problem", "text": "어떤 성질을 발견했나요?", "answer": ""},
    {"kind": "input_meaning", "text": "입력 변수는 무엇인가요?", "block": 0, "answer": ""},
    {"kind": "logic", "text": "무엇이 보장되나요?", "block": 1, "answer": ""},
    {"kind": "boundary", "text": "통하지 않는 입력은?", "block": 1, "answer": ""},
    {"kind": "output_meaning", "text": "출력은 무엇인가요?", "block": 2, "answer": ""},
    {"kind": "varying", "text": "만약 입력이 하나뿐이라면?", "answer": ""},
]


def _create(client, **overrides):
    body = {
        "problem": "BOJ 1000",
        "key_idea": "두 배",
        "code": CODE,
        "language": "python",
        "units": UNITS,
        "blocks": BLOCKS,
        "questions": QUESTIONS,
        **overrides,
    }
    res = client.post("/v1/records", json=body)
    assert res.status_code == 201, res.text
    return res.json()


class TestRecords:
    def test_create_stores_blocks_and_questions_as_sent(self, multi_user_e2e):
        rec = _create(multi_user_e2e.as_user("a"))
        assert [(b["kind"], b["units"]) for b in rec["blocks"]] == [("input", [0]), ("logic", [1]), ("output", [2])]
        assert rec["units"] == UNITS
        block_ids = [b["id"] for b in rec["blocks"]]
        assert [(q["kind"], q["text"], q["block_id"]) for q in rec["questions"]] == [
            (q["kind"], q["text"], None if "block" not in q else block_ids[q["block"]]) for q in QUESTIONS
        ]

    def test_update_blocks_replaces_questions_with_carried_answers(self, multi_user_e2e):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        questions = [
            {"kind": "problem", "text": "어떤 성질을 발견했나요?", "answer": "성질"},
            {"kind": "logic", "text": "무엇이 보장되나요?", "block": 0, "answer": ""},
        ]
        res = client.put(
            f"/v1/records/{rec['id']}/blocks",
            json={"blocks": [{"kind": "logic", "units": [2, 0]}], "questions": questions},
        )
        assert res.status_code == 200, res.text
        updated = res.json()
        assert [b["units"] for b in updated["blocks"]] == [[0, 2]]
        assert [(q["kind"], q["answer"]) for q in updated["questions"]] == [("problem", "성질"), ("logic", "")]
        assert updated["questions"][1]["block_id"] == updated["blocks"][0]["id"]

    @pytest.mark.parametrize(
        "blocks",
        [
            [{"kind": "logic", "units": [3]}],
            [{"kind": "logic", "units": []}],
            [{"kind": "logic", "units": [0, 1]}, {"kind": "logic", "units": [1, 2]}],
        ],
    )
    def test_invalid_blocks_rejected(self, multi_user_e2e, blocks):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        body = {"blocks": blocks, "questions": QUESTIONS[:1]}
        assert client.put(f"/v1/records/{rec['id']}/blocks", json=body).status_code == 422

    def test_question_on_missing_block_rejected(self, multi_user_e2e):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        body = {"blocks": BLOCKS[:1], "questions": [{"kind": "logic", "text": "L?", "block": 1, "answer": ""}]}
        assert client.put(f"/v1/records/{rec['id']}/blocks", json=body).status_code == 422

    @pytest.mark.parametrize(
        "units",
        [
            [{**UNITS[0], "end": [1, 17]}, *UNITS[1:]],  # 줄 끝을 넘는다
            [UNITS[1], UNITS[0], UNITS[2]],  # 순서가 어긋났다
            [{**UNITS[0], "end": [1, 0]}, *UNITS[1:]],  # 빈 문장
        ],
    )
    def test_invalid_units_rejected(self, multi_user_e2e, units):
        body = {
            "problem": "p",
            "key_idea": "k",
            "code": CODE,
            "language": "python",
            "units": units,
            "blocks": BLOCKS,
            "questions": QUESTIONS,
        }
        assert multi_user_e2e.as_user("a").post("/v1/records", json=body).status_code == 422

    def test_layouts_contain_answers(self, multi_user_e2e):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        q = rec["questions"][1]
        client.patch(
            f"/v1/records/{rec['id']}/answers", json={"answers": [{"question_id": q["id"], "answer": "n은 입력 수"}]}
        )
        layouts = client.get(f"/v1/records/{rec['id']}/layouts").json()
        assert len(layouts) == 3
        assert all("n은 입력 수" in lay["markdown"] for lay in layouts)

    def test_other_users_cannot_see_or_edit(self, multi_user_e2e):
        rec = _create(multi_user_e2e.as_user("a"))
        other = multi_user_e2e.as_user("b")
        assert other.get(f"/v1/records/{rec['id']}").status_code == 404
        assert other.delete(f"/v1/records/{rec['id']}").status_code == 404


class TestGroups:
    def test_share_within_group(self, multi_user_e2e):
        a, b, c = (multi_user_e2e.as_user(u) for u in "abc")
        group = a.post("/v1/groups", json={"name": "PS 스터디"}).json()
        joined = b.post("/v1/groups/join", json={"invite_code": group["invite_code"].lower()}).json()
        assert joined["role"] == "member"
        assert joined["member_count"] == 2

        rec = _create(a)
        assert a.put(f"/v1/records/{rec['id']}/groups", json={"group_ids": [group["id"]]}).status_code == 200

        detail = b.get(f"/v1/groups/{group['id']}").json()
        assert [r["id"] for r in detail["records"]] == [rec["id"]]
        viewed = b.get(f"/v1/records/{rec['id']}").json()
        assert viewed["is_owner"] is False
        assert viewed["group_ids"] == []
        assert b.patch(f"/v1/records/{rec['id']}/answers", json={"answers": []}).status_code == 403

        assert c.get(f"/v1/groups/{group['id']}").status_code == 404
        assert c.get(f"/v1/records/{rec['id']}").status_code == 404

        # 공유를 풀면 멤버도 못 본다
        a.put(f"/v1/records/{rec['id']}/groups", json={"group_ids": []})
        assert b.get(f"/v1/records/{rec['id']}").status_code == 404

    def test_cannot_share_to_foreign_group(self, multi_user_e2e):
        a, b = multi_user_e2e.as_user("a"), multi_user_e2e.as_user("b")
        group = b.post("/v1/groups", json={"name": "남의 그룹"}).json()
        rec = _create(a)
        assert a.put(f"/v1/records/{rec['id']}/groups", json={"group_ids": [group["id"]]}).status_code == 403

    def test_join_with_bad_code(self, multi_user_e2e):
        assert multi_user_e2e.as_user("a").post("/v1/groups/join", json={"invite_code": "NOPE"}).status_code == 404
