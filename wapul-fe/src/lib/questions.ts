/**
 * 질문 문구 은행과 기록별 질문 생성
 *
 * - 같은 뜻의 문구를 여러 개 두고 하나를 무작위로 고른다. 모든 문구는 목적, 원리, 보장되는 성질을 향한다.
 * - 예제 답은 다른 문제에 대한 답이다. 내용은 베낄 수 없고 형식만 참고하게 된다.
 * - 질문 수는 코드 복잡도나 사용 횟수로 줄이지 않는다.
 * - 경계 질문과 구조별 질문은 블럭의 문장에 붙은 표시(wapul-seg의 condition, loop, recursion)로 고른다.
 */
import type {
  BlockIn,
  BlockKind,
  QuestionIn,
  QuestionKind,
  RecordOut,
  Unit
} from '#lib/api/client.js';

const PHRASES = {
  problem: [
    '어떤 성질을 발견해서 이 방법을 쓰게 됐나요?',
    '문제의 어떤 성질이 이 방법을 쓸 수 있게 해 주었나요?',
    '이 방법을 고르게 만든 문제의 성질은 무엇이었나요?'
  ],
  logic: [
    '이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?',
    '이 부분을 지나고 나면 무엇이 성립하고, 왜 그런가요?',
    '이 부분이 끝난 뒤 항상 참인 것은 무엇이고, 그 이유는 무엇인가요?'
  ],
  boundary: [
    '이 설명이 통하지 않는 입력은 뭘까요?',
    '어떤 입력에서 이 설명이 깨질까요?',
    '이 설명이 맞지 않게 되는 입력은 무엇일까요?'
  ],
  input_meaning: [
    '입력을 담은 변수와 자료구조는 각각 무엇을 나타내나요?',
    '입력을 받은 각 변수와 자료구조가 뜻하는 것은 무엇인가요?'
  ],
  input_condition: [
    '입력 조건(범위, 형식, 끝나는 조건) 중 이 코드가 기대는 것은 무엇인가요?',
    '이 코드가 믿고 있는 입력 조건(범위, 형식, 끝나는 조건)은 무엇인가요?'
  ],
  output_meaning: [
    '출력하는 값은 앞에서 만든 결과의 무엇에 해당하나요?',
    '출력하는 값은 앞에서 구한 결과 중 무엇인가요?'
  ],
  output_format: [
    '출력 형식이나 정밀도에서 지켜야 했던 조건은 무엇인가요?',
    '출력할 때 형식이나 정밀도에서 맞춰야 했던 것은 무엇인가요?'
  ],
  revision: [
    '처음 제출에서 무엇이 달라졌고, 왜 그게 필요했나요?',
    '처음 제출과 비교해 무엇을 바꿨고, 그 변경이 왜 필요했나요?'
  ]
} satisfies { [K in Exclude<QuestionKind, 'varying'>]: string[] };

// 기록마다 바뀌는 질문의 세 갈래
const VARYING_PERSPECTIVE = [
  '이 블럭의 결과를 다음 블럭은 어떻게 쓰나요?',
  '다음 블럭은 이 블럭이 만든 결과에서 무엇을 가져다 쓰나요?'
];

const VARYING_STRUCTURE = {
  recursion: [
    '재귀가 멈추는 조건과 그 이유는 무엇인가요?',
    '이 재귀가 반드시 끝나는 이유는 무엇인가요?'
  ],
  loop: [
    '반복이 한 바퀴 돌 때마다 유지되는 성질은 무엇인가요?',
    '이 반복문이 끝났을 때 무엇이 성립하나요?'
  ]
};

const VARYING_GENERAL = [
  '만약 입력 크기가 지금 제한의 10배라면 이 풀이는 어떻게 될까요?',
  '만약 같은 값이 여러 번 들어온다면 이 풀이는 어떻게 될까요?',
  '만약 입력이 하나뿐이라면 이 풀이는 어떻게 될까요?'
];

const EXAMPLES = {
  problem: [
    'N이 100만이라 O(n²) 정렬은 시간 안에 못 끝난다. 비교 정렬은 O(n log n)보다 빠를 수 없어서 병합 정렬을 썼다.',
    '퀸은 한 줄에 하나만 놓인다. 그래서 줄마다 하나씩 놓아 보고, 이미 막힌 칸이면 더 내려가지 않고 되돌아가는 백트래킹을 썼다.',
    '무게 w까지 담을 때의 최대 가치는 앞의 물건들만 보고 정해지고, 같은 부분 문제가 여러 번 나온다. 그래서 DP로 한 번씩만 계산했다.',
    '가장 일찍 끝나는 회의를 먼저 고르면 남는 시간이 가장 넓다. 이 선택이 최적해를 망치지 않아서 DP 없이 그리디로 충분했다.',
    'N번째 값은 바로 앞 두 값만 있으면 정해진다. 재귀는 같은 값을 여러 번 계산하고 깊이도 깊어서, 두 값만 들고 가는 반복문으로 썼다.'
  ],
  logic: [
    '이 반복이 끝나면 dp[w]에는 지금까지 본 물건으로 무게 w 이하를 담을 때의 최대 가치가 들어 있다. 물건마다 넣거나 빼는 두 경우뿐이고, 둘 다 이미 최댓값으로 정해진 칸에서 오기 때문이다.',
    '정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다. 그래서 앞에서부터 보면 항상 가장 일찍 끝나는 회의를 먼저 만난다.',
    '이 부분이 끝나면 cur와 prev에는 F(i)와 F(i-1)이 들어 있다. 매번 두 값을 한 칸씩 밀어 다음 값을 만들기 때문이다.',
    '시작점이 거리 0으로 큐에 들어가고 방문 표시가 됐다. 그래서 탐색은 시작점에서만 퍼져 나가고, 시작점을 다시 넣는 일은 없다.',
    '큐에서 꺼낸 칸의 dist는 시작점에서의 최단 거리다. 간선 길이가 모두 1이라 큐에는 거리 순서대로 들어가고, 먼저 방문한 쪽이 항상 더 가깝기 때문이다.',
    '이 반복이 끝나면 prefix[i][j]에는 (1,1)부터 (i,j)까지의 합이 들어 있다. 위와 왼쪽 합을 더하면 겹친 왼쪽 위 영역이 두 번 들어가서 한 번 빼 주기 때문이다.',
    '체가 끝나면 isPrime[i]는 i가 소수일 때만 참이다. 합성수는 자기보다 작은 소인수의 배수로 반드시 한 번은 지워지기 때문이다.',
    '합치고 나면 두 원소의 루트가 같아져 같은 집합으로 판정된다. 한쪽 루트를 다른 쪽 루트 밑에 붙여서, 양쪽 원소 모두 같은 루트를 따라가게 되기 때문이다.',
    '힙에는 지금까지 본 수 중 가장 큰 n개만 남고, 맨 위가 n번째로 큰 수다. 크기가 n을 넘을 때마다 그중 가장 작은 값을 빼기 때문이다.',
    '부호를 바꿔 넣었으니 최소 힙의 맨 위를 다시 뒤집으면 지금까지 넣은 수 중 최댓값이다. 부호를 바꾸면 크기 순서가 거꾸로 되기 때문이다.',
    '메모 배열이 모두 -1이라 아직 계산하지 않은 상태로 구분된다. 실제 답은 0 이상이라 -1과 겹치지 않기 때문이다.',
    '이미 구한 상태면 저장된 값을 바로 돌려주므로 같은 상태는 한 번만 계산된다. 상태 하나의 답은 언제 물어도 같기 때문이다.',
    '이 반복이 끝나면 dp[i]는 i를 1로 만드는 최소 연산 횟수다. 1을 빼거나 2, 3으로 나눈 결과는 i보다 작아서 이미 최솟값이 정해져 있고, 그중 가장 작은 것에 1을 더하기 때문이다.',
    '기저 칸이 채워졌다. i == j이면 고를 수 있는 방법이 하나뿐이고, i == 1이면 j개 중 하나를 고르는 방법이 j개이기 때문이다.',
    '칸을 행 순서대로 보므로 지금 칸에 왔을 때 그 칸의 경로 수는 이미 확정돼 있다. 이 칸으로 오는 칸은 모두 위나 왼쪽에 있어서 먼저 처리되기 때문이다.',
    '도착 칸에서는 더 퍼뜨리지 않는다. 도착 칸의 점프 길이는 0이라, 여기서 퍼뜨리면 자기 자신에게 경로 수를 다시 더하게 되기 때문이다.',
    '이 탐색이 끝나면 답은 lo와 hi 사이에 있다. 가운데 값이 조건을 만족하면 그보다 작은 쪽은 답이 될 수 없어서, 매번 절반을 버려도 답이 남기 때문이다.',
    'cnt는 간격을 mid 이하로 만들 때 더 지어야 하는 휴게소 수다. 간격마다 (간격 - 1) / mid개를 넣으면 가장 적게 넣으면서도 모든 간격이 mid 이하가 되기 때문이다.',
    '남은 금액이 0이면 더 볼 동전 없이 끝난다. 남은 동전으로는 0원을 만드는 데 하나도 쓰지 않기 때문이다.',
    '이 반복이 끝나면 각 칸에는 그 칸이 끝인 구간 중 합이 가장 큰 값이 들어 있다. 앞 칸까지의 최대 합이 음수면 이어 붙이는 것보다 새로 시작하는 쪽이 항상 크기 때문이다.',
    'dfs(v)가 끝나면 size[v]는 v를 루트로 한 서브트리의 정점 수다. 자식들의 서브트리는 서로 겹치지 않아서, 자식의 크기를 모두 더하고 자기 자신 1을 더하면 되기 때문이다.',
    '스택의 크기는 지금 열려 있는 괄호 수다. 여는 괄호에서 넣고 닫는 괄호에서 빼서, 짝이 맞은 괄호는 스택에 남지 않기 때문이다.',
    '앞에서부터 0을 지우고 나면 스택 맨 위는 0이 아니거나 스택이 비어 있다. 맨 위가 0인 동안 계속 꺼내기 때문이다.',
    '데드라인 안에서 가장 늦은 빈 날에 배정했다. 가장 늦은 날을 쓰면 이른 날이 남아서 데드라인이 짧은 다른 일도 넣을 수 있기 때문이다.',
    '합치기를 몇 번 하든 트리 높이는 log N을 넘지 않는다. 항상 작은 쪽을 큰 쪽 밑에 붙여서, 높이가 늘어날 때마다 집합 크기가 두 배 이상이 되기 때문이다.',
    '두 포인터가 움직이는 동안 sum은 언제나 start부터 end 앞까지의 합이다. end를 늘릴 때 더하고 start를 늘릴 때 빼서, 구간에 들어오고 나가는 값만 반영하기 때문이다.',
    'a^0을 1로 돌려준다. 지수를 반으로 줄여 가면 결국 0에 닿고, 곱셈의 시작값은 1이어야 결과가 바뀌지 않기 때문이다.',
    'n이 0이나 1이면 factorial(n)은 1이다. 재귀는 n을 하나씩 줄이므로 언젠가 이 조건에 닿아서 끝나기 때문이다.',
    '고른 수는 항상 앞 수보다 크다. 다음 칸에는 앞 수보다 큰 후보만 넣어 보기 때문에, 같은 조합을 순서만 바꿔 두 번 만드는 일도 없다.',
    '어긋나면 꺼냈던 글자를 되돌려서 스택이 검사 전 상태로 돌아간다. 꺼낸 순서의 반대로 다시 넣기 때문이다.'
  ],
  boundary: [
    '물건 무게가 배낭 용량보다 큰 경우. 이때는 넣는 경우를 아예 따지면 안 된다.',
    '끝나는 시간이 같은 회의가 여러 개일 때. 시작 시간까지 함께 정렬하지 않으면 길이가 0인 회의를 놓친다.',
    'N이 0이나 1일 때. 반복문이 한 번도 돌지 않아서 초기값이 그대로 답이 된다.'
  ],
  input_meaning: [
    'w[i], v[i]는 i번째 물건의 무게와 가치다. K는 배낭에 담을 수 있는 최대 무게다.',
    'meetings는 (끝나는 시간, 시작 시간) 쌍의 목록이다. 바로 정렬 기준으로 쓰려고 끝나는 시간을 앞에 뒀다.'
  ],
  input_condition: [
    'N이 최대 100만이라 한 줄씩 받으면 느려서 한 번에 읽었다.',
    '입력 끝에 0 0이 오면 끝난다는 조건에 기대고 있다. 이 줄이 없으면 반복이 끝나지 않는다.',
    '무게와 가치가 모두 양수라는 조건에 기대서 음수는 따로 처리하지 않았다.'
  ],
  output_meaning: [
    'dp[K]는 모든 물건을 본 뒤 무게 K 이하로 얻는 최대 가치라서 그대로 출력한다.',
    'count는 지금까지 고른 회의 수라서 반복이 끝난 뒤의 값이 곧 답이다.'
  ],
  output_format: [
    '소수점 아래 6자리까지 출력해야 해서 형식을 고정했다.',
    '답이 커서 1,000,000,007로 나눈 나머지를 출력해야 했다.',
    '한 줄에 하나씩 출력해야 해서 결과를 모아 줄바꿈으로 이어 한 번에 출력했다.'
  ],
  revision: [
    '처음엔 끝나는 시간만으로 정렬해서 길이가 0인 회의가 순서에 따라 빠졌다. 시작 시간도 함께 정렬해야 같은 시간에 끝나는 회의를 모두 셀 수 있었다.',
    '처음엔 int로 합을 구해서 넘쳤다. 최댓값이 10^5 × 10^9라 64비트 정수가 필요했다.',
    '처음엔 재귀로 풀어서 깊이 제한에 걸렸다. 반복문으로 바꿔 스택을 쓰지 않게 했다.'
  ],
  varying: [
    '다음 블럭은 정렬된 회의 목록을 앞에서부터 한 번만 훑는다. 정렬 덕분에 지금 고를 수 있는 회의 중 가장 일찍 끝나는 것이 항상 먼저 나온다.',
    '더 놓을 퀸이 없을 때(row == N) 멈춘다. 호출할 때마다 row가 1씩 커지므로 언젠가 반드시 N에 닿는다.',
    'N이 10배면 O(n²) 정렬은 100배 느려져서 시간 제한을 넘는다. O(n log n)이면 10배를 조금 넘게만 늘어난다.'
  ]
} satisfies { [K in QuestionKind]: string[] };

const BLOCK_QUESTIONS = {
  input: ['input_meaning', 'input_condition'],
  output: ['output_meaning', 'output_format'],
  logic: ['logic']
} satisfies { [K in BlockKind]: QuestionKind[] };

/** 블럭과, 그 블럭의 문장 중 하나라도 켜진 표시 */
export type BlockFacts = { kind: BlockKind; condition: boolean; loop: boolean; recursion: boolean };

export function blockFacts(units: Unit[], blocks: BlockIn[]): BlockFacts[] {
  return blocks.map((b) => {
    const us = b.units.map((i) => units[i]);

    return {
      kind: b.kind,
      condition: us.some((u) => u.condition),
      loop: us.some((u) => u.loop),
      recursion: us.some((u) => u.recursion)
    };
  });
}

function choice<T>(items: T[], random: () => number): T {
  return items[Math.floor(random() * items.length)];
}

/** 새 질문. 답은 빈 칸에서 시작한다 */
function ask(kind: QuestionKind, text: string, block?: number): QuestionIn {
  return block === undefined ? { kind, text, answer: '' } : { kind, text, answer: '', block };
}

/** 세 갈래 중 이 코드에 붙을 수 있는 갈래에서 하나를 뽑는다 */
function pickVarying(blocks: BlockFacts[], random: () => number): QuestionIn {
  const options: QuestionIn[] = [];

  // 관점 바꾸기: 뒤에 블럭이 이어지는 로직 블럭
  blocks.slice(0, -1).forEach((b, i) => {
    if (b.kind === 'logic') {
      options.push(ask('varying', choice(VARYING_PERSPECTIVE, random), i));
    }
  });

  // 구조별: 블럭에 그 구조가 있을 때만
  for (const structure of ['recursion', 'loop'] as const) {
    blocks.forEach((b, i) => {
      if (b[structure]) {
        options.push(ask('varying', choice(VARYING_STRUCTURE[structure], random), i));
      }
    });
  }

  // 일반 질문 줄기: 언제나 붙을 수 있다
  options.push(ask('varying', choice(VARYING_GENERAL, random)));

  return choice(options, random);
}

/** 기록에 붙을 질문을 표시 순서대로 만든다. block은 blocks의 번호다 */
export function buildQuestions(
  blocks: BlockFacts[],
  initiallyWrong: boolean,
  random: () => number = Math.random
): QuestionIn[] {
  const varying = pickVarying(blocks, random);
  const questions = [ask('problem', choice(PHRASES.problem, random))];

  blocks.forEach((b, i) => {
    for (const kind of BLOCK_QUESTIONS[b.kind]) {
      questions.push(ask(kind, choice(PHRASES[kind], random), i));
    }

    if (b.condition) {
      questions.push(ask('boundary', choice(PHRASES.boundary, random), i));
    }

    if (varying.block === i) questions.push(varying);
  });

  if (varying.block === undefined) questions.push(varying);

  if (initiallyWrong) questions.push(ask('revision', choice(PHRASES.revision, random)));

  return questions;
}

/**
 * 블럭을 고친 뒤 새로 만든 질문에, 종류와 문장이 그대로인 블럭(기록 단위 질문은 그대로)의 질문을
 * 문구와 답까지 옮긴다. 기록마다 바뀌는 질문도 붙은 자리가 남아 있으면 이전 것을 그대로 쓴다.
 */
export function keepQuestions(
  questions: QuestionIn[],
  blocks: BlockIn[],
  old: RecordOut
): QuestionIn[] {
  const blockKey = (b: BlockIn) => `${b.kind}:${b.units.join(',')}`;
  const oldKeys = new Map(old.blocks.map((b) => [b.id, blockKey(b)]));
  const newIndex = new Map(blocks.map((b, i) => [blockKey(b), i]));
  const at = (block: string | null) => (block === null ? '' : (oldKeys.get(block) ?? '?'));

  const kept = questions.map((q) => {
    if (q.kind === 'varying') return q;

    const key = q.block === undefined || q.block === null ? '' : blockKey(blocks[q.block]);
    const same = old.questions.find((o) => o.kind === q.kind && at(o.block_id) === key);

    return same ? { ...q, text: same.text, answer: same.answer } : q;
  });

  const oldVarying = old.questions.find((q) => q.kind === 'varying');

  if (oldVarying === undefined) return kept;

  const block = oldVarying.block_id === null ? null : newIndex.get(at(oldVarying.block_id));

  if (block === undefined) return kept;

  // 이전 질문을 그 블럭의 질문 뒤에, 기록 단위면 블럭 질문들 뒤(달라진 점 질문 앞)에 둔다
  const rest = kept.filter((q) => q.kind !== 'varying');

  const after =
    block === null
      ? rest.findLastIndex((q) => q.kind !== 'revision')
      : rest.findLastIndex((q) => q.block === block);

  rest.splice(after + 1, 0, {
    ...ask('varying', oldVarying.text, block ?? undefined),
    answer: oldVarying.answer
  });

  return rest;
}

/** 질문 종류의 예제 답을 매번 다른 순서로. 답 칸에는 첫 예제부터 보인다 */
export function shuffledExamples(kind: QuestionKind, random: () => number = Math.random): string[] {
  const examples = [...EXAMPLES[kind]];

  for (let i = examples.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [examples[i], examples[j]] = [examples[j], examples[i]];
  }

  return examples;
}
