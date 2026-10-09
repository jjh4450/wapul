<script lang="ts">
  let { alt }: { alt?: string } = $props();
</script>

<!-- 외부 이미지를 불러오면 기록을 연 사람의 주소가 그 서버로 간다. 대체 글만 보인다 -->
{#if alt}<span class="text-muted-foreground">[이미지: {alt}]</span>{/if}
