<script setup lang="ts">
import { computed } from 'vue'
import { Bell, Box, DocumentChecked, House, Setting, SwitchButton, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import PermissionGate from '../components/PermissionGate.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const activeMenuIndex = computed(() => {
  if (route.path !== '/admin/config') return route.path
  const section = typeof route.query.section === 'string' ? route.query.section : 'residence-location'
  return `/admin/config?section=${section}`
})

const userInitial = computed(() => auth.user?.display_name?.trim().slice(0, 1) || '用')

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
      <div class="side-nav-inner">
        <div class="brand">
          <div class="brand-mark">
            <el-icon><House /></el-icon>
          </div>
          <div>
            <strong>HomeVault</strong>
            <span>家庭物品记录</span>
          </div>
        </div>

        <el-menu router :default-active="activeMenuIndex" class="nav-menu">
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
          <PermissionGate permission="items:view">
            <el-menu-item index="/reminders">
              <el-icon><Bell /></el-icon>
              <span>提醒</span>
            </el-menu-item>
          </PermissionGate>
          <PermissionGate permission="users:manage">
            <el-menu-item index="/admin/users">
              <el-icon><UserFilled /></el-icon>
              <span>用户</span>
            </el-menu-item>
          </PermissionGate>
          <PermissionGate permission="logs:view">
            <el-menu-item index="/admin/logs">
              <el-icon><DocumentChecked /></el-icon>
              <span>操作日志</span>
            </el-menu-item>
          </PermissionGate>
          <PermissionGate permission="config:manage">
            <PermissionGate permission="items:view">
              <el-sub-menu index="admin-config">
                <template #title>
                  <el-icon><Setting /></el-icon>
                  <span>后台管理</span>
                </template>
                <el-menu-item index="/admin/config?section=residence-location">住宅与位置</el-menu-item>
                <el-menu-item index="/admin/config?section=family-members">家庭成员</el-menu-item>
                <el-menu-item index="/admin/config?section=category-fields">分类字段</el-menu-item>
                <el-menu-item index="/admin/config?section=status-dictionaries">状态与字典</el-menu-item>
              </el-sub-menu>
            </PermissionGate>
          </PermissionGate>
        </el-menu>

        <div class="account-footer">
          <div class="account-avatar">{{ userInitial }}</div>
          <div class="account-copy">
            <strong>{{ auth.user?.display_name }}</strong>
            <span>{{ auth.user?.roles.join(' / ') }}</span>
          </div>
          <el-button
            text
            circle
            :icon="SwitchButton"
            aria-label="退出登录"
            title="退出登录"
            @click="handleLogout"
          />
        </div>
      </div>
    </el-aside>

    <el-container class="content-shell">
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

.side-nav-inner {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
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
  flex: 1;
  border-right: none;
  background: transparent;
}

.account-footer {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 32px;
  gap: 10px;
  align-items: center;
  margin: 16px;
  padding: 12px;
  border: 1px solid #eadfce;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.68);
}

.account-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  color: #fff;
  font-weight: 700;
  background: #2f6f5f;
  border-radius: 8px;
}

.account-copy {
  min-width: 0;
}

.account-copy strong,
.account-copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-copy strong {
  color: #25342d;
  font-size: 14px;
}

.account-copy span {
  margin-top: 3px;
  color: #7d867f;
  font-size: 12px;
}

.content-shell {
  min-width: 0;
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

  .side-nav-inner {
    min-height: auto;
  }

  .brand {
    padding: 16px;
  }

  .nav-menu {
    flex: none;
  }

  .main-content {
    padding: 20px 16px;
  }

  .account-footer {
    margin: 10px 16px 16px;
  }
}
</style>
