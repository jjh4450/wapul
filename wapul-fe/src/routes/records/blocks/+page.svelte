<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import BlockEditor from '#lib/components/BlockEditor.svelte';

  const id = page.url.searchParams.get('id') ?? '';
</script>

<BlockEditor {id} onsaved={(saved) => goto(resolve(`/records/write?id=${saved}`))} />
