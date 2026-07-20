<template>
  <div class="app-shell">
    <!-- 登录界面 -->
    <section v-if="!user" class="auth-screen">
      <div class="auth-panel">
        <div class="brand">
          <div class="brand-mark">化</div>
          <div>
            <h1>化学品安全管理系统</h1>
            <p>库存、刷卡、OCR、审批和危化品管控一体化工作台</p>
          </div>
        </div>

        <el-tabs v-model="authMode" stretch>
          <el-tab-pane label="登录" name="login">
            <el-form :model="loginForm" label-position="top" @keyup.enter="login">
              <el-form-item label="用户名">
                <el-input v-model="loginForm.username" :prefix-icon="User" placeholder="admin" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="loginForm.password" :prefix-icon="Lock" type="password" show-password placeholder="admin123" />
              </el-form-item>
              <el-button type="primary" class="wide-button" :icon="SwitchButton" :loading="authLoading" @click="login">
                登录系统
              </el-button>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="注册" name="register">
            <el-form :model="registerForm" label-position="top" @keyup.enter="register">
              <el-form-item label="用户名">
                <el-input v-model="registerForm.username" />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="registerForm.name" />
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="registerForm.password" type="password" show-password />
              </el-form-item>
              <el-alert title="注册账号默认为普通使用人；库管和安全管理员权限由管理员配置。" type="info" show-icon :closable="false" />
              <el-button type="success" class="wide-button" :icon="Plus" :loading="authLoading" @click="register">
                注册并登录
              </el-button>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </section>

    <!-- 根据角色显示不同界面 -->
    <AdminDashboard v-else-if="isAdmin" :user="user" @logout="logout" />
    <UserDashboard v-else :user="user" @logout="logout" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Lock, Plus, SwitchButton, User } from '@element-plus/icons-vue'
import {
  authLogin,
  authLogout,
  authMe,
  authRegister,
  setAuthToken,
} from './api'
import AdminDashboard from './components/AdminDashboard.vue'
import UserDashboard from './components/UserDashboard.vue'

const authMode = ref('login')
const authLoading = ref(false)
const user = ref(null)

const loginForm = reactive({ username: 'admin', password: 'admin123' })
const registerForm = reactive({ username: '', password: '', name: '', role: 'operator', department: '', phone: '' })

// 判断是否为管理员角色
const isAdmin = computed(() => {
  return ['admin', 'keeper', 'safety_manager'].includes(user.value?.role)
})

function notifyError(error, fallback) {
  ElMessage.error(error?.response?.data?.error || fallback)
}

async function login() {
  authLoading.value = true
  try {
    const res = await authLogin(loginForm)
    setAuthToken(res.data.token)
    user.value = res.data.user
    ElMessage.success('登录成功')
  } catch (error) {
    notifyError(error, '登录失败')
  } finally {
    authLoading.value = false
  }
}

async function register() {
  authLoading.value = true
  try {
    const res = await authRegister(registerForm)
    setAuthToken(res.data.token)
    user.value = res.data.user
    ElMessage.success('注册成功')
  } catch (error) {
    notifyError(error, '注册失败')
  } finally {
    authLoading.value = false
  }
}

async function logout() {
  try {
    await authLogout()
  } catch {
    // 忽略过期会话
  }
  setAuthToken('')
  user.value = null
}

async function bootstrap() {
  if (!localStorage.getItem('chemical_token')) return
  try {
    const res = await authMe()
    user.value = res.data
  } catch {
    setAuthToken('')
  }
}

onMounted(bootstrap)
</script>

<style>
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: #f4f6f8;
  color: #1f2933;
  font-family: Inter, "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
}

.app-shell {
  min-height: 100vh;
}

.auth-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    linear-gradient(135deg, rgba(20, 105, 88, 0.16), rgba(63, 88, 130, 0.08)),
    #eef3f1;
}

.auth-panel {
  width: min(460px, 100%);
  padding: 28px;
  background: #ffffff;
  border: 1px solid #d9e1e6;
  border-radius: 8px;
  box-shadow: 0 18px 48px rgba(31, 41, 51, 0.12);
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.brand h1 {
  margin: 0 0 6px;
  font-size: 24px;
  letter-spacing: 0;
}

.brand p {
  margin: 0;
  color: #60707c;
  line-height: 1.5;
}

.brand-mark {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  background: #14795f;
  color: #fff;
  font-size: 26px;
  font-weight: 700;
}

.wide-button {
  width: 100%;
}
</style>