<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, waitFor, within } from 'storybook/test';
  import { buttonVariants } from '#lib/components/ui/button/index.js';
  import * as Dialog from './index.js';
  import DialogRoot from './dialog.svelte';

  const { Story } = defineMeta({
    title: 'UI/Dialog',
    component: DialogRoot,
    tags: ['autodocs']
  });
</script>

<Story
  name="Default"
  play={async ({ canvas, userEvent }) => {
    // 대화상자는 포털로 body에 그려진다
    const body = within(document.body);

    await userEvent.click(canvas.getByRole('button', { name: '열기' }));
    await expect(await body.findByRole('dialog')).toHaveTextContent('링크를 드릴게요');
    await userEvent.click(body.getByRole('button', { name: '닫기' }));
    // 닫히는 애니메이션이 끝나야 사라진다
    await waitFor(() => expect(body.queryByRole('dialog')).not.toBeInTheDocument());
  }}
>
  <Dialog.Root>
    <Dialog.Trigger class={buttonVariants({ variant: 'outline' })}>열기</Dialog.Trigger>
    <Dialog.Content>
      <Dialog.Header>
        <Dialog.Title>링크를 드릴게요</Dialog.Title>
        <Dialog.Description>바깥을 누르거나 Esc로도 닫을 수 있어요.</Dialog.Description>
      </Dialog.Header>
    </Dialog.Content>
  </Dialog.Root>
</Story>
