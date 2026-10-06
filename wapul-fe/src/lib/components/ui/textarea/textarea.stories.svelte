<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { Textarea } from './index.js';

  const { Story } = defineMeta({
    title: 'UI/Textarea',
    component: Textarea,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Textarea class="w-96" placeholder="정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다..." />
</Story>
