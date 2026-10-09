<script lang="ts">
  import { IconCheck, IconCopy } from '@tabler/icons-svelte';
  import * as Dialog from '#lib/components/ui/dialog/index.js';
  import * as InputGroup from '#lib/components/ui/input-group/index.js';

  let {
    link,
    open = $bindable(false)
  }: {
    /** 기록을 담은 링크 */
    link: string;
    open?: boolean;
  } = $props();

  let input = $state<HTMLInputElement | null>(null);

  let copied = $state(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      copied = true;
    } catch {
      // 클립보드를 쓸 수 없으면 링크를 골라 두어 직접 복사하게 한다
      input?.select();
    }
  }
</script>

<Dialog.Root bind:open onOpenChange={() => (copied = false)}>
  <Dialog.Content class="sm:max-w-xl">
    <Dialog.Header>
      <Dialog.Title>아앗! 아직 저장할 백엔드가 없어요...</Dialog.Title>
      <Dialog.Description>
        하지만 이 내용을 저장한 링크를 드릴게요! 이 링크로 들어오면 지금 모습 그대로 열려요.
      </Dialog.Description>
    </Dialog.Header>

    <InputGroup.Root>
      <InputGroup.Input
        bind:ref={input}
        readonly
        value={link}
        aria-label="저장 링크"
        class="font-mono text-xs"
        onfocus={() => input?.select()}
      />
      <InputGroup.Addon align="inline-end">
        <InputGroup.Button
          size="icon-xs"
          aria-label={copied ? '복사했어요' : '링크 복사'}
          onclick={copy}
        >
          {#if copied}<IconCheck />{:else}<IconCopy />{/if}
        </InputGroup.Button>
      </InputGroup.Addon>
    </InputGroup.Root>
    <!-- 아이콘만 바뀌면 화면 낭독기는 복사된 줄 모른다 -->
    <p class="sr-only" aria-live="polite">{copied ? '링크를 복사했어요.' : ''}</p>

    <!-- 쿠키를 남기지 않는 youtube-nocookie 주소로 넣는다 -->
    <iframe
      class="aspect-video w-full rounded-2xl"
      src="https://www.youtube-nocookie.com/embed/pCOBmmJARPE"
      title="진정한 남자들은 DB를 쓰지 않습니다"
      allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
      referrerpolicy="strict-origin-when-cross-origin"
      allowfullscreen
    ></iframe>
  </Dialog.Content>
</Dialog.Root>
