<template>
  <div class="page-container">
    <div class="toolbar">
      <h2>群组管理</h2>
      <div class="spacer" />
      <el-button type="primary" @click="showAdd = true">
        <el-icon><Plus /></el-icon> 新增群组
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
    <el-row :gutter="16" v-loading="loading" v-if="serverStore.selectedId">
      <!-- 左侧群组列表 -->
      <el-col :span="6">
        <el-card header="群组列表" shadow="never">
          <div v-for="g in groups" :key="g.name" class="group-item" :class="{ active: selectedGroup?.name === g.name }" @click="selectGroup(g)">
            <div class="group-name">{{ g.name }}</div>
            <div class="group-count">{{ g.member_count }} 人</div>
          </div>
          <el-empty v-if="groups.length === 0" description="暂无群组" :image-size="60" />
        </el-card>
      </el-col>
      <!-- 右侧成员 -->
      <el-col :span="18">
        <el-card v-if="selectedGroup" shadow="never">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between">
              <span>{{ selectedGroup.name }} — 成员 ({{ selectedGroup.members?.length || 0 }}人)</span>
              <div>
                <el-button size="small" @click="showAddMember = true">
                  <el-icon><Plus /></el-icon> 添加成员
                </el-button>
                <el-popconfirm title="确定删除此群组？" @confirm="handleDeleteGroup">
                  <template #reference>
                    <el-button size="small" type="danger">
                      <el-icon><Delete /></el-icon> 删除群组
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </template>
          <el-table :data="selectedGroup.member_details || []" stripe size="small">
            <el-table-column prop="username" label="账号" />
            <el-table-column prop="full_name" label="全名" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-popconfirm title="从群组中移除此成员？" @confirm="removeMember(row.username)">
                  <template #reference>
                    <el-button link type="danger" size="small">移出</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        <el-empty v-else description="请选择一个群组" :image-size="80" style="margin-top: 60px" />
      </el-col>
    </el-row>

    <!-- 新增群组弹窗 -->
    <el-dialog v-model="showAdd" title="新增群组" width="400px">
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="群组名称">
          <el-input v-model="addForm.name" placeholder="如: smb_design" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" @click="handleAddGroup">创建</el-button>
      </template>
    </el-dialog>

    <!-- 添加成员弹窗 -->
    <el-dialog v-model="showAddMember" title="添加成员" width="500px">
      <el-select v-model="addMembers" multiple filterable placeholder="搜索用户..." style="width: 100%">
        <el-option v-for="u in allUsers" :key="u.username" :label="`${u.username} (${u.full_name})`" :value="u.username" />
      </el-select>
      <template #footer>
        <el-button @click="showAddMember = false">取消</el-button>
        <el-button type="primary" @click="handleAddMembers">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useServerStore } from '@/stores/server'
import { groupsApi } from '@/api/groups'
import { usersApi } from '@/api/users'
import { ElMessage } from 'element-plus'

const serverStore = useServerStore()
const loading = ref(false)
const groups = ref([])
const selectedGroup = ref(null)
const showAdd = ref(false)
const showAddMember = ref(false)
const addForm = ref({ name: '' })
const addMembers = ref([])
const allUsers = ref([])

async function loadGroups() {
  loading.value = true
  try {
    const res = await groupsApi.list()
    groups.value = res.data.groups || []
    // 保持选中状态
    if (selectedGroup.value) {
      const refreshed = groups.value.find(g => g.name === selectedGroup.value.name)
      if (refreshed) selectGroup(refreshed, false)
    }
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

async function selectGroup(g, reload = true) {
  if (reload) {
    try {
      const res = await groupsApi.get(g.name)
      selectedGroup.value = res.data
    } catch { /* handled */ }
  } else {
    selectedGroup.value = g
  }
}

async function loadAllUsers() {
  try {
    const res = await usersApi.list()
    allUsers.value = res.data.users || []
  } catch { /* handled */ }
}

async function handleAddGroup() {
  if (!addForm.value.name) return ElMessage.warning('请输入群组名称')
  try {
    await groupsApi.create({ name: addForm.value.name })
    ElMessage.success('群组已创建')
    showAdd.value = false
    addForm.value.name = ''
    loadGroups()
  } catch { /* handled */ }
}

async function handleDeleteGroup() {
  try {
    await groupsApi.delete(selectedGroup.value.name)
    ElMessage.success('已删除')
    selectedGroup.value = null
    loadGroups()
  } catch { /* handled */ }
}

async function handleAddMembers() {
  if (addMembers.value.length === 0) return
  const current = selectedGroup.value.members || []
  const all = [...new Set([...current, ...addMembers.value])]
  try {
    await groupsApi.updateMembers(selectedGroup.value.name, all)
    ElMessage.success('成员已添加')
    showAddMember.value = false
    addMembers.value = []
    selectGroup(selectedGroup.value, true)
  } catch { /* handled */ }
}

async function removeMember(username) {
  const current = (selectedGroup.value.members || []).filter(m => m !== username)
  try {
    await groupsApi.updateMembers(selectedGroup.value.name, current)
    ElMessage.success('已移出')
    selectGroup(selectedGroup.value, true)
  } catch { /* handled */ }
}

onMounted(() => {
  loadGroups()
  loadAllUsers()
})
</script>

<style scoped>
.group-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  transition: background 0.2s;
}
.group-item:hover { background: #f0f2f5; }
.group-item.active { background: #ecf5ff; color: var(--primary-color); }
.group-name { font-weight: 500; }
.group-count { font-size: 12px; color: #909399; }
</style>
