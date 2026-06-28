<script setup lang="ts">
import { Bell, Box, Key, UserFilled } from '@element-plus/icons-vue'
</script>

<template>
  <section>
    <h1 class="page-title">仪表盘</h1>
    <p class="page-subtitle">集中查看家庭物品、位置、权限、提醒和操作日志入口，后续阶段将继续补齐批量和导入导出能力。</p>

    <div class="summary-grid">
      <el-card shadow="never">
        <el-icon><Box /></el-icon>
        <strong>物品基础</strong>
        <span>查看住宅、位置、分类和物品清单</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><UserFilled /></el-icon>
        <strong>角色权限</strong>
        <span>管理账号启停、密码重置和系统角色分配</span>
      </el-card>
      <el-card shadow="never">
        <el-icon><Bell /></el-icon>
        <strong>站内提醒</strong>
        <span>查看待处理、即将到期和已逾期提醒</span>
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
