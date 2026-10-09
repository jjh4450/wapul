<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, spyOn, within } from 'storybook/test';
  import SaveLinkDialog from './SaveLinkDialog.svelte';

  const link = 'https://wapul.example/share#v1.q1YqSs1JTS4tUrJSUEpKzFNSqgUA';

  // 열린 모달이 문서를 덮으므로 autodocs는 쓰지 않는다. 모달은 body에 붙어서 body에서 찾는다
  const { Story } = defineMeta({
    title: 'Components/SaveLinkDialog',
    component: SaveLinkDialog,
    args: { link, open: true }
  });

  function clipboard(result: 'ok' | 'blocked') {
    return () => {
      const write = spyOn(navigator.clipboard, 'writeText');

      if (result === 'ok') write.mockResolvedValue();
      else write.mockRejectedValue(new DOMException('denied', 'NotAllowedError'));

      return () => write.mockRestore();
    };
  }
</script>

<Story
  name="Open"
  beforeEach={clipboard('ok')}
  play={async ({ canvasElement, userEvent }) => {
    const page = within(canvasElement.ownerDocument.body);

    await expect(await page.findByText('아앗! 아직 저장할 백엔드가 없어요...')).toBeInTheDocument();
    await expect(page.getByRole('textbox', { name: '저장 링크' })).toHaveValue(link);
    await expect(page.getByTitle('진정한 남자들은 DB를 쓰지 않습니다')).toHaveAttribute(
      'src',
      'https://www.youtube-nocookie.com/embed/pCOBmmJARPE'
    );

    await userEvent.click(page.getByRole('button', { name: '링크 복사' }));
    await expect(navigator.clipboard.writeText).toHaveBeenCalledWith(link);
    await expect(page.getByRole('button', { name: '복사했어요' })).toBeInTheDocument();
  }}
/>

<Story
  name="ClipboardBlocked"
  beforeEach={clipboard('blocked')}
  play={async ({ canvasElement, userEvent }) => {
    const page = within(canvasElement.ownerDocument.body);

    await userEvent.click(await page.findByRole('button', { name: '링크 복사' }));

    // 복사하지 못하면 링크 전체를 골라 두어 직접 복사할 수 있다
    const box = page.getByRole('textbox', { name: '저장 링크' });

    await expect(box).toHaveProperty('selectionStart', 0);
    await expect(box).toHaveProperty('selectionEnd', link.length);
    await expect(page.getByRole('button', { name: '링크 복사' })).toBeInTheDocument();
  }}
/>
