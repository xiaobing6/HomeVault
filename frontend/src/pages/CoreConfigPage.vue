<script setup lang="ts">
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'

import { getChineseErrorMessage } from '../api/client'
import CategoryFieldPanel from '../components/config/CategoryFieldPanel.vue'
import DictionaryPanel from '../components/config/DictionaryPanel.vue'
import FamilyMemberPanel from '../components/config/FamilyMemberPanel.vue'
import ResidenceLocationPanel from '../components/config/ResidenceLocationPanel.vue'
import { useConfigurationStore } from '../stores/configuration'

const configuration = useConfigurationStore()
const { loading } = storeToRefs(configuration)

onMounted(async () => {
  try {
    await configuration.load()
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
})
</script>

<template>
  <section class="core-config-page" v-loading="loading">
    <h1 class="page-title">核心配置</h1>

    <el-tabs class="config-tabs">
      <el-tab-pane label="住宅与位置">
        <ResidenceLocationPanel />
      </el-tab-pane>
      <el-tab-pane label="家庭成员">
        <FamilyMemberPanel />
      </el-tab-pane>
      <el-tab-pane label="分类字段">
        <CategoryFieldPanel />
      </el-tab-pane>
      <el-tab-pane label="状态与字典">
        <DictionaryPanel />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style scoped>
.core-config-page {
  display: grid;
  gap: 18px;
}

.config-tabs {
  min-width: 0;
}

.config-tabs :deep(.el-tabs__content) {
  overflow: visible;
}
</style>
