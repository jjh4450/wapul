<script lang="ts">
  import { goto } from '$app/navigation';
  import { resolve } from '$app/paths';
  import { page } from '$app/state';
  import AnswerSheet from '#lib/components/AnswerSheet.svelte';

  const id = page.url.searchParams.get('id') ?? '';
</script>

<AnswerSheet
  {id}
  onfinish={() => goto(resolve(`/records/view?id=${id}&done=1`))}
  onnotowner={() => goto(resolve(`/records/view?id=${id}`))}
/>
