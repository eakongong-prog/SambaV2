import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'servers',
        name: 'Servers',
        component: () => import('@/views/servers/ServerListView.vue'),
        meta: { title: '服务器管理' },
      },
      {
        path: 'servers/add',
        name: 'ServerAdd',
        component: () => import('@/views/servers/ServerFormView.vue'),
        meta: { title: '添加服务器' },
      },
      {
        path: 'servers/:id/edit',
        name: 'ServerEdit',
        component: () => import('@/views/servers/ServerFormView.vue'),
        meta: { title: '编辑服务器' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/UserListView.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'users/add',
        name: 'UserAdd',
        component: () => import('@/views/users/UserFormView.vue'),
        meta: { title: '新增用户' },
      },
      {
        path: 'users/:name/edit',
        name: 'UserEdit',
        component: () => import('@/views/users/UserFormView.vue'),
        meta: { title: '编辑用户' },
      },
      {
        path: 'groups',
        name: 'Groups',
        component: () => import('@/views/groups/GroupListView.vue'),
        meta: { title: '群组管理' },
      },
      {
        path: 'shares',
        name: 'Shares',
        component: () => import('@/views/shares/ShareListView.vue'),
        meta: { title: '共享管理' },
      },
      {
        path: 'shares/add',
        name: 'ShareAdd',
        component: () => import('@/views/shares/ShareFormView.vue'),
        meta: { title: '新增共享' },
      },
      {
        path: 'shares/:name/edit',
        name: 'ShareEdit',
        component: () => import('@/views/shares/ShareFormView.vue'),
        meta: { title: '编辑共享' },
      },
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/permissions/AclBrowserView.vue'),
        meta: { title: '权限管理' },
      },
      {
        path: 'services',
        name: 'Services',
        component: () => import('@/views/services/ServiceControlView.vue'),
        meta: { title: '服务控制' },
      },
      {
        path: 'config',
        name: 'ConfigEditor',
        component: () => import('@/views/config/ConfigEditorView.vue'),
        meta: { title: '配置编辑' },
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/logs/LogViewerView.vue'),
        meta: { title: '日志查看' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()
  // 公开页面直接放行
  if (to.meta.public) return next()

  // 未初始化则先尝试恢复 session
  if (!auth.initialized) {
    await auth.init()
  }

  if (!auth.token) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }

  next()
})

export default router
