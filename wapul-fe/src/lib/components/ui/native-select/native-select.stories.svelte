<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import * as NativeSelect from './index.js';
  import NativeSelectRoot from './native-select.svelte';

  const { Story } = defineMeta({
    title: 'UI/NativeSelect',
    component: NativeSelectRoot,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <NativeSelect.Root>
    <NativeSelect.Option value="cpp">C++</NativeSelect.Option>
    <NativeSelect.Option value="python">Python</NativeSelect.Option>
    <NativeSelect.Option value="java">Java</NativeSelect.Option>
  </NativeSelect.Root>
</Story>

<Story name="Small">
  <NativeSelect.Root size="sm">
    <NativeSelect.Option value="input">입력</NativeSelect.Option>
    <NativeSelect.Option value="logic">로직</NativeSelect.Option>
    <NativeSelect.Option value="output">출력</NativeSelect.Option>
  </NativeSelect.Root>
</Story>
