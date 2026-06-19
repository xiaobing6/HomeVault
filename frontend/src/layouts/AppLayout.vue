<script setup lang="ts">
import { Box, House, Setting, SwitchButton } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import PermissionGate from '../components/PermissionGate.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

async function handleLogout() {
  try {
    await auth.logout()
    ElMessage.success('已退出登录')
    await router.push({ name: 'login' })
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  }
}
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="side-nav">
      <div class="brand">
        <div class="brand-mark">
          <el-icon><House /></el-icon>
        </div>
        <div>
          <strong>HomeVault</strong>
          <span>家庭物品记录</span>
        </div>
      </div>

      <el-menu router :default-active="route.path" class="nav-menu">
        <el-menu-item index="/">
          <el-icon><Box /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <PermissionGate permission="items:view">
          <el-menu-item index="/items">
            <el-icon><House /></el-icon>
            <span>物品</span>
          </el-menu-item>
        </PermissionGate>
        <PermissionGate permission="config:manage">
          <PermissionGate permission="items:view">
            <el-menu-item index="/admin/config">
              <el-icon><Setting /></el-icon>
              <span>后台管理</span>
            </el-menu-item>
          </PermissionGate>
        </PermissionGate>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="top-bar">
        <div>
          <div class="welcome">欢迎回来，{{ auth.user?.display_name }}</div>
          <div class="role-line">{{ auth.user?.roles.join(' / ') }}</div>
        </div>
        <el-button :icon="SwitchButton" @click="handleLogout">退出</el-button>
      </el-header>
      <el-main class="main-content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
}

.side-nav {
  background: #fffaf1;
  border-right: 1px solid #eadfce;
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 22px 20px;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  color: #fff;
  background: #4f8f72;
  border-radius: 8px;
}

.brand span {
  display: block;
  margin-top: 3px;
  color: #768078;
  font-size: 12px;
}

.nav-menu {
  border-right: none;
  background: transparent;
}

.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(255, 255, 255, 0.76);
  border-bottom: 1px solid #eadfce;
}

.welcome {
  font-weight: 700;
}

.role-line {
  margin-top: 4px;
  color: #7d867f;
  font-size: 12px;
}

.main-content {
  padding: 28px;
}

@media (max-width: 720px) {
  .app-shell {
    display: block;
  }

  .side-nav {
    width: 100% !important;
    border-right: none;
    border-bottom: 1px solid #eadfce;
  }

  .brand {
    padding: 16px;
  }

  .nav-menu {
    display: flex;
    overflow-x: auto;
  }

  .top-bar {
    height: auto;
    min-height: 64px;
    padding: 12px 16px;
  }

  .main-content {
    padding: 20px 16px;
  }
}
</style>
