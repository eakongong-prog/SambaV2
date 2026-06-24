<template>
  <div class="sidebar" :class="{ collapsed: app.sidebarCollapsed }">
    <div class="logo-area">
      <h2 v-if="!app.sidebarCollapsed" class="logo-text">SambaV2</h2>
      <h2 v-else class="logo-text-collapsed">S</h2>
    </div>
    <el-menu
      :default-active="activeMenu"
      :collapse="app.sidebarCollapsed"
      :collapse-transition="false"
      background-color="#1a1a2e"
      text-color="#bfcbd9"
      active-text-color="#409eff"
      router
    >
      <el-menu-item index="/dashboard">
        <el-icon><Odometer /></el-icon>
        <span>仪表盘</span>
      </el-menu-item>
      <el-menu-item index="/servers">
        <el-icon><Monitor /></el-icon>
        <span>服务器管理</span>
      </el-menu-item>
      <el-sub-menu index="identity">
        <template #title>
          <el-icon><User /></el-icon>
          <span>用户与群组</span>
        </template>
        <el-menu-item index="/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/groups">
          <el-icon><Avatar /></el-icon>
          <span>群组管理</span>
        </el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/shares">
        <el-icon><FolderOpened /></el-icon>
        <span>共享管理</span>
      </el-menu-item>
      <el-menu-item index="/permissions">
        <el-icon><Lock /></el-icon>
        <span>权限管理</span>
      </el-menu-item>
      <el-sub-menu index="operations">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>运行维护</span>
        </template>
        <el-menu-item index="/services">
          <el-icon><DataAnalysis /></el-icon>
          <span>服务控制</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Document /></el-icon>
          <span>配置编辑</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Tickets /></el-icon>
          <span>日志查看</span>
        </el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'

const route = useRoute()
const app = useAppStore()

const activeMenu = computed(() => {
  const name = route.name
  // 子菜单路径映射到父菜单项
  const map = {
    Users: '/users',
    UserAdd: '/users',
    UserEdit: '/users',
    Groups: '/groups',
    Shares: '/shares',
    ShareAdd: '/shares',
    ShareEdit: '/shares',
    Permissions: '/permissions',
    Services: '/services',
    ConfigEditor: '/config',
    Logs: '/logs',
    Dashboard: '/dashboard',
    Servers: '/servers',
    ServerAdd: '/servers',
    ServerEdit: '/servers',
  }
  return map[name] || route.path
})
</script>

<style scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background-color: #1a1a2e;
  transition: width 0.3s;
  z-index: 100;
  overflow: hidden;
}
.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.logo-area {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.logo-text {
  color: #fff;
  font-size: 20px;
  white-space: nowrap;
}
.logo-text-collapsed {
  color: #fff;
  font-size: 22px;
}

.el-menu {
  border-right: none;
}
</style>
