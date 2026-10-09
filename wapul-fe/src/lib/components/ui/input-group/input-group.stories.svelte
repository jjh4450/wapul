<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { IconCopy, IconSearch } from '@tabler/icons-svelte';
  import { expect, fn } from 'storybook/test';
  import * as InputGroup from './index.js';
  import InputGroupRoot from './input-group.svelte';

  const { Story } = defineMeta({
    title: 'UI/InputGroup',
    component: InputGroupRoot,
    tags: ['autodocs']
  });

  const copy = fn();
</script>

<Story
  name="WithButton"
  play={async ({ canvas, userEvent }) => {
    // 칸 안 끝에 단추를 붙인다 (복사 칸)
    await userEvent.click(canvas.getByRole('button', { name: '복사' }));
    await expect(copy).toHaveBeenCalledOnce();
    await expect(canvas.getByRole('textbox', { name: '링크' })).toHaveValue(
      'https://wapul.example'
    );
  }}
>
  <InputGroup.Root>
    <InputGroup.Input readonly value="https://wapul.example" aria-label="링크" />
    <InputGroup.Addon align="inline-end">
      <InputGroup.Button size="icon-xs" aria-label="복사" onclick={copy}>
        <IconCopy />
      </InputGroup.Button>
    </InputGroup.Addon>
  </InputGroup.Root>
</Story>

<Story name="WithIcon">
  <InputGroup.Root>
    <InputGroup.Input placeholder="문제 찾기" aria-label="문제 찾기" />
    <InputGroup.Addon>
      <IconSearch />
    </InputGroup.Addon>
  </InputGroup.Root>
</Story>
