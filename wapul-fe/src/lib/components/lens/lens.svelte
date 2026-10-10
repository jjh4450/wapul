<script lang="ts" module>
  import { type VariantProps, tv } from 'tailwind-variants';
  import type { HTMLAttributes } from 'svelte/elements';
  import { cn, type WithElementRef } from '#lib/utils.js';

  /**
   * 물방울 같은 유리: 반투명 바탕, 비스듬한 반사광(before), 가장자리 굴절 띠와 맨 위의 테두리 빛, 그늘(after).
   * 코드 뷰의 돋보기 창(pane)과 답 쓰기의 질문 묶음 막대(bar)가 같이 쓰고, 크기에 따라 바깥 그림자와 안쪽 빛의
   * 번짐(--lens-glow), 왼쪽 위 반사(--lens-catch)만 다르다. 반사광은 블럭 색(--block)을 띤다. 바탕을
   * 흐리게(backdrop-blur) 하면 굴절 띠가 반투명한 창 안만 보고 겹쳐 그려지므로 흐리지 않는다
   */
  export const lensVariants = tv({
    base: 'relative overflow-hidden before:pointer-events-none before:absolute before:inset-0 before:bg-linear-to-br before:from-white/60 before:via-white/0 before:via-35% before:to-(--block)/10 after:pointer-events-none after:absolute after:inset-0 after:rounded-[inherit] after:shadow-[inset_0_0_0_1px_rgb(255_255_255/0.75),inset_0_1px_0_rgb(255_255_255),inset_0_0_var(--lens-glow)_rgb(0_0_0/0.08),var(--lens-catch),inset_-1px_-1px_0_rgb(0_0_0/0.06)] dark:before:from-white/15 dark:after:shadow-[inset_0_0_0_1px_rgb(255_255_255/0.15),inset_0_1px_0_rgb(255_255_255/0.3),inset_0_0_var(--lens-glow)_rgb(0_0_0/0.4)]',
    variants: {
      size: {
        pane: 'rounded-2xl shadow-[0_12px_32px_-12px_rgb(0_0_0/0.35),0_1px_2px_rgb(0_0_0/0.08)] [--lens-catch:inset_8px_8px_12px_-10px_rgb(255_255_255)] [--lens-glow:16px]',
        // 얇아서 안쪽 빛을 좁히고 왼쪽 위 반사는 뺀다
        bar: 'rounded-full shadow-[0_3px_8px_-4px_rgb(0_0_0/0.3),0_1px_1px_rgb(0_0_0/0.06)] [--lens-catch:0_0_#0000] [--lens-glow:3px]'
      },
      tint: {
        clear: 'bg-white/30 dark:bg-white/5',
        // 블럭 색으로 물든 유리 (펼친 질문 묶음)
        block: 'bg-(--block)/15'
      }
    },
    defaultVariants: {
      size: 'pane',
      tint: 'clear'
    }
  });

  export type LensSize = VariantProps<typeof lensVariants>['size'];

  export type LensTint = VariantProps<typeof lensVariants>['tint'];

  export type LensProps = WithElementRef<HTMLAttributes<HTMLDivElement>> & {
    size?: LensSize;
    tint?: LensTint;
  };
</script>

<script lang="ts">
  let {
    class: className,
    size = 'pane',
    tint = 'clear',
    ref = $bindable(null),
    children,
    ...restProps
  }: LensProps = $props();
</script>

<div bind:this={ref} class={cn(lensVariants({ size, tint }), className)} {...restProps}>
  {@render children?.()}
</div>
