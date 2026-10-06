<script lang="ts">
  import { onMount } from 'svelte';
  import { resolve } from '$app/paths';
  import { api, type RecordSummary } from '#lib/api/client.js';
  import { Badge } from '#lib/components/ui/badge/index.js';
  import { Button } from '#lib/components/ui/button/index.js';
  import * as Card from '#lib/components/ui/card/index.js';
  import { LANGUAGE_LABEL, formatDate } from '#lib/study.js';

  let records = $state<RecordSummary[] | null>(null);

  let error = $state('');

  onMount(async () => {
    const result = await api.listRecords();

    if (result.ok) records = result.data;
    else error = result.message;
  });
</script>

<div class="mb-6 flex items-center justify-between">
  <h1 class="text-2xl font-semibold">내 풀이 기록</h1>
  <Button href={resolve('/records/new')}>새 기록</Button>
</div>

{#if error}
  <p class="text-destructive">{error}</p>
{:else if records === null}
  <p class="text-muted-foreground">불러오는 중...</p>
{:else if records.length === 0}
  <p class="text-muted-foreground">아직 기록이 없어요. 맞은 풀이 하나로 첫 기록을 시작해 보세요.</p>
{:else}
  <div class="grid gap-4 md:grid-cols-2">
    {#each records as record (record.id)}
      <Card.Root>
        <Card.Header>
          <Card.Title>{record.problem}</Card.Title>
          <Card.Description>{record.key_idea}</Card.Description>
        </Card.Header>
        <Card.Content class="flex items-center gap-2 text-sm text-muted-foreground">
          <Badge variant="outline">{LANGUAGE_LABEL[record.language]}</Badge>
          {formatDate(record.updated_at)}
        </Card.Content>
        <Card.Footer class="gap-2">
          <Button size="sm" variant="outline" href={resolve(`/records/write?id=${record.id}`)}
            >이어서 쓰기</Button
          >
          <Button size="sm" variant="ghost" href={resolve(`/records/view?id=${record.id}`)}
            >결과물</Button
          >
        </Card.Footer>
      </Card.Root>
    {/each}
  </div>
{/if}
