<script lang="ts">
  import './layout.css';
  import favicon from '#lib/assets/favicon.svg';
  import { resolve } from '$app/paths';
  import { BACKEND } from '#lib/api/client.js';
  import type { LayoutProps } from './$types';

  let { children }: LayoutProps = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <title>wapul</title>
</svelte:head>

<header class="border-b">
  <nav class="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm">
    <a href={resolve('/')} class="font-semibold">wapul</a>
    <a href={resolve('/records/new')} class="text-muted-foreground hover:text-foreground">새 기록</a
    >
    {#if BACKEND}
      <a href={resolve('/groups')} class="text-muted-foreground hover:text-foreground">그룹</a>
    {/if}
  </nav>
</header>

<main class="mx-auto max-w-6xl px-4 py-8">
  {@render children()}
</main>
