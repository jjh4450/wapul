<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { startAnalytics } from '#lib/analytics.js';
  import { BACKEND, api, type RecordCreate } from '#lib/api/client.js';
  import { holds, unpackRecord } from '#lib/share.js';

  let error = $state('');

  /** 링크와 내용이 같은, 이 브라우저에 담아 둔 기록. 같은 링크를 다시 열 때 사본이 쌓이지 않게 쓴다 */
  async function kept(content: RecordCreate): Promise<string | null> {
    const listed = await api.listRecords();

    for (const { id } of listed.ok ? listed.data : []) {
      const record = await api.getRecord(id);

      if (record.ok && holds(record.data, content)) return id;
    }

    return null;
  }

  /** 링크에 담긴 기록을 연다. 같은 기록이 없으면 새로 만든다. 못 열면 null */
  async function open(payload: string): Promise<string | null> {
    try {
      const content = await unpackRecord(payload);

      const same = await kept(content);

      if (same !== null) return same;

      const result = await api.createRecord(content);

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

    if (id === null) {
      error = '링크가 깨졌어요. 저장할 때 받은 링크를 끝까지 복사했는지 확인해 주세요.';

      return;
    }

    await goto(resolve(`/records/view?id=${id}`), { replaceState: true });
    // 주소에서 링크 본문이 빠졌으니 방문 분석을 켠다 (hooks.client.ts)
    startAnalytics();
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
