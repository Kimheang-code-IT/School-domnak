<script setup lang="ts">
/** Unknown routes (static SPA) — show the global error page with 404. */
throw createError({
  statusCode: 404,
  statusMessage: 'Page not found',
  fatal: true,
})
</script>
