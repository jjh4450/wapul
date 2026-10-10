<script lang="ts">
  import Markdown, { type Plugin } from 'svelte-exmarkdown';
  import { gfmPlugin } from 'svelte-exmarkdown/gfm';
  import Code from './code.svelte';
  import Image from './image.svelte';
  import Link from './link.svelte';

  let {
    source
  }: {
    /** 그릴 md. 공유 링크로 남이 만든 기록도 오므로 믿지 않는다 */
    source: string;
  } = $props();

  // 날 HTML은 글자 그대로 그린다(vector<int>도 사라지지 않는다). 링크, 이미지, 코드 블럭만 바꿔 그린다
  const plugins: Plugin[] = [gfmPlugin(), { renderer: { a: Link, img: Image, pre: Code } }];
</script>

<div
  data-clarity-mask="true"
  class="prose max-w-none dark:prose-invert prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-normal prose-code:before:content-none prose-code:after:content-none"
>
  <Markdown md={source} {plugins} />
</div>
