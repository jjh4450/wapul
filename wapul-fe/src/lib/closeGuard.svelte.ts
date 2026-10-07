import { tick } from 'svelte';
import type { QuestionKind } from '#lib/api/client.js';

// 답하지 않고 묶음을 닫으려 할 때 띄우는 모달의 제목
const PLEAS = [
  '대답을 안... 하고 넘어가실 거예요?',
  '정말요? 한 줄만 적어도 괜찮은데...',
  '이 블럭은 아직 할 말이 남은 것 같아요...'
];

// 흔들림 길이 (layout.css의 --animate-shake와 같다). 애니메이션이 끝나는 이벤트에 기대지 않고
// 시간으로 풀어서, 이벤트를 놓쳐도 닫기가 막힌 채로 남지 않는다
export const SHAKE_MS = 400;

/** 답하지 않은 칸이 있는지. 건너뛸 수 있는 달라진 점 질문은 세지 않는다 */
export function hasBlank(questions: { kind: QuestionKind; answer: string }[]): boolean {
  return questions.some((q) => q.kind !== 'revision' && q.answer.trim() === '');
}

/**
 * 펼친 질문 묶음을 답하지 않고 닫으려 할 때 막는 흐름. 빈 칸이 있으면 처음 누를 때 묶음을 흔들고
 * 모달로 묻고, 한 번 더 누르면 흔든 뒤에야 닫기가 풀린다. 컴포넌트는 이것을 그리기만 한다
 */
export class CloseGuard {
  /** 펼친 묶음에서 답하지 않고 닫기를 누른 횟수. 두 번 누르면 닫기가 풀린다 */
  tries = $state(0);

  shaking = $state(false);

  /** 호소 모달의 제목. 빈 문자열이면 닫혀 있다 */
  plea = $state('');

  #timer: ReturnType<typeof setTimeout> | undefined;

  readonly #reduceMotion: () => boolean;

  readonly #random: () => number;

  /** reduceMotion은 동작 줄이기를 켠 사용자인지. 켰으면 흔들지 않고 바로 다음 단계로 간다 */
  constructor(
    reduceMotion: () => boolean = () => matchMedia('(prefers-reduced-motion: reduce)').matches,
    random: () => number = Math.random
  ) {
    this.#reduceMotion = reduceMotion;
    this.#random = random;
  }

  /** 닫기가 풀렸는지. blank는 펼친 묶음에 답하지 않은 칸이 있는지 */
  unlocked(blank: boolean): boolean {
    return !blank || (this.tries >= 2 && !this.shaking);
  }

  /** 닫기를 눌렀다. 닫아도 되면 true. 아니면 횟수를 세고 흔든다 */
  close(blank: boolean): boolean {
    if (this.unlocked(blank)) {
      this.tries = 0;

      return true;
    }

    // 닫기가 풀리기 전(마지막 흔들림 중)에 누른 것은 세지 않는다
    if (this.tries >= 2) return false;

    this.tries += 1;

    if (this.tries === 1) this.plea = PLEAS[Math.floor(this.#random() * PLEAS.length)];

    this.shake();

    return false;
  }

  /** 다른 묶음을 펼쳤다. 횟수를 처음부터 센다 */
  reset() {
    this.tries = 0;
    this.shaking = false;
  }

  /** 펼친 묶음을 흔든다. 흔드는 중에 또 흔들면 처음부터 다시 흔든다 */
  async shake() {
    if (this.#reduceMotion()) return;

    clearTimeout(this.#timer);
    this.shaking = false;
    await tick();
    this.shaking = true;
    this.#timer = setTimeout(() => (this.shaking = false), SHAKE_MS);
  }
}
