<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import * as Button from './index.js';
  import ButtonRoot from './button.svelte';

  const { Story } = defineMeta({
    title: 'UI/Button',
    component: ButtonRoot,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Button.Root>다음</Button.Root>
</Story>

<Story name="Outline">
  <Button.Root variant="outline">블럭 추가</Button.Root>
</Story>

<Story name="Ghost">
  <Button.Root variant="ghost" size="sm">다른 예시</Button.Root>
</Story>

<Story name="Destructive">
  <Button.Root variant="destructive" size="sm">삭제</Button.Root>
</Story>
