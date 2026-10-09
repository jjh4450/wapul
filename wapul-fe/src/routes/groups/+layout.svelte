<script lang="ts">
  import { BACKEND } from '#lib/api/client.js';
  import type { LayoutProps } from './$types';

  let { children }: LayoutProps = $props();
</script>

<!-- 백엔드를 끈 배포에는 그룹이 없다. 메뉴에서 숨기고, 주소로 들어와도 안내만 한다 -->
{#if BACKEND}
  {@render children()}
{:else}
  <p class="text-muted-foreground">그룹은 백엔드가 생기면 쓸 수 있어요.</p>
{/if}
