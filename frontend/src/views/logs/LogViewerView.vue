<template>
  <div class="page-container">
    <div class="toolbar">
      <h2>日志查看</h2>
      <div class="spacer" />
      <el-select v-model="logFile" placeholder="选择日志文件" style="width: 180px" @change="loadLogs" size="default">
        <el-option v-for="f in logFiles" :key="f.name" :label="`${f.name} (${f.size}B)`" :value="f.name" />
      </el-select>
      <el-select v-model="filterLevel" placeholder="日志级别" style="width: 120px" @change="loadLogs" clearable size="default">
        <el-option label="全部" value="all" />
        <el-option label="错误" value="error" />
        <el-option label="警告" value="warning" />
        <el-option label="信息" value="info" />
        <el-option label="调试" value="debug" />
      </el-select>
      <el-input v-model="searchText" placeholder="搜索关键词" style="width: 200px" @keyup.enter="loadLogs" clearable size="default" />
      <el-button @click="loadLogs" :loading="loading" type="primary">
        <el-icon><Search /></el-icon> 搜索
      </el-button>
      <el-button @click="autoRefresh = !autoRefresh" :type="autoRefresh ? 'success' : 'default'">
        <el-icon><Refresh /></el-icon> {{ autoRefresh ? '刷新中' : '手动' }}
      </el-button>
    </div>
    <el-alert
      v-if="!serverStore.selectedId"
      type="warning"
      title="请先在顶部选择一台 Samba 服务器"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <!-- 日志表格 -->
    <el-card v-if="serverStore.selectedId" shadow="never">
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px">
        <span style="font-size: 13px; color: #909399">当前：{{ currentLogFile }} | 共 {{ totalCount }} 条</span>
        <el-input-number v-model="logLines" :min="10" :max="1000" :step="100" size="small" style="width: 120px" @change="loadLogs" />
        <span style="font-size: 13px; color: #909399">行</span>
        <el-button size="small" @click="exportLogs" :disabled="!allEntries.length">导出</el-button>
      </div>
      <el-table
        :data="entries"
        v-loading="loading"
        stripe
        size="small"
        :height="'calc(100vh - 320px)'"
        highlight-current-row
      >
        <el-table-column label="级别" width="70" fixed="left">
          <template #default="{ row }">
            <el-tag :type="levelTag(row.level)" size="small" effect="dark">
              {{ row.level.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间" width="170" />
        <el-table-column prop="source" label="来源" width="200" show-overflow-tooltip />
        <el-table-column label="消息" min-width="400">
          <template #default="{ row }">
            <div class="log-msg">{{ row.message }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useServerStore } from '@/stores/server'
import { logsApi } from '@/api/logs'

const serverStore = useServerStore()
const loading = ref(false)

const logFile = ref('')
const logFiles = ref([])
const filterLevel = ref('all')
const searchText = ref('')
const logLines = ref(100)
const entries = ref([])
const allEntries = ref([])
const currentLogFile = ref('')
const totalCount = ref(0)
const autoRefresh = ref(false)

let refreshTimer = null

function levelTag(level) {
  const map = { error: 'danger', warning: 'warning', info: 'default', debug: '' }
  return map[level] || 'info'
}

async function loadLogs() {
  loading.value = true
  try {
    const params = { lines: logLines.value }
    if (filterLevel.value) params.level = filterLevel.value
    if (searchText.value) params.search = searchText.value
    if (logFile.value) params.log_file = logFile.value

    const res = await logsApi.get(params)
    entries.value = res.data.entries || []
    totalCount.value = res.data.count || 0
    currentLogFile.value = res.data.log_file || ''

    // 缓存日志文件列表
    if (res.data.log_files) {
      logFiles.value = res.data.log_files
      if (!logFile.value && logFiles.value.length > 0) {
        logFile.value = logFiles.value[0].name
      }
    }
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

function exportLogs() {
  const content = entries.value
    .map(e => `[${e.timestamp}] [${e.level.toUpperCase()}] ${e.source && e.source !== '-' ? e.source + ' ' : ''}${e.message}`)
    .join('\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `samba-log-${new Date().toISOString().slice(0, 10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// 自动刷新
function startAutoRefresh() {
  if (refreshTimer) return
  refreshTimer = setInterval(() => {
    if (autoRefresh.value) loadLogs()
    else {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }, 5000)
}

onMounted(() => {
  loadLogs()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.log-msg {
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
}
</style>
