<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect, within } from 'storybook/test';
  import { record } from '#lib/api/fixtures.js';
  import { buildLayouts } from '#lib/layouts.js';
  import { MarkdownView } from './index.js';

  const { Story } = defineMeta({
    title: 'Components/MarkdownView',
    component: MarkdownView,
    tags: ['autodocs']
  });

  // 공유 링크로 누구나 만들 수 있는 md: 위험한 링크, 날 HTML, 외부 이미지, PS 글에 흔한 꺾쇠
  const untrusted = [
    '[눌러 보세요](javascript:alert(1))',
    '',
    '<img src=x onerror="alert(1)"> <iframe src="https://evil.example"></iframe>',
    '',
    '![추적](https://tracker.example/pixel.png)',
    '',
    '`vector<int>`에 담고 a<b and c>d 이면 넘긴다. [문서](https://example.com)'
  ].join('\n');
</script>

<Story
  name="WriteUp"
  args={{ source: buildLayouts(record)[1].markdown }}
  play={async ({ canvasElement }) => {
    const view = within(canvasElement);

    await expect(view.getByRole('heading', { name: '문제' })).toBeInTheDocument();

    // 블럭 코드는 코드 화면과 같은 색으로 칠한다
    const code = canvasElement.querySelector('pre');

    await expect(code).toHaveTextContent('int n; cin >> n;');
    await expect(code?.querySelector('.text-code-keyword')).toHaveTextContent('int');
  }}
/>

<Story
  name="Untrusted"
  args={{ source: untrusted }}
  play={async ({ canvasElement }) => {
    const view = within(canvasElement);

    // 위험한 주소는 링크가 아니라 글자로만 남는다
    await expect(view.getByText('눌러 보세요').closest('a')).toBeNull();
    await expect(view.getByRole('link', { name: '문서' })).toHaveAttribute(
      'href',
      'https://example.com'
    );

    // 날 HTML은 요소가 되지 않고 글자로 보이며, 외부 이미지는 불러오지 않는다
    await expect(canvasElement.querySelector('img, iframe')).toBeNull();
    await expect(canvasElement).toHaveTextContent('<iframe src="https://evil.example"></iframe>');
    await expect(view.getByText('[이미지: 추적]')).toBeInTheDocument();
    await expect(canvasElement).toHaveTextContent('vector<int>에 담고 a<b and c>d 이면 넘긴다.');
  }}
/>
