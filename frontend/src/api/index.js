import axios from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// 请求拦截器：注入 token + server_id
http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  // 自动注入 server_id
  const serverId = localStorage.getItem('sambav2_server_id')
  if (serverId && !config.params?.server_id) {
    config.params = config.params || {}
    config.params.server_id = serverId
  }
  return config
})

// 响应拦截器：401 → 跳转登录
http.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore().logout()
      ElMessage.error('登录已过期，请重新登录')
      router.push({ name: 'Login' })
    } else if (error.response?.status === 404) {
      // 后端路由尚未实现，静默处理
    } else if (error.response?.status >= 500) {
      ElMessage.error(error.response?.data?.detail || '服务器内部错误')
    } else {
      const msg = error.response?.data?.detail || error.message || '请求失败'
      if (msg && !msg.includes('Network Error')) {
        ElMessage.error(msg)
      }
    }
    return Promise.reject(error)
  },
)

export default http
