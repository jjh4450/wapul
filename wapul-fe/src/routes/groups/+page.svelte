<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import GroupList from '#lib/components/GroupList.svelte';
</script>

<GroupList onopen={(groupId) => goto(resolve(`/groups/view?id=${groupId}`))} />
