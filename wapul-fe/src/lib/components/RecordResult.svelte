<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { api, type GroupOut, type LayoutOut, type RecordOut } from '#lib/api/client.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import { Checkbox } from '#lib/components/ui/checkbox/index.js';
  import { Label } from '#lib/components/ui/label/index.js';
  import * as Tabs from '#lib/components/ui/tabs/index.js';

  let {
    id,
    done = false,
    ondeleted
  }: {
    id: string;
    /** 답을 다 쓰고 막 넘어왔을 때 완성 안내를 띄운다 */
    done?: boolean;
    ondeleted: () => void;
  } = $props();

  let record = $state<RecordOut | null>(null);

  let layouts = $state<LayoutOut[]>([]);

  let selected = $state('');

  let groups = $state<GroupOut[]>([]);

  let shared = $state<string[]>([]);

  let error = $state('');

  let status = $state('');

  const current = $derived(layouts.find((l) => l.id === selected));

  onMount(async () => {
    const [recordResult, layoutResult] = await Promise.all([api.getRecord(id), api.getLayouts(id)]);

    if (!recordResult.ok) {
      error = recordResult.message;

      return;
    }

    if (!layoutResult.ok) {
      error = layoutResult.message;

      return;
    }

    record = recordResult.data;
    layouts = layoutResult.data;
    selected = layouts[0]?.id ?? '';
    shared = [...recordResult.data.group_ids];

    if (recordResult.data.is_owner) {
      const groupResult = await api.listGroups();

      if (groupResult.ok) groups = groupResult.data;
    }
  });

  async function copy() {
    if (!current) return;
    await navigator.clipboard.writeText(current.markdown);
    status = 'md를 복사했어요.';
  }

  function download() {
    if (!current || !record) return;
    const url = URL.createObjectURL(new Blob([current.markdown], { type: 'text/markdown' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${record.problem.replace(/[\\/:*?"<>|]/g, '_')}.md`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function toggleShare(groupId: string, on: boolean) {
    shared = on ? [...shared, groupId] : shared.filter((g) => g !== groupId);
  }

  async function saveShares() {
    const result = await api.updateShares(id, shared);
    status = result.ok ? '공유 범위를 저장했어요.' : result.message;
  }

  async function remove() {
    if (!confirm('이 기록을 지울까요? 되돌릴 수 없어요.')) return;
    const result = await api.deleteRecord(id);

    if (result.ok) ondeleted();
    else status = result.message;
  }
</script>

{#if record}
  {#if done}
    <p class="mb-6 rounded-2xl bg-primary/10 px-4 py-3 font-medium">글감이 완성됐어요!</p>
  {/if}

  <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-semibold">{record.problem}</h1>
      <p class="text-sm text-muted-foreground">{record.owner_name}</p>
    </div>
    {#if record.is_owner}
      <div class="flex gap-2">
        <Button variant="outline" size="sm" href={resolve(`/records/write?id=${id}`)}
          >답 고치기</Button
        >
        <Button variant="destructive" size="sm" onclick={remove}>지우기</Button>
      </div>
    {/if}
  </div>

  <p class="mb-3 text-sm text-muted-foreground">
    배치안을 골라 md로 받으세요. 배치안마다 순서만 다르고, 쓴 문장은 그대로예요.
  </p>
  <Tabs.Root bind:value={selected}>
    <Tabs.List>
      {#each layouts as layout (layout.id)}
        <Tabs.Trigger value={layout.id}>{layout.title}</Tabs.Trigger>
      {/each}
    </Tabs.List>
    {#each layouts as layout (layout.id)}
      <Tabs.Content value={layout.id}>
        <pre
          class="overflow-x-auto rounded-2xl bg-muted p-4 text-sm leading-6 whitespace-pre-wrap">{layout.markdown}</pre>
      </Tabs.Content>
    {/each}
  </Tabs.Root>

  <div class="mt-4 flex items-center gap-2">
    <Button onclick={download}>md 받기</Button>
    <Button variant="outline" onclick={copy}>md 복사</Button>
    <span class="text-sm text-muted-foreground">{status}</span>
  </div>

  {#if record.is_owner}
    <section class="mt-10 grid max-w-xl gap-3">
      <h2 class="font-medium">그룹에 공유</h2>
      {#if groups.length === 0}
        <p class="text-sm text-muted-foreground">
          속한 그룹이 없어요. <a href={resolve('/groups')} class="underline underline-offset-4"
            >그룹 만들기·가입</a
          >
        </p>
      {:else}
        {#each groups as group (group.id)}
          <Label class="font-normal">
            <Checkbox
              checked={shared.includes(group.id)}
              onCheckedChange={(on) => toggleShare(group.id, on)}
            />
            {group.name}
          </Label>
        {/each}
        <Button variant="outline" size="sm" class="justify-self-start" onclick={saveShares}
          >공유 저장</Button
        >
      {/if}
    </section>
  {/if}
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}
