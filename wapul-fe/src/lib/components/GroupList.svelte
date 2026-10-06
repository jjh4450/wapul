<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { api, type GroupOut } from '#lib/api/client.js';
  import { Badge } from '#lib/components/ui/badge/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import * as Card from '#lib/components/ui/card/index.js';
  import { Input } from '#lib/components/ui/input/index.js';

  let { onopen }: { onopen: (groupId: string) => void } = $props();

  let groups = $state<GroupOut[] | null>(null);

  let name = $state('');

  let inviteCode = $state('');

  let error = $state('');

  onMount(async () => {
    const result = await api.listGroups();

    if (result.ok) groups = result.data;
    else error = result.message;
  });

  async function create(event: SubmitEvent) {
    event.preventDefault();
    const result = await api.createGroup(name.trim());

    if (result.ok) onopen(result.data.id);
    else error = result.message;
  }

  async function join(event: SubmitEvent) {
    event.preventDefault();
    const result = await api.joinGroup(inviteCode.trim());

    if (result.ok) onopen(result.data.id);
    else error = result.message;
  }
</script>

<h1 class="mb-6 text-2xl font-semibold">그룹</h1>

<div class="mb-10 grid gap-6 md:grid-cols-2">
  <form class="grid gap-2" onsubmit={create}>
    <label for="group-name" class="text-sm font-medium">새 그룹 만들기</label>
    <div class="flex gap-2">
      <Input id="group-name" bind:value={name} placeholder="그룹 이름" />
      <Button type="submit" disabled={name.trim() === ''}>만들기</Button>
    </div>
  </form>
  <form class="grid gap-2" onsubmit={join}>
    <label for="invite-code" class="text-sm font-medium">초대 코드로 가입</label>
    <div class="flex gap-2">
      <Input id="invite-code" bind:value={inviteCode} placeholder="ABCD2345" />
      <Button type="submit" variant="outline" disabled={inviteCode.trim() === ''}>가입</Button>
    </div>
  </form>
</div>

{#if error}
  <p class="mb-4 text-destructive">{error}</p>
{/if}

{#if groups === null}
  <p class="text-muted-foreground">불러오는 중...</p>
{:else if groups.length === 0}
  <p class="text-muted-foreground">아직 속한 그룹이 없어요.</p>
{:else}
  <div class="grid gap-4 md:grid-cols-2">
    {#each groups as group (group.id)}
      <a href={resolve(`/groups/view?id=${group.id}`)}>
        <Card.Root class="hover:bg-muted/50">
          <Card.Header>
            <Card.Title>{group.name}</Card.Title>
            <Card.Description>멤버 {group.member_count}명</Card.Description>
            <Card.Action>
              <Badge variant={group.role === 'owner' ? 'default' : 'secondary'}
                >{group.role === 'owner' ? '그룹장' : '멤버'}</Badge
              >
            </Card.Action>
          </Card.Header>
        </Card.Root>
      </a>
    {/each}
  </div>
{/if}
