<script setup lang="ts">
import { Bell, Box, Key, UserFilled } from '@element-plus/icons-vue'
</script>

<template>
  <section>
    <h1 class="page-title">仪表盘</h1>
    <p class="page-subtitle">第一阶段先确认登录、权限和基础布局，物品统计会在库存模块接入后显示真实数据。</p>

    <div class="summary-grid">
      <el-card shadow="never">
        <el-icon><Box /></el-icon>
        <strong>物品基础</strong>
        <span>准备接入住宅、位置和物品卡片</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><UserFilled /></el-icon>
        <strong>角色权限</strong>
        <span>管理员、编辑者、查看者已预留</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><Bell /></el-icon>
        <strong>站内提醒</strong>
        <span>后续展示保修、有效期和检查提醒</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><Key /></el-icon>
        <strong>安全登录</strong>
        <span>token 登录和退出已接入</span>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.summary-grid :deep(.el-card__body) {
  display: grid;
  gap: 10px;
  min-height: 150px;
}

.summary-grid .el-icon {
  color: #4f8f72;
  font-size: 28px;
}

.summary-grid strong {
  color: #26342e;
}

.summary-grid span {
  color: #748078;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
