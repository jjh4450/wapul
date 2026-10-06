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
}`;

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
  is_owner: true,
  group_ids: [],
  blocks: [
    { id: 'block-input', kind: 'input', name: '입력 받기', start_line: 4, end_line: 7 },
    { id: 'block-logic', kind: 'logic', name: '회의 고르기', start_line: 9, end_line: 13 },
    { id: 'block-output', kind: 'output', name: '결과 출력', start_line: 15, end_line: 16 }
  ],
  questions: [
    {
      id: 'q-problem',
      block_id: null,
      kind: 'problem',
      text: '어떤 성질을 발견해서 이 방법을 쓰게 됐나요?',
      answer: '',
      examples: [
        '퀸은 한 줄에 하나만 놓인다. 그래서 줄마다 하나씩 놓아 보고, 막힌 칸이면 되돌아가는 백트래킹을 썼다.',
        'N번째 값은 바로 앞 두 값만 있으면 정해진다. 두 값만 들고 가는 반복문으로 썼다.'
      ]
    },
    {
      id: 'q-input-meaning',
      block_id: 'block-input',
      kind: 'input_meaning',
      text: '입력을 담은 변수와 자료구조는 각각 무엇을 나타내나요?',
      answer: 'm은 (끝나는 시간, 시작 시간) 쌍의 목록이다.',
      examples: ['w[i], v[i]는 i번째 물건의 무게와 가치다.']
    },
    {
      id: 'q-input-condition',
      block_id: 'block-input',
      kind: 'input_condition',
      text: '입력 조건(범위, 형식, 끝나는 조건) 중 이 코드가 기대는 것은 무엇인가요?',
      answer: '',
      examples: [
        'N이 최대 100만이라 한 줄씩 받으면 느려서 한 번에 읽었다.',
        '입력 끝에 0 0이 오면 끝난다는 조건에 기대고 있다.'
      ]
    },
    {
      id: 'q-logic',
      block_id: 'block-logic',
      kind: 'logic',
      text: '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?',
      answer: '',
      examples: ['정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다.']
    },
    {
      id: 'q-boundary',
      block_id: 'block-logic',
      kind: 'boundary',
      text: '이 설명이 통하지 않는 입력은 뭘까요?',
      answer: '',
      examples: ['N이 0이나 1일 때. 반복문이 한 번도 돌지 않는다.']
    },
    {
      id: 'q-output-meaning',
      block_id: 'block-output',
      kind: 'output_meaning',
      text: '출력하는 값은 앞에서 만든 결과의 무엇에 해당하나요?',
      answer: '',
      examples: ['count는 지금까지 고른 회의 수라서 반복이 끝난 뒤의 값이 곧 답이다.']
    },
    {
      id: 'q-output-format',
      block_id: 'block-output',
      kind: 'output_format',
      text: '출력 형식이나 정밀도에서 지켜야 했던 조건은 무엇인가요?',
      answer: '',
      examples: ['답이 커서 1,000,000,007로 나눈 나머지를 출력해야 했다.']
    },
    {
      id: 'q-varying',
      block_id: null,
      kind: 'varying',
      text: '만약 입력이 하나뿐이라면 이 풀이는 어떻게 될까요?',
      answer: '',
      examples: ['N이 10배면 O(n²) 정렬은 100배 느려진다.']
    },
    {
      id: 'q-revision',
      block_id: null,
      kind: 'revision',
      text: '처음 제출에서 무엇이 달라졌고, 왜 그게 필요했나요?',
      answer: '',
      examples: ['처음엔 int로 합을 구해서 넘쳤다.']
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
      '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n```cpp\nint main() {}\n```\n\n### 입력 받기 (4~7줄)\n'
  },
  {
    id: 'interleaved',
    title: '블럭마다 코드와 설명',
    markdown:
      '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n### 입력 받기 (4~7줄)\n\n```cpp\nint n; cin >> n;\n```\n'
  },
  {
    id: 'notes-first',
    title: '설명 먼저, 코드는 끝에',
    markdown: '# BOJ 1931 회의실 배정\n\n## 내 구현\n\n### 입력 받기 (4~7줄)\n\n### 전체 코드\n'
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
