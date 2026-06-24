<template>
  <div class="page-container">
    <div class="toolbar">
      <h2>服务器管理</h2>
      <div class="spacer" />
      <el-button type="primary" @click="$router.push('/servers/add')">
        <el-icon><Plus /></el-icon> 添加服务器
      </el-button>
    </div>

    <!-- 卡片列表 -->
    <div v-loading="loading">
      <el-row :gutter="16">
        <el-col v-for="s in servers" :key="s.id" :xs="24" :sm="12" :md="8" :lg="6" style="margin-bottom: 16px">
          <el-card shadow="hover" class="server-card">
            <div class="server-name">
              <el-icon :size="16" :color="s.is_connected ? '#67c23a' : '#c0c4cc'">
                <CircleCheckFilled v-if="s.is_connected" />
                <CircleCheck v-else />
              </el-icon>
              {{ s.name }}
            </div>
            <div class="server-detail">
              <div>IP：{{ s.host }}:{{ s.port }}</div>
              <div>用户：{{ s.username }}</div>
              <div>认证：{{ s.auth_type === 'password' ? '密码' : '密钥' }}</div>
              <div class="last-connected" v-if="s.last_connected">
                最后连接：{{ formatDateTime(s.last_connected) }}
              </div>
            </div>
            <div class="server-actions">
              <el-button size="small" @click="handleTest(s.id)">
                <el-icon><Connection /></el-icon> 测试
              </el-button>
              <el-button size="small" @click="$router.push(`/servers/${s.id}/edit`)">
                <el-icon><Edit /></el-icon> 编辑
              </el-button>
              <el-popconfirm title="确定删除此服务器？" @confirm="handleDelete(s.id)">
                <template #reference>
                  <el-button size="small" type="danger">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <el-empty v-if="!loading && servers.length === 0" description="还没有添加服务器，点击右上角按钮添加" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { serversApi } from '@/api/servers'
import { useServerStore } from '@/stores/server'
import { ElMessage } from 'element-plus'
import { formatDateTime } from '@/utils/formatter'

const servers = ref([])
const loading = ref(false)
const serverStore = useServerStore()

async function load() {
  loading.value = true
  try {
    const res = await serversApi.list()
    servers.value = res.data
  } catch { /* interceptor handles */ } finally {
    loading.value = false
  }
}

async function handleTest(id) {
  try {
    const res = await serversApi.testConnection(id)
    if (res.data.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(`连接失败：${res.data.message}`)
    }
  } catch { /* interceptor handles */ }
}

async function handleDelete(id) {
  try {
    await serversApi.delete(id)
    ElMessage.success('已删除')
    if (serverStore.selectedId === id) serverStore.clear()
    load()
  } catch { /* interceptor handles */ }
}

onMounted(load)
</script>

<style scoped>
.server-card {
  cursor: default;
}
.server-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.server-detail {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
}
.last-connected {
  color: #909399;
  font-size: 12px;
}
.server-actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
</style>
