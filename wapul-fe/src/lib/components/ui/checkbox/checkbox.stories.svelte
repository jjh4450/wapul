<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { Checkbox } from './index.js';
  import { Label } from '../label/index.js';

  const { Story } = defineMeta({
    title: 'UI/Checkbox',
    component: Checkbox,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Label><Checkbox /> 처음 제출은 틀렸어요</Label>
</Story>

<Story name="Checked">
  <Label><Checkbox checked /> 처음 제출은 틀렸어요</Label>
</Story>
