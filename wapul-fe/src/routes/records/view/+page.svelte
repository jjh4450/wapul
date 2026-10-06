<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import RecordResult from '#lib/components/RecordResult.svelte';
</script>

<RecordResult
  id={page.url.searchParams.get('id') ?? ''}
  done={page.url.searchParams.get('done') === '1'}
  ondeleted={() => goto(resolve('/'))}
/>
