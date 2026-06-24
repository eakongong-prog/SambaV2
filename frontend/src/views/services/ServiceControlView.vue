<template>
  <div class="page-container">
    <h2 style="margin-bottom: 20px">服务控制</h2>
    <el-alert
      v-if="!serverStore.selectedId"
      type="warning"
      title="请先在顶部选择一台 Samba 服务器"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <template v-if="serverStore.selectedId">
      <!-- 服务状态卡片 -->
      <el-row :gutter="16" style="margin-bottom: 20px">
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-title">
                <el-icon :size="18" :color="status.smbd?.running ? '#67c23a' : '#f56c6c'"><Monitor /></el-icon>
                <span>SMB 服务 (smbd)</span>
                <el-tag :type="status.smbd?.running ? 'success' : 'danger'" size="small" effect="dark" style="margin-left: auto">
                  {{ status.smbd?.running ? '运行中' : '已停止' }}
                </el-tag>
              </div>
            </template>
            <div v-if="status.smbd?.running" class="stats">
              <div class="stat"><span class="label">PID</span> <span>{{ status.smbd.pid }}</span></div>
              <div class="stat"><span class="label">内存</span> <span>{{ status.smbd.memory }}</span></div>
              <div class="stat"><span class="label">CPU</span> <span>{{ status.smbd.cpu }}</span></div>
              <div class="stat"><span class="label">运行时间</span> <span>{{ status.smbd.uptime }}</span></div>
            </div>
            <el-empty v-else description="服务未运行" :image-size="40" />
            <div class="card-actions">
              <el-button v-if="!status.smbd?.running" type="success" size="small" :loading="acting" @click="act('smbd','start')">启动</el-button>
              <el-button v-else type="warning" size="small" :loading="acting" @click="act('smbd','restart')">重启</el-button>
              <el-button v-if="status.smbd?.running" type="danger" size="small" :loading="acting" @click="act('smbd','stop')">停止</el-button>
            </div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <template #header>
              <div class="card-title">
                <el-icon :size="18" :color="status.nmbd?.running ? '#67c23a' : '#f56c6c'"><Monitor /></el-icon>
                <span>NMB 服务 (nmbd)</span>
                <el-tag :type="status.nmbd?.running ? 'success' : 'danger'" size="small" effect="dark" style="margin-left: auto">
                  {{ status.nmbd?.running ? '运行中' : '已停止' }}
                </el-tag>
              </div>
            </template>
            <div v-if="status.nmbd?.running" class="stats">
              <div class="stat"><span class="label">PID</span> <span>{{ status.nmbd.pid }}</span></div>
              <div class="stat"><span class="label">内存</span> <span>{{ status.nmbd.memory }}</span></div>
              <div class="stat"><span class="label">CPU</span> <span>{{ status.nmbd.cpu }}</span></div>
              <div class="stat"><span class="label">运行时间</span> <span>{{ status.nmbd.uptime }}</span></div>
            </div>
            <el-empty v-else description="服务未运行" :image-size="40" />
            <div class="card-actions">
              <el-button v-if="!status.nmbd?.running" type="success" size="small" :loading="acting" @click="act('nmbd','start')">启动</el-button>
              <el-button v-else type="warning" size="small" :loading="acting" @click="act('nmbd','restart')">重启</el-button>
              <el-button v-if="status.nmbd?.running" type="danger" size="small" :loading="acting" @click="act('nmbd','stop')">停止</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 重载配置 -->
      <el-card shadow="hover" style="margin-bottom: 20px">
        <template #header>
          <div class="card-title"><el-icon><Refresh /></el-icon><span>配置重载</span></div>
        </template>
        <p style="color: #909399; font-size: 13px; margin-bottom: 12px">
          修改 smb.conf 后无需重启服务，执行热重载即可生效。建议先通过「配置编辑」页面校验语法。
        </p>
        <el-button type="primary" :loading="acting" @click="handleReload">重载配置</el-button>
      </el-card>

      <!-- 实时会话 -->
      <el-card shadow="hover">
        <template #header>
          <div class="card-title">
            <el-icon><Connection /></el-icon>
            <span>实时会话</span>
            <el-tag size="small" style="margin-left: 8px">{{ sessions.length }} 个连接</el-tag>
            <el-button size="small" style="margin-left: auto" @click="loadSessions" :loading="loading">刷新</el-button>
          </div>
        </template>
        <el-table :data="sessions" v-loading="loading" stripe size="small">
          <el-table-column prop="pid" label="PID" width="80" />
          <el-table-column prop="user" label="用户" width="120" />
          <el-table-column prop="machine" label="客户端" min-width="140" />
          <el-table-column prop="share" label="共享" width="160" />
          <el-table-column prop="connected_at" label="连接时间" min-width="160" />
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-popconfirm title="强制断开会话？" @confirm="handleDisconnect(row.pid)">
                <template #reference>
                  <el-button link type="danger" size="small">断开</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && sessions.length === 0" description="当前无活跃会话" :image-size="60" />
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useServerStore } from '@/stores/server'
import { servicesApi } from '@/api/services'
import { ElMessage } from 'element-plus'

const serverStore = useServerStore()
const loading = ref(false)
const acting = ref(false)

const status = ref({ smbd: null, nmbd: null })
const sessions = ref([])

async function loadStatus() {
  try {
    const res = await servicesApi.status()
    status.value = res.data
  } catch { /* handled */ }
}

async function loadSessions() {
  loading.value = true
  try {
    const res = await servicesApi.sessions()
    sessions.value = res.data.sessions || []
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

async function act(name, action) {
  acting.value = true
  try {
    const res = await servicesApi.action(name, action)
    ElMessage.success(`${name} ${action} 成功`)
    setTimeout(loadStatus, 1000)
  } catch { /* handled */ } finally {
    acting.value = false
  }
}

async function handleReload() {
  acting.value = true
  try {
    await servicesApi.reloadConfig()
    ElMessage.success('配置已重载')
  } catch { /* handled */ } finally {
    acting.value = false
  }
}

async function handleDisconnect(pid) {
  try {
    await servicesApi.disconnectSession(pid)
    ElMessage.success(`会话 ${pid} 已断开`)
    loadSessions()
  } catch { /* handled */ }
}

onMounted(() => {
  loadStatus()
  loadSessions()
})
</script>

<style scoped>
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}
.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.stat {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px dashed #ebeef5;
  font-size: 13px;
}
.stat .label {
  color: #909399;
}
.card-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}
</style>
