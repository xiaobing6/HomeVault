<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import CategoryFieldPanel from '../components/config/CategoryFieldPanel.vue'
import DictionaryPanel from '../components/config/DictionaryPanel.vue'
import FamilyMemberPanel from '../components/config/FamilyMemberPanel.vue'
import ResidenceLocationPanel from '../components/config/ResidenceLocationPanel.vue'
import { useAuthStore } from '../stores/auth'
import { useConfigurationStore } from '../stores/configuration'

const auth = useAuthStore()
const configuration = useConfigurationStore()
const route = useRoute()
const { loading } = storeToRefs(configuration)
const canReadConfig = auth.hasPermission('items:view')
const sectionNames = ['residence-location', 'family-members', 'category-fields', 'status-dictionaries'] as const
type SectionName = typeof sectionNames[number]

const activeSection = computed(() => normalizeSection(route.query.section))

onMounted(async () => {
  if (!canReadConfig) return

  try {
    await configuration.load()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})

function normalizeSection(section: unknown): SectionName {
  return typeof section === 'string' && sectionNames.includes(section as SectionName)
    ? section as SectionName
    : 'residence-location'
}
</script>

<template>
  <section class="core-config-page" v-loading="loading">
    <el-alert
      v-if="!canReadConfig"
      title="缺少物品查看权限，无法读取核心配置。"
      type="error"
      show-icon
      :closable="false"
    />

    <template v-else>
      <ResidenceLocationPanel v-if="activeSection === 'residence-location'" />
      <FamilyMemberPanel v-else-if="activeSection === 'family-members'" />
      <CategoryFieldPanel v-else-if="activeSection === 'category-fields'" />
      <DictionaryPanel v-else-if="activeSection === 'status-dictionaries'" />
    </template>
  </section>
</template>

<style scoped>
.core-config-page {
  min-width: 0;
  width: 100%;
}
</style>
