<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'

import { useConfigurationStore } from '../../stores/configuration'

const configuration = useConfigurationStore()
const { data } = storeToRefs(configuration)

const statuses = computed(() => data.value?.item_statuses ?? [])
const dictionaryGroups = computed(() => data.value?.dictionary_groups ?? [])
</script>

<template>
  <div class="panel-grid two-columns">
    <section class="tool-section">
      <h2>物品状态</h2>
      <el-table :data="statuses" size="small" class="data-table">
        <el-table-column prop="name" label="名称" min-width="120" />
        <el-table-column prop="code" label="编码" min-width="140" />
        <el-table-column prop="semantic" label="语义" min-width="120" />
        <el-table-column prop="is_system" label="系统" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'info' : 'success'">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="tool-section">
      <h2>字典</h2>
      <el-table
        :data="dictionaryGroups"
        row-key="id"
        size="small"
        class="data-table"
        default-expand-all
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.options" size="small" class="nested-table">
              <el-table-column prop="label" label="选项" min-width="140" />
              <el-table-column prop="value" label="值" min-width="140" />
              <el-table-column prop="is_active" label="启用" width="86">
                <template #default="{ row: option }">
                  <el-tag size="small" :type="option.is_active ? 'success' : 'info'">
                    {{ option.is_active ? '是' : '否' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column prop="code" label="编码" min-width="160" show-overflow-tooltip />
        <el-table-column prop="is_system" label="系统" width="86">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_system ? 'info' : 'success'">
              {{ row.is_system ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.panel-grid {
  display: grid;
  gap: 18px;
}

.two-columns {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.tool-section {
  min-width: 0;
  padding: 18px;
  background: #fff;
  border: 1px solid #eadfce;
  border-radius: 8px;
}

.tool-section h2 {
  margin: 0 0 14px;
  color: #26342e;
  font-size: 16px;
}

.data-table {
  margin-top: 4px;
}

.nested-table {
  width: calc(100% - 20px);
  margin-left: 20px;
}

@media (max-width: 960px) {
  .two-columns {
    grid-template-columns: 1fr;
  }
}
</style>
