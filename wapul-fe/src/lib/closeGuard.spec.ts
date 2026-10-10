import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CloseGuard, hasBlank, SHAKE_MS, skippable } from './closeGuard.svelte.js';

describe('skippable', () => {
  it('lets only the revision question go unanswered', () => {
    expect(skippable({ kind: 'revision' })).toBe(true);
    expect(skippable({ kind: 'logic' })).toBe(false);
  });
});

describe('hasBlank', () => {
  it('counts an empty or whitespace answer, but not of a revision question', () => {
    expect(hasBlank([{ kind: 'logic', answer: '끝나는 시간 순' }])).toBe(false);
    expect(hasBlank([{ kind: 'logic', answer: '  ' }])).toBe(true);
    expect(hasBlank([{ kind: 'revision', answer: '' }])).toBe(false);
  });
});

describe('CloseGuard', () => {
  beforeEach(() => vi.useFakeTimers());

  afterEach(() => vi.useRealTimers());

  /** 흔들기가 시작되기까지 (tick 뒤) */
  const started = () => vi.advanceTimersByTimeAsync(0);

  const shaken = () => vi.advanceTimersByTimeAsync(SHAKE_MS);

  it('closes right away when nothing is blank', () => {
    const guard = new CloseGuard(() => false);

    expect(guard.unlocked(false)).toBe(true);
    expect(guard.close(false)).toBe(true);
    expect(guard.plea).toBe('');
    expect(guard.shaking).toBe(false);
  });

  it('takes three tries: plead and shake, shake and unlock, close', async () => {
    const guard = new CloseGuard(() => false);

    expect(guard.unlocked(true)).toBe(false);

    expect(guard.close(true)).toBe(false);
    expect(guard.tries).toBe(1);
    expect(guard.plea).not.toBe('');
    await started();
    expect(guard.shaking).toBe(true);
    await shaken();
    expect(guard.shaking).toBe(false);
    expect(guard.unlocked(true)).toBe(false);

    guard.plea = '';

    expect(guard.close(true)).toBe(false);
    expect(guard.tries).toBe(2);
    expect(guard.plea).toBe('');
    await started();
    expect(guard.unlocked(true)).toBe(false);
    await shaken();
    expect(guard.unlocked(true)).toBe(true);

    expect(guard.close(true)).toBe(true);
    expect(guard.tries).toBe(0);
  });

  it('does not count a press during the last shake', async () => {
    const guard = new CloseGuard(() => false);

    guard.close(true);
    guard.close(true);
    await started();

    expect(guard.close(true)).toBe(false);
    expect(guard.tries).toBe(2);

    await shaken();

    expect(guard.close(true)).toBe(true);
  });

  it('skips the shake and unlocks at once for users who reduce motion', () => {
    const guard = new CloseGuard(() => true);

    guard.close(true);
    guard.close(true);

    expect(guard.shaking).toBe(false);
    expect(guard.unlocked(true)).toBe(true);
  });

  it('starts counting again when another thread is opened', async () => {
    const guard = new CloseGuard(() => false);

    guard.close(true);
    await started();
    guard.reset();

    expect(guard.tries).toBe(0);
    expect(guard.shaking).toBe(false);
    expect(guard.close(true)).toBe(false);
    expect(guard.tries).toBe(1);
  });
});
