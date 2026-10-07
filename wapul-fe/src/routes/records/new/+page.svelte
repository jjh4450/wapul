<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import NewRecordForm from '#lib/components/NewRecordForm.svelte';
</script>

<NewRecordForm
  oncreated={(id) => goto(resolve(`/records/blocks?id=${id}`))}
  onsaved={(id) => goto(resolve(`/records/write?id=${id}`))}
/>
