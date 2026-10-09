<script lang="ts">
  import type { Snippet } from 'svelte';

  let { href, children }: { href?: string; children?: Snippet } = $props();

  // javascript: 같은 주소는 링크로 만들지 않고 글자만 남긴다
  const safe = $derived(href !== undefined && /^(https?:|mailto:)/i.test(href));
</script>

{#if safe}
  <a {href} target="_blank" rel="noopener noreferrer nofollow">{@render children?.()}</a>
{:else}
  <span>{@render children?.()}</span>
{/if}
