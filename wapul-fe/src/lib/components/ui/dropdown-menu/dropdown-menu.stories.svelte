<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, within } from 'storybook/test';
  import { buttonVariants } from '#lib/components/ui/button/index.js';
  import * as DropdownMenu from './index.js';
  import DropdownMenuRoot from './dropdown-menu.svelte';

  const { Story } = defineMeta({
    title: 'UI/DropdownMenu',
    component: DropdownMenuRoot,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <DropdownMenu.Root>
    <DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>열기</DropdownMenu.Trigger>
    <DropdownMenu.Content class="w-40" align="start">
      <DropdownMenu.Group>
        <DropdownMenu.Label>기록</DropdownMenu.Label>
        <DropdownMenu.Item>이어서 쓰기</DropdownMenu.Item>
        <DropdownMenu.Item>결과물</DropdownMenu.Item>
      </DropdownMenu.Group>
      <DropdownMenu.Separator />
      <DropdownMenu.Item disabled>지우기</DropdownMenu.Item>
    </DropdownMenu.Content>
  </DropdownMenu.Root>
</Story>

<Story
  name="RadioGroup"
  play={async ({ canvas, userEvent }) => {
    // 메뉴는 포털로 body에 그려진다
    const body = within(document.body);

    await userEvent.click(canvas.getByRole('button', { name: '종류' }));
    await expect(await body.findByRole('menuitemradio', { name: '로직' })).toBeChecked();
  }}
>
  <DropdownMenu.Root>
    <DropdownMenu.Trigger class={buttonVariants({ variant: 'outline' })}>종류</DropdownMenu.Trigger>
    <DropdownMenu.Content class="w-32" align="start">
      <DropdownMenu.Group>
        <DropdownMenu.Label>종류</DropdownMenu.Label>
        <DropdownMenu.RadioGroup value="logic">
          <DropdownMenu.RadioItem value="input">입력</DropdownMenu.RadioItem>
          <DropdownMenu.RadioItem value="logic">로직</DropdownMenu.RadioItem>
          <DropdownMenu.RadioItem value="output">출력</DropdownMenu.RadioItem>
        </DropdownMenu.RadioGroup>
      </DropdownMenu.Group>
    </DropdownMenu.Content>
  </DropdownMenu.Root>
</Story>
