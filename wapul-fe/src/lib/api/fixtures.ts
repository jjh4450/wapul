/**
 * story에서 가짜 API(fake.ts)가 돌려줄 데이터. 백엔드 응답과 같은 타입으로 적어서
 * API 계약이 바뀌면 타입 검사(pnpm check)에서 바로 드러난다.
 */
import type { GroupDetail, GroupOut, LayoutOut, RecordOut, RecordSummary } from './client.js';

const code = `#include <bits/stdc++.h>
using namespace std;

int main() {
    int n; cin >> n;
    vector<pair<int, int>> m(n);
    for (auto& [e, s] : m) cin >> s >> e;

    sort(m.begin(), m.end());
    int cnt = 0, end = 0;
    for (auto [e, s] : m) {
        if (s >= end) { cnt++; end = e; }
    }

    cout << cnt << '\\n';
}
`;

// wapul-seg가 위 코드에 실제로 낸 문장 위치 (none 문장 포함)
const at = (
  line: number,
  from: number,
  to: number,
  tags: { condition?: true; loop?: true } = {}
) => ({
  start: [line, from],
  end: [line, to],
  condition: false,
  loop: false,
  recursion: false,
  ...tags
});

export const record: RecordOut = {
  id: 'record-1',
  problem: 'BOJ 1931 회의실 배정',
  key_idea: '끝나는 시간이 빠른 회의부터 고른다',
  language: 'cpp',
  owner_name: '김코딩',
  created_at: '2026-10-05T09:00:00+0000',
  updated_at: '2026-10-05T09:30:00+0000',
  code,
  initially_wrong: true,
  units: [
    at(1, 0, 24),
    at(2, 0, 20),
    at(4, 0, 10),
    at(5, 4, 10),
    at(5, 11, 20),
    at(6, 4, 32),
    at(7, 4, 26, { loop: true }),
    at(7, 27, 41),
    at(9, 4, 29),
    at(10, 4, 25),
    at(11, 4, 25, { loop: true }),
    at(12, 8, 21, { condition: true }),
    at(12, 24, 30),
    at(12, 31, 39),
    at(15, 4, 24)
  ],
  is_owner: true,
  group_ids: [],
  blocks: [
    { id: 'block-input', kind: 'input', units: [3, 4, 5, 6, 7] },
    { id: 'block-logic', kind: 'logic', units: [8, 9, 10, 11, 12, 13] },
    { id: 'block-output', kind: 'output', units: [14] }
  ],
  questions: [
    {
      id: 'q-problem',
      block_id: null,
      kind: 'problem',
      text: '어떤 성질을 발견해서 이 방법을 쓰게 됐나요?',
      answer: ''
    },
    {
      id: 'q-input-meaning',
      block_id: 'block-input',
      kind: 'input_meaning',
      text: '입력을 담은 변수와 자료구조는 각각 무엇을 나타내나요?',
      answer: 'm은 (끝나는 시간, 시작 시간) 쌍의 목록이다.'
    },
    {
      id: 'q-input-condition',
      block_id: 'block-input',
      kind: 'input_condition',
      text: '입력 조건(범위, 형식, 끝나는 조건) 중 이 코드가 기대는 것은 무엇인가요?',
      answer: ''
    },
    {
      id: 'q-logic',
      block_id: 'block-logic',
      kind: 'logic',
      text: '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?',
      answer: ''
    },
    {
      id: 'q-boundary',
      block_id: 'block-logic',
      kind: 'boundary',
      text: '이 설명이 통하지 않는 입력은 뭘까요?',
      answer: ''
    },
    {
      id: 'q-output-meaning',
      block_id: 'block-output',
      kind: 'output_meaning',
      text: '출력하는 값은 앞에서 만든 결과의 무엇에 해당하나요?',
      answer: ''
    },
    {
      id: 'q-output-format',
      block_id: 'block-output',
      kind: 'output_format',
      text: '출력 형식이나 정밀도에서 지켜야 했던 조건은 무엇인가요?',
      answer: ''
    },
    {
      id: 'q-varying',
      block_id: null,
      kind: 'varying',
      text: '만약 입력이 하나뿐이라면 이 풀이는 어떻게 될까요?',
      answer: ''
    },
    {
      id: 'q-revision',
      block_id: null,
      kind: 'revision',
      text: '처음 제출에서 무엇이 달라졌고, 왜 그게 필요했나요?',
      answer: ''
    }
  ]
};

/** 같은 기록을 그룹 멤버가 볼 때 */
export const sharedRecord: RecordOut = { ...record, is_owner: false };

export const records: RecordSummary[] = [
  {
    id: 'record-1',
    problem: 'BOJ 1931 회의실 배정',
    key_idea: '끝나는 시간이 빠른 회의부터 고른다',
    language: 'cpp',
    owner_name: '김코딩',
    created_at: '2026-10-05T09:00:00+0000',
    updated_at: '2026-10-05T09:30:00+0000'
  },
  {
    id: 'record-2',
    problem: 'BOJ 12865 평범한 배낭',
    key_idea: '무게별 최대 가치를 물건 하나씩 넣어 가며 채운다',
    language: 'python',
    owner_name: '김코딩',
    created_at: '2026-10-03T12:00:00+0000',
    updated_at: '2026-10-04T08:00:00+0000'
  }
];

export const layouts: LayoutOut[] = [
  {
    id: 'code-first',
    title: '전체 코드 먼저',
    markdown:
      '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n```cpp\nint main() {}\n```\n\n### 입력 (5~7줄)\n'
  },
  {
    id: 'interleaved',
    title: '블럭마다 코드와 설명',
    markdown:
      '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n### 입력 (5~7줄)\n\n```cpp\nint n; cin >> n;\n```\n'
  },
  {
    id: 'notes-first',
    title: '설명 먼저, 코드는 끝에',
    markdown: '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n### 입력 (5~7줄)\n\n### 전체 코드\n'
  }
];

export const groups: GroupOut[] = [
  { id: 'group-1', name: 'PS 스터디', invite_code: 'ABCD2345', role: 'owner', member_count: 3 },
  {
    id: 'group-2',
    name: '알고리즘 동아리',
    invite_code: 'WXYZ6789',
    role: 'member',
    member_count: 12
  }
];

export const groupDetail: GroupDetail = {
  ...groups[0],
  members: [
    { display_name: '김코딩', role: 'owner' },
    { display_name: '이알고', role: 'member' },
    { display_name: '박풀이', role: 'member' }
  ],
  records: [{ ...records[0], shared_at: '2026-10-05T10:00:00+0000' }]
};
