<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

import { createProtectedMediaObjectUrl } from '../../api/media'

const props = defineProps<{
  src?: string | null
  alt: string
}>()

const objectUrl = ref<string | null>(null)
let requestId = 0

function clearObjectUrl() {
  if (objectUrl.value) URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = null
}

watch(
  () => props.src,
  async (src) => {
    const currentRequestId = ++requestId
    clearObjectUrl()
    if (!src) return
    try {
      const nextObjectUrl = await createProtectedMediaObjectUrl(src)
      if (currentRequestId === requestId) {
        objectUrl.value = nextObjectUrl
      } else {
        URL.revokeObjectURL(nextObjectUrl)
      }
    } catch {
      if (currentRequestId === requestId) clearObjectUrl()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  requestId += 1
  clearObjectUrl()
})
</script>

<template>
  <img v-if="objectUrl" :src="objectUrl" :alt="alt" />
  <slot v-else />
</template>

<style scoped>
img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
