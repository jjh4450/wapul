<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, waitFor, within } from 'storybook/test';
  import { buttonVariants } from '#lib/components/ui/button/index.js';
  import * as AlertDialog from './index.js';
  import AlertDialogRoot from './alert-dialog.svelte';

  const { Story } = defineMeta({
    title: 'UI/AlertDialog',
    component: AlertDialogRoot,
    tags: ['autodocs']
  });
</script>

<Story
  name="Default"
  play={async ({ canvas, userEvent }) => {
    // 대화상자는 포털로 body에 그려진다
    const body = within(document.body);

    await userEvent.click(canvas.getByRole('button', { name: '열기' }));
    await expect(await body.findByRole('alertdialog')).toHaveTextContent('정말 지울까요?');
    await userEvent.click(body.getByRole('button', { name: '그만두기' }));
    // 닫히는 애니메이션이 끝나야 사라진다
    await waitFor(() => expect(body.queryByRole('alertdialog')).not.toBeInTheDocument());
  }}
>
  <AlertDialog.Root>
    <AlertDialog.Trigger class={buttonVariants({ variant: 'outline' })}>열기</AlertDialog.Trigger>
    <AlertDialog.Content>
      <AlertDialog.Header>
        <AlertDialog.Title>정말 지울까요?</AlertDialog.Title>
        <AlertDialog.Description>지운 기록은 되돌릴 수 없어요.</AlertDialog.Description>
      </AlertDialog.Header>
      <AlertDialog.Footer>
        <AlertDialog.Cancel>그만두기</AlertDialog.Cancel>
        <AlertDialog.Action>지우기</AlertDialog.Action>
      </AlertDialog.Footer>
    </AlertDialog.Content>
  </AlertDialog.Root>
</Story>
