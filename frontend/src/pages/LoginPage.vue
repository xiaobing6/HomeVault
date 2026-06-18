<script setup lang="ts">
import { Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getChineseErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'ChangeMe123!' })

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
    await router.push((route.query.redirect as string) || '/')
  } catch (error) {
    ElMessage.error(getChineseErrorMessage(error))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-copy">
        <p class="eyebrow">HomeVault</p>
        <h1>把家里的东西安稳地记下来</h1>
        <p>登录后可以查看家庭物品、位置、角色权限和后续管理功能。</p>
      </div>
      <el-form class="login-form" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" :prefix-icon="User" size="large" placeholder="账号" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            :prefix-icon="Lock"
            size="large"
            type="password"
            placeholder="密码"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="login-button" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 48px;
}

.login-panel {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(280px, 360px);
  gap: 40px;
  width: min(900px, 100%);
  padding: 44px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid #eadfce;
  border-radius: 8px;
  box-shadow: 0 18px 50px rgba(84, 68, 45, 0.12);
}

.eyebrow {
  margin: 0 0 12px;
  color: #4f8f72;
  font-weight: 700;
}

h1 {
  margin: 0;
  color: #26342e;
  font-size: 34px;
  line-height: 1.2;
}

.login-copy p:last-child {
  color: #6f796f;
  line-height: 1.7;
}

.login-form {
  align-self: center;
}

.login-button {
  width: 100%;
}

@media (max-width: 720px) {
  .login-page {
    padding: 24px 16px;
  }

  .login-panel {
    grid-template-columns: 1fr;
    gap: 24px;
    padding: 28px 20px;
  }

  h1 {
    font-size: 28px;
  }
}
</style>
