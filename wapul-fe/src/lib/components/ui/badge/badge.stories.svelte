<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { Badge } from './index.js';

  const { Story } = defineMeta({
    title: 'UI/Badge',
    component: Badge,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Badge>로직</Badge>
</Story>

<Story name="Secondary">
  <Badge variant="secondary">입력</Badge>
</Story>

<Story name="Outline">
  <Badge variant="outline">python</Badge>
</Story>
