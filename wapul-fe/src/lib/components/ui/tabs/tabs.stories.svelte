<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import * as Tabs from './index.js';
  import TabsRoot from './tabs.svelte';

  const { Story } = defineMeta({
    title: 'UI/Tabs',
    component: TabsRoot,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Tabs.Root value="a" class="w-96">
    <Tabs.List>
      <Tabs.Trigger value="a">전체 코드 먼저</Tabs.Trigger>
      <Tabs.Trigger value="b">블럭마다 코드와 설명</Tabs.Trigger>
    </Tabs.List>
    <Tabs.Content value="a">전체 코드 뒤에 블럭별 설명이 이어진다.</Tabs.Content>
    <Tabs.Content value="b">블럭 코드와 설명이 번갈아 나온다.</Tabs.Content>
  </Tabs.Root>
</Story>
