"""기록·그룹 API E2E 테스트"""

import pytest

pytestmark = pytest.mark.e2e

CODE = "n = int(input())\n\nans = n * 2 if n > 0 else 0\n\nprint(ans)\n"


def _create(client, **overrides):
    body = {"problem": "BOJ 1000", "key_idea": "두 배", "code": CODE, "language": "python", **overrides}
    res = client.post("/v1/records", json=body)
    assert res.status_code == 201, res.text
    return res.json()


class TestRecords:
    def test_create_proposes_blocks_and_questions(self, multi_user_e2e):
        rec = _create(multi_user_e2e.as_user("a"))
        assert [b["kind"] for b in rec["blocks"]] == ["input", "logic", "output"]
        kinds = [q["kind"] for q in rec["questions"]]
        assert kinds[0] == "problem"
        assert "boundary" in kinds
        assert "revision" not in kinds
        assert all(q["examples"] for q in rec["questions"])

    def test_initially_wrong_adds_revision_question(self, multi_user_e2e):
        rec = _create(multi_user_e2e.as_user("a"), initially_wrong=True)
        assert rec["questions"][-1]["kind"] == "revision"

    def test_update_blocks_keeps_answers_that_still_apply(self, multi_user_e2e):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        problem_q = rec["questions"][0]
        res = client.patch(
            f"/v1/records/{rec['id']}/answers", json={"answers": [{"question_id": problem_q["id"], "answer": "성질"}]}
        )
        assert res.status_code == 204

        res = client.put(
            f"/v1/records/{rec['id']}/blocks",
            json={"blocks": [{"kind": "logic", "name": "전부", "start_line": 1, "end_line": 5}]},
        )
        assert res.status_code == 200, res.text
        updated = res.json()
        assert [b["name"] for b in updated["blocks"]] == ["전부"]
        assert updated["questions"][0]["answer"] == "성질"

    @pytest.mark.parametrize(
        "blocks",
        [
            [{"kind": "logic", "name": "x", "start_line": 1, "end_line": 99}],
            [{"kind": "logic", "name": "x", "start_line": 3, "end_line": 1}],
            [
                {"kind": "logic", "name": "x", "start_line": 1, "end_line": 3},
                {"kind": "logic", "name": "y", "start_line": 3, "end_line": 5},
            ],
        ],
    )
    def test_invalid_blocks_rejected(self, multi_user_e2e, blocks):
        client = multi_user_e2e.as_user("a")
        rec = _create(client)
        assert client.put(f"/v1/records/{rec['id']}/blocks", json={"blocks": blocks}).status_code == 422

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
