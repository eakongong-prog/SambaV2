<template>
  <div class="page-container">
    <div class="toolbar">
      <h2>用户管理</h2>
      <div class="spacer" />
      <el-input v-model="search" placeholder="搜索账号或姓名" style="width: 220px" clearable size="default" />
      <el-select v-model="filterGroup" placeholder="部门筛选" style="width: 160px" clearable size="default">
        <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
      </el-select>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新增用户
      </el-button>
      <el-button @click="showImport = true">
        <el-icon><Upload /></el-icon> 批量导入
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

    <el-table :data="filteredUsers" v-loading="loading" stripe style="width: 100%" :default-sort="{ prop: 'username', order: 'ascending' }">
      <el-table-column prop="username" label="账号" min-width="120" sortable />
      <el-table-column prop="full_name" label="全名" min-width="120" />
      <el-table-column prop="uid" label="UID" width="80" />
      <el-table-column label="主群组" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.groups" type="primary" size="small">{{ row.groups.split(',')[0] }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="groups" label="所属群组" min-width="200">
        <template #default="{ row }">
          <el-tag v-for="g in (row.groups || '').split(',').filter(Boolean)" :key="g" size="small" style="margin: 2px">{{ g }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.disabled ? 'danger' : 'success'" size="small" effect="dark">
            {{ row.disabled ? '禁用' : '启用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          <el-button link type="warning" size="small" @click="openResetPassword(row)">改密</el-button>
          <el-popconfirm title="确定删除此用户？此操作不可逆" @confirm="handleDelete(row.username)">
            <template #reference>
              <el-button link type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="showForm" :title="editing ? '编辑用户' : '新增用户'" width="520px" :close-on-click-modal="false" @closed="resetForm">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="拼音账号" prop="username">
          <el-input v-model="form.username" :disabled="editing" placeholder="如: zhangsan" />
        </el-form-item>
        <el-form-item label="全名" prop="full_name">
          <el-input v-model="form.full_name" placeholder="如: 张三" />
        </el-form-item>
        <el-form-item v-if="!editing" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="设置初始密码">
            <template #append>
              <el-button @click="form.password = randomPassword()">随机生成</el-button>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="主群组" prop="primary_group">
          <el-select v-model="form.primary_group" style="width: 100%">
            <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item label="附加群组">
          <el-select v-model="form.additional_groups" multiple style="width: 100%" placeholder="无附加群组">
            <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editing ? '保存修改' : '创建用户' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 改密弹窗 -->
    <el-dialog v-model="showPassword" title="重置密码" width="400px">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.password" type="password" show-password>
            <template #append>
              <el-button @click="pwdForm.password = randomPassword()">随机生成</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPassword = false">取消</el-button>
        <el-button type="primary" @click="handleResetPassword">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入弹窗 -->
    <el-dialog v-model="showImport" title="批量导入用户" width="600px">
      <el-alert type="info" title="每行一个用户，格式：账号,密码,全名,主群组" :closable="false" style="margin-bottom: 12px" />
      <el-input v-model="importText" type="textarea" :rows="8" placeholder="zhangsan,Pass123,张三,smb_export&#10;lisi,Pass456,李四,smb_market" />
      <template #footer>
        <el-button @click="showImport = false">取消</el-button>
        <el-button type="primary" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { useServerStore } from '@/stores/server'
import { usersApi } from '@/api/users'
import { ElMessage } from 'element-plus'

const serverStore = useServerStore()
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const filterGroup = ref('')
const users = ref([])
const showForm = ref(false)
const showPassword = ref(false)
const showImport = ref(false)
const importText = ref('')
const editing = ref(false)
const formRef = ref(null)

const groups = ['smb_public', 'smb_general', 'smb_export', 'smb_market', 'smb_rnd', 'smb_purchase', 'smb_finance', 'smb_admin', 'smb_it']

const form = reactive({
  username: '',
  full_name: '',
  password: '',
  primary_group: 'smb_public',
  additional_groups: [],
})
const formRules = {
  username: [{ required: true, message: '请输入拼音账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const pwdForm = reactive({ username: '', password: '' })

const filteredUsers = computed(() => {
  let list = users.value
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(u => u.username.toLowerCase().includes(q) || (u.full_name || '').toLowerCase().includes(q))
  }
  if (filterGroup.value) {
    list = list.filter(u => (u.groups || '').includes(filterGroup.value))
  }
  return list
})

async function loadUsers() {
  if (!serverStore.selectedId) return
  loading.value = true
  try {
    const res = await usersApi.list()
    users.value = res.data.users || []
  } catch { /* handled */ } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = false
  resetForm()
  showForm.value = true
}

function openEdit(row) {
  editing.value = true
  form.username = row.username
  form.full_name = row.full_name || ''
  form.primary_group = (row.groups || '').split(',')[0] || 'smb_public'
  form.additional_groups = (row.groups || '').split(',').filter(Boolean).slice(1)
  form.password = '********'
  showForm.value = true
}

function resetForm() {
  form.username = ''
  form.full_name = ''
  form.password = ''
  form.primary_group = 'smb_public'
  form.additional_groups = []
}

function openResetPassword(row) {
  pwdForm.username = row.username
  pwdForm.password = ''
  showPassword.value = true
}

function randomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let pwd = ''
  for (let i = 0; i < 12; i++) pwd += chars[Math.floor(Math.random() * chars.length)]
  return pwd
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editing.value) {
      await usersApi.update(form.username, {
        full_name: form.full_name,
        primary_group: form.primary_group,
        additional_groups: form.additional_groups,
      })
      ElMessage.success('更新成功')
    } else {
      await usersApi.create({ ...form })
      ElMessage.success('创建成功')
    }
    showForm.value = false
    loadUsers()
  } catch { /* handled */ } finally {
    saving.value = false
  }
}

async function handleDelete(username) {
  try {
    await usersApi.delete(username)
    ElMessage.success('已删除')
    loadUsers()
  } catch { /* handled */ }
}

async function handleResetPassword() {
  if (!pwdForm.password) return ElMessage.warning('请输入新密码')
  try {
    await usersApi.resetPassword(pwdForm.username, pwdForm.password)
    ElMessage.success('密码已重置')
    showPassword.value = false
  } catch { /* handled */ }
}

async function handleImport() {
  if (!importText.value.trim()) return
  const parsed = []
  for (const line of importText.value.trim().split('\n')) {
    const parts = line.split(',').map(s => s.trim())
    if (parts.length >= 2) {
      parsed.push({
        username: parts[0],
        password: parts[1],
        full_name: parts[2] || '',
        primary_group: parts[3] || 'smb_public',
        additional_groups: [],
      })
    }
  }
  if (parsed.length === 0) return ElMessage.warning('无有效数据')
  try {
    const res = await usersApi.batchImport({ users: parsed })
    ElMessage.success(`导入完成：成功 ${res.data.created.length}，失败 ${res.data.failed.length}`)
    showImport.value = false
    importText.value = ''
    loadUsers()
  } catch { /* handled */ }
}

onMounted(loadUsers)
</script>
