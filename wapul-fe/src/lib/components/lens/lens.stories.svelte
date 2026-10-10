<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import { expect } from 'storybook/test';
  import { Lens } from './index.js';

  const { Story } = defineMeta({
    title: 'Components/Lens',
    component: Lens,
    tags: ['autodocs']
  });

  // 블럭 색(로직 1)을 띤 코드 바탕 위에 놓는다. 유리는 바탕이 비쳐야 보인다
  const backdrop = 'grid gap-4 rounded-2xl bg-muted/40 p-6 font-mono text-sm';

  const tint = '--block: oklch(0.74 0.16 70)';
</script>

<Story
  name="Pane"
  args={{ size: 'pane' }}
  play={async ({ canvas }) => {
    // 돋보기 창: 둥근 모서리와 큰 그림자
    await expect(canvas.getByRole('group', { name: '화면 아래' })).toHaveClass('rounded-2xl');
  }}
>
  {#snippet template(args)}
    <div class={backdrop} style={tint}>
      <span>for (auto [e, s] : m) &#123;</span>
      <Lens {...args} role="group" aria-label="화면 아래" class="p-3 text-xs">
        <p class="m-0">119 &nbsp; v119 = 119</p>
        <p class="m-0">120 &nbsp; v120 = 120</p>
      </Lens>
    </div>
  {/snippet}
</Story>

<Story
  name="Bar"
  args={{ size: 'bar' }}
  play={async ({ canvasElement }) => {
    // 질문 묶음 막대: 얇은 알약 모양
    await expect(canvasElement.querySelector('[data-lens]')).toHaveClass('rounded-full');
  }}
>
  {#snippet template(args)}
    <div class={backdrop} style={tint}>
      <span>&#125;</span>
      <Lens {...args} data-lens class="flex h-2 gap-0.5">
        <span class="flex-1 bg-(--block)/65"></span>
        <span class="flex-1 bg-(--block)/15"></span>
      </Lens>
    </div>
  {/snippet}
</Story>

<Story
  name="BarTinted"
  args={{ size: 'bar', tint: 'block' }}
  play={async ({ canvasElement }) => {
    // 펼친 묶음의 막대는 블럭 색으로 물든다
    const bar = canvasElement.querySelector('[data-lens]');

    await expect(bar).toHaveClass('bg-(--block)/15');
    await expect(bar).not.toHaveClass('bg-white/30');
  }}
>
  {#snippet template(args)}
    <div class={backdrop} style={tint}>
      <span>&#125;</span>
      <Lens {...args} data-lens class="flex h-2 gap-0.5">
        <span class="flex-1 bg-(--block)/65"></span>
        <span class="flex-1 bg-(--block)/15"></span>
      </Lens>
    </div>
  {/snippet}
</Story>
