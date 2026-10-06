<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { Label } from './index.js';
  import { Input } from '../input/index.js';

  const { Story } = defineMeta({
    title: 'UI/Label',
    component: Label,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <div class="grid w-80 gap-2">
    <Label for="problem">문제</Label>
    <Input id="problem" />
  </div>
</Story>
