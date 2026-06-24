<template>
  <div class="page-container">
    <h2 style="margin-bottom: 20px">权限管理</h2>
    <el-alert
      v-if="!serverStore.selectedId"
      type="warning"
      title="请先在顶部选择一台 Samba 服务器"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    />

    <template v-if="serverStore.selectedId">
      <!-- 顶部：共享选择 -->
      <div class="toolbar" style="margin-bottom: 16px">
        <el-select v-model="selectedShare" placeholder="选择共享" style="width: 220px" @change="handleShareChange">
          <el-option v-for="s in shares" :key="s.name" :label="s.name" :value="s.name" />
        </el-select>
        <!-- 面包屑 -->
        <el-breadcrumb v-if="breadcrumbs.length" separator="/" style="margin-left: 16px">
          <el-breadcrumb-item @click="navigateTo('')">
            <el-icon><HomeFilled /></el-icon>
          </el-breadcrumb-item>
          <el-breadcrumb-item v-for="(crumb, i) in breadcrumbs" :key="i" @click="navigateTo(crumb.path)">
            {{ crumb.name }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>

      <el-row :gutter="16" v-if="selectedShare" style="height: calc(100vh - 240px)">
        <!-- 左侧：目录浏览 -->
        <el-col :span="8">
          <el-card shadow="never" class="dir-card">
            <template #header><span>目录浏览</span></template>
            <div v-loading="loadingTree">
              <div
                v-for="item in directoryItems"
                :key="item.path"
                class="dir-item"
                :class="{ active: currentPath === item.path }"
                @click="selectItem(item)"
              >
                <el-icon :size="18" :color="item.is_dir ? '#e6a23c' : '#909399'">
                  <Folder v-if="item.is_dir" />
                  <Document v-else />
                </el-icon>
                <span class="dir-name">{{ item.name }}</span>
                <span v-if="!item.is_dir" class="dir-size">{{ item.size }}</span>
              </div>
              <el-empty v-if="directoryItems.length === 0 && !loadingTree" description="目录为空" :image-size="50" />
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：ACL 详情 -->
        <el-col :span="16">
          <el-card shadow="never" v-loading="loadingAcl">
            <template #header>
              <div style="display: flex; align-items: center; justify-content: space-between">
                <span>ACL 详情 — {{ currentPath || '/' }}</span>
                <el-button size="small" @click="loadAcl" :loading="loadingAcl">刷新</el-button>
              </div>
            </template>

            <template v-if="aclData">
              <!-- 基本信息 -->
              <div class="acl-summary">
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item label="所有者">{{ aclData.owner }}</el-descriptions-item>
                  <el-descriptions-item label="所属组">{{ aclData.group }}</el-descriptions-item>
                  <el-descriptions-item label="权限码">{{ aclData.octal_mode }}</el-descriptions-item>
                </el-descriptions>
              </div>

              <!-- ACL 条目 -->
              <div v-if="aclData.entries.length" style="margin-top: 16px">
                <h4>访问 ACL</h4>
                <el-table :data="aclData.entries" size="small" stripe>
                  <el-table-column label="类型" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.type === 'user' ? 'primary' : row.type === 'group' ? 'success' : 'info'" size="small">
                        {{ row.type === 'user' ? '用户' : row.type === 'group' ? '群组' : row.type === 'mask' ? '掩码' : '其他' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="name" label="名称" width="140" />
                  <el-table-column label="读" width="60" align="center">
                    <template #default="{ row }">
                      <el-icon v-if="row.read" color="#67c23a"><Check /></el-icon>
                      <el-icon v-else color="#dcdfe6"><Close /></el-icon>
                    </template>
                  </el-table-column>
                  <el-table-column label="写" width="60" align="center">
                    <template #default="{ row }">
                      <el-icon v-if="row.write" color="#67c23a"><Check /></el-icon>
                      <el-icon v-else color="#dcdfe6"><Close /></el-icon>
                    </template>
                  </el-table-column>
                  <el-table-column label="执行" width="60" align="center">
                    <template #default="{ row }">
                      <el-icon v-if="row.execute" color="#67c23a"><Check /></el-icon>
                      <el-icon v-else color="#dcdfe6"><Close /></el-icon>
                    </template>
                  </el-table-column>
                </el-table>
              </div>

              <!-- Default ACL -->
              <div v-if="aclData.default_entries.length" style="margin-top: 16px">
                <h4>默认 ACL（继承规则）</h4>
                <el-table :data="aclData.default_entries" size="small" stripe>
                  <el-table-column label="类型" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.type === 'user' ? 'primary' : row.type === 'group' ? 'success' : 'info'" size="small">
                        {{ row.type === 'user' ? '用户' : row.type === 'group' ? '群组' : '其他' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="name" label="名称" width="140" />
                  <el-table-column prop="permissions" label="权限" width="80" />
                </el-table>
              </div>

              <!-- 添加 ACL 条目 -->
              <div style="margin-top: 16px">
                <h4>添加 ACL 条目</h4>
                <el-form :inline="true" size="small">
                  <el-form-item label="类型">
                    <el-select v-model="newEntry.type" style="width: 90px">
                      <el-option label="用户" value="user" />
                      <el-option label="群组" value="group" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="名称">
                    <el-input v-model="newEntry.name" placeholder="用户名/组名" style="width: 140px" />
                  </el-form-item>
                  <el-form-item label="权限">
                    <el-checkbox-group v-model="newEntry.perms">
                      <el-checkbox label="r">读</el-checkbox>
                      <el-checkbox label="w">写</el-checkbox>
                      <el-checkbox label="x">执行</el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                  <el-form-item>
                    <el-checkbox v-model="newEntry.recursive">递归子目录</el-checkbox>
                  </el-form-item>
                  <el-form-item>
                    <el-button type="primary" @click="handleAddEntry" :loading="setting">添加</el-button>
                  </el-form-item>
                </el-form>
              </div>

              <!-- 预设模板 -->
              <div style="margin-top: 16px">
                <h4>预设模板</h4>
                <el-space>
                  <el-popconfirm title="将应用「私有模式」：创建者独占，其他人无权。确定？" @confirm="handleTemplate('private')">
                    <template #reference>
                      <el-button type="danger" size="small" :loading="setting">🔒 私有模式</el-button>
                    </template>
                  </el-popconfirm>
                  <el-popconfirm title="将应用「协作模式」：部门内可读写。确定？" @confirm="handleTemplate('collaborative')">
                    <template #reference>
                      <el-button type="warning" size="small" :loading="setting">👥 协作模式</el-button>
                    </template>
                  </el-popconfirm>
                  <el-popconfirm title="将应用「公开模式」：所有人可读。确定？" @confirm="handleTemplate('public')">
                    <template #reference>
                      <el-button type="success" size="small" :loading="setting">🌍 公开模式</el-button>
                    </template>
                  </el-popconfirm>
                </el-space>
              </div>
            </template>

            <el-empty v-else-if="!loadingAcl" description="请选择左侧目录查看 ACL" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useServerStore } from '@/stores/server'
import { sharesApi } from '@/api/shares'
import { permissionsApi } from '@/api/permissions'
import { ElMessage } from 'element-plus'

const route = useRoute()
const serverStore = useServerStore()

const shares = ref([])
const selectedShare = ref('')
const currentPath = ref('')
const directoryItems = ref([])
const aclData = ref(null)
const loadingTree = ref(false)
const loadingAcl = ref(false)
const setting = ref(false)

const newEntry = reactive({
  type: 'user',
  name: '',
  perms: ['r', 'w', 'x'],
  recursive: false,
})

const breadcrumbs = computed(() => {
  if (!currentPath.value) return []
  return currentPath.value.split('/').filter(Boolean).map((name, i, arr) => ({
    name,
    path: arr.slice(0, i + 1).join('/'),
  }))
})

// 从 URL query 预选共享
onMounted(async () => {
  if (route.query.share) {
    selectedShare.value = route.query.share
  }
  await loadShares()
  if (selectedShare.value) {
    loadTree()
  }
})

async function loadShares() {
  try {
    const res = await sharesApi.list()
    shares.value = res.data.shares || []
  } catch { /* handled */ }
}

function handleShareChange() {
  currentPath.value = ''
  aclData.value = null
  loadTree()
}

async function loadTree() {
  loadingTree.value = true
  try {
    const res = await permissionsApi.tree(selectedShare.value, currentPath.value)
    directoryItems.value = (res.data.items || []).filter(i => i.is_dir)
  } catch { /* handled */ } finally {
    loadingTree.value = false
  }
}

async function loadAcl() {
  if (!selectedShare.value) return
  loadingAcl.value = true
  try {
    const res = await permissionsApi.getAcl(selectedShare.value, currentPath.value)
    aclData.value = res.data
  } catch { /* handled */ } finally {
    loadingAcl.value = false
  }
}

function selectItem(item) {
  if (item.is_dir) {
    currentPath.value = item.path
    loadTree()
    loadAcl()
  } else {
    // 文件：直接查看 ACL
    currentPath.value = item.path
    loadAcl()
  }
}

function navigateTo(path) {
  currentPath.value = path
  loadTree()
  if (path || selectedShare.value) loadAcl()
}

async function handleAddEntry() {
  if (!newEntry.name) return ElMessage.warning('请输入用户名或组名')
  setting.value = true
  try {
    const perms = (newEntry.perms.includes('r') ? 'r' : '') +
                  (newEntry.perms.includes('w') ? 'w' : '') +
                  (newEntry.perms.includes('x') ? 'x' : '') || '---'

    await permissionsApi.updateAcl({
      share: selectedShare.value,
      path: currentPath.value,
      entries: [{ type: newEntry.type, name: newEntry.name, permissions: perms, default: false }],
      recursive: newEntry.recursive,
    })
    ElMessage.success('ACL 条目已添加')
    loadAcl()
  } catch { /* handled */ } finally {
    setting.value = false
  }
}

async function handleTemplate(template) {
  setting.value = true
  try {
    await permissionsApi.applyTemplate({
      share: selectedShare.value,
      template,
      group_name: '',
      recursive: true,
    })
    ElMessage.success('模板已应用')
    loadAcl()
  } catch { /* handled */ } finally {
    setting.value = false
  }
}
</script>

<style scoped>
.dir-card :deep(.el-card__body) {
  max-height: calc(100vh - 320px);
  overflow-y: auto;
}
.dir-item {
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
  transition: background 0.15s;
}
.dir-item:hover { background: #f0f2f5; }
.dir-item.active { background: #ecf5ff; }
.dir-name { flex: 1; font-size: 13px; }
.dir-size { font-size: 12px; color: #909399; }
.acl-summary { margin-bottom: 12px; }
h4 { font-size: 14px; color: #303133; margin-bottom: 8px; }
</style>
