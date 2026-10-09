<script lang="ts">
  import { getAstNode, type HastNode } from 'svelte-exmarkdown';
  import type { Language } from '#lib/api/client.js';
  import { highlight, type Tint } from '#lib/highlight.js';
  import { LANGUAGE_LABEL } from '#lib/study.js';

  // SAFETY: LANGUAGE_LABEL은 satisfies로 Language의 모든 값을, 그 값만 키로 가진다
  const languages = Object.keys(LANGUAGE_LABEL) as Language[];

  const node: { current: HastNode } = getAstNode();

  /** 노드 안의 글자를 모두 잇는다 */
  function text(n: HastNode): string {
    if (n.type === 'text' || n.type === 'raw') return n.value;

    return n.type === 'element' || n.type === 'root' ? n.children.map(text).join('') : '';
  }

  // pre > code(class="language-cpp") > 글자. 아는 언어면 코드 화면과 같은 색으로 칠한다
  const code = $derived(
    node.current.type === 'element'
      ? node.current.children.find((c) => c.type === 'element' && c.tagName === 'code')
      : undefined
  );

  // 라이브러리가 hast의 className 배열을 class 문자열로 바꿔 둔다
  const classes = $derived(
    code?.type === 'element' ? String(code.properties?.class ?? '').split(/\s+/) : []
  );

  const language = $derived(languages.find((l) => classes.includes(`language-${l}`)));

  const source = $derived((code ? text(code) : text(node.current)).replace(/\n$/, ''));

  const tints = $derived(language ? highlight(source, language) : []);

  /** 한 줄을 색 조각대로 나눈다. 칸은 글자(코드 포인트) 단위다 */
  function runs(line: string, tint: Tint[] = []) {
    const chars = [...line];
    const out: { text: string; color: string | undefined }[] = [];
    let col = 0;

    for (const t of tint) {
      if (t.from > col) out.push({ text: chars.slice(col, t.from).join(''), color: undefined });
      out.push({ text: chars.slice(t.from, t.to).join(''), color: t.color });
      col = t.to;
    }

    if (col < chars.length) out.push({ text: chars.slice(col).join(''), color: undefined });

    return out;
  }
</script>

<pre
  class="not-prose my-4 overflow-x-auto rounded-xl bg-muted p-4 font-mono text-sm leading-6"><code
    >{#each source.split('\n') as line, i (i)}<span class="block min-h-lh whitespace-pre"
        >{#each runs(line, tints[i]) as run, k (k)}{#if run.color}<span class={run.color}
              >{run.text}</span
            >{:else}{run.text}{/if}{/each}</span
      >{/each}</code
  ></pre>
