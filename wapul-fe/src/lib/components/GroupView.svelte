<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { api, type GroupDetail } from '#lib/api/client.js';
  import { Badge } from '#lib/components/ui/badge/index.js';
  import * as Card from '#lib/components/ui/card/index.js';
  import { LANGUAGE_LABEL, formatDate } from '#lib/study.js';

  let { id }: { id: string } = $props();

  let group = $state<GroupDetail | null>(null);

  let error = $state('');

  onMount(async () => {
    const result = await api.getGroup(id);

    if (result.ok) group = result.data;
    else error = result.message;
  });
</script>

{#if group}
  <div class="mb-8 grid gap-1">
    <h1 class="text-2xl font-semibold">{group.name}</h1>
    <p class="text-sm text-muted-foreground">
      초대 코드 <span class="font-mono font-medium text-foreground">{group.invite_code}</span>
    </p>
  </div>

  <div class="grid gap-10 lg:grid-cols-[1fr_16rem]">
    <section class="grid content-start gap-4">
      <h2 class="font-medium">공유된 기록</h2>
      {#if group.records.length === 0}
        <p class="text-sm text-muted-foreground">아직 공유된 기록이 없어요.</p>
      {/if}
      {#each group.records as record (record.id)}
        <a href={resolve(`/records/view?id=${record.id}`)}>
          <Card.Root class="hover:bg-muted/50">
            <Card.Header>
              <Card.Title>{record.problem}</Card.Title>
              <Card.Description>{record.key_idea}</Card.Description>
            </Card.Header>
            <Card.Content class="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">{LANGUAGE_LABEL[record.language]}</Badge>
              {record.owner_name} · {formatDate(record.shared_at)}
            </Card.Content>
          </Card.Root>
        </a>
      {/each}
    </section>

    <section class="grid content-start gap-2">
      <h2 class="font-medium">멤버</h2>
      <ul class="grid gap-1 text-sm">
        {#each group.members as member, i (i)}
          <li class="flex items-center gap-2">
            {member.display_name}
            {#if member.role === 'owner'}<Badge variant="secondary">그룹장</Badge>{/if}
          </li>
        {/each}
      </ul>
    </section>
  </div>
{:else if error}
  <p class="text-destructive">{error}</p>
{:else}
  <p class="text-muted-foreground">불러오는 중...</p>
{/if}
