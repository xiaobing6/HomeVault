<script setup lang="ts">
import { Box, Collection, Location, User } from '@element-plus/icons-vue'

import type { ItemSummary } from '../../api/inventory'

defineProps<{
  items: ItemSummary[]
}>()

const emit = defineEmits<{
  'open-detail': [itemId: number]
}>()
</script>

<template>
  <el-empty v-if="items.length === 0" description="还没有物品" />

  <div v-else class="item-grid">
    <button
      v-for="item in items"
      :key="item.id"
      class="item-tile"
      type="button"
      @click="emit('open-detail', item.id)"
    >
      <div class="thumb">
        <img v-if="item.primary_image_url" :src="item.primary_image_url" :alt="item.name" />
        <el-icon v-else><Box /></el-icon>
      </div>

      <div class="tile-body">
        <div class="title-row">
          <strong>{{ item.name }}</strong>
          <el-tag v-if="item.is_archived" size="small" type="info">已归档</el-tag>
          <el-tag v-else-if="item.status_name" size="small" effect="plain">
            {{ item.status_name }}
          </el-tag>
        </div>

        <div class="meta-line">
          <el-icon><Collection /></el-icon>
          <span>{{ item.category_name || '未分类' }}</span>
        </div>
        <div class="meta-line">
          <el-icon><Location /></el-icon>
          <span>{{ item.location_node_name || item.residence_name || '未设置位置' }}</span>
        </div>
        <div class="meta-line">
          <el-icon><User /></el-icon>
          <span>{{ item.keeper_member_name || item.owner_member_name || '未设置保管人' }}</span>
        </div>

        <div class="tile-footer">
          <span>{{ item.quantity }} {{ item.unit }}</span>
          <el-tag v-if="item.is_container" size="small" type="success">容器</el-tag>
        </div>
      </div>
    </button>
  </div>
</template>

<style scoped>
.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.item-tile {
  display: grid;
  grid-template-columns: 84px minmax(0, 1fr);
  gap: 12px;
  min-width: 0;
  min-height: 148px;
  padding: 12px;
  color: inherit;
  text-align: left;
  background: #fff;
  border: 1px solid #e2e8df;
  border-radius: 8px;
  cursor: pointer;
}

.item-tile:hover,
.item-tile:focus-visible {
  border-color: #8bb79d;
  outline: none;
  box-shadow: 0 2px 10px rgba(42, 67, 50, 0.08);
}

.thumb {
  display: grid;
  width: 84px;
  height: 84px;
  place-items: center;
  overflow: hidden;
  color: #779182;
  background: #eef5ef;
  border-radius: 6px;
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb .el-icon {
  font-size: 28px;
}

.tile-body {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.title-row,
.tile-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.title-row strong {
  min-width: 0;
  overflow: hidden;
  color: #25342d;
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-line {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: #68756d;
  font-size: 12px;
}

.meta-line span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tile-footer {
  margin-top: 2px;
  color: #3e4c44;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 520px) {
  .item-grid {
    grid-template-columns: 1fr;
  }
}
</style>
