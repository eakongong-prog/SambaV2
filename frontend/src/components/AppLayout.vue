<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <SidebarMenu />

    <!-- 右侧主体 -->
    <div class="main-area" :class="{ collapsed: app.sidebarCollapsed }">
      <!-- 顶栏 -->
      <div class="top-bar">
        <div class="top-left">
          <el-icon class="collapse-btn" @click="app.toggleSidebar()" :size="20">
            <Fold v-if="!app.sidebarCollapsed" />
            <Expand v-else />
          </el-icon>
          <div class="brand">SambaV2</div>
        </div>
        <div class="top-right">
          <!-- 服务器切换 -->
          <ServerSwitcher />
          <!-- 用户信息 -->
          <el-dropdown trigger="click">
            <span class="user-info">
              <el-icon><UserFilled /></el-icon>
              {{ auth.username }}
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="showChangePassword = true">
                  <el-icon><Key /></el-icon> 修改密码
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- 内容区 -->
      <div class="content-area">
        <router-view />
      </div>
    </div>

    <!-- 修改密码弹窗 -->
    <el-dialog v-model="showChangePassword" title="修改密码" width="420px" :close-on-click-modal="false">
      <el-form :model="passwordForm" label-width="100px" size="default">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.newPassword" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showChangePassword = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { ElMessage } from 'element-plus'
import SidebarMenu from './SidebarMenu.vue'
import ServerSwitcher from './ServerSwitcher.vue'

const router = useRouter()
const auth = useAuthStore()
const app = useAppStore()

const showChangePassword = ref(false)
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

async function handleChangePassword() {
  if (!passwordForm.oldPassword) return ElMessage.warning('请输入原密码')
  if (!passwordForm.newPassword) return ElMessage.warning('请输入新密码')
  if (passwordForm.newPassword !== passwordForm.confirmPassword)
    return ElMessage.warning('两次输入的新密码不一致')
  try {
    await auth.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    showChangePassword.value = false
    passwordForm.oldPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch { /* interceptor handles */ }
}

function handleLogout() {
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.3s;
}
.main-area.collapsed {
  margin-left: var(--sidebar-collapsed-width);
}

/* 顶栏 */
.top-bar {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
  flex-shrink: 0;
}
.top-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.collapse-btn {
  cursor: pointer;
  color: #606266;
}
.collapse-btn:hover {
  color: var(--primary-color);
}
.brand {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}
.top-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #606266;
}

/* 内容区 */
.content-area {
  flex: 1;
  overflow: auto;
  background: #f5f7fa;
  padding: 20px;
}
</style>
