<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { BACKEND, api } from '#lib/api/client.js';
  import { decodeShare } from '#lib/share.js';

  let error = $state('');

  /** 링크에 담긴 기록을 새 기록으로 만든다. 못 열면 null */
  async function open(payload: string): Promise<string | null> {
    try {
      const result = await api.createRecord(await decodeShare(payload));

      return result.ok ? result.data.id : null;
    } catch {
      return null;
    }
  }

  // 주소창에는 긴 본문 대신 기록 주소만 남긴다
  async function load() {
    if (BACKEND) return;

    error = '';

    const id = await open(location.hash.slice(1));

    if (id === null)
      error = '링크가 깨졌어요. 저장할 때 받은 링크를 끝까지 복사했는지 확인해 주세요.';
    else await goto(resolve(`/records/view?id=${id}`), { replaceState: true });
  }

  onMount(load);
</script>

<!-- 깨진 링크를 보고 같은 탭에 링크를 다시 붙여 넣으면 #뒤만 바뀌어 페이지가 다시 뜨지 않는다 -->
<svelte:window onhashchange={load} />

{#if BACKEND}
  <p class="text-muted-foreground">
    백엔드 없이 저장한 링크예요. 지금은 기록을 서버에 저장하므로 이 링크는 열지 않아요.
  </p>
{:else if error}
  <p class="text-destructive" role="alert">{error}</p>
{:else}
  <p class="text-muted-foreground">저장한 기록을 여는 중...</p>
{/if}
