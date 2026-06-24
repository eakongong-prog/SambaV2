<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/servers')">
      <template #content>
        <h3>{{ isEdit ? '编辑服务器' : '添加服务器' }}</h3>
      </template>
    </el-page-header>

    <el-card style="max-width: 640px; margin: 20px 0">
      <el-form :model="form" ref="formRef" :rules="rules" label-width="100px" size="default">
        <el-form-item label="显示名称" prop="name">
          <el-input v-model="form.name" placeholder="如：公司Samba服务器" />
        </el-form-item>
        <el-form-item label="主机地址" prop="host">
          <el-input v-model="form.host" placeholder="IP 或域名" />
        </el-form-item>
        <el-form-item label="SSH 端口" prop="port">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="SSH 用户" prop="username">
          <el-input v-model="form.username" placeholder="如：root" />
        </el-form-item>
        <el-form-item label="认证方式" prop="auth_type">
          <el-radio-group v-model="form.auth_type">
            <el-radio label="password">密码</el-radio>
            <el-radio label="key">密钥文件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.auth_type === 'password'" label="SSH 密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="SSH 登录密码" />
        </el-form-item>
        <el-form-item v-else label="密钥路径" prop="key_path">
          <el-input v-model="form.key_path" placeholder="如：/home/user/.ssh/id_rsa" />
        </el-form-item>
        <el-form-item>
          <el-button @click="handleTest" :loading="testing">
            <el-icon><Connection /></el-icon> 测试连接
          </el-button>
          <el-button type="primary" @click="handleSave" :loading="saving">
            {{ isEdit ? '保存修改' : '添加服务器' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { serversApi } from '@/api/servers'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const isEdit = route.name === 'ServerEdit'
const formRef = ref(null)
const testing = ref(false)
const saving = ref(false)

const form = reactive({
  name: '',
  host: '',
  port: 22,
  username: 'root',
  auth_type: 'password',
  password: '',
  key_path: '',
})

const rules = {
  name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
  username: [{ required: true, message: '请输入SSH用户名', trigger: 'blur' }],
}

onMounted(async () => {
  if (!isEdit) return
  const id = route.params.id
  try {
    const res = await serversApi.get(id)
    Object.assign(form, {
      name: res.data.name,
      host: res.data.host,
      port: res.data.port,
      username: res.data.username,
      auth_type: res.data.auth_type,
      key_path: res.data.key_path || '',
      password: '',
    })
  } catch { /* interceptor handles */ }
})

async function handleTest() {
  testing.value = true
  try {
    // 先用当前表单数据创建临时连接测试（或使用保存后的 ID）
    // 如果已保存，用 ID 测试
    if (isEdit) {
      const res = await serversApi.testConnection(route.params.id)
      ElMessage[res.data.success ? 'success' : 'error'](res.data.message)
    } else {
      // 新建时先保存再测试
      const createRes = await serversApi.create({ ...form })
      const res = await serversApi.testConnection(createRes.data.id)
      ElMessage[res.data.success ? 'success' : 'error'](res.data.message)
      // 如果用户不想保存这个测试用的，可以删除
      if (!res.data.success) {
        await serversApi.delete(createRes.data.id)
      }
    }
  } catch { /* interceptor handles */ } finally {
    testing.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit) {
      await serversApi.update(route.params.id, { ...form })
      ElMessage.success('保存成功')
    } else {
      await serversApi.create({ ...form })
      ElMessage.success('添加成功')
    }
    router.push('/servers')
  } catch { /* interceptor handles */ } finally {
    saving.value = false
  }
}
</script>
