<template>
  <div class="page-container">
    <el-page-header @back="$router.push('/users')">
      <template #content><h3>{{ isEdit ? '编辑用户' : '新增用户' }}</h3></template>
    </el-page-header>

    <el-card style="max-width: 600px; margin: 20px 0">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="拼音账号" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" placeholder="如: zhangsan" />
        </el-form-item>
        <el-form-item label="全名" prop="full_name">
          <el-input v-model="form.full_name" placeholder="如: 张三" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
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
          <el-select v-model="form.additional_groups" multiple style="width: 100%" placeholder="无">
            <el-option v-for="g in groups" :key="g" :label="g" :value="g" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ isEdit ? '保存修改' : '创建用户' }}
          </el-button>
          <el-button @click="$router.push('/users')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usersApi } from '@/api/users'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const isEdit = route.name === 'UserEdit'
const formRef = ref(null)
const saving = ref(false)

const groups = ['smb_public', 'smb_general', 'smb_export', 'smb_market', 'smb_rnd', 'smb_purchase', 'smb_finance', 'smb_admin', 'smb_it']

const form = reactive({
  username: '',
  full_name: '',
  password: '',
  primary_group: 'smb_public',
  additional_groups: [],
})

const rules = {
  username: [{ required: true, message: '请输入拼音账号', trigger: 'blur' }],
  password: isEdit ? [] : [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function randomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
  let pwd = ''
  for (let i = 0; i < 12; i++) pwd += chars[Math.floor(Math.random() * chars.length)]
  return pwd
}

onMounted(async () => {
  if (!isEdit) return
  try {
    const res = await usersApi.get(route.params.name)
    const u = res.data
    form.username = u.username
    form.full_name = u.full_name || ''
    form.password = '********'
    form.primary_group = (u.groups || '').split(',')[0] || 'smb_public'
    form.additional_groups = (u.groups || '').split(',').filter(Boolean).slice(1)
  } catch { /* handled */ }
})

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit) {
      await usersApi.update(form.username, {
        full_name: form.full_name,
        primary_group: form.primary_group,
        additional_groups: form.additional_groups,
      })
      ElMessage.success('修改已保存')
    } else {
      await usersApi.create({ ...form })
      ElMessage.success('用户创建成功')
    }
    router.push('/users')
  } catch { /* handled */ } finally {
    saving.value = false
  }
}
</script>
