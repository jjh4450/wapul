<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import * as Card from './index.js';
  import CardRoot from './card.svelte';

  const { Story } = defineMeta({
    title: 'UI/Card',
    component: CardRoot,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Card.Root class="w-80">
    <Card.Header>
      <Card.Title>BOJ 1931 회의실 배정</Card.Title>
      <Card.Description>끝나는 시간이 빠른 회의부터 고른다</Card.Description>
    </Card.Header>
    <Card.Content>python · 2026-10-05</Card.Content>
  </Card.Root>
</Story>
