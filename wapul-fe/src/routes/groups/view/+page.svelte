<script lang="ts">
  import { page } from '$app/state';
  import GroupView from '#lib/components/GroupView.svelte';
</script>

<GroupView id={page.url.searchParams.get('id') ?? ''} />
