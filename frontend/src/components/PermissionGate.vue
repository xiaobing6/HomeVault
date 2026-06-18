<script setup lang="ts">
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ permission: string }>()
const auth = useAuthStore()
</script>

<template>
  <slot v-if="auth.hasPermission(props.permission)" />
</template>
