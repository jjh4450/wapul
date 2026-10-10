/**
 * 한글처럼 조합해 쓰는 글자의 마지막 글자를, 칸 밖의 버튼이 동작하기 전에 확정한다.
 *
 * Safari는 버튼을 눌러도 칸에서 커서가 빠지지 않고, 일부 모바일 키보드는 조합 중인 글자를 확정하기 전까지
 * 값에 넣지 않는다. 그 상태에서 누른 버튼이 칸을 닫거나 값을 읽으면 마지막 글자를 잃는다. 그래서 조합 중인
 * 칸 밖을 누르면 그 버튼보다 먼저 칸에서 커서를 빼서 조합을 끝낸다. click에만 걸어서 스크롤하는 터치에는
 * 키보드가 닫히지 않는다.
 *
 * keep 안을 누를 때는 그대로 둔다: 커서를 칸에 둔 채 고르는 자동완성 목록.
 */
export function settleComposition(keep?: () => Element | null) {
  return (field: HTMLElement) => {
    let composing = false;

    const start = () => {
      composing = true;
    };

    const end = () => {
      composing = false;
    };

    const click = (event: MouseEvent) => {
      const target = event.target;

      if (!composing || !(target instanceof Node) || field.contains(target)) return;

      if (keep?.()?.contains(target)) return;

      field.blur();
    };

    field.addEventListener('compositionstart', start);
    field.addEventListener('compositionend', end);
    field.addEventListener('blur', end);
    // 누른 버튼의 click보다 먼저 받는다
    document.addEventListener('click', click, true);

    return () => {
      field.removeEventListener('compositionstart', start);
      field.removeEventListener('compositionend', end);
      field.removeEventListener('blur', end);
      document.removeEventListener('click', click, true);
    };
  };
}
