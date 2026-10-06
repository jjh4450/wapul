<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { Input } from './index.js';

  const { Story } = defineMeta({
    title: 'UI/Input',
    component: Input,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Input class="w-80" placeholder="문제 제목이나 링크" />
</Story>
