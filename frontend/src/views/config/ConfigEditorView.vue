<template>
  <div class="page-container">
    <h2 style="margin-bottom: 20px">smb.conf 编辑器</h2>
    <el-alert
      v-if="!serverStore.selectedId"
      type="warning"
      title="请先在顶部选择一台 Samba 服务器"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <template v-if="serverStore.selectedId">
      <!-- 顶部信息栏 -->
      <div class="info-bar">
        <span>
          文件路径：<el-tag type="info" size="small">{{ configInfo.path }}</el-tag>
        </span>
        <span v-if="configInfo.last_modified" style="margin-left: 20px">
          最后修改：<el-tag type="info" size="small">{{ fmt(configInfo.last_modified * 1000) }}</el-tag>
        </span>
        <div class="spacer" />
        <el-button @click="loadConfig" :loading="loading">
          <el-icon><Refresh /></el-icon> 重新加载
        </el-button>
        <el-button @click="handleValidate" :loading="validating">
          <el-icon><Select /></el-icon> 校验语法
        </el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon><Check /></el-icon> 保存配置
        </el-button>
      </div>

      <el-row :gutter="16" style="height: calc(100vh - 260px)">
        <!-- 编辑器 -->
        <el-col :span="18">
          <div ref="editorContainer" class="editor-container"></div>
        </el-col>
        <!-- 右侧：备份列表 + 校验结果 -->
        <el-col :span="6">
          <el-card header="备份历史" shadow="never" size="small" class="backup-card">
            <template #header>
              <div style="display: flex; align-items: center; justify-content: space-between">
                <span>备份历史</span>
                <el-button size="small" @click="handleCreateBackup" :loading="backing">
                  <el-icon><Plus /></el-icon> 备份
                </el-button>
              </div>
            </template>
            <div v-loading="loadingBackups">
              <div
                v-for="b in backups"
                :key="b.filename"
                class="backup-item"
                @click="handleRestore(b)"
              >
                <div class="b-name">{{ b.filename }}</div>
                <div class="b-info">{{ b.size }} — {{ b.date }}</div>
              </div>
              <el-empty v-if="backups.length === 0" description="暂无备份" :image-size="40" />
            </div>
          </el-card>

          <el-card header="校验结果" shadow="never" size="small" style="margin-top: 12px">
            <div v-if="validateResult === null" style="color: #909399; font-size: 13px">
              点击「校验语法」检查配置
            </div>
            <el-alert v-else-if="validateResult.valid" type="success" title="配置语法正确 ✅" :closable="false" />
            <el-alert v-else type="error" title="配置语法错误" :description="validateResult.message" :closable="false" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useServerStore } from '@/stores/server'
import { configApi } from '@/api/config'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDateTime } from '@/utils/formatter'
import * as monaco from 'monaco-editor'

const serverStore = useServerStore()
const editorContainer = ref(null)
let editor = null

const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const loadingBackups = ref(false)
const backing = ref(false)
const configInfo = ref({ path: '', exists: false, content: '', last_modified: 0 })
const backups = ref([])
const validateResult = ref(null)

function fmt(ts) { return formatDateTime(new Date(ts).toISOString()) }

async function loadConfig() {
  loading.value = true
  try {
    const res = await configApi.get()
    configInfo.value = res.data
    if (editor && configInfo.value.content !== null) {
      editor.setValue(configInfo.value.content)
    }
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

async function loadBackups() {
  loadingBackups.value = true
  try {
    const res = await configApi.listBackups()
    backups.value = res.data.backups || []
  } catch { /* handled */ } finally {
    loadingBackups.value = false
  }
}

async function handleSave() {
  if (!editor) return
  const content = editor.getValue()
  saving.value = true
  try {
    const res = await configApi.update({ content })
    ElMessage.success(res.data.message || '保存成功')
    validateResult.value = null
    loadBackups()
  } catch {
    // testparm 错误消息会在响应中
  } finally {
    saving.value = false
  }
}

async function handleValidate() {
  if (!editor) return
  const content = editor.getValue()
  validating.value = true
  try {
    const res = await configApi.validate({ content })
    validateResult.value = res.data
  } catch { /* handled */ } finally {
    validating.value = false
  }
}

async function handleCreateBackup() {
  backing.value = true
  try {
    await configApi.createBackup()
    ElMessage.success('备份已创建')
    loadBackups()
  } catch { /* handled */ } finally {
    backing.value = false
  }
}

async function handleRestore(b) {
  try {
    await ElMessageBox.confirm(
      `确定恢复到 ${b.filename}？当前配置将被覆盖。`,
      '确认恢复',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
    await configApi.restoreBackup(b.filename)
    ElMessage.success('配置已恢复')
    loadConfig()
  } catch { /* cancelled */ }
}

function initEditor() {
  if (!editorContainer.value) return
  editor = monaco.editor.create(editorContainer.value, {
    value: '# 加载中...',
    language: 'ini',
    theme: 'vs-dark',
    fontSize: 14,
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    tabSize: 4,
    wordWrap: 'on',
  })
}

onMounted(async () => {
  await nextTick()
  initEditor()
  if (serverStore.selectedId) {
    await Promise.all([loadConfig(), loadBackups()])
  }
})

onBeforeUnmount(() => {
  editor?.dispose()
})
</script>

<style scoped>
.info-bar {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding: 10px 16px;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
}
.spacer { flex: 1; }

.editor-container {
  height: 100%;
  min-height: 400px;
  border-radius: 6px;
  overflow: hidden;
}
.backup-card .el-card__body {
  max-height: 300px;
  overflow-y: auto;
}
.backup-item {
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 4px;
  border: 1px solid #ebeef5;
  transition: background 0.2s;
}
.backup-item:hover { background: #ecf5ff; }
.b-name { font-size: 13px; font-weight: 500; word-break: break-all; }
.b-info { font-size: 11px; color: #909399; margin-top: 2px; }
</style>
